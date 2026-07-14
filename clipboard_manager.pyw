"""
Clipboard Manager for Windows — Final Version
===============================================
Stores the last 3 copies. Press Ctrl+Shift+V to open picker.
Zero nested mainloops. Robust paste via ALT trick + focus verify.
"""

import ctypes
import ctypes.wintypes as wintypes
import time
import tkinter as tk
from tkinter import font as tkfont
import sys
import os

# ══════════════════════════════════════════════════════════════
# Configuration
# ══════════════════════════════════════════════════════════════
MAX_ENTRIES     = 3
POLL_MS         = 50
HOTKEY_COOLDOWN = 1200
POST_PICK_DELAY = 500

# ══════════════════════════════════════════════════════════════
# Windows API Setup
# ══════════════════════════════════════════════════════════════
user32   = ctypes.windll.user32
kernel32 = ctypes.windll.kernel32

CF_UNICODETEXT = 13
GHND = 0x0042

VK_CONTROL = 0x11
VK_SHIFT   = 0x10
VK_V       = 0x56
VK_MENU    = 0x12  # ALT key

KEYEVENTF_KEYUP       = 0x0002
KEYEVENTF_EXTENDEDKEY = 0x0001
KEYEVENTF_SCANCODE    = 0x0004

INPUT_KEYBOARD = 1


class KEYBDINPUT(ctypes.Structure):
    _fields_ = [
        ("wVk", wintypes.WORD), ("wScan", wintypes.WORD),
        ("dwFlags", wintypes.DWORD), ("time", wintypes.DWORD),
        ("dwExtraInfo", ctypes.c_void_p),
    ]

class MOUSEINPUT(ctypes.Structure):
    _fields_ = [
        ("dx", ctypes.c_long), ("dy", ctypes.c_long),
        ("mouseData", wintypes.DWORD), ("dwFlags", wintypes.DWORD),
        ("time", wintypes.DWORD), ("dwExtraInfo", ctypes.c_void_p),
    ]

class _INPUT_UNION(ctypes.Union):
    _fields_ = [("ki", KEYBDINPUT), ("mi", MOUSEINPUT)]

class INPUT(ctypes.Structure):
    _fields_ = [("type", wintypes.DWORD), ("union", _INPUT_UNION)]


# 64-bit pointer fixes
kernel32.GlobalAlloc.restype   = ctypes.c_void_p
kernel32.GlobalAlloc.argtypes  = [ctypes.c_uint, ctypes.c_size_t]
kernel32.GlobalLock.restype    = ctypes.c_void_p
kernel32.GlobalLock.argtypes   = [ctypes.c_void_p]
kernel32.GlobalUnlock.argtypes = [ctypes.c_void_p]
user32.GetClipboardData.restype  = ctypes.c_void_p
user32.GetClipboardData.argtypes = [ctypes.c_uint]
user32.SetClipboardData.restype  = ctypes.c_void_p
user32.SetClipboardData.argtypes = [ctypes.c_uint, ctypes.c_void_p]
user32.SendInput.restype  = ctypes.c_uint
user32.SendInput.argtypes = [ctypes.c_uint, ctypes.c_void_p, ctypes.c_int]
user32.GetForegroundWindow.restype  = ctypes.c_void_p
user32.SetForegroundWindow.argtypes = [ctypes.c_void_p]
user32.keybd_event.argtypes = [
    ctypes.c_ubyte, ctypes.c_ubyte, ctypes.c_ulong, ctypes.c_void_p
]
user32.ShowWindow.argtypes = [ctypes.c_void_p, ctypes.c_int]
user32.PostMessageW.argtypes = [ctypes.c_void_p, ctypes.c_uint, ctypes.c_void_p, ctypes.c_void_p]
user32.GetWindowThreadProcessId.argtypes = [ctypes.c_void_p, ctypes.c_void_p]
user32.GetWindowThreadProcessId.restype = wintypes.DWORD
user32.AttachThreadInput.argtypes = [wintypes.DWORD, wintypes.DWORD, wintypes.BOOL]
kernel32.GetCurrentThreadId.restype = wintypes.DWORD
user32.SetWindowPos.argtypes = [ctypes.c_void_p, ctypes.c_void_p, ctypes.c_int, ctypes.c_int, ctypes.c_int, ctypes.c_int, ctypes.c_uint]
user32.BringWindowToTop.argtypes = [ctypes.c_void_p]


