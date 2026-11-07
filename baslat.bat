@echo off
chcp 65001 >nul
title UYAP Taksit Kontrol Robotu
echo ========================================================
echo       UYAP TAKSİTLİ DOSYA KONTROL ROBOTU
echo ========================================================
echo.
echo Program başlatılıyor, lütfen bekleyiniz...
cd /d "%~dp0"
python main.py
if %ERRORLEVEL% NEQ 0 (
    echo.
    echo [HATA] Program sonlandı veya Python bulunamadı.
    echo Lütfen hata mesajını kontrol ediniz.
    pause
)

