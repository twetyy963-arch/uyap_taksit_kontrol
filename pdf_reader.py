# -*- coding: utf-8 -*-
"""
UYAP Taksit Kontrol Robotu - PDF ve Liste Ayrıştırma Modülü
TPI kodundaki dosyaların veya derdest ilamat listelerinin bulunduğu PDF'leri okur.
Harici kütüphane (pdfplumber/pypdf) olmadan da standart yerel zlib ayrıştırıcısıyla
çalışabilir; kütüphaneler varsa bunları da kullanır.

UYAP İlamat Listesi Formatı Kuralı:
1. İlk sayfada 'TPİ - TAKSİDE BAĞLANAN PARA CEZASI İLAMLARI' başlığından önceki dosyalar KESİNLİKLE ATLANIR.
2. TPİ başladığında sol sütunda yıl (2022, 2024, 2025, 2026 vb.) başta bir kez yazar;
   devam eden satırlardaki numaralar o aktif yıla bağlanarak 'YIL/2-NO' şeklinde çıkarılır.
3. Son sayfada 'VAB - VASİ ATAMASI BEKLEYEN İLAMLARI' veya başka bir infaz türü koduna
   geçildiği anda okuma DERHAL DURDURULUR; VAB altındaki dosyalar listeye ASLA dahil edilmez.
4. Sayfa altındaki tarih (7 Kasım 2026...) ve sayfa numaraları (536/573...) filtrelenir.
"""
import os
import re
import zlib

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

    @staticmethod
    def _clean_pdf_string(s):
        """PDF metin kaçış karakterlerini ve UYAP özel font kodlamalarını Türkçeleştirir."""
        s = s.replace(r'\(', '(').replace(r'\)', ')').replace(r'\\', '\\')
        s = s.replace(r'\n', '\n').replace(r'\r', '\r').replace(r'\t', ' ')
        s = re.sub(r'\\([0-7]{1,3})', lambda m: chr(int(m.group(1), 8)) if int(m.group(1), 8) < 256 else '', s)

        uyap_charmap = {
            0x12: 'İ',
            0x13: 'ı',
            0x1f: 'Ğ',
            0x1e: 'Ş',
            0x18: 'Ç',
            0x1c: 'Ö',
            0x1d: 'Ü',
            0x0e: 'ş',
            0x0f: 'ğ',
            0x08: 'ç',
            0x0c: 'ö',
            0x0d: 'ü',
        }
        return ''.join(uyap_charmap.get(ord(c), c) for c in s)

    def _extract_text_pure_python(self, file_path):
        """
        Harici paket bağımlılığı olmadan, Python yerel zlib kütüphanesiyle
        PDF içerisindeki FlateDecode ve BT...ET metin bloklarını ayrıştırır.
        Yalnızca görünür metin blokları işlenir, gömülü font ve ikili akışlar atlanır.
        """
        try:
            with open(file_path, "rb") as f:
                content = f.read()

            all_lines = []
            pos = 0
            content_len = len(content)

            while pos < content_len:
                s_idx = content.find(b"stream", pos)
                if s_idx == -1:
                    break

                start = s_idx + 6
                if content[start:start+2] == b"\r\n":
                    start += 2
                elif content[start:start+1] in (b"\n", b"\r"):
                    start += 1

                e_idx = content.find(b"endstream", start)
                if e_idx == -1:
                    break

                s_data = content[start:e_idx].rstrip(b"\r\n")
                pos = e_idx + 9

                if not s_data:
                    continue

                decompressed = None
                try:
                    decompressed = zlib.decompress(s_data)
                except Exception:
                    try:
                        decompressed = zlib.decompress(s_data, -zlib.MAX_WBITS)
                    except Exception:
                        continue

                raw_s = ""
                for enc in ["utf-8", "cp1254", "latin1", "iso-8859-9"]:
                    try:
                        raw_s = decompressed.decode(enc)
                        break
                    except Exception:
                        continue
                if not raw_s:
                    raw_s = decompressed.decode("latin1", errors="ignore")

                # BT / ET blokları: Yalnızca gerçek metin operatörlerini al
                bt_blocks = re.findall(r"BT\s*(.*?)\s*ET", raw_s, re.DOTALL)
                if not bt_blocks:
                    continue

                for block in bt_blocks:
                    # Tj operatörü: (metin) Tj
                    for tj in re.findall(r'\(((?:[^\\)]|\\.)*)\)\s*Tj', block):
                        cl = self._clean_pdf_string(tj).strip()
                        if cl:
                            all_lines.append(cl)

                    # TJ operatörü: [(metin1) offset (metin2)] TJ
                    for tj_arr in re.findall(r'\[(.*?)\]\s*TJ', block):
                        items = re.findall(r'\(((?:[^\\)]|\\.)*)\)', tj_arr)
                        joined = "".join(self._clean_pdf_string(it) for it in items).strip()
                        if joined:
                            all_lines.append(joined)

                    # Hexadecimal metinler: <00320030...> Tj
                    for hex_str in re.findall(r'<([0-9a-fA-F\s]+)>\s*Tj', block):
                        hex_clean = re.sub(r'\s+', '', hex_str)
                        if len(hex_clean) % 2 == 0:
                            try:
                                raw_bytes = bytes.fromhex(hex_clean)
                                for enc in ["utf-16-be", "utf-8", "cp1254", "latin1"]:
                                    try:
                                        dec = raw_bytes.decode(enc)
                                        if any(c.isdigit() for c in dec):
                                            all_lines.append(dec.strip())
                                            break
                                    except Exception:
                                        pass
                            except Exception:
                                pass

                    # ' veya " ile yeni satıra geçen metinler
                    for quote_str in re.findall(r'\(((?:[^\\)]|\\.)*)\)\s*[\'"]', block):
                        cl = self._clean_pdf_string(quote_str).strip()
                        if cl:
                            all_lines.append(cl)

            return "\n".join(all_lines)
        except Exception:
            return ""

    def extract_text_from_pdf(self, file_path):
        """
        PDF dosyasından metni çıkarır.
        """
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"Dosya bulunamadı: {file_path}")

        ext = os.path.splitext(file_path)[1].lower()

        # 1. Görsel dosyası ise OCR çalıştır
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

        # 2. Metin dosyası ise
        if ext in [".txt", ".csv"]:
            try:
                for enc in ["utf-8", "cp1254", "latin1"]:
                    try:
                        with open(file_path, "r", encoding=enc) as f:
                            return f.read()
                    except Exception:
                        continue
            except Exception:
                pass

        # 3. pdfplumber (kurulu ise)
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

        # 4. pypdf (kurulu ise)
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

        # 5. Yerel Python akış ayrıştırıcı
        pure_text = self._extract_text_pure_python(file_path)
        if pure_text and len(pure_text.strip()) > 0:
            return pure_text

        return ""

    def parse_case_numbers(self, raw_text):
        """
        Ham metinden TPİ ilamat numaralarını 'YIL/2-NO' şeklinde çıkarır.
        
        UYAP İlamat Listesi Yapısı:
        - İlk sayfadaki TPİ öncesi dosyalar KESİNLİKLE ATLANIR.
        - 'TPİ - TAKSİDE BAĞLANAN PARA CEZASI İLAMLARI' görüldüğünde kayıt başlar.
        - Yıl başta bir kez yazar (örn. 2022, 2024, 2025, 2026); sonraki tüm satırlar
          o aktif yılın ilamat numaralarıdır.
        - Son sayfada 'VAB - VASİ ATAMASI BEKLEYEN İLAMLARI' veya başka bir infaz türü
          başlığı görüldüğü anda okuma DERHAL DURUR.
        - Sayfa altındaki tarih (7 Kasım 2026, 14:24) ve sayfa no (536/573) filtrelenir.
        """
        if not raw_text:
            return []

        # 'Sayfa: 1 / 3' veya 'Sayfa 1' gibi açık sayfa numarası başlıklarını temizle
        raw_text = re.sub(r'Sayfa\s*:?\s*\d+\s*(?:/\s*\d+)?', '', raw_text, flags=re.IGNORECASE)

        tokens = re.findall(r'[^\s]+', raw_text)

        # Sayfa altı filtreleme (örn. 7 Kasım 2026, 14:24 ve 536/573)
        filtered = []
        i = 0
        months = {
            'ocak', 'şubat', 'subat', 'mart', 'nisan', 'mayıs', 'mayis', 'haziran',
            'temmuz', 'ağustos', 'agustos', 'eylül', 'eylul', 'ekim', 'kasım', 'kasim', 'kas', 'ara', 'aralık'
        }

        while i < len(tokens):
            tok = tokens[i].strip()
            # Tarih günü mü? (1-31 arası ve takip eden 1-7 token içinde ay adı, saat veya sayfa no var mı)
            if tok.isdigit() and 1 <= int(tok) <= 31:
                is_footer = False
                for k in range(i + 1, min(len(tokens), i + 8)):
                    t_clean = tokens[k].lower().rstrip(',')
                    if t_clean in months or ':' in tokens[k] or re.match(r'^[1-9]\d{0,2}/\d{1,3}$', tokens[k]):
                        is_footer = True
                        break
                if is_footer:
                    while i < len(tokens) and not re.match(r'^[1-9]\d{0,2}/\d{1,3}$', tokens[i].strip()):
                        i += 1
                    i += 1  # Sayfa numarasını da atla
                    continue

            # Tek başına sayfa numarası (örn 536/573, 1/12) varsa atla
            if re.match(r'^[1-9]\d{0,2}/\d{1,3}$', tok):
                i += 1
                continue

            filtered.append(tok)
            i += 1

        # Belgede TPİ başlığı var mı kontrol et
        has_tpi_header = any(
            t.upper() in ('TP', 'TPİ', 'TPI') or 'TAKSİDE' in t.upper() or 'TAKSIDE' in t.upper()
            for t in filtered
        )
        inside = not has_tpi_header  # Belgede TPİ başlığı yoksa baştan itibaren oku
        cur_year = None
        cases = []

        for tok in filtered:
            upper = tok.upper()

            # 1. Başlangıç Kontrolü: TP, TPİ veya TAKSİDE BAĞLANAN
            if upper in ('TP', 'TPİ', 'TPI') or 'TAKSİDE' in upper or 'TAKSIDE' in upper:
                inside = True
                cur_year = None
                continue

            # 2. Bitiş Kontrolü: VAB, VASİ veya sonraki infaz başlığı görüldüğünde dur
            if inside and has_tpi_header and (
                upper in ('VAB', 'DPİ', 'DPI', 'HPİ', 'HPI', 'KPİ', 'KPI') or
                'VASİ' in upper or 'VASI' in upper or 'TOPLAM' in upper
            ):
                inside = False
                break

            if not inside:
                continue

            # 3. Eğik çizgili ilamat kalıbı (örn. 2024/536 veya 2024/2-536)
            slash_match = re.search(r'\b(20\d{2})\s*[/\\-]\s*(?:2\s*[-/]\s*)?(\d{1,7})\b', tok)
            if slash_match:
                y, n = slash_match.group(1), slash_match.group(2)
                fmt = f"{y}/2-{n}"
                if fmt not in cases:
                    cases.append(fmt)
                continue

            # 4. 4 basamaklı yıl (2015-2035)
            if tok.isdigit() and len(tok) == 4 and 2015 <= int(tok) <= 2035:
                cur_year = tok
                continue

            # 5. Dosya numarası (1-7 hane)
            if tok.isdigit() and cur_year and 1 <= len(tok) <= 7:
                fmt = f"{cur_year}/2-{tok}"
                if fmt not in cases:
                    cases.append(fmt)

        return cases

    def load_case_list(self, file_path):
        """Dosyayı okuyup hazır ilamat numaraları listesi döndürür."""
        text = self.extract_text_from_pdf(file_path)
        return self.parse_case_numbers(text)
