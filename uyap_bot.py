# -*- coding: utf-8 -*-
"""
UYAP Taksit Kontrol Robotu - Ana Otomasyon ve Süreç Yöneticisi
Akıllı Çift Yöntemli (Görsel Şablon + Windows OCR) Buton Bulucu içerir.
Referans görsel klasörü boş veya eksik olsa bile Windows yerel OCR
teknolojisiyle UYAP ekranındaki metinleri tespit ederek tıklar.
"""
import os
import time
from config import (
    DEFAULT_IMAGE_DIR,
    IMAGE_FILES,
    BUTTON_OCR_CANDIDATES,
    TIMEOUTS,
    SPEED_PROFILES,
    DEFAULT_SPEED,
    MATCH_CONFIDENCE,
    resolve_image_file
)
from screen_control import ScreenController
from ocr_engine import OcrEngine
from calibration_manager import CalibrationManager

class UyapBot:
    def __init__(self, image_dir=None, ocr_engine=None):
        if image_dir is None:
            image_dir = DEFAULT_IMAGE_DIR
        self.image_dir = image_dir
        self.controller = ScreenController(confidence=MATCH_CONFIDENCE)
        self.ocr = ocr_engine if ocr_engine else OcrEngine()
        self.calibration = CalibrationManager()
        self.speed_profile = DEFAULT_SPEED
        self.is_running = False
        self.should_stop = False

    def get_delays(self):
        """Mevcut hız profiline göre işlem bekleme sürelerini döndürür."""
        return SPEED_PROFILES.get(self.speed_profile, SPEED_PROFILES["normal"])

    def set_speed_profile(self, profile_name):
        """Çalışma hız profilini ayarlar ('normal', 'yavas', 'hizli')."""
        if profile_name in SPEED_PROFILES:
            self.speed_profile = profile_name

    def get_image_path(self, key):
        """Verilen anahtar için akıllı görsel dosya yolunu döndürür."""
        return resolve_image_file(self.image_dir, key)

    def log(self, message, callback=None):
        """Log mesajını hem konsola hem de GUI geri çağrısına iletir."""
        timestamp = time.strftime("[%H:%M:%S]")
        full_msg = f"{timestamp} {message}"
        print(full_msg)
        if callback:
            callback(full_msg)

    def find_button(self, key, timeout=None, poll_interval=0.35, log_callback=None):
        """
        Akıllı Hibrit (Görsel Şablon + Windows OCR) Buton Tespiti:
        1. Önce varsa şablon görselini (PNG) ekranda arar.
        2. Görsel diskte yoksa veya ekranda eşleşmediyse Windows OCR ile
           ekrandaki Türkçe buton metnini tarar.
        3. Koordinatı (center_x, center_y, width, height, 'method') olarak döndürür.
        """
        if timeout is None:
            timeout = TIMEOUTS["sayfa_yukleme"]

        template_path = self.get_image_path(key)
        has_template = bool(template_path and os.path.exists(template_path))
        candidates = BUTTON_OCR_CANDIDATES.get(key, [])

        start_time = time.time()
        attempt = 0

        while time.time() - start_time < timeout:
            if self.should_stop:
                return None

            attempt += 1
            screen = self.controller.grab_screen()

            # 1. YÖNTEM: Görsel Şablon Eşleme (Eğer dosya varsa)
            if has_template:
                match = self.controller.match_template(screen, template_path)
                if match:
                    x, y, w, h = match
                    cx, cy = x + w // 2, y + h // 2
                    return (cx, cy, w, h, "görsel")

            # 2. YÖNTEM: Windows OCR Akıllı Metin Tespiti (Görsel yoksa veya eşleşmediyse)
            if candidates and self.ocr:
                coords = self.ocr.find_text_coordinates(screen, candidates)
                if coords:
                    cx, cy, w, h = coords
                    return (cx, cy, w, h, "ocr")

            time.sleep(poll_interval)

        # Zaman aşımı uyarısı
        if not has_template:
            self.log(
                f"[Uyarı] '{key}' için referans görsel diskte bulunamadı ({template_path}). "
                f"OCR ile '{candidates[0]}' metni de ekranda tespit edilemedi.",
                log_callback
            )
        else:
            self.log(
                f"[Uyarı] '{key}' butonu {timeout} saniye içinde ekranda görülemedi.",
                log_callback
            )

        return None

    def reset_to_search_screen(self, log_callback=None):
        """
        GÜVENLİ GERİ DÖNÜŞ (RECOVERY) PROTOKOLÜ:
        Hata nerede olursa olsun açık pencereleri kapatıp ana arama ekranına döner.
        """
        self.log("Ana arama ekranına sıfırlanıyor (ESC basılıyor)...", log_callback)
        for _ in range(2):
            self.controller.press_esc()
            time.sleep(0.3)

        # Eğer manuel kalibrasyon varsa doğrudan kalibre koordinatlarla sıfırla
        if self.calibration and self.calibration.is_calibrated():
            coords = self.calibration.coordinates
            self.controller.click(coords["arama"][0], coords["arama"][1])
            time.sleep(0.3)
            self.controller.click(coords["dosya_no"][0], coords["dosya_no"][1])
            self.controller.clear_text_field()
            self.log("Ana arama ekranına başarıyla dönüldü (Özel kalibre noktalarıyla).", log_callback)
            return True

        # Arama ekranının geldiğini kontrol et
        pos = self.find_button("arama", timeout=2.5, poll_interval=0.3, log_callback=None)
        if pos:
            # Dosya no alanını temizle
            dosya_pos = self.find_button("dosya_no", timeout=1.5, poll_interval=0.3, log_callback=None)
            if dosya_pos:
                box_x = dosya_pos[0] + (dosya_pos[2] // 2 + 50 if dosya_pos[4] == "ocr" else 65)
                box_y = dosya_pos[1]
                self.controller.click(box_x, box_y)
                self.controller.clear_text_field()
            self.log("Ana arama ekranına başarıyla dönüldü.", log_callback)
            return True

        self.log("Uyarı: Ana arama ekranı teyit edilemedi.", log_callback)
        return False

    def test_screen_detection(self):
        """
        Mevcut ekranı test eder ve hangi butonların görüldüğünü raporlar.
        """
        results = {}
        screen = self.controller.grab_screen()
        for key in ["arama", "dosya_no", "sorgula", "ayrinti", "infaz"]:
            template_path = self.get_image_path(key)
            has_template = bool(template_path and os.path.exists(template_path))
            found = False
            method = None

            if has_template:
                match = self.controller.match_template(screen, template_path)
                if match:
                    found = True
                    method = "Görsel Şablon"

            if not found and self.ocr:
                candidates = BUTTON_OCR_CANDIDATES.get(key, [])
                coords = self.ocr.find_text_coordinates(screen, candidates)
                if coords:
                    found = True
                    method = f"Windows OCR ('{candidates[0]}')"

            results[key] = {
                "bulundu": found,
                "yontem": method,
                "sablon_var": has_template
            }
        return results

    def check_and_dismiss_mahsup_popup(self, log_callback=None, max_checks=2):
        """
        'Mahsup bilgileri güncellendi/değişti' açılır modal uyarı pencerelerini ekranda görerek algılar ve anında kapatır.
        Ekranın orta bölgesini hedefli OCR ile tarar; uyarı belirdiğinde [Tamam] butonuna tıklar ve Enter/Boşluk basar.
        """
        popup_found = False
        try:
            # 1. Ekranın orta bölgesinde (uyarı kutusunun çıktığı alanda) görsel/OCR algılama
            screen = self.controller.grab_screen()
            if screen and self.ocr:
                sw, sh = screen.size
                center_box = (int(sw * 0.2), int(sh * 0.25), int(sw * 0.8), int(sh * 0.75))
                center_crop = screen.crop(center_box)

                # Orta alanda uyarı veya onay butonunu ara
                coords = self.ocr.find_text_coordinates(
                    center_crop,
                    ["mahsup", "güncellendi", "guncellendi", "değişti", "degisti", "taksit mahsup", "tamam"]
                )
                if coords:
                    popup_found = True
                    self.log("ℹ UYAP 'Mahsup Bilgileri Güncellendi' uyarısı ekranda algılandı -> [Tamam] onaylanıyor...", log_callback)
                    real_x = center_box[0] + coords[0]
                    real_y = center_box[1] + coords[1]
                    self.controller.click(real_x, real_y)
                    time.sleep(0.06)
                    self.controller.press_key(0x0D)  # Enter
                    self.controller.press_key(0x20)  # Boşluk
                    time.sleep(0.2)
                    return True

            # 2. Eğer odak uyarıdaysa hızlı klavye onayı
            template_path = self.get_image_path("mahsup_uyari")
            if template_path and os.path.exists(template_path):
                template_match = self.controller.match_template(screen, template_path)
                if template_match:
                    popup_found = True
                    self.controller.click(template_match[0] + template_match[2] // 2, template_match[1] + template_match[3] // 2)
                    self.controller.press_key(0x0D)
                    time.sleep(0.15)
                    return True
        except Exception:
            pass
        return popup_found

    def _process_case_calibrated(self, case_no, log_callback=None, is_first_case=True):
        """
        Kullanıcının bir kez ekranda gösterip kaydettiği özel koordinatlarla
        ilamat dosyasını sıfır hatayla ve doğrudan tıklar.
        """
        coords = self.calibration.coordinates
        delays = self.get_delays()
        speed_factor = 0.45 if getattr(self, "current_speed", "") == "hizli" else 1.0
        result = {
            "dosya_no": case_no,
            "sirasi": "-",
            "miktari": "-",
            "taksit_no": "-",
            "son_odeme_tarihi": "-",
            "son_odedigi_tarih": "-",
            "durum": "Bilinmeyen Durum"
        }

        self.log(f"--- [Kalibre Mod] Dosya İşleniyor: {case_no} ---", log_callback)

        # AŞAMA 1: İlamat Dosya Arama (SADECE İLK DOSYADA BASILIR!)
        c_dosya = coords["dosya_no"]
        if is_first_case:
            c_arama = coords["arama"]
            self.log(f"Aşama 1: İlk dosya için 'İlamat Dosya Arama' butonuna tıklanıyor ({c_arama[0]}, {c_arama[1]})...", log_callback)
            self.controller.click(c_arama[0], c_arama[1])
            time.sleep(delays["adim_arasi"] * speed_factor)
        else:
            self.log("Aşama 1: Arama ekranı zaten açık, doğrudan Dosya No alanına geçiliyor...", log_callback)

        if self.should_stop:
            return result

        # AŞAMA 2: Dosya No Kutusuna Yazma
        self.log(f"Aşama 2: Dosya No kutusuna '{case_no}' yazılıyor...", log_callback)
        self.controller.clear_and_type(c_dosya[0], c_dosya[1], case_no)
        time.sleep(0.12)

        if self.should_stop:
            return result

        # AŞAMA 3: Sorgula Butonu
        c_sorgula = coords["sorgula"]
        c_ayrinti = coords.get("ayrinti") or coords.get("sonuc_satiri")
        self.log(f"Aşama 3: 'Sorgula' butonuna tıklanıyor...", log_callback)
        self.controller.click(c_sorgula[0], c_sorgula[1])
        time.sleep(0.35)  # Sorgu sonucunun ekrana oturması için akıcı bekleme

        if self.should_stop:
            return result

        # AŞAMA 4: Dosya Ayrıntı Bilgileri Butonuna Tıklama (Tek Tıklama)
        c_infaz = coords["infaz_sekmesi"]
        self.log(f"Aşama 4: 'Dosya Ayrıntı Bilgileri' butonuna tıklanıyor ({c_ayrinti[0]}, {c_ayrinti[1]})...", log_callback)
        self.controller.click(c_ayrinti[0], c_ayrinti[1])
        time.sleep(0.4)  # İlam Dosyası (Ayrıntı) penceresinin açılması

        # Dosya ayrıntı açılışında belirebilecek uyarıları kontrol et (varsa anında onaylar)
        self.check_and_dismiss_mahsup_popup(log_callback)

        if self.should_stop:
            return result

        # AŞAMA 5: Para Cezası İnfaz Butonu
        c_tablo = coords["taksit_tablosu"]
        self.log(f"Aşama 5: 'Para Cezası İnfaz' butonuna tıklanıyor ({c_infaz[0]}, {c_infaz[1]})...", log_callback)
        self.controller.click(c_infaz[0], c_infaz[1])
        time.sleep(0.35)  # Taksit tablosunun açılması

        # AŞAMA 6: Taksit Mahsup Uyarısı Kontrolü
        self.check_and_dismiss_mahsup_popup(log_callback)

        if self.should_stop:
            return result

        # AŞAMA 7: Taksit Tablosunun Okunması (Önce Panodan Doğrudan Kopyalama, Yedek Olarak OCR)
        c_tablo = coords["taksit_tablosu"]
        self.log(f"Aşama 7: Taksit tablosu doğrudan okunuyor (Ctrl+A / Ctrl+C)...", log_callback)
        time.sleep(0.1)

        parsed_data = None
        try:
            # 1. YÖNTEM: Panodan doğrudan kopyalama (Kaydırma çubuğunun altındaki tüm satırları da eksiksiz alır)
            copied_text = self.controller.select_all_and_copy(c_tablo[0], c_tablo[1])
            if not copied_text:
                # Olası takılı kalan 'Mahsup' uyarısını kapat ve panoyu tekrar dene
                self.controller.press_key(0x0D)  # Enter
                time.sleep(0.05)
                self.controller.press_key(0x20)  # Boşluk
                time.sleep(0.1)
                copied_text = self.controller.select_all_and_copy(c_tablo[0], c_tablo[1])

            if copied_text and self.ocr:
                parsed_data = self.ocr.parse_clipboard_table(copied_text)
        except Exception as e:
            self.log(f"⚠ Panodan okuma esnasında hata oluştu: {e}", log_callback)

        if parsed_data:
            self.log("✔ Tablo verileri panodan sıfır hatayla doğrudan aktarıldı (tüm satırlar dahil).", log_callback)
        else:
            # 2. YÖNTEM: Yedek OCR Taraması
            self.log("ℹ Panodan kopyalanamadı, yedek görsel OCR taraması yapılıyor...", log_callback)
            try:
                screen_img = self.controller.grab_screen()
                parsed_data = {}
                if screen_img and self.ocr:
                    sw, sh = screen_img.size
                    crop_box = (
                        max(0, int(c_tablo[0] - 600)),
                        max(0, int(c_tablo[1] - 150)),
                        min(sw, int(c_tablo[0] + 600)),
                        min(sh, int(c_tablo[1] + 450))
                    )
                    table_crop = screen_img.crop(crop_box)
                    parsed_data = self.ocr.parse_installment_table(table_crop)

                    if "Boş veya Okunamadı" in parsed_data.get("durum", ""):
                        parsed_data = self.ocr.parse_installment_table(screen_img)
            except Exception as e:
                self.log(f"⚠ Yedek OCR taramasında hata: {e}", log_callback)

        parsed_data = parsed_data or {}
        result["sirasi"] = parsed_data.get("sirasi", "-")
        result["miktari"] = parsed_data.get("miktari", "-")
        result["taksit_no"] = parsed_data.get("taksit_no", "-")
        result["son_odeme_tarihi"] = parsed_data.get("son_odeme_tarihi", "-")
        result["son_odedigi_tarih"] = parsed_data.get("son_odedigi_tarih", "-")
        result["durum"] = parsed_data.get("durum", "Başarılı")

        self.log(
            f"Sonuç: Sıra: {result['sirasi']} | Taksit: {result['taksit_no']} | "
            f"Miktar: {result['miktari']} | Vade: {result['son_odeme_tarihi']} | "
            f"Son Ödediği: {result['son_odedigi_tarih']} | Durum: {result['durum']}",
            log_callback
        )

        # AŞAMA 8: Pencereler Kapat Butonları İle Kapatılıyor
        self.log("Aşama 8: Pencereler 'Kapat' butonları ile kapatılıyor...", log_callback)

        try:
            # 1. Taksit ekranındaki Kapat butonu
            c_kapat_taksit = coords.get("kapat_taksit")
            if c_kapat_taksit:
                self.log(f"1. Taksit ekranı 'Kapat' butonuna tıklanıyor ({c_kapat_taksit[0]}, {c_kapat_taksit[1]})...", log_callback)
                self.controller.click(c_kapat_taksit[0], c_kapat_taksit[1])
            else:
                kapat_pos = self.ocr.find_text_coordinates(self.controller.grab_screen(), ["kapat"]) if self.ocr else None
                if kapat_pos:
                    self.controller.click(kapat_pos[0], kapat_pos[1])
                else:
                    self.controller.press_esc()
            time.sleep(0.2)

            # 2. Dosya ayrıntı ekranındaki Kapat butonu
            c_kapat_ayrinti = coords.get("kapat_ayrinti") or c_kapat_taksit
            if c_kapat_ayrinti:
                self.log(f"2. Dosya ayrıntı ekranı 'Kapat' butonuna tıklanıyor ({c_kapat_ayrinti[0]}, {c_kapat_ayrinti[1]})...", log_callback)
                self.controller.click(c_kapat_ayrinti[0], c_kapat_ayrinti[1])
            else:
                kapat_pos2 = self.ocr.find_text_coordinates(self.controller.grab_screen(), ["kapat"]) if self.ocr else None
                if kapat_pos2:
                    self.controller.click(kapat_pos2[0], kapat_pos2[1])
                else:
                    self.controller.press_esc()
            time.sleep(0.2)

            # 3. Dosya No kutusuna tıkla ve içini temizle (Sıradaki dosya numarası için hazır et)
            self.log("Dosya No alanı temizleniyor ve sıradaki ilamat numarasına hazırlanıyor...", log_callback)
            self.controller.click(c_dosya[0], c_dosya[1])
            self.controller.clear_text_field()
            time.sleep(0.08)
        except Exception as e:
            self.log(f"⚠ Pencere kapatma aşamasında hata: {e}", log_callback)

        return result

    def process_single_case(self, case_no, log_callback=None, is_first_case=True):
        """
        Tek bir ilamat dosyasını baştan sona işler.
        Tüm adımlarda bekleme, akıllı tespit ve hata yakalama yapar.
        """
        # Kullanıcı ekranda yerleri göstermişse doğrudan o özel koordinatlarla çalış
        if self.calibration and self.calibration.is_calibrated():
            try:
                return self._process_case_calibrated(case_no, log_callback, is_first_case=is_first_case)
            except Exception as e:
                self.log(f"⚠ {case_no} dosyasında hata oluştu, bir sonrakine geçiliyor: {e}", log_callback)
                try:
                    self.controller.press_esc()
                    time.sleep(0.3)
                    self.controller.press_esc()
                except Exception:
                    pass
                return {
                    "dosya_no": case_no,
                    "sirasi": "-",
                    "miktari": "-",
                    "taksit_no": "-",
                    "son_odeme_tarihi": "-",
                    "son_odedigi_tarih": "-",
                    "durum": f"Hata: {str(e)[:35]}"
                }

        delays = self.get_delays()
        result = {
            "dosya_no": case_no,
            "sirasi": "-",
            "miktari": "-",
            "taksit_no": "-",
            "son_odeme_tarihi": "-",
            "son_odedigi_tarih": "-",
            "durum": "Bilinmeyen Durum"
        }

        self.log(f"--- Dosya İşleniyor: {case_no} ---", log_callback)

        # -------------------------------------------------------------
        # AŞAMA 1: İlamat Dosya Arama Butonuna Tıklama (SADECE İLK DOSYADA!)
        # -------------------------------------------------------------
        if is_first_case:
            self.log("Aşama 1: 'İlamat Dosya Arama' butonu aranıyor...", log_callback)
            arama_pos = self.find_button("arama", timeout=TIMEOUTS["sayfa_yukleme"], log_callback=log_callback)
            if not arama_pos:
                result["durum"] = "Hata: İlamat Dosya Arama Butonu Bulunamadı"
                self.log(result["durum"], log_callback)
                self.reset_to_search_screen(log_callback)
                return result

            self.log(f"Arama butonu tıklandı ({arama_pos[4]} yöntemiyle X:{arama_pos[0]}, Y:{arama_pos[1]}).", log_callback)
            self.controller.click(arama_pos[0], arama_pos[1])
            time.sleep(delays["adim_arasi"])
        else:
            self.log("Aşama 1: Arama ekranı zaten açık, doğrudan Dosya No alanına geçiliyor...", log_callback)

        # -------------------------------------------------------------
        # AŞAMA 2: Dosya No Kutusuna Yazma
        # -------------------------------------------------------------
        self.log(f"Aşama 2: Dosya no kutusuna '{case_no}' yazılıyor...", log_callback)
        dosya_pos = self.find_button("dosya_no", timeout=TIMEOUTS["sayfa_yukleme"], log_callback=log_callback)
        if not dosya_pos:
            result["durum"] = "Hata: Dosya No Alanı Bulunamadı"
            self.log(result["durum"], log_callback)
            self.reset_to_search_screen(log_callback)
            return result

        # Butonun/etiketin hemen sağındaki metin giriş kutusuna tıkla
        box_offset = dosya_pos[2] // 2 + 50 if dosya_pos[4] == "ocr" else 65
        box_x = dosya_pos[0] + box_offset
        box_y = dosya_pos[1]

        self.controller.clear_and_type(box_x, box_y, case_no)
        time.sleep(delays["adim_arasi"])

        # -------------------------------------------------------------
        # AŞAMA 3: Sorgula Butonuna Tıklama
        # -------------------------------------------------------------
        self.log("Aşama 3: 'Sorgula' butonuna tıklanıyor...", log_callback)
        sorgula_pos = self.find_button("sorgula", timeout=TIMEOUTS["sayfa_yukleme"], log_callback=log_callback)
        if not sorgula_pos:
            result["durum"] = "Hata: Sorgula Butonu Bulunamadı"
            self.log(result["durum"], log_callback)
            self.reset_to_search_screen(log_callback)
            return result

        self.controller.click(sorgula_pos[0], sorgula_pos[1])
        self.log("UYAP sorgu sonucu bekleniyor (ekran değişimi takip ediliyor)...", log_callback)
        self.controller.wait_for_screen_change(
            timeout=delays["max_timeout"],
            settle_time=delays["settle_time"],
            should_stop_callback=lambda: self.should_stop
        )

        # -------------------------------------------------------------
        # AŞAMA 4: Dosya Ayrıntı Bilgileri (UYAP Sorgu Yüklenmesi Beklenir)
        # -------------------------------------------------------------
        self.log("Aşama 4: Sorgu sonucu ve 'Dosya Ayrıntı Bilgileri' bekleniyor...", log_callback)
        ayrinti_pos = self.find_button(
            "ayrinti",
            timeout=delays["max_timeout"],
            log_callback=log_callback
        )
        if not ayrinti_pos:
            result["durum"] = "Hata: Dosya Bulunamadı veya Ayrıntı Ekranı Gelmedi"
            self.log(result["durum"], log_callback)
            self.reset_to_search_screen(log_callback)
            return result

        self.controller.click(ayrinti_pos[0], ayrinti_pos[1])
        self.log("Dosya ayrıntı penceresi bekleniyor (ekran değişimi takip ediliyor)...", log_callback)
        self.controller.wait_for_screen_change(
            timeout=delays["max_timeout"],
            settle_time=delays["settle_time"],
            should_stop_callback=lambda: self.should_stop
        )

        # Dosya ayrıntı ekranında olası uyarıları kontrol et
        self.check_and_dismiss_mahsup_popup(log_callback)

        # -------------------------------------------------------------
        # AŞAMA 5: Para Cezası İnfaz Butonu
        # -------------------------------------------------------------
        self.log("Aşama 5: 'Para Cezası İnfaz' butonu bekleniyor...", log_callback)
        infaz_pos = self.find_button("infaz", timeout=delays["max_timeout"], log_callback=log_callback)
        if not infaz_pos:
            result["durum"] = "Hata: Para Cezası İnfaz Butonu Gelmedi / Tıklanamadı"
            self.log(result["durum"], log_callback)
            self.reset_to_search_screen(log_callback)
            return result

        self.controller.click(infaz_pos[0], infaz_pos[1])
        self.log("'Para Cezası İnfaz' sekmesi bekleniyor (ekran değişimi takip ediliyor)...", log_callback)
        self.controller.wait_for_screen_change(
            timeout=delays["max_timeout"],
            settle_time=delays["settle_time"],
            should_stop_callback=lambda: self.should_stop
        )

        # -------------------------------------------------------------
        # AŞAMA 6: Taksit Mahsup Uyarısı Kontrolü
        # -------------------------------------------------------------
        self.check_and_dismiss_mahsup_popup(log_callback)

        # -------------------------------------------------------------
        # AŞAMA 7: Taksit Tablosunun Gelmesi ve Okunması
        # -------------------------------------------------------------
        self.log("Aşama 7: Taksit tablosu ekranı bekleniyor...", log_callback)
        taksit_pos = self.find_button("taksit_ekrani", timeout=TIMEOUTS["sayfa_yukleme"], log_callback=log_callback)
        if not taksit_pos:
            result["durum"] = "Hata: Taksit Ekranı Gelmedi"
            self.log(result["durum"], log_callback)
            self.reset_to_search_screen(log_callback)
            return result

        self.log("Taksit tablosu ekranda tespit edildi, okunuyor...", log_callback)
        time.sleep(delays["adim_arasi"])

        # 1. YÖNTEM: Panodan doğrudan kopyalama (Scrollbar altındakiler dahil)
        copied_text = self.controller.select_all_and_copy(taksit_pos[0], taksit_pos[1])
        parsed_data = self.ocr.parse_clipboard_table(copied_text)

        if not parsed_data:
            # 2. YÖNTEM: Yedek OCR
            self.log("ℹ Panodan kopyalanamadı, yedek görsel OCR taraması yapılıyor...", log_callback)
            screen_img = self.controller.grab_screen()
            sw, sh = screen_img.size
            crop_box = (
                max(0, int(taksit_pos[0] - 650)),
                max(0, int(taksit_pos[1] - 120)),
                min(sw, int(taksit_pos[0] + 650)),
                min(sh, int(taksit_pos[1] + 650))
            )
            table_crop = screen_img.crop(crop_box)
            parsed_data = self.ocr.parse_installment_table(table_crop)

        # Eğer kırpılan bölgede veri çıkmadıysa yedek olarak tüm ekranı tara
        if "Boş veya Okunamadı" in parsed_data.get("durum", ""):
            parsed_data = self.ocr.parse_installment_table(screen_img)

        result["sirasi"] = parsed_data.get("sirasi", "-")
        result["miktari"] = parsed_data.get("miktari", "-")
        result["taksit_no"] = parsed_data.get("taksit_no", "-")
        result["son_odeme_tarihi"] = parsed_data.get("son_odeme_tarihi", "-")
        result["son_odedigi_tarih"] = parsed_data.get("son_odedigi_tarih", "-")
        result["durum"] = parsed_data.get("durum", "Başarılı")

        self.log(
            f"Sonuç: Sıra: {result['sirasi']} | Taksit: {result['taksit_no']} | "
            f"Miktar: {result['miktari']} | Vade: {result['son_odeme_tarihi']} | "
            f"Son Ödediği: {result['son_odedigi_tarih']} | Durum: {result['durum']}",
            log_callback
        )

        # -------------------------------------------------------------
        # AŞAMA 8: Kapatma ve Arama Ekranına Dönüş
        # -------------------------------------------------------------
        self.log("Aşama 8: 'Kapat' butonları ile pencereler kapatılıyor...", log_callback)
        # 1. Kapat (Taksit ekranı)
        kapat1 = self.ocr.find_text_coordinates(self.controller.grab_screen(), ["kapat"]) if self.ocr else None
        if kapat1:
            self.controller.click(kapat1[0], kapat1[1])
        else:
            self.controller.press_esc()
        time.sleep(0.7)

        # 2. Kapat (İlamat dosyası ayrıntı ekranı)
        kapat2 = self.ocr.find_text_coordinates(self.controller.grab_screen(), ["kapat"]) if self.ocr else None
        if kapat2:
            self.controller.click(kapat2[0], kapat2[1])
        else:
            self.controller.press_esc()
        time.sleep(0.7)

        # Dosya No kutusunu yeni dosya için temizle
        dosya_pos_final = self.find_button("dosya_no", timeout=2.5, poll_interval=0.3, log_callback=None)
        if dosya_pos_final:
            box_offset = dosya_pos_final[2] // 2 + 50 if dosya_pos_final[4] == "ocr" else 65
            self.controller.click(dosya_pos_final[0] + box_offset, dosya_pos_final[1])
            self.controller.clear_text_field()
            time.sleep(0.3)

        return result

    def run_batch(self, case_list, row_callback=None, log_callback=None, finish_callback=None):
        """Tüm dosya listesini sırayla çalıştırır."""
        self.is_running = True
        self.should_stop = False
        self.controller.prevent_sleep(True)
        all_results = []

        total = len(case_list)
        self.log(f"Toplam {total} adet dosya kontrol edilecek.", log_callback)

        for idx, case_no in enumerate(case_list, start=1):
            if self.should_stop:
                self.log("Kullanıcı tarafından durduruldu!", log_callback)
                break

            self.log(f"[{idx}/{total}] İşlem başlatılıyor: {case_no}", log_callback)
            is_first = (idx == 1)
            res = self.process_single_case(case_no, log_callback, is_first_case=is_first)
            all_results.append(res)

            if row_callback:
                row_callback(res, idx, total)

            time.sleep(0.5)

        self.is_running = False
        self.controller.prevent_sleep(False)
        self.log("İşlem tamamlandı!", log_callback)

        if finish_callback:
            finish_callback(all_results)

        return all_results

    def stop(self):
        """Çalışan işlemi durdurur."""
        self.should_stop = True
