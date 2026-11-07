# -*- coding: utf-8 -*-
"""
UYAP Taksit Kontrol Robotu - Ana Otomasyon ve Süreç Yöneticisi
Her aşama için hata yakalama, zaman aşımı (timeout) ve güvenli sıfırlama (recovery) protokolü içerir.
"""
import os
import time
from config import IMAGE_FILES, TIMEOUTS, MATCH_CONFIDENCE
from screen_control import ScreenController
from ocr_engine import OcrEngine

class UyapBot:
    def __init__(self, image_dir=None, ocr_engine=None):
        if image_dir is None:
            user_desktop = os.path.join(os.environ.get("USERPROFILE", "C:\\Users\\Administrator"), "Desktop")
            image_dir = os.path.join(user_desktop, "program")
        self.image_dir = image_dir
        self.controller = ScreenController(confidence=MATCH_CONFIDENCE)
        self.ocr = ocr_engine if ocr_engine else OcrEngine()
        self.is_running = False
        self.should_stop = False

    def get_image_path(self, key):
        """Verilen anahtar için tam görsel dosya yolunu döndürür."""
        filename = IMAGE_FILES.get(key, "")
        return os.path.join(self.image_dir, filename)

    def log(self, message, callback=None):
        """Log mesajını hem konsola hem de GUI geri çağrısına iletir."""
        timestamp = time.strftime("[%H:%M:%S]")
        full_msg = f"{timestamp} {message}"
        print(full_msg)
        if callback:
            callback(full_msg)

    def reset_to_search_screen(self, log_callback=None):
        """
        GÜVENLİ GERİ DÖNÜŞ (RECOVERY) PROTOKOLÜ:
        Hata nerede olursa olsun açık pencereleri kapatıp ana arama ekranına döner.
        """
        self.log("Ana arama ekranına sıfırlanıyor (ESC basılıyor)...", log_callback)
        for _ in range(3):
            self.controller.press_esc()
            time.sleep(0.4)

        # Arama ekranının geldiğini kontrol et
        pos = self.controller.wait_for_template(
            self.get_image_path("arama"),
            timeout=3.0,
            poll_interval=0.3
        )
        if pos:
            # Dosya no alanını temizle
            dosya_pos = self.controller.wait_for_template(
                self.get_image_path("dosya_no"),
                timeout=2.0
            )
            if dosya_pos:
                self.controller.click(dosya_pos[0] + 60, dosya_pos[1])
                self.controller.clear_text_field()
            self.log("Ana arama ekranına başarıyla dönüldü.", log_callback)
            return True

        self.log("Uyarı: Ana arama ekranı görsel olarak teyit edilemedi.", log_callback)
        return False

    def process_single_case(self, case_no, log_callback=None):
        """
        Tek bir ilamat dosyasını baştan sona işler.
        Tüm adımlarda bekleme ve hata tespiti yapar.
        """
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
        # AŞAMA 1: İlamat Dosyası Arama Butonuna Tıklama
        # -------------------------------------------------------------
        self.log("Aşama 1: 'İlamat Dosyası Arama' butonu aranıyor...", log_callback)
        arama_pos = self.controller.wait_for_template(
            self.get_image_path("arama"),
            timeout=TIMEOUTS["sayfa_yukleme"]
        )
        if not arama_pos:
            result["durum"] = "Hata: İlamat Dosyası Arama Butonu Bulunamadı"
            self.log(result["durum"], log_callback)
            self.reset_to_search_screen(log_callback)
            return result

        self.controller.click(arama_pos[0], arama_pos[1])
        time.sleep(TIMEOUTS["adim_arasi_bekleme"])

        # -------------------------------------------------------------
        # AŞAMA 2: Dosya No Kutusuna Yazma
        # -------------------------------------------------------------
        self.log(f"Aşama 2: Dosya no kutusuna '{case_no}' yazılıyor...", log_callback)
        dosya_pos = self.controller.wait_for_template(
            self.get_image_path("dosya_no"),
            timeout=TIMEOUTS["sayfa_yukleme"]
        )
        if not dosya_pos:
            result["durum"] = "Hata: Dosya No Alanı Bulunamadı"
            self.log(result["durum"], log_callback)
            self.reset_to_search_screen(log_callback)
            return result

        # Butonun hemen sağındaki metin kutusuna tıkla
        box_x = dosya_pos[0] + 65
        box_y = dosya_pos[1]
        self.controller.clear_and_type(box_x, box_y, case_no)
        time.sleep(TIMEOUTS["adim_arasi_bekleme"])

        # -------------------------------------------------------------
        # AŞAMA 3: Sorgula Butonuna Tıklama
        # -------------------------------------------------------------
        self.log("Aşama 3: 'Sorgula' butonuna tıklanıyor...", log_callback)
        sorgula_pos = self.controller.wait_for_template(
            self.get_image_path("sorgula"),
            timeout=TIMEOUTS["sayfa_yukleme"]
        )
        if not sorgula_pos:
            result["durum"] = "Hata: Sorgula Butonu Bulunamadı"
            self.log(result["durum"], log_callback)
            self.reset_to_search_screen(log_callback)
            return result

        self.controller.click(sorgula_pos[0], sorgula_pos[1])
        time.sleep(0.8)

        # -------------------------------------------------------------
        # AŞAMA 4: Dosya Ayrıntı Bilgileri (UYAP Sorgu Yüklenmesi Beklenir)
        # -------------------------------------------------------------
        self.log("Aşama 4: Sorgu sonucu ve 'Dosya Ayrıntı Bilgileri' bekleniyor...", log_callback)
        ayrinti_pos = self.controller.wait_for_template(
            self.get_image_path("ayrinti"),
            timeout=TIMEOUTS["sayfa_yukleme"] + 3.0  # UYAP sorgusu için ekstra süre
        )
        if not ayrinti_pos:
            result["durum"] = "Hata: Dosya Bulunamadı veya Ayrıntı Ekranı Gelmedi"
            self.log(result["durum"], log_callback)
            self.reset_to_search_screen(log_callback)
            return result

        self.controller.click(ayrinti_pos[0], ayrinti_pos[1])
        time.sleep(TIMEOUTS["adim_arasi_bekleme"])

        # -------------------------------------------------------------
        # AŞAMA 5: Para Cezası İnfaz Butonu
        # -------------------------------------------------------------
        self.log("Aşama 5: 'Para Cezası İnfaz' butonu bekleniyor...", log_callback)
        infaz_pos = self.controller.wait_for_template(
            self.get_image_path("infaz"),
            timeout=TIMEOUTS["sayfa_yukleme"]
        )
        if not infaz_pos:
            result["durum"] = "Hata: Para Cezası İnfaz Butonu Gelmedi / Tıklanamadı"
            self.log(result["durum"], log_callback)
            self.reset_to_search_screen(log_callback)
            return result

        self.controller.click(infaz_pos[0], infaz_pos[1])
        time.sleep(TIMEOUTS["adim_arasi_bekleme"])

        # -------------------------------------------------------------
        # AŞAMA 6: Taksit Mahsup Uyarısı Kontrolü (Hızlı Kontrol)
        # -------------------------------------------------------------
        mahsup_pos = self.controller.wait_for_template(
            self.get_image_path("mahsup_uyari"),
            timeout=TIMEOUTS["uyari_kontrol"],
            poll_interval=0.2
        )
        if mahsup_pos:
            self.log("Aşama 6: 'Taksit Mahsup Uyarısı' çıktı, 'Tamam' basılıyor...", log_callback)
            self.controller.press_key(0x0D)  # Enter tuşu ile uyarılara 'Tamam' de
            time.sleep(0.5)

        # -------------------------------------------------------------
        # AŞAMA 7: Taksit Tablosunun Gelmesi ve OCR İle Okunması
        # -------------------------------------------------------------
        self.log("Aşama 7: Taksit tablosu ekranı bekleniyor...", log_callback)
        taksit_pos = self.controller.wait_for_template(
            self.get_image_path("taksit_ekrani"),
            timeout=TIMEOUTS["sayfa_yukleme"]
        )
        if not taksit_pos:
            result["durum"] = "Hata: Taksit Ekranı Gelmedi"
            self.log(result["durum"], log_callback)
            self.reset_to_search_screen(log_callback)
            return result

        self.log("Taksit tablosu ekranda tespit edildi, OCR ile taranıyor...", log_callback)
        time.sleep(0.4)
        screen_img = self.controller.grab_screen()
        
        # Tablo Bölgesini Kırparak (ROI) OCR Yap (Hız ve doğruluk için görev çubuğunu vb. eler)
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
        self.log("Aşama 8: Pencereler kapatılıyor ve ana ekrana dönülüyor...", log_callback)
        # 1. Kapat (Taksit ekranı)
        self.controller.press_esc()
        time.sleep(0.5)
        # 2. Kapat (İlamat dosyası ayrıntı ekranı)
        self.controller.press_esc()
        time.sleep(0.5)

        # Dosya No kutusunu yeni dosya için temizle
        dosya_pos_final = self.controller.wait_for_template(
            self.get_image_path("dosya_no"),
            timeout=3.0
        )
        if dosya_pos_final:
            self.controller.click(dosya_pos_final[0] + 65, dosya_pos_final[1])
            self.controller.clear_text_field()

        return result

    def run_batch(self, case_list, row_callback=None, log_callback=None, finish_callback=None):
        """
        Tüm dosya listesini sırayla çalıştırır.
        """
        self.is_running = True
        self.should_stop = False
        self.controller.prevent_sleep(True)  # Uzun işlem sırasında bilgisayarın uyumasını önle
        all_results = []

        total = len(case_list)
        self.log(f"Toplam {total} adet dosya kontrol edilecek.", log_callback)

        for idx, case_no in enumerate(case_list, start=1):
            if self.should_stop:
                self.log("Kullanıcı tarafından durduruldu!", log_callback)
                break

            self.log(f"[{idx}/{total}] İşlem başlatılıyor: {case_no}", log_callback)
            res = self.process_single_case(case_no, log_callback)
            all_results.append(res)

            if row_callback:
                row_callback(res, idx, total)

            # Dosyalar arası kısa insansı dinlenme
            time.sleep(0.6)

        self.is_running = False
        self.controller.prevent_sleep(False)  # Normal güç durumuna dön
        self.log("İşlem tamamlandı!", log_callback)

        if finish_callback:
            finish_callback(all_results)

        return all_results

    def stop(self):
        """Çalışan işlemi durdurur."""
        self.should_stop = True

