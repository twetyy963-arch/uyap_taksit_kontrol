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
            return {"Text": "", "Words": []}

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

    @staticmethod
    def normalize_text(text):
        """Türkçe karakterleri ve noktalama işaretlerini arama için standartlaştırır."""
        t = str(text).lower()
        mapping = {
            'ı': 'i', 'İ': 'i', 'ğ': 'g', 'Ğ': 'g', 'ü': 'u', 'Ü': 'u',
            'ş': 's', 'Ş': 's', 'ö': 'o', 'Ö': 'o', 'ç': 'c', 'Ç': 'c'
        }
        for k, v in mapping.items():
            t = t.replace(k, v)
        return re.sub(r'[^a-z0-9]', '', t)

    @classmethod
    def is_word_match(cls, w_text, cand_word):
        """
        Kelimeleri esnek şekilde karşılaştırır (tam eşleşme, ek alma toleransı).
        Rastgele küçük harf gürültülerine (3 harf altı) eşleşmeyi engeller.
        """
        nw = cls.normalize_text(w_text)
        nc = cls.normalize_text(cand_word)
        if not nw or not nc:
            return False
        if nw == nc:
            return True
        # En az 4 harfliyse ve başlangıçları uyuşuyorsa (ek alma toleransı: dosya/dosyası, infaz/infazı)
        if len(nw) >= 4 and len(nc) >= 4:
            if nw.startswith(nc) or nc.startswith(nw):
                return True
        return False

    def find_text_coordinates(self, image_or_data, candidates):
        """
        Görüntüde veya OCR veri sözlüğünde verilen aday metinleri arar.
        Buton isimlerindeki ufak takı / harf farklarına takılmaz (İlamat Dosya vs İlamat Dosyası).
        İlk eşleşen metnin merkez koordinatlarını (cx, cy, width, height) döndürür.
        """
        if isinstance(image_or_data, dict):
            ocr_data = image_or_data
        else:
            ocr_data = self.recognize_pil_image(image_or_data)

        words = ocr_data.get('Words', [])
        if not words or not candidates:
            return None

        sorted_words = sorted(words, key=lambda w: (w.get('Y', 0), w.get('X', 0)))

        # 1. Çok kelimeli adayları esnek ara (örn: 'ilamat dosya arama', 'dosya arama')
        for cand in candidates:
            cand_words = cand.split()
            if len(cand_words) >= 2:
                for i in range(len(sorted_words) - len(cand_words) + 1):
                    window = sorted_words[i:i + len(cand_words)]
                    # Aynı satırda olma toleransı (25 piksel Y farkı)
                    y_diff = max(w.get('Y', 0) for w in window) - min(w.get('Y', 0) for w in window)
                    if y_diff > 25:
                        continue
                    match = True
                    for w, cw in zip(window, cand_words):
                        if not self.is_word_match(w.get('Text', ''), cw):
                            match = False
                            break
                    if match:
                        min_x = min(w.get('X', 0) for w in window)
                        max_x = max(w.get('X', 0) + w.get('W', 0) for w in window)
                        min_y = min(w.get('Y', 0) for w in window)
                        max_y = max(w.get('Y', 0) + w.get('H', 0) for w in window)
                        cx = (min_x + max_x) // 2
                        cy = (min_y + max_y) // 2
                        return (cx, cy, max_x - min_x, max_y - min_y)

        # 2. Tek kelimelik adayları esnek ara (örn: 'sorgula', 'arama', 'ilamat')
        for cand in candidates:
            for w in words:
                # Çok küçük piksel gürültülerini (noise) atla
                if w.get('W', 0) < 18 or w.get('H', 0) < 8:
                    continue
                if self.is_word_match(w.get('Text', ''), cand):
                    cx = w.get('X', 0) + w.get('W', 0) // 2
                    cy = w.get('Y', 0) + w.get('H', 0) // 2
                    return (cx, cy, w.get('W', 0), w.get('H', 0))

        return None

    def parse_clipboard_table(self, clipboard_text):
        """
        UYAP taksit tablosundan Ctrl+A + Ctrl+C veya Ctrl+Home + Ctrl+Shift+End + Ctrl+C
        ile panoya kopyalanan metni ayrıştırır.
        
        KULLANICI KURALI:
        1. 'Ödendiği Tarih' sütununda EN SON DOLU olan satır bulunur.
        2. Hafızaya bu en son dolu satırın HEMEN ALTINDAKİ satır alınır
           (Sırası, Miktarı, Taksit No, Son Ödeme Tarihi / Vade).
        3. 'Son Ödediği Tarih' sütununa ise o en son dolu satırdaki ödeme tarihi yazılır.
        4. Eğer hiç ödeme yoksa (1. satır da boşsa): 1. taksit satırı alınır, Son Ödediği Tarih: 'Ödeme Yok'.
        5. 'Tüm Taksitler Ödenmiş' kararı: Yalnızca en son ödenen taksit sıra numarası
           toplam taksit sayısına (örn: 24/24) ulaştığında verilir!
        """
        if not clipboard_text or not clipboard_text.strip():
            return None

        lines = [l.strip('\r') for l in clipboard_text.strip().split('\n') if l.strip()]
        if not lines:
            return None

        # Tarih deseni: GG.AA.YYYY veya GG/AA/YYYY (aradaki boşluklara toleranslı)
        date_regex = re.compile(r'(\d{1,2}\s*[./-]\s*\d{1,2}\s*[./-]\s*\d{4})')
        amount_pattern = re.compile(r'\b(\d{1,3}(?:\.\d{3})*,\d{2})\b')
        parsed_rows = []

        for line in lines:
            low = line.lower()
            # Başlık satırını atla (tarih içermeyen başlıklar)
            if any(k in low for k in ["sıra", "miktar", "taksit", "ödendi", "vade", "tarih"]) and not date_regex.search(line):
                continue

            raw_dates = date_regex.findall(line)
            # Tarihleri normalize et (boşlukları temizle)
            dates = [re.sub(r'\s+', '', d) for d in raw_dates]

            parts = [p.strip() for p in line.split('\t')]
            if len(parts) < 4:
                parts = [p.strip() for p in re.split(r'\s{2,}', line)]

            # Eğer satırda hiç tarih yoksa ve parça sayısı yetersizse atla
            if not dates and len(parts) < 4:
                continue

            sira = parts[0] if parts and parts[0].isdigit() else "-"
            # Miktar tespiti
            amounts = amount_pattern.findall(line)
            miktar = amounts[0] if amounts else (parts[1] if len(parts) > 1 and ',' in parts[1] else "-")
            if miktar != "-" and not miktar.endswith("TL"):
                miktar = f"{miktar} TL"

            taksit = "-"
            for p in parts[1:]:
                if p.isdigit() and p != sira:
                    taksit = p
                    break

            # Son Ödeme Tarihi (Vade) ve Ödendiği Tarih tespiti:
            # 1. Önce doğrudan sütun indeksinden dene (parts[3] = Vade, parts[4] = Ödendiği Tarih)
            son_odeme = "-"
            odendi = ""

            if len(parts) >= 4 and date_regex.search(parts[3]):
                son_odeme = re.sub(r'\s+', '', parts[3].strip())
                if len(parts) >= 5 and date_regex.search(parts[4]):
                    odendi = re.sub(r'\s+', '', parts[4].strip())
            elif dates:
                # Sütun bölünememişse regex ile çıkarılan tarihlerden al
                son_odeme = dates[0]
                odendi = dates[1] if len(dates) >= 2 else ""

            if son_odeme != "-" or dates:
                parsed_rows.append({
                    "sirasi": sira,
                    "miktari": miktar,
                    "taksit_no": taksit,
                    "son_odeme_tarihi": son_odeme if son_odeme != "-" else (dates[0] if dates else "-"),
                    "odendi_tarihi": odendi
                })

        if not parsed_rows:
            return None

        # 1. En son ödenen (ödendiği tarih dolu olan) satırı tespit et
        last_paid_idx = -1
        last_paid_date = "Ödeme Yok"
        for idx, row in enumerate(parsed_rows):
            if row["odendi_tarihi"]:
                last_paid_idx = idx
                last_paid_date = row["odendi_tarihi"]

        # 2. En son dolu olanın HEMEN ALTINDAKİ satırı hedef taksit satırı olarak al
        target_idx = last_paid_idx + 1

        if target_idx < len(parsed_rows):
            # Henüz ödenmemiş taksit satırı bulundu!
            target_row = parsed_rows[target_idx]
            return {
                "sirasi": target_row["sirasi"],
                "miktari": target_row["miktari"],
                "taksit_no": target_row["taksit_no"],
                "son_odeme_tarihi": target_row["son_odeme_tarihi"],
                "son_odedigi_tarih": last_paid_date,  # Sadece son dolu olan ödendiği tarih!
                "durum": "Başarılı"
            }
        else:
            # Hedef satır tablonun sınırını aştı.
            # GERÇEKTEN BORÇ BİTTİ Mİ KONTROLÜ:
            is_finished = False
            if last_paid_idx >= 0:
                last_row = parsed_rows[last_paid_idx]
                sira_val = int(last_row["sirasi"]) if str(last_row["sirasi"]).isdigit() else 0
                taksit_val = int(last_row["taksit_no"]) if str(last_row["taksit_no"]).isdigit() else 0

                # Eğer en son ödenen taksit toplam taksit sayısına ulaştıysa (örn: 24/24) borç bitmiştir!
                if taksit_val > 0 and sira_val >= taksit_val:
                    is_finished = True
                elif taksit_val == 0:
                    is_finished = True

            if is_finished:
                return {
                    "sirasi": "-",
                    "miktari": "-",
                    "taksit_no": "-",
                    "son_odeme_tarihi": "-",
                    "son_odedigi_tarih": last_paid_date,
                    "durum": "Tüm Taksitler Ödenmiş (Borç Bitti)"
                }
            else:
                # Tablonun kopyalanan satırlarının hepsi dolu olsa bile toplam taksit bitmemiş!
                last_row = parsed_rows[last_paid_idx] if last_paid_idx >= 0 else parsed_rows[-1]
                sira_val = int(last_row["sirasi"]) if str(last_row["sirasi"]).isdigit() else len(parsed_rows)
                next_sira = str(sira_val + 1)
                return {
                    "sirasi": next_sira,
                    "miktari": last_row["miktari"],
                    "taksit_no": last_row["taksit_no"],
                    "son_odeme_tarihi": "Sonraki Vade Bekleniyor",
                    "son_odedigi_tarih": last_paid_date,
                    "durum": "Başarılı"
                }

    def parse_installment_table(self, table_img):
        """
        Ekrandaki taksit tablosunu Windows OCR ile okur ve aynı kuralı uygular:
        1. 'Ödendiği Tarih' sütununda en son dolu olan satır bulunur.
        2. Bu satırın altındaki satır hafızaya alınır (Sırası, Miktarı, Taksit No, Son Ödeme Tarihi).
        3. Son Ödediği Tarih olarak ise sadece o son dolu olan tarih alınır.
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

        date_pattern = re.compile(r'\b(\d{1,2}[./-]\d{1,2}[./-]\d{4})\b')
        amount_pattern = re.compile(r'\b(\d{1,3}(?:\.\d{3})*,\d{2})\b')

        parsed_rows = []
        for line in raw_lines:
            low = line.lower()
            # Başlık satırlarını atla
            if any(k in low for k in ["sıra", "miktar", "taksit", "ödendi", "vade", "tarih"]) and not date_pattern.search(line):
                continue

            dates = date_pattern.findall(line)
            amounts = amount_pattern.findall(line)

            if not dates and not amounts:
                continue

            # Sıra No ve Taksit No tespiti:
            cleaned = date_pattern.sub('', line)
            cleaned = amount_pattern.sub('', cleaned)
            cleaned = re.sub(r'\bTL\b', '', cleaned, flags=re.IGNORECASE)
            remaining_nums = re.findall(r'\b\d+\b', cleaned)

            sira = remaining_nums[0] if remaining_nums else "-"
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
                odendi_tarihi = ""  # BOŞ!
            else:
                son_odeme = "-"
                odendi_tarihi = ""

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

        # En son ödenen satırı bul
        last_paid_idx = -1
        last_paid_date = "Ödeme Yok"
        for idx, row in enumerate(parsed_rows):
            if row["odendi_tarihi"]:
                last_paid_idx = idx
                last_paid_date = row["odendi_tarihi"]

        # En son dolu olanın HEMEN ALTINDAKİ satırı al
        target_idx = last_paid_idx + 1

        if target_idx < len(parsed_rows):
            target_row = parsed_rows[target_idx]
            return {
                "sirasi": target_row["sirasi"],
                "miktari": target_row["miktari"],
                "taksit_no": target_row["taksit_no"],
                "son_odeme_tarihi": target_row["son_odeme_tarihi"],
                "son_odedigi_tarih": last_paid_date,
                "durum": "Başarılı"
            }
        else:
            return {
                "sirasi": "-",
                "miktari": "-",
                "taksit_no": "-",
                "son_odeme_tarihi": "-",
                "son_odedigi_tarih": last_paid_date,
                "durum": "Tüm Taksitler Ödenmiş (Borç Bitti)"
            }
