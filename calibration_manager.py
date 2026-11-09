# -*- coding: utf-8 -*-
"""
UYAP Taksit Kontrol Robotu - Manuel Kalibrasyon ve Koordinat Yöneticisi
Kullanıcının UYAP üzerindeki buton ve alanları bir kez gösterip kaydetmesini sağlar.
"""
import os
import json
import ctypes
import winsound

CALIBRATION_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "kalibrasyon.json")

class POINT(ctypes.Structure):
    _fields_ = [("x", ctypes.c_long), ("y", ctypes.c_long)]

user32 = ctypes.windll.user32

CALIBRATION_STEPS = [
    {
        "key": "arama",
        "title": "1. İlamat Dosya Arama Butonu",
        "desc": "Sol menüdeki 'İlamat Dosya Arama' butonunun üzerine gelin (Robot buna sadece İLK dosya başlarken 1 kez basacaktır)."
    },
    {
        "key": "dosya_no",
        "title": "2. Dosya No Giriş Alanı",
        "desc": "Dosya numarasının yazılacağı beyaz giriş kutusunun üzerine gelin."
    },
    {
        "key": "sorgula",
        "title": "3. Sorgula Butonu",
        "desc": "Dosyayı sorguladığımız 'Sorgula' butonunun üzerine gelin."
    },
    {
        "key": "ayrinti",
        "title": "4. Dosya Ayrıntı Bilgileri Butonu",
        "desc": "Arama sonucunda altta çıkan 'Dosya Ayrıntı Bilgileri' butonunun üzerine gelin."
    },
    {
        "key": "infaz_sekmesi",
        "title": "5. Para Cezası İnfaz Sekmesi",
        "desc": "Dosya açıldığında üstte yer alan 'Para Cezası İnfaz' sekmesinin üzerine gelin."
    },
    {
        "key": "taksit_tablosu",
        "title": "6. Taksit Tablosu (3. Taksit Satırı)",
        "desc": "Taksit tablosundaki 3. taksit satırının (rakam ve tarihlerin) üzerine gelin (3 taksitli kısa dosyalarda da tablonun doğru seçilebilmesi için 3. satır hizası seçilmelidir)."
    },
    {
        "key": "kapat_taksit",
        "title": "7. Taksit Ekranı 'Kapat' Butonu",
        "desc": "Taksit ekranının altındaki 'Kapat' butonunun üzerine gelin."
    },
    {
        "key": "kapat_ayrinti",
        "title": "8. Dosya Ayrıntı Ekranı 'Kapat' Butonu",
        "desc": "Dosya ayrıntı ekranının altındaki 'Kapat' butonunun üzerine gelin (Taksit ekranındakiyle aynı yerdeyse yine oraya basabilirsiniz)."
    }
]

class CalibrationManager:
    def __init__(self, file_path=CALIBRATION_FILE):
        self.file_path = file_path
        self.coordinates = self.load()

    def get_cursor_pos(self):
        """Mevcut fare imleci koordinatlarını (x, y) döndürür."""
        pt = POINT()
        user32.GetCursorPos(ctypes.byref(pt))
        return (int(pt.x), int(pt.y))

    def play_beep(self):
        """Tuşa basıldığında onay bip sesi çalar."""
        try:
            winsound.MessageBeep(winsound.MB_OK)
        except Exception:
            pass

    def load(self):
        """Kayıtlı kalibrasyon verisini yükler."""
        if os.path.exists(self.file_path):
            try:
                with open(self.file_path, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                pass
        return {}

    def save(self, coords=None):
        """Koordinatları kalibrasyon dosyasına kaydeder."""
        if coords is not None:
            self.coordinates = coords
        with open(self.file_path, "w", encoding="utf-8") as f:
            json.dump(self.coordinates, f, indent=2, ensure_ascii=False)
        return True

    def clear(self):
        """Kayıtlı kalibrasyonu siler."""
        self.coordinates = {}
        if os.path.exists(self.file_path):
            try:
                os.remove(self.file_path)
            except Exception:
                pass

    def is_calibrated(self):
        """Temel adımların koordinatları tanımlı mı kontrol eder."""
        core_keys = ["arama", "dosya_no", "sorgula", "ayrinti", "infaz_sekmesi", "taksit_tablosu"]
        return all(
            (k in self.coordinates) or (k == "ayrinti" and "sonuc_satiri" in self.coordinates)
            for k in core_keys
        )

