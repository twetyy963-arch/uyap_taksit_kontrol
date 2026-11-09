# -*- coding: utf-8 -*-
"""
UYAP Taksit Kontrol Robotu - Kapsamlı Otomasyon ve Doğrulama Test Paketi
Tüm modülleri, OCR ayrıştırmayı, PDF bölüm filtrelemeyi ve hata durumlarını test eder.
"""
import sys
import os
import unittest
import pandas as pd

# Proje dizinini ekle
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from ocr_engine import OcrEngine
from pdf_reader import PdfReader

class TestUyapAutomationSuite(unittest.TestCase):
    def setUp(self):
        self.ocr = OcrEngine()
        self.pdf_reader = PdfReader(ocr_engine=self.ocr)

    # -------------------------------------------------------------
    # 1. OCR TABLO VE TAKSİT TESTLERİ
    # -------------------------------------------------------------
    def test_table_middle_unpaid(self):
        """1 ve 2 ödenmiş, 3 boş -> 3. satır seçilmeli, son ödediği 2. satırın tarihi olmalı."""
        simulated = {
            'Words': [],
            'Text': '''
Sıra No   Miktar     Taksit No   Son Ödeme Tarihi   Ödendiği Tarih
1         1.500,00 TL 1           15.01.2025         14.01.2025
2         1.500,00 TL 2           15.02.2025         10.02.2025
3         1.500,00 TL 3           15.03.2025
4         1.500,00 TL 4           15.04.2025
'''
        }
        self.ocr.recognize_pil_image = lambda img: simulated
        res = self.ocr.parse_installment_table(None)
        self.assertEqual(res['sirasi'], '3')
        self.assertEqual(res['taksit_no'], '3')
        self.assertEqual(res['miktari'], '1.500,00 TL')
        self.assertEqual(res['son_odeme_tarihi'], '15.03.2025')
        self.assertEqual(res['son_odedigi_tarih'], '10.02.2025')
        self.assertEqual(res['durum'], 'Başarılı')

    def test_table_first_unpaid_no_payments(self):
        """Daha önce hiç ödeme yapılmamışsa -> 1. satır seçilmeli, 'Ödeme Yok' yazmalı."""
        simulated = {
            'Words': [],
            'Text': '''
Sıra No   Miktar     Taksit No   Son Ödeme Tarihi   Ödendiği Tarih
1         2.000,00 TL 1           01.04.2025
2         2.000,00 TL 2           01.05.2025
'''
        }
        self.ocr.recognize_pil_image = lambda img: simulated
        res = self.ocr.parse_installment_table(None)
        self.assertEqual(res['sirasi'], '1')
        self.assertEqual(res['taksit_no'], '1')
        self.assertEqual(res['son_odedigi_tarih'], 'Ödeme Yok')
        self.assertEqual(res['durum'], 'Başarılı')

    def test_table_all_paid_completed(self):
        """Tablonun tamamı doluysa -> Sıra '-', Vade '-', Durum: Tüm Taksitler Ödenmiş."""
        simulated = {
            'Words': [],
            'Text': '''
Sıra No   Miktar     Taksit No   Son Ödeme Tarihi   Ödendiği Tarih
1         1.000,00 TL 1           10.01.2025         09.01.2025
2         1.000,00 TL 2           10.02.2025         08.02.2025
3         1.000,00 TL 3           10.03.2025         10.03.2025
'''
        }
        self.ocr.recognize_pil_image = lambda img: simulated
        res = self.ocr.parse_installment_table(None)
        self.assertEqual(res['sirasi'], '-')
        self.assertEqual(res['miktari'], '-')
        self.assertEqual(res['taksit_no'], '-')
        self.assertEqual(res['son_odeme_tarihi'], '-')
        self.assertEqual(res['son_odedigi_tarih'], '10.03.2025')
        self.assertIn("Tüm Taksitler Ödenmiş", res['durum'])

    def test_table_empty(self):
        """Tabloda hiç veri yoksa güvenli hata mesajı dönmeli."""
        simulated = {'Words': [], 'Text': ''}
        self.ocr.recognize_pil_image = lambda img: simulated
        res = self.ocr.parse_installment_table(None)
        self.assertIn("Boş veya Okunamadı", res['durum'])

    # -------------------------------------------------------------
    # 2. PDF VE BAŞLIK FİLTRELEME TESTLERİ
    # -------------------------------------------------------------
    def test_pdf_section_filtering(self):
        """
        'TAKSİDE BAĞLANAN PARA CEZASI İLAMLARI' dışındaki
        farklı başlıklara geçince oraları kesinlikle sorgulamamalı.
        """
        complex_pdf_text = '''
BİLGİ BELGESİ - İNFAZ BÜROSU

TPİ - TAKSİDE BAĞLANAN PARA CEZASI İLAMLARI
2022   18399
2024   21843  40286  57657
       70038  71951
2025   1846   3751

DPİ - DOĞRUDAN ADLİ PARA CEZASI İLAMLARI
2024   99901  99902  99903
2025   88801  88802

HPİ - HAPİSTEN ÇEVRİLEN PARA CEZASI İLAMLARI
2024   77701  77702
'''
        cases = self.pdf_reader.parse_case_numbers(complex_pdf_text)

        # 1. TPI altındakiler kesinlikle listede OLMALI
        self.assertIn('2022/2-18399', cases)
        self.assertIn('2024/2-21843', cases)
        self.assertIn('2024/2-70038', cases)
        self.assertIn('2025/2-1846', cases)

        # 2. DPİ ve HPİ altındaki dosyalar KESİNLİKLE LİSTEDE OLMAMALI!
        for c in cases:
            self.assertNotIn('99901', c)
            self.assertNotIn('99902', c)
            self.assertNotIn('88801', c)
            self.assertNotIn('77701', c)

        # Toplamda tam olarak 8 adet TPI dosyası bulunmalı
        self.assertEqual(len(cases), 8)

    def test_first_and_last_page_non_tpi_exclusion(self):
        """İlk sayfadaki DPİ ve son sayfadaki HPİ/Kamu çalışma dosyalarının kesinlikle taranmadığını doğrular."""
        multi_page_report = '''
        T.C.
        ANKARA CUMHURİYET BAŞSAVCILIĞI
        İlamat ve İnfaz Bürosu
        Sayfa: 1 / 3

        DPİ - DOĞRUDAN ADLİ PARA CEZASI İLAMLARI
        2024/2-9901
        2024/2-9902
        2024   9903   9904

        Sayfa: 2 / 3
        T.C.
        ANKARA CUMHURİYET BAŞSAVCILIĞI
        İlamat ve İnfaz Bürosu

        TPİ - TAKSİDE BAĞLANAN PARA CEZASI İLAMLARI
        2024/2-536
        2024/2-537
        2024   538    539

        Sayfa: 3 / 3
        T.C.
        ANKARA CUMHURİYET BAŞSAVCILIĞI
        İlamat ve İnfaz Bürosu

        HPİ - HAPİSTEN ÇEVRİLEN PARA CEZASI İLAMLARI
        2024/2-8801
        2024/2-8802

        KAMUYA YARARLI BİR İŞTE ÇALIŞTIRMA İLAMLARI
        2024   7701   7702

        GENEL TOPLAM: 12 ADET İLAMAT
        '''
        cases = self.pdf_reader.parse_case_numbers(multi_page_report)

        # 1. Yalnızca TPİ altındaki dosyalar (536, 537, 538, 539) listede OLMALI
        self.assertIn('2024/2-536', cases)
        self.assertIn('2024/2-537', cases)
        self.assertIn('2024/2-538', cases)
        self.assertIn('2024/2-539', cases)
        self.assertEqual(len(cases), 4)

        # 2. İlk sayfadaki DPİ dosyaları KESİNLİKLE OLMAMALI
        self.assertNotIn('2024/2-9901', cases)
        self.assertNotIn('2024/2-9902', cases)
        self.assertNotIn('2024/2-9903', cases)
        self.assertNotIn('2024/2-9904', cases)

        # 3. Son sayfadaki HPİ ve Kamu çalışma dosyaları KESİNLİKLE OLMAMALI
        self.assertNotIn('2024/2-8801', cases)
        self.assertNotIn('2024/2-8802', cases)
        self.assertNotIn('2024/2-7701', cases)
        self.assertNotIn('2024/2-7702', cases)

    def test_derdest_pdf_parsing(self):
        """Derdest listelerindeki 2024/2-536 veya 2024/536 formatındaki dosyaları doğru çıkarır."""
        derdest_text = '''
        ANKARA CUMHURİYET BAŞSAVCILIĞI İNFAZ BÜROSU
        2024 YILI DERDEST İLAMAT DOSYALARI LİSTESİ
        2024/2-536
        2024/2-537
        2024/538
        2024/2-539
        Toplam 4 adet dosya. Tarih: 15.02.2024 Miktar: 5.000,00 TL
        '''
        cases = self.pdf_reader.parse_case_numbers(derdest_text)
        self.assertIn('2024/2-536', cases)
        self.assertIn('2024/2-537', cases)
        self.assertIn('2024/2-538', cases)
        self.assertIn('2024/2-539', cases)
        self.assertEqual(len(cases), 4)

    def test_pure_python_pdf_extraction(self):
        """Harici kütüphane olmadan oluşturulan sıkıştırılmış PDF'i başarıyla okur."""
        import zlib
        raw_stream = b'''BT
/F1 12 Tf
72 712 Td
(DERDEST ILAMAT LISTESI 2024/2-536 2024/2-537 2024/2-538 2024/2-539) Tj
ET'''
        compressed = zlib.compress(raw_stream)
        pdf_bytes = b'''%%PDF-1.4
1 0 obj << /Type /Catalog /Pages 2 0 R >> endobj
2 0 obj << /Type /Pages /Kids [3 0 R] /Count 1 >> endobj
3 0 obj << /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Contents 4 0 R >> endobj
4 0 obj << /Length %d /Filter /FlateDecode >>
stream
%b
endstream
endobj
xref
0 5
0000000000 65535 f 
trailer << /Size 5 /Root 1 0 R >>
startxref
400
%%%%EOF''' % (len(compressed), compressed)
        
        test_pdf_file = os.path.join(os.path.dirname(__file__), "temp_test_derdest.pdf")
        try:
            with open(test_pdf_file, "wb") as f:
                f.write(pdf_bytes)
            extracted_cases = self.pdf_reader.load_case_list(test_pdf_file)
            self.assertEqual(extracted_cases, ['2024/2-536', '2024/2-537', '2024/2-538', '2024/2-539'])
        finally:
            if os.path.exists(test_pdf_file):
                os.remove(test_pdf_file)

    # -------------------------------------------------------------
    # 3. EXCEL RAPOR OLUŞTURMA VE TABLO BÜTÜNLÜĞÜ TESTİ
    # -------------------------------------------------------------
    def test_excel_generation(self):
        """Sonuç listesinin Excel'e başarıyla yazıldığını doğrular."""
        sample_results = [
            {
                "dosya_no": "2024/2-21843",
                "sirasi": "3",
                "miktari": "1.500,00 TL",
                "taksit_no": "3",
                "son_odeme_tarihi": "15.03.2025",
                "son_odedigi_tarih": "10.02.2025",
                "durum": "Başarılı"
            },
            {
                "dosya_no": "2024/2-40286",
                "sirasi": "-",
                "miktari": "-",
                "taksit_no": "-",
                "son_odeme_tarihi": "-",
                "son_odedigi_tarih": "-",
                "durum": "Hata: Para Cezası İnfaz Butonu Gelmedi"
            },
            {
                "dosya_no": "2025/2-1846",
                "sirasi": "-",
                "miktari": "-",
                "taksit_no": "-",
                "son_odeme_tarihi": "-",
                "son_odedigi_tarih": "12.01.2025",
                "durum": "Tüm Taksitler Ödenmiş (Borç Bitti)"
            }
        ]
        df = pd.DataFrame(sample_results)
        test_excel_path = os.path.join(os.path.dirname(__file__), "test_output.xlsx")
        try:
            df.to_excel(test_excel_path, index=False)
            self.assertTrue(os.path.exists(test_excel_path))
            df_read = pd.read_excel(test_excel_path)
            self.assertEqual(len(df_read), 3)
            self.assertEqual(df_read.iloc[1]['durum'], "Hata: Para Cezası İnfaz Butonu Gelmedi")
            self.assertEqual(df_read.iloc[2]['durum'], "Tüm Taksitler Ödenmiş (Borç Bitti)")
        finally:
            if os.path.exists(test_excel_path):
                os.remove(test_excel_path)

    # -------------------------------------------------------------
    # 4. KULLANICI DERDEST PDF (1324 DOSYA) KONTROL TESTİ
    # -------------------------------------------------------------
    def test_user_uploaded_pdf_1324_cases(self):
        """Kullanıcının yüklediği derdest-536-539.pdf dosyasından tam 1324 dosya çıkarıldığını doğrular."""
        user_pdf = r"C:\Users\Administrator\.gemini\antigravity\brain\02338462-dd4f-40d4-aa74-200ebcf05615\.user_uploaded\media_1794053502034_1b630494.pdf"
        if not os.path.exists(user_pdf):
            self.skipTest("Kullanıcı test PDF dosyası bulunamadı.")

        cases = self.pdf_reader.load_case_list(user_pdf)
        # 1. Tam olarak 1324 dosya olmalı
        self.assertEqual(len(cases), 1324, f"Beklenen 1324, bulunan: {len(cases)}")
        # 2. İlk dosya 2022/2-18399 olmalı
        self.assertEqual(cases[0], "2022/2-18399")
        # 3. Son dosya 2026/2-62266 olmalı (VAB öncesi son dosya)
        self.assertEqual(cases[-1], "2026/2-62266")
        # 4. VAB dosyaları (örn. 2023/2-24448) listede KESİNLİKLE OLMAMALI
        self.assertNotIn("2023/2-24448", cases)
        # 5. TPİ öncesi ilk sayfa dosyaları (örn. 2024/2-59000) KESİNLİKLE OLMAMALI
        self.assertNotIn("2024/2-59000", cases)

    # -------------------------------------------------------------
    # 5. AKILLI OCR BUTON TESPİTİ VE GÖRSEL ÇÖZÜMLEME TESTİ
    # -------------------------------------------------------------
    def test_ocr_button_coordinate_finding(self):
        """Windows OCR çıktısından çok kelimeli ve tek kelimeli butonların doğru bulunduğunu doğrular."""
        mock_ocr_data = {
            "Text": "İlamat Dosyası Arama Dosya No: 2024/2-536 Sorgula",
            "Words": [
                {"Text": "İlamat", "X": 50, "Y": 100, "W": 40, "H": 20},
                {"Text": "Dosyası", "X": 95, "Y": 100, "W": 45, "H": 20},
                {"Text": "Arama", "X": 145, "Y": 100, "W": 40, "H": 20},
                {"Text": "Dosya", "X": 300, "Y": 100, "W": 40, "H": 20},
                {"Text": "No:", "X": 345, "Y": 100, "W": 25, "H": 20},
                {"Text": "Sorgula", "X": 550, "Y": 100, "W": 55, "H": 22},
            ]
        }

        # 1. 'İlamat Dosyası Arama' çok kelimeli buton tespiti
        pos_arama = self.ocr.find_text_coordinates(mock_ocr_data, ["İlamat Dosyası Arama", "Arama"])
        self.assertIsNotNone(pos_arama)
        self.assertEqual(pos_arama[0], 117)  # cx = (50 + 185) // 2
        self.assertEqual(pos_arama[1], 110)  # cy = (100 + 120) // 2

        # 2. 'Sorgula' tek kelimeli buton tespiti
        pos_sorgula = self.ocr.find_text_coordinates(mock_ocr_data, ["Sorgula", "Ara"])
        self.assertIsNotNone(pos_sorgula)
        self.assertEqual(pos_sorgula[0], 577)  # cx = 550 + 27
        self.assertEqual(pos_sorgula[1], 111)  # cy = 100 + 11

        # 3. Olmayan bir buton
        pos_yok = self.ocr.find_text_coordinates(mock_ocr_data, ["Olmayan Buton", "Bilinmeyen"])
        self.assertIsNone(pos_yok)

    # -------------------------------------------------------------
    # 6. MANUEL KALİBRASYON YÖNETİCİSİ TESTİ
    # -------------------------------------------------------------
    def test_calibration_lifecycle(self):
        """Kullanıcının koordinat gösterme (kalibrasyon) yaşam döngüsünü test eder."""
        from calibration_manager import CalibrationManager
        tmp_calib = os.path.join(os.path.dirname(__file__), "test_kalibrasyon.json")
        try:
            cm = CalibrationManager(file_path=tmp_calib)
            self.assertFalse(cm.is_calibrated())

            # 8 adımın koordinatlarını kaydet
            mock_data = {
                "arama": [100, 200],
                "dosya_no": [300, 200],
                "sorgula": [500, 200],
                "ayrinti": [400, 350],
                "infaz_sekmesi": [600, 150],
                "taksit_tablosu": [700, 450],
                "kapat_taksit": [800, 600],
                "kapat_ayrinti": [800, 600]
            }
            cm.save(mock_data)
            self.assertTrue(cm.is_calibrated())
            self.assertEqual(cm.coordinates["arama"], [100, 200])
            self.assertEqual(cm.coordinates["ayrinti"], [400, 350])
            self.assertEqual(cm.coordinates["kapat_taksit"], [800, 600])

            # Sıfırlama
            cm.clear()
            self.assertFalse(cm.is_calibrated())
            self.assertFalse(os.path.exists(tmp_calib))
        finally:
            if os.path.exists(tmp_calib):
                os.remove(tmp_calib)

    # -------------------------------------------------------------
    # 7. HIZ PROFİLLERİ VE MAHSUP UYARISI YÖNETİMİ TESTİ
    # -------------------------------------------------------------
    def test_speed_profiles_and_delays(self):
        """Farklı hız profillerinin (normal, yavaş, hızlı) doğru bekleme süreleri sağladığını test eder."""
        from uyap_bot import UyapBot
        from config import SPEED_PROFILES
        bot = UyapBot()

        # Varsayılan normal profil
        self.assertEqual(bot.speed_profile, "normal")
        delays = bot.get_delays()
        self.assertEqual(delays["sorgu_bekleme"], 4.0)
        self.assertEqual(delays["ayrinti_bekleme"], 5.0)
        self.assertEqual(delays["max_timeout"], 15.0)

        # Yavaş (donma korumalı) profil
        bot.set_speed_profile("yavas")
        self.assertEqual(bot.speed_profile, "yavas")
        y_delays = bot.get_delays()
        self.assertGreater(y_delays["sorgu_bekleme"], delays["sorgu_bekleme"])
        self.assertGreater(y_delays["ayrinti_bekleme"], delays["ayrinti_bekleme"])
        self.assertEqual(y_delays["max_timeout"], 25.0)

        # Hızlı profil
        bot.set_speed_profile("hizli")
        self.assertEqual(bot.speed_profile, "hizli")
        h_delays = bot.get_delays()
        self.assertLess(h_delays["sorgu_bekleme"], delays["sorgu_bekleme"])

    def test_screen_change_detection(self):
        """Ekrandaki görsel değişimin akıllıca algılandığını doğrular."""
        from screen_control import ScreenController
        from PIL import Image
        sc = ScreenController()

        # 1. Ekran değişmediğinde zaman aşımına uğramalı (False dönmeli)
        img1 = Image.new('RGB', (100, 100), color=(255, 255, 255))
        sc.grab_screen = lambda bbox=None: img1
        no_change = sc.wait_for_screen_change(timeout=0.4, poll_interval=0.1, settle_time=0.05)
        self.assertFalse(no_change)

        # 2. Ekran değiştiğinde anında True dönmeli
        call_count = [0]
        def mock_grab(bbox=None):
            call_count[0] += 1
            if call_count[0] == 1:
                return Image.new('RGB', (100, 100), color=(255, 255, 255))
            else:
                return Image.new('RGB', (100, 100), color=(0, 0, 0)) # Siyah oldu (değişim)
        sc.grab_screen = mock_grab
        detected = sc.wait_for_screen_change(timeout=1.0, poll_interval=0.05, settle_time=0.05)
        self.assertTrue(detected)

    def test_mahsup_popup_dismissal(self):
        """'Mahsup bilgileri güncellendi' veya 'Tamam' butonu çıktığında robotun bunu tespit edip kapattığını test eder."""
        from uyap_bot import UyapBot
        bot = UyapBot()

        # 1. Hiçbir uyarı yokken hızlıca False dönmeli
        bot.controller.get_active_window_title = lambda: "İlamat Dosya Arama"
        bot.ocr.find_text_coordinates = lambda screen, cand: None
        bot.controller.match_template = lambda screen, tmpl: None
        dismissed = bot.check_and_dismiss_mahsup_popup(max_checks=1)
        self.assertFalse(dismissed)

        # 2. 'Tamam' butonu veya 'Mahsup bilgileri güncellendi' tespit edildiğinde True dönmeli
        clicked_coords = []
        bot.controller.get_active_window_title = lambda: "Uyarı"
        bot.controller.click = lambda x, y, **kw: clicked_coords.append((x, y))
        bot.ocr.find_text_coordinates = lambda screen, cand: (500, 400, 80, 30) if any(w in cand for w in ["tamam", "mahsup bilgileri güncellendi"]) else None
        dismissed_with_popup = bot.check_and_dismiss_mahsup_popup(max_checks=1)
        self.assertTrue(dismissed_with_popup)
        self.assertIn((500, 400), clicked_coords)

    def test_loop_first_vs_subsequent_files(self):
        """İlk dosyada 'arama' butonuna basıldığını, sonraki dosyalarda arama butonuna basılmadan devam edildiğini test eder."""
        from uyap_bot import UyapBot
        from PIL import Image
        bot = UyapBot()
        bot.calibration.coordinates = {
            "arama": [100, 200],
            "dosya_no": [300, 200],
            "sorgula": [500, 200],
            "ayrinti": [400, 350],
            "infaz_sekmesi": [600, 150],
            "taksit_tablosu": [700, 450],
            "kapat_taksit": [800, 600],
            "kapat_ayrinti": [800, 600]
        }
        clicks = []
        bot.controller.click = lambda x, y, **kw: clicks.append((x, y))
        bot.controller.clear_and_type = lambda x, y, t: clicks.append(("type", x, y, t))
        bot.controller.clear_text_field = lambda: None
        bot.controller.grab_screen = lambda bbox=None: Image.new('RGB', (1920, 1080))
        bot.ocr.parse_installment_table = lambda img: {"durum": "Başarılı"}
        bot.check_and_dismiss_mahsup_popup = lambda log_cb=None: False

        # 1. Dosya (is_first_case=True) -> arama butonuna basmalı!
        clicks.clear()
        bot.process_single_case("2024/100", is_first_case=True)
        self.assertIn((100, 200), clicks)  # 'arama' koordinatı tıklandı!
        self.assertIn((800, 600), clicks)  # 'kapat' butonları tıklandı!

        # 2. Dosya (is_first_case=False) -> arama butonuna BASMAMALI!
        clicks.clear()
        bot.process_single_case("2024/101", is_first_case=False)
        self.assertNotIn((100, 200), clicks)  # 'arama' koordinatı tıklanmadı!
        self.assertTrue(any(c[0] == "type" and c[3] == "2024/101" for c in clicks)) # Doğrudan dosya no yazıldı!

    def test_parse_clipboard_table_user_case_61040(self):
        """Kullanıcının 2024/2-61040 dosyasındaki 24 taksitli kaydırmalı tablosunu hatasız çözdüğünü test eder."""
        raw_clipboard_data = """Sırası\tMiktarı (TL)\tTaksit\tSon Ödeme T.\tÖdendiği Tarih
1\t2.083,41\t24\t10/11/2025\t10/10/2025
2\t2.083,33\t24\t10/12/2025\t10/11/2025
3\t2.083,33\t24\t10/01/2026\t10/12/2025
4\t2.083,33\t24\t10/02/2026\t07/01/2026
5\t2.083,33\t24\t10/03/2026\t04/02/2026
6\t2.083,33\t24\t10/04/2026\t09/03/2026
7\t2.083,33\t24\t10/05/2026\t02/04/2026
8\t2.083,33\t24\t10/06/2026\t28/04/2026
9\t2.083,33\t24\t10/07/2026\t03/06/2026
10\t2.083,33\t24\t10/08/2026\t02/07/2026
11\t2.083,33\t24\t10/09/2026\t05/08/2026
12\t2.083,33\t24\t10/10/2026\t05/09/2026
13\t2.083,33\t24\t10/11/2026\t07/10/2026
14\t2.083,33\t24\t10/12/2026\t30/10/2026
15\t2.083,33\t24\t10/01/2027\t
16\t2.083,33\t24\t10/02/2027\t
"""
        parsed = self.ocr.parse_clipboard_table(raw_clipboard_data)
        self.assertIsNotNone(parsed)
        self.assertEqual(parsed["sirasi"], "15")
        self.assertEqual(parsed["taksit_no"], "24")
        self.assertEqual(parsed["son_odeme_tarihi"], "10/01/2027")
        self.assertEqual(parsed["son_odedigi_tarih"], "30/10/2026")
        self.assertEqual(parsed["durum"], "Başarılı")

if __name__ == "__main__":
    unittest.main(verbosity=2)