# ══════════════════════════════════════════════════════════════
# Debug Log
# ══════════════════════════════════════════════════════════════
LOG_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "debug.log")

def log(msg):
    try:
        with open(LOG_FILE, "a", encoding="utf-8") as f:
            f.write(f"[{time.strftime('%H:%M:%S')}] {msg}\n")
    except:
        pass


# ══════════════════════════════════════════════════════════════
# Clipboard Helpers
# ══════════════════════════════════════════════════════════════
def clip_get():
    """Read clipboard text. Returns str or None."""
    try:
        if not user32.OpenClipboard(0):
            return None
        try:
            h = user32.GetClipboardData(CF_UNICODETEXT)
            if not h:
                return None
            p = kernel32.GlobalLock(h)
            if not p:
                return None
            try:
                return ctypes.c_wchar_p(p).value
            finally:
                kernel32.GlobalUnlock(h)
        finally:
            user32.CloseClipboard()
    except Exception as e:
        log(f"clip_get ERR: {e}")
        return None


def clip_set(text):
    """Write text to clipboard. Returns bool."""
    try:
        if not user32.OpenClipboard(0):
            return False
        try:
            user32.EmptyClipboard()
            raw = text.encode("utf-16-le") + b"\x00\x00"
            h = kernel32.GlobalAlloc(GHND, len(raw))
            if not h:
                return False
            p = kernel32.GlobalLock(h)
            if not p:
                return False
            ctypes.memmove(p, raw, len(raw))
            kernel32.GlobalUnlock(h)
            user32.SetClipboardData(CF_UNICODETEXT, h)
            return True
        finally:
            user32.CloseClipboard()
    except Exception as e:
        log(f"clip_set ERR: {e}")
        return False


def is_key_pressed(vk):
    return bool(user32.GetAsyncKeyState(vk) & 0x8000)


# ══════════════════════════════════════════════════════════════
# History
# ══════════════════════════════════════════════════════════════
class History:
    def __init__(self):
        self.items = []
        self._prev = None

    def poll(self):
        """Check clipboard for new content. Returns True if changed."""
        txt = clip_get()
        if txt is None or txt == self._prev:
            return False
        self._prev = txt
        # Move to front if exists, otherwise insert
        if txt in self.items:
            self.items.remove(txt)
        self.items.insert(0, txt)
        self.items = self.items[:MAX_ENTRIES]
        log(f"Clip: {repr(txt[:50])} | {len(self.items)} items")
        return True

    def get(self, idx):
        """Get item by index (no side effects)."""
        if 0 <= idx < len(self.items):
            return self.items[idx]
        return None


