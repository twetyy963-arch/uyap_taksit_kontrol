@echo off
cd /d "%~dp0"
title UYAP Robotu - Kurulum ve Paket Yukleyici

echo ========================================================
echo        UYAP ROBOTU PAKET YUKLEME VE KONTROL
echo ========================================================
echo.
echo Gerekli paketler kontrol ediliyor ve yukleniyor...
echo.
python -m pip install -r requirements.txt
echo.
echo ========================================================
echo Kurulum tamamlandi! "baslat.bat" ile calistirabilirsiniz.
echo ========================================================
pause
