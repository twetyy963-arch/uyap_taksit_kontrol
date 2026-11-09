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

# UYAP Referans Buton Görselleri Varsayılan Dizini
DEFAULT_IMAGE_DIR = os.path.join(USER_DESKTOP, "program")

# Referans Görsel Dosya Adları (Tam İsimler)
IMAGE_FILES = {
    "arama": "1 - ilamat dosya arama.png",
    "dosya_no": "2- dosya no.png",
    "sorgula": "3- sorgula.png",
    "ayrinti": "4- dosya ayrıntı bilgileri.png",
    "infaz": "5- para cezası infaz.png",
    "mahsup_uyari": "6-taksit mahsup uyarı.png",
    "taksit_ekrani": "7- ödendiği tarih boş olan.png",
}

# Görsel Dosyaları İçin Akıllı Anahtar Kelimeler (Farklı isimlendirmeleri de bulur)
IMAGE_KEYWORDS = {
    "arama": ["arama", "ilamat", "dosya"],
    "dosya_no": ["dosya", "no"],
    "sorgula": ["sorgula", "ara"],
    "ayrinti": ["ayrıntı", "ayrinti", "detay"],
    "infaz": ["infaz", "ceza"],
    "mahsup_uyari": ["mahsup", "uyarı", "uyari", "güncellendi", "guncellendi", "tamam"],
    "taksit_ekrani": ["taksit", "ödendi", "odendi"],
}

# Windows OCR İle Ekrandan Buton Bulma Aday Metinleri (Görsel Olmasa Bile Çalışır)
# İsimlerdeki 'dosya' vs 'dosyası' gibi takı farklarına takılmaz!
BUTTON_OCR_CANDIDATES = {
    "arama": [
        "ilamat dosya arama",
        "ilamat dosyası arama",
        "dosya arama",
        "dosyası arama",
        "ilamat arama",
        "ilamat dosya",
        "ilamat dosyası",
        "arama",
        "ilamat"
    ],
    "dosya_no": [
        "dosya no",
        "dosya numarası",
        "ilamat no",
        "dosya"
    ],
    "sorgula": [
        "sorgula",
        "sorgu",
        "ara",
        "bul"
    ],
    "ayrinti": [
        "dosya ayrıntı bilgileri",
        "dosya ayrıntı",
        "ayrıntı bilgileri",
        "ayrıntı",
        "ayrinti",
        "detay"
    ],
    "infaz": [
        "para cezası infaz",
        "para cezası",
        "para ceza",
        "cezası infaz",
        "infaz"
    ],
    "mahsup_uyari": [
        "mahsup bilgileri güncellendi",
        "mahsup bilgileri",
        "bilgileri güncellendi",
        "taksit mahsup",
        "güncellendi",
        "guncellendi",
        "mahsup",
        "uyarı",
        "uyari",
        "tamam"
    ],
    "taksit_ekrani": [
        "taksit no",
        "ödendiği tarih",
        "son ödeme tarihi",
        "vadesi",
        "miktarı",
        "taksit",
        "vade"
    ]
}

# Hız Profilleri (UYAP Donma Koruması ve Akıllı Ekran Değişim Takibi)
SPEED_PROFILES = {
    "yavas": {
        "label": "🛡 Yavaş (UYAP Donuyorsa / Ekstra Beklemeli)",
        "max_timeout": 25.0,        # Ekran değişimi için azami bekleme süresi
        "settle_time": 2.0,         # Değişiklikten sonra ekranın tam oturması
        "adim_arasi": 1.5,          # Küçük adımlar arasındaki bekleme
        "sorgu_bekleme": 6.0,       # Ekran değişimi yakalanamazsa asgari bekleme
        "sorgu_fallback": 6.0,
        "ayrinti_bekleme": 7.0,
        "ayrinti_fallback": 7.0,
        "infaz_bekleme": 5.0,
        "infaz_fallback": 5.0,
        "mahsup_bekleme": 2.5,
        "kapatma_bekleme": 1.2
    },
    "normal": {
        "label": "🐢 Sakin / Güvenli (Önerilen - Akıllı Ekran Takipli)",
        "max_timeout": 15.0,        # Ekran değişimi için azami bekleme süresi
        "settle_time": 1.2,         # Değişiklikten sonra ekranın tam oturması
        "adim_arasi": 1.0,
        "sorgu_bekleme": 4.0,
        "sorgu_fallback": 4.0,
        "ayrinti_bekleme": 5.0,
        "ayrinti_fallback": 5.0,
        "infaz_bekleme": 3.5,
        "infaz_fallback": 3.5,
        "mahsup_bekleme": 1.8,
        "kapatma_bekleme": 0.8
    },
    "hizli": {
        "label": "⚡ Hızlı (Hızlı Sistemler)",
        "max_timeout": 8.0,
        "settle_time": 0.6,
        "adim_arasi": 0.5,
        "sorgu_bekleme": 2.0,
        "sorgu_fallback": 2.0,
        "ayrinti_bekleme": 2.5,
        "ayrinti_fallback": 2.5,
        "infaz_bekleme": 1.8,
        "infaz_fallback": 1.8,
        "mahsup_bekleme": 1.0,
        "kapatma_bekleme": 0.4
    }
}
DEFAULT_SPEED = "normal"

# Zaman Aşımı ve Bekleme Süreleri (Geriye Dönük Uyumluluk İçin)
TIMEOUTS = {
    "sayfa_yukleme": 15.0,     # Ekranın veya butonun gelmesi için azami bekleme
    "uyari_kontrol": 2.5,      # Taksit mahsup uyarısı için hızlı bekleme
    "adim_arasi_bekleme": 1.0  # İşlem adımları arasındaki varsayılan bekleme
}

# Başlangıçta UYAP Ekranına Geçiş İçin Geri Sayım Süresi (Saniye)
STARTUP_COUNTDOWN = 10

# Görsel Eşleştirme Hassasiyeti (0.0 - 1.0)
MATCH_CONFIDENCE = 0.70

# Çıktı Excel Dosyası Yolu
DEFAULT_EXCEL_OUTPUT = os.path.join(USER_DESKTOP, "uyap_taksit_kontrol_raporu.xlsx")

def resolve_image_file(image_dir, key):
    """
    Belirtilen klasörde referans görseli arar.
    Tam isimle bulamazsa anahtar kelimelere ve sayıya göre akıllıca eşleştirir.
    """
    if not image_dir or not os.path.exists(image_dir):
        return ""

    exact_name = IMAGE_FILES.get(key, "")
    exact_path = os.path.join(image_dir, exact_name)
    if os.path.exists(exact_path):
        return exact_path

    # Klasör içerisindeki dosyaları tara
    try:
        files = os.listdir(image_dir)
        keywords = IMAGE_KEYWORDS.get(key, [])
        key_num = exact_name.split("-")[0].strip() if "-" in exact_name else ""

        for f in files:
            f_lower = f.lower()
            if not f_lower.endswith((".png", ".jpg", ".jpeg", ".bmp")):
                continue
            # Numara ile eşleşme (örn. '1.png', '1-arama.png')
            if key_num and (f_lower.startswith(key_num) or f" {key_num} " in f_lower or f"{key_num}-" in f_lower):
                return os.path.join(image_dir, f)
            # Anahtar kelime ile eşleşme
            if any(kw in f_lower for kw in keywords):
                return os.path.join(image_dir, f)
    except Exception:
        pass

    return exact_path
