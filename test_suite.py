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

if __name__ == "__main__":
    unittest.main(verbosity=2)
