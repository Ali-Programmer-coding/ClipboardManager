@echo off
title Clipboard Manager
echo Starting Clipboard Manager...
echo Press Ctrl+Shift+V anywhere to use it.
echo Close this window to stop.
echo.
pythonw "%~dp0clipboard_manager.pyw"
if %errorlevel% neq 0 (
    echo.
    echo Error! Trying with python.exe instead...
    python "%~dp0clipboard_manager.pyw"
)
pause