# ══════════════════════════════════════════════════════════════
# Picker Window — Clean Apple-like dark UI
# ══════════════════════════════════════════════════════════════
class PickerWindow:
    BG       = "#1C1C1E"
    ITEM_BG  = "#2C2C2E"
    HOVER_BG = "#48484A"
    FG       = "#FFFFFF"
    FG_DIM   = "#8E8E93"
    FG_BLUE  = "#0A84FF"
    SEP      = "#38383A"
    MAX_LEN  = 55

    def __init__(self, history, root, on_select):
        self.history = history
        self.root = root
        self.on_select = on_select
        self.win = None
        self._widgets = []
        self._sel = 0
        self._ready = False

    def open(self):
        entries = self.history.items
        if not entries:
            self.on_select(None)
            return

        win = tk.Toplevel(self.root)
        self.win = win
        win.overrideredirect(True)
        win.attributes("-topmost", True)
        win.attributes("-alpha", 0.97)
        win.configure(bg=self.BG)

        # Rounded corners via border radius illusion (small border)
        win.configure(highlightthickness=1, highlightbackground="#555555")

        title_f  = tkfont.Font(family="Segoe UI", size=11, weight="bold")
        item_f   = tkfont.Font(family="Segoe UI", size=9)
        num_f    = tkfont.Font(family="Segoe UI", size=9, weight="bold")
        hint_f   = tkfont.Font(family="Segoe UI", size=8)
        sep_font = tkfont.Font(family="Segoe UI", size=8)

        outer = tk.Frame(win, bg=self.BG)
        outer.pack(fill="both", expand=True, padx=1, pady=1)

        # ── Title ──
        title_frame = tk.Frame(outer, bg=self.BG)
        title_frame.pack(fill="x", padx=10, pady=(8, 2))

        tk.Label(title_frame, text="📋", font=title_f,
                 bg=self.BG).pack(side="left", padx=(4, 4))
        tk.Label(title_frame, text="Clipboard", font=title_f,
                 fg=self.FG, bg=self.BG).pack(side="left")

        tk.Label(title_frame, text=str(len(entries)), font=hint_f,
                 fg=self.FG_DIM, bg=self.BG).pack(side="right", padx=(0, 4))

        # ── Separator thin ──
        tk.Frame(outer, bg=self.SEP, height=1).pack(fill="x", padx=10, pady=(2, 4))

        # ── Items ──
        inner = tk.Frame(outer, bg=self.BG)
        inner.pack(fill="x", padx=4)

        self._widgets = []
        for i, txt in enumerate(entries):
            preview = txt.replace("\r\n", " ").replace("\n", " ").replace("\t", " ")
            preview = " ".join(preview.split())[:self.MAX_LEN]
            if len(txt) > self.MAX_LEN:
                preview += "…"

            row = tk.Frame(inner, bg=self.ITEM_BG, cursor="hand2",
                           highlightthickness=0)
            row.pack(fill="x", padx=2, pady=1)
            self._widgets.append(row)

            # Number & dot
            tk.Label(row, text=str(i + 1), font=num_f,
                     fg=self.FG_BLUE, bg=self.ITEM_BG, width=2,
                     anchor="e").pack(side="left", padx=(8, 2), pady=5)
            tk.Label(row, text="·", font=sep_font,
                     fg=self.FG_DIM, bg=self.ITEM_BG).pack(side="left", padx=(0, 4))

            # Text
            tk.Label(row, text=preview, font=item_f,
                     fg=self.FG, bg=self.ITEM_BG, anchor="w"
                     ).pack(side="left", fill="x", expand=True, pady=5)

            # Char count (compact)
            tk.Label(row, text=str(len(txt)), font=hint_f,
                     fg=self.FG_DIM, bg=self.ITEM_BG
                     ).pack(side="right", padx=(0, 8), pady=5)

            for w in (row,):
                w.bind("<Button-1>", self._click(i))
                w.bind("<Enter>", self._enter(i))
                w.bind("<Leave>", self._leave(i))

        # ── Hints bar ──
        tk.Frame(outer, bg=self.SEP, height=1).pack(fill="x", padx=10, pady=(4, 3))
        hints = tk.Frame(outer, bg=self.BG)
        hints.pack(fill="x", padx=10, pady=(0, 8))
        for key, desc in [("↑↓", "Nav"), ("⏎", "Paste"), ("1-3", "Pick"), ("Esc", "X")]:
            cell = tk.Frame(hints, bg=self.BG)
            cell.pack(side="left", padx=(0, 8))
            tk.Label(cell, text=key, font=hint_f, fg=self.FG_BLUE, bg=self.BG,
                     relief="solid", bd=0, padx=3, pady=0,
                     highlightthickness=0).pack(side="left", padx=(0, 2))
            tk.Label(cell, text=desc, font=hint_f,
                     fg=self.FG_DIM, bg=self.BG).pack(side="left")

        # ── Size ──
        win.update_idletasks()
        w = max(win.winfo_reqwidth(), 270)
        h = win.winfo_reqheight()
        win.geometry(f"{w}x{h}+0+0")
        win.update_idletasks()

        # ── Position near cursor (offset to right-down) ──
        pt = wintypes.POINT()
        user32.GetCursorPos(ctypes.byref(pt))
        x, y = pt.x + 12, pt.y + 12
        sw = user32.GetSystemMetrics(0)
        sh = user32.GetSystemMetrics(1)
        if x + w > sw - 10: x = pt.x - w - 12
        if y + h > sh - 10: y = pt.y - h - 12
        if x < 10: x = 10
        if y < 10: y = 10
        win.geometry(f"+{x}+{y}")

        # ── Keyboard ──
        win.bind("<Up>",     lambda e: self._move(-1))
        win.bind("<Down>",   lambda e: self._move(1))
        win.bind("<Return>", lambda e: self._pick())
        win.bind("<Escape>", lambda e: self._cancel())
        for k in range(1, min(4, len(entries) + 1)):
            win.bind(str(k), self._num(k - 1))

        self._hl()
        win.after(200, self._activate)
        log(f"Picker: {len(entries)} items")

    def _activate(self):
        if self.win and self.win.winfo_exists():
            self.win.focus_force()
            self.win.grab_set()
            self._ready = True
            self._hl()
            log("Picker ready")

    def _click(self, i):
        def h(e):
            if self._ready:
                self._sel_idx(i)
        return h

    def _enter(self, i):
        def h(e):
            if i < len(self._widgets):
                self._set_bg(i, self.HOVER_BG)
        return h

    def _leave(self, i):
        def h(e):
            if i < len(self._widgets):
                bg = self.HOVER_BG if i == self._sel else self.ITEM_BG
                self._set_bg(i, bg)
        return h

    def _num(self, i):
        def h(e):
            if self._ready:
                self._sel_idx(i)
        return h

    def _move(self, d):
        if not self._ready or not self._widgets:
            return
        self._sel = (self._sel + d) % len(self._widgets)
        self._hl()

    def _set_bg(self, i, color):
        if i < len(self._widgets):
            w = self._widgets[i]
            w.configure(bg=color)
            for c in w.winfo_children():
                try:
                    c.configure(bg=color)
                except:
                    pass

    def _hl(self):
        for i, w in enumerate(self._widgets):
            bg = self.HOVER_BG if i == self._sel else self.ITEM_BG
            self._set_bg(i, bg)

    def _sel_idx(self, i):
        if not self._ready:
            return
        log(f"Selected: {i}")
        self._close()
        self.on_select(i)

    def _pick(self):
        if self._widgets:
            self._sel_idx(self._sel)

    def _cancel(self):
        log("Cancelled")
        self._close()
        self.on_select(None)

    def _close(self):
        self._ready = False
        if self.win and self.win.winfo_exists():
            try:
                self.win.grab_release()
            except:
                pass
            self.win.destroy()
        self.win = None
        log("Picker closed")

    def is_open(self):
        return self.win is not None and self.win.winfo_exists()


