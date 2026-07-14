# 📋 Clipboard Manager

یک مدیر کلیپ‌بورد هوشمند برای ویندوز — آخرین ۳ متن کپی‌شده را ذخیره و با یک میانبر سریع قابل دسترسی می‌کند.

A smart clipboard manager for Windows — stores the last 3 copied texts and provides quick access via hotkey.

## ✨ Features / امکانات

- **ذخیره ۳ کپی آخر** — هر متنی کپی کنید (`Ctrl+C`) ذخیره می‌شود
- **میانبر `Ctrl+Alt+V`** — پنجره انتخابگر را باز می‌کند (بدون تداخل با میانبرهای مرورگر)
- **نمایش زیبا** — طراحی تاریک Apple-inspired با گوشه‌های نرم
- **انتخاب با کیبورد یا موس** — ↑↓ + Enter, کلیک, یا کلیدهای ۱/۲/۳
- **پیست هوشمند** — پس از انتخاب، فوکوس را به پنجره قبلی برمی‌گرداند و پیست می‌کند
- **سبک و بدون وابستگی** — فقط Python استاندارد (tkinter + ctypes)
- **فایل exe مستقل** — بدون نیاز به Python

## 📥 Download / دانلود

| فایل | توضیح |
|------|-------|
| `ClipboardManager.exe` | فایل اجرایی مستقل (۱۰MB) — فقط اجرا کنید! |
| `clipboard_manager.pyw` | سورس کد (برای اجرا با Python) |
| `start.bat` | اجرا با دوبار کلیک (در صورت داشتن Python) |

## 🚀 Usage / نحوه استفاده

1. **برنامه را اجرا کنید** (`ClipboardManager.exe` یا `start.bat`)
2. **چند متن کپی کنید** (`Ctrl+C`)
3. **`Ctrl+Alt+V`** را بزنید → لیست ۳ کپی آخر نمایش داده می‌شود
4. **گزینه مورد نظر را انتخاب کنید:**
   - ↑↓ + **Enter**
   - **کلیک موس**
   - **کلید ۱ / ۲ / ۳**
5. متن انتخاب‌شده **خودکار پیست می‌شود**
6. **`Esc`** → بسته شدن بدون پیست

## ⌨️ Hotkeys / کلیدهای میانبر

| کلید | عملکرد |
|------|--------|
| `Ctrl+Alt+V` | باز کردن انتخابگر |
| `↑ ↓` | حرکت بین گزینه‌ها |
| `Enter (⏎)` | انتخاب و پیست |
| `1 / 2 / 3` | انتخاب سریع |
| `Esc` | لغو |

> **نکته:** از `Ctrl+Shift+V` به `Ctrl+Alt+V` تغییر کرد تا با میانبر "Paste without formatting" مرورگرها تداخل نداشته باشد.

## 📁 Project Structure / ساختار پروژه

```
ClipboardManager/
├── ClipboardManager.exe    # فایل اجرایی (تولید شده با PyInstaller)
├── clipboard_manager.pyw   # سورس کد اصلی
├── start.bat               # راه‌انداز سریع
├── install_autostart.py    # اضافه کردن به Startup ویندوز
└── README.md               # این فایل
```

## 🔧 Requirements / پیش‌نیازها

- **Windows** 10 یا 11
- **برای فایل exe:** هیچی!
- **برای سورس کد:** Python 3.6+ (با tkinter داخلی)

## 🛠️ Build from Source / ساخت از سورس

```bash
pip install pyinstaller
pyinstaller --onefile --noconsole --name ClipboardManager clipboard_manager.pyw
```

## 📜 License

MIT License — free to use, modify, and distribute.
