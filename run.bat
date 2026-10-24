@echo off
title TikTok Analytics Studio
echo Menjalankan TikTok Analytics Studio...
python tiktok_analytics_gui.py
if %errorlevel% neq 0 (
    echo.
    echo Terjadi kesalahan saat menjalankan aplikasi.
    pause
)
