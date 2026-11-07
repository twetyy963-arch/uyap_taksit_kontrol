# -*- coding: utf-8 -*-
"""
UYAP Taksit Kontrol Robotu - Yapılandırma Dosyası
"""
import os

# Temel Dizinler
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
SCRIPTS_DIR = BASE_DIR

# Kullanıcı Masaüstü Yolu
USER_DESKTOP = os.path.join(os.environ.get("USERPROFILE", "C:\\Users\\Administrator"), "Desktop")

# UYAP Referans Buton Görselleri Dizini
DEFAULT_IMAGE_DIR = os.path.join(USER_DESKTOP, "program")

# Referans Görsel Dosya Adları
IMAGE_FILES = {
    "arama": "1 - ilamat dosyası arama.png",
    "dosya_no": "2- dosya no.png",
    "sorgula": "3- sorgula.png",
    "ayrinti": "4- dosya ayrıntı bilgileri.png",
    "infaz": "5- para cezası infaz.png",
    "mahsup_uyari": "6-taksit mahsup uyarı.png",
    "taksit_ekrani": "7- ödendiği tarih boş olan.png",
}

# Zaman Aşımı ve Bekleme Süreleri (Saniye)
TIMEOUTS = {
    "sayfa_yukleme": 12.0,    # Ekranın veya butonun gelmesi için azami bekleme
    "uyari_kontrol": 1.5,     # Taksit mahsup uyarısı için hızlı bekleme
    "adim_arasi_bekleme": 0.4 # İşlem adımları arasındaki güvenli insansı bekleme
}

# Başlangıçta UYAP Ekranına Geçiş İçin Geri Sayım Süresi (Saniye)
STARTUP_COUNTDOWN = 10

# Görsel Eşleştirme Hassasiyeti (0.0 - 1.0)
MATCH_CONFIDENCE = 0.75

# Çıktı Excel Dosyası Yolu
DEFAULT_EXCEL_OUTPUT = os.path.join(USER_DESKTOP, "uyap_taksit_kontrol_raporu.xlsx")

