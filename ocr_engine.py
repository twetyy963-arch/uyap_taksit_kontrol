# -*- coding: utf-8 -*-
"""
UYAP Taksit Kontrol Robotu - OCR ve Tablo Çözümleme Modülü
Windows'un yerel Türkçe OCR motorunu (Windows.Media.Ocr) kullanarak
ekrandaki taksit tablosunu okur ve ilk ödenmemiş taksiti tespit eder.
"""
import os
import re
import json
import subprocess
import tempfile

class OcrEngine:
    def __init__(self, script_dir=None):
        if script_dir is None:
            script_dir = os.path.dirname(os.path.abspath(__file__))
        self.script_dir = script_dir
        self.ps1_path = os.path.join(script_dir, "win_ocr.ps1")

    def run_windows_ocr(self, image_path):
        """
        Windows yerel OCR motorunu (PowerShell üzerinden) çalıştırır.
        """
        if not os.path.exists(self.ps1_path):
            raise FileNotFoundError(f"win_ocr.ps1 bulunamadı: {self.ps1_path}")

        cmd = [
            "powershell",
            "-NoProfile",
            "-ExecutionPolicy", "Bypass",
            "-File", self.ps1_path,
            "-ImagePath", image_path
        ]

        proc = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="ignore")
        if proc.returncode != 0:
            raise RuntimeError(f"OCR hatası: {proc.stderr}")

        stdout = proc.stdout.strip()
        try:
            return json.loads(stdout)
        except Exception:
            for line in stdout.splitlines():
                line = line.strip()
                if line.startswith("{"):
                    try:
                        return json.loads(stdout[stdout.find(line):])
                    except Exception:
                        pass
            return {"Text": stdout, "Words": []}

    def cluster_words_into_lines(self, words, y_threshold=12):
        """
        Kelimeleri Y koordinatına göre satırlara gruplar ve X koordinatına göre soldan sağa sıralar.
        """
        if not words:
            return []
        sorted_words = sorted(words, key=lambda w: (w.get('Y', 0), w.get('X', 0)))
        rows = []
        for w in sorted_words:
            placed = False
            for row in rows:
                avg_y = sum(item.get('Y', 0) for item in row) / len(row)
                if abs(w.get('Y', 0) - avg_y) <= y_threshold:
                    row.append(w)
                    placed = True
                    break
            if not placed:
                rows.append([w])

        for row in rows:
            row.sort(key=lambda w: w.get('X', 0))

        rows.sort(key=lambda row: min(w.get('Y', 0) for w in row))
        return [' '.join(w.get('Text', '') for w in row) for row in rows]

    def recognize_pil_image(self, pil_img):
        """
        PIL görüntüsünü geçici bir dosyaya kaydedip OCR uygular.
        """
        with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp:
            tmp_path = tmp.name

        try:
            pil_img.save(tmp_path)
            data = self.run_windows_ocr(tmp_path)
            return data
        finally:
            if os.path.exists(tmp_path):
                try:
                    os.remove(tmp_path)
                except Exception:
                    pass

    def parse_installment_table(self, table_img):
        """
        7. Ekrandaki taksit tablosunu analiz eder.
        
        Kural:
        - Yukarıdan aşağıya satırlar taranır.
        - 'Ödendiği Tarih' sütunu kontrol edilir.
        - Dolu satırların altındaki İLK BOŞ satır tespit edilir.
        - Hiç ödenen yoksa (1. satır boşsa) doğrudan 1. satır alınır.
        - Bir önceki satırın ödenen tarihi 'son_odedigi_tarih' olarak eklenir.
        - Eğer TABLONUN TAMAMI DOLUYSA: Tüm taksitler ödenmiş demektir;
          Sırası ve Vade '-' yapılır, son ödediği tarih en son ödeme olarak yazılır
          ve Durum 'Tüm Taksitler Ödenmiş (Borç Bitti)' olarak belirtilir.
        """
        ocr_result = self.recognize_pil_image(table_img)
        words = ocr_result.get("Words", [])

        if words:
            raw_lines = self.cluster_words_into_lines(words, y_threshold=14)
        else:
            all_text = ocr_result.get("Text", "")
            raw_lines = [l.strip() for l in all_text.splitlines() if l.strip()]

        if not raw_lines:
            return {
                "sirasi": "-",
                "miktari": "-",
                "taksit_no": "-",
                "son_odeme_tarihi": "-",
                "son_odedigi_tarih": "-",
                "durum": "Taksit Tablosu Boş veya Okunamadı"
            }

        # Tarih deseni: GG.AA.YYYY veya GG/AA/YYYY
        date_pattern = re.compile(r'\b(\d{1,2}[./-]\d{1,2}[./-]\d{4})\b')
        # Para miktarı deseni: örn. 1.250,00 veya 1250,00 veya 500,00
        amount_pattern = re.compile(r'\b(\d{1,3}(?:\.\d{3})*,\d{2})\b')

        parsed_rows = []
        for line in raw_lines:
            # Başlık satırlarını atla
            if any(k in line.lower() for k in ["sıra", "miktar", "taksit", "ödendi", "vade", "tarih"]):
                continue

            dates = date_pattern.findall(line)
            amounts = amount_pattern.findall(line)

            # Bir taksit satırında en az bir tarih veya miktar olmalıdır
            if not dates and not amounts:
                continue

            # Sıra No ve Taksit No tespiti:
            cleaned = date_pattern.sub('', line)
            cleaned = amount_pattern.sub('', cleaned)
            cleaned = re.sub(r'\bTL\b', '', cleaned, flags=re.IGNORECASE)
            remaining_nums = re.findall(r'\b\d+\b', cleaned)

            sira = remaining_nums[0] if remaining_nums else "1"
            taksit = remaining_nums[1] if len(remaining_nums) > 1 else sira

            miktar = amounts[0] if amounts else "-"
            if miktar != "-" and not miktar.endswith("TL"):
                miktar = f"{miktar} TL"

            # Tarih mantığı:
            if len(dates) >= 2:
                son_odeme = dates[0]
                odendi_tarihi = dates[1]
            elif len(dates) == 1:
                son_odeme = dates[0]
                odendi_tarihi = None  # BOŞ!
            else:
                son_odeme = "-"
                odendi_tarihi = None

            parsed_rows.append({
                "sirasi": sira,
                "miktari": miktar,
                "taksit_no": taksit,
                "son_odeme_tarihi": son_odeme,
                "odendi_tarihi": odendi_tarihi
            })

        if not parsed_rows:
            return {
                "sirasi": "-",
                "miktari": "-",
                "taksit_no": "-",
                "son_odeme_tarihi": "-",
                "son_odedigi_tarih": "-",
                "durum": "Taksit Satırları Ayrıştırılamadı"
            }

        # İLK BOŞ SATIRI ARAMA VE BİR ÜSTTEKİ ÖDENEN TARİHİ ALMA
        last_paid_date = "Ödeme Yok"
        target_row = None

        for row in parsed_rows:
            if row["odendi_tarihi"] is not None:
                # Ödenmiş satır: hafızaya son ödenen tarih olarak kaydet
                last_paid_date = row["odendi_tarihi"]
            else:
                # İLK BOŞ SATIR BULUNDU!
                target_row = row
                break

        # DURUM: TABLONUN TAMAMI DOLUYSA (TÜM TAKSİTLER BİTMİŞ)
        if target_row is None:
            return {
                "sirasi": "-",
                "miktari": "-",
                "taksit_no": "-",
                "son_odeme_tarihi": "-",
                "son_odedigi_tarih": last_paid_date,
                "durum": "Tüm Taksitler Ödenmiş (Borç Bitti)"
            }

        return {
            "sirasi": target_row["sirasi"],
            "miktari": target_row["miktari"],
            "taksit_no": target_row["taksit_no"],
            "son_odeme_tarihi": target_row["son_odeme_tarihi"],
            "son_odedigi_tarih": last_paid_date,
            "durum": "Başarılı"
        }