# ══════════════════════════════════════════════════════════════
# Main Application
# ══════════════════════════════════════════════════════════════
class App:
    def __init__(self):
        self.history = History()
        self.last_open = 0
        self.keys_released = True
        self.picker_just_closed = 0
        self._picker = None
        self._pasting = False  # Block polling during paste

        self.root = tk.Tk()
        self.root.title("ClipboardManager")
        self.root.withdraw()

        # Clear log
        try:
            with open(LOG_FILE, "w", encoding="utf-8") as f:
                f.write("")
        except:
            pass
        log("Started")

    def run(self):
        self.root.after(200, self._tick)
        self.root.mainloop()

    def _tick(self):
        """Main polling loop — single mainloop, no nesting."""
        try:
            # Don't poll clipboard during paste operation
            if not self._pasting:
                self.history.poll()

            now = int(time.time() * 1000)
            picker_active = self._picker and self._picker.is_open()

            if not picker_active and not self._pasting:
                ctrl  = is_key_pressed(VK_CONTROL)
                alt   = is_key_pressed(VK_MENU)
                v     = is_key_pressed(VK_V)
                all_pressed = ctrl and alt and v

                if not all_pressed:
                    self.keys_released = True

                can_open = (
                    all_pressed
                    and self.keys_released
                    and (now - self.last_open) > HOTKEY_COOLDOWN
                    and (now - self.picker_just_closed) > POST_PICK_DELAY
                    and self.history.items
                )

                if can_open:
                    self.keys_released = False
                    self.last_open = now
                    log(f"Hotkey! {len(self.history.items)} items")
                    self._show_picker()

        except Exception as e:
            log(f"TICK ERR: {e}")

        self.root.after(POLL_MS, self._tick)

    def _show_picker(self):
        """Open picker window."""
        # Save the window that has focus BEFORE picker opens
        prev_win = user32.GetForegroundWindow()
        log(f"prev_win={prev_win}")

        def on_select(idx):
            """Called when user selects an item or cancels."""
            log(f"on_select: {idx}")
            self.picker_just_closed = int(time.time() * 1000)

            if idx is not None:
                selected_text = self.history.get(idx)
                if selected_text:
                    result = clip_set(selected_text)
                    actual = clip_get()
                    ok = (actual == selected_text)
                    log(f"clip_set={result} verify={ok}")
                    self._do_paste(prev_win)
                else:
                    log("ERR: selected idx not in history")
            else:
                log("Cancelled — no paste")

        self._picker = PickerWindow(self.history, self.root, on_select)
        self._picker.open()

    def _do_paste(self, prev_win):
        self._pasting = True

        def step1_focus():
            if prev_win:
                HWND_TOP = 0
                SWP_NOMOVE = 0x0002
                SWP_NOSIZE = 0x0001
                SWP_SHOWWINDOW = 0x0040
                user32.SetWindowPos(prev_win, HWND_TOP, 0, 0, 0, 0,
                                    SWP_NOMOVE | SWP_NOSIZE | SWP_SHOWWINDOW)
                user32.BringWindowToTop(prev_win)
                user32.SetForegroundWindow(prev_win)
                actual = user32.GetForegroundWindow()
                log(f"step1: fg={actual} match={actual == prev_win}")
            self.root.after(200, step2_paste)

        def step2_paste():
            log(f"step2: fg={user32.GetForegroundWindow()}")

            # Ctrl+V via keybd_event (VK codes — simple & proven)
            user32.keybd_event(VK_CONTROL, 0, 0, 0)
            user32.keybd_event(VK_V, 0, 0, 0)
            user32.keybd_event(VK_V, 0, KEYEVENTF_KEYUP, 0)
            user32.keybd_event(VK_CONTROL, 0, KEYEVENTF_KEYUP, 0)
            log("step2: keybd_event Ctrl+V sent")

            # WM_PASTE fallback for Win32 controls
            if prev_win:
                user32.PostMessageW(prev_win, 0x0302, 0, 0)
                log("step2: WM_PASTE sent")

            log("step2: DONE")
            self._pasting = False

        self.root.after(50, step1_focus)

    def _show_toast(self, msg):
        """Show a small auto-hiding toast notification."""
        toast = tk.Toplevel(self.root)
        toast.overrideredirect(True)
        toast.attributes("-topmost", True)
        toast.configure(bg="#1C1C1E")

        f = tkfont.Font(family="Segoe UI", size=10)
        lbl = tk.Label(toast, text=msg, font=f, fg="#FFFFFF", bg="#1C1C1E",
                       padx=16, pady=8)
        lbl.pack()

        toast.update_idletasks()
        w = toast.winfo_reqwidth()
        h = toast.winfo_reqheight()
        sw = user32.GetSystemMetrics(0)
        sh = user32.GetSystemMetrics(1)
        x = (sw - w) // 2
        y = sh - h - 40
        toast.geometry(f"+{x}+{y}")

        toast.after(1800, toast.destroy)


# ══════════════════════════════════════════════════════════════
# Entry Point
# ══════════════════════════════════════════════════════════════
if __name__ == "__main__":
    mutex = kernel32.CreateMutexW(None, False, "Global\\ClipMgr_v6_final")
    if kernel32.GetLastError() == 183:
        print("Already running.")
        sys.exit(0)
    App().run()
