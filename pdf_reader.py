# -*- coding: utf-8 -*-
"""
UYAP Taksit Kontrol Robotu - PDF ve Liste Ayrıştırma Modülü
TPI kodundaki dosyaların listesini içeren PDF'leri okur ve
yalnızca 'TAKSİDE BAĞLANAN PARA CEZASI İLAMLARI' başlığı altındaki
dosyaları 'YIL/2-NO' (örn. 2026/2-50, 2024/2-21843) formatında çıkarır.
Diğer başlıkları (Doğrudan para cezası, hapis vb.) kesinlikle filtreler ve atlar.
"""
import os
import re

try:
    import pdfplumber  # type: ignore
    HAS_PDFPLUMBER = True
except (ImportError, ModuleNotFoundError):
    HAS_PDFPLUMBER = False

try:
    import pypdf  # type: ignore
    HAS_PYPDF = True
except (ImportError, ModuleNotFoundError):
    HAS_PYPDF = False

class PdfReader:
    def __init__(self, ocr_engine=None):
        self.ocr_engine = ocr_engine

    def extract_text_from_pdf(self, file_path):
        """
        PDF dosyasından metni çıkarır.
        Önce Python kütüphanelerini dener, yoksa Windows OCR kullanır.
        """
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"Dosya bulunamadı: {file_path}")

        ext = os.path.splitext(file_path)[1].lower()

        # 1. Eğer dosya bir görsel ise (.png, .jpg, .jpeg, .bmp)
        if ext in [".png", ".jpg", ".jpeg", ".bmp"]:
            if self.ocr_engine:
                res = self.ocr_engine.run_windows_ocr(file_path)
                if isinstance(res, dict):
                    words = res.get("Words", [])
                    if words:
                        lines = self.ocr_engine.cluster_words_into_lines(words, y_threshold=12)
                        return "\n".join(lines)
                    return res.get("Text", "")
                elif isinstance(res, list):
                    return "\n".join(str(l) for l in res)
            return ""

        # 2. pdfplumber varsa (En yüksek doğruluk)
        if HAS_PDFPLUMBER:
            full_text = []
            try:
                with pdfplumber.open(file_path) as pdf:  # type: ignore
                    for page in pdf.pages:
                        text = page.extract_text()
                        if text:
                            full_text.append(text)
                if full_text:
                    return "\n".join(full_text)
            except Exception:
                pass

        # 3. pypdf varsa
        if HAS_PYPDF:
            full_text = []
            try:
                reader = pypdf.PdfReader(file_path)  # type: ignore
                for page in reader.pages:
                    text = page.extract_text()
                    if text:
                        full_text.append(text)
                if full_text:
                    return "\n".join(full_text)
            except Exception:
                pass

        # 4. Metin dosyası (.txt) ise
        if ext == ".txt":
            try:
                with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                    return f.read()
            except Exception:
                pass

        return ""

    def parse_case_numbers(self, raw_text):
        """
        Ham metinden ilamat numaralarını 'YIL/2-NO' şeklinde çıkarır.
        
        Kritik Kural:
        - SADECE 'TAKSİDE BAĞLANAN PARA CEZASI İLAMLARI' veya 'TPİ' başlığı altındaki dosyalar alınır.
        - Başka bir başlığa geçildiğinde (örn. 'DOĞRUDAN', 'HAPİS', 'DİĞER İLAMLAR' vb.) okuma durdurulur/atlanır.
        - Sol sütundaki YIL (örn. 2022, 2024, 2025) hafızada tutulur.
        - Devam eden satırlardaki numaralar da mevcut aktif yıla bağlanır.
        """
        case_numbers = []
        current_year = None
        inside_target_section = False

        # Başlık tanıma regexleri
        target_section_pattern = re.compile(r'(?:tp[iİ]|taks[iİ]de\s+ba[gğ]lanan)', re.IGNORECASE)

        lines = raw_text.splitlines()
        for line in lines:
            line_clean = line.strip()
            if not line_clean:
                continue

            # 1. Hedef başlık kontrolü: 'TPİ' veya 'TAKSİDE BAĞLANAN' gördük mü?
            if target_section_pattern.search(line_clean):
                inside_target_section = True
                current_year = None
                continue

            # 2. Farklı bir bölüme mi geçildi?
            if inside_target_section:
                has_digits = bool(re.search(r'\d', line_clean))
                # Rakam içermeyen veya belirgin başlık formatındaki satırlar
                if not has_digits and len(line_clean) > 8:
                    if not target_section_pattern.search(line_clean):
                        # Farklı bir başlığa geçildi, hedef bölümden çık!
                        inside_target_section = False
                        current_year = None
                        continue

            # Eğer hedef bölüm içinde değilsek bu satırdaki dosyaları atla
            if not inside_target_section:
                continue

            # 3. Satırdaki tüm tam sayıları bul
            nums = re.findall(r'\b\d+\b', line_clean)
            if not nums:
                continue

            # İlk sayı 4 haneli bir yıl mı? (örn. 2015 - 2035)
            first_num = nums[0]
            if len(first_num) == 4 and 2015 <= int(first_num) <= 2035:
                current_year = first_num
                file_nums = nums[1:]
            else:
                # Başında yıl yoksa, mevcut aktif yılın devam eden satırıdır
                file_nums = nums

            if current_year:
                for fn in file_nums:
                    if 1 <= len(fn) <= 7:
                        formatted = f"{current_year}/2-{fn}"
                        case_numbers.append(formatted)

        # Eğer belgede hiç açık 'TPİ' başlığı bulunamadıysa:
        if not case_numbers and not inside_target_section:
            return self._fallback_parse_cases(raw_text)

        return case_numbers

    def _fallback_parse_cases(self, raw_text):
        """Başlık bulunamazsa düz metindeki ilamat numaralarını çıkarır."""
        case_numbers = []
        current_year = None
        for line in raw_text.splitlines():
            line = line.strip()
            if not line:
                continue
            nums = re.findall(r'\b\d+\b', line)
            if not nums:
                continue
            first_num = nums[0]
            if len(first_num) == 4 and 2015 <= int(first_num) <= 2035:
                current_year = first_num
                file_nums = nums[1:]
            else:
                file_nums = nums
            if current_year:
                for fn in file_nums:
                    if 1 <= len(fn) <= 7:
                        case_numbers.append(f"{current_year}/2-{fn}")
        return case_numbers

    def load_case_list(self, file_path):
        """Dosyayı okuyup hazır ilamat numaraları listesi döndürür."""
        text = self.extract_text_from_pdf(file_path)
        return self.parse_case_numbers(text)
