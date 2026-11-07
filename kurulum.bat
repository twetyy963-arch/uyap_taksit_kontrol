@echo off
chcp 65001 >nul
title UYAP Robotu - Kurulum ve Paket Yükleyici
echo ========================================================
echo        UYAP ROBOTU PAKET YÜKLEME VE KONTROL
echo ========================================================
echo.
echo Gerekli paketler kontrol ediliyor ve yükleniyor...
echo.
python -m pip install -r requirements.txt
echo.
echo ========================================================
echo Kurulum tamamlandı! "baslat.bat" ile çalıştırabilirsiniz.
echo ========================================================
pause

