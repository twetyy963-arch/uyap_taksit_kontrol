# -*- coding: utf-8 -*-
"""
UYAP Taksit Kontrol Robotu - Ekran, Fare ve Klavye Yönetim Modülü
Dış kütüphane bağımlılığı olmadan (ctypes + PIL + NumPy ile) çalışabilir;
OpenCV veya PyAutoGUI kurulu ise otomatik olarak onları da kullanır.
"""
import os
import time
import ctypes
import numpy as np
from PIL import Image, ImageGrab, ImageChops, ImageStat

# DPI Farkındalığını Etkinleştir (Windows %125, %150 ölçeklendirmede piksel kaymasını önler)
try:
    ctypes.windll.shcore.SetProcessDpiAwareness(2)
except Exception:
    try:
        ctypes.windll.user32.SetProcessDPIAware()
    except Exception:
        pass

# Win32 Yapıları ve Sabitleri
user32 = ctypes.windll.user32
kernel32 = ctypes.windll.kernel32

# 64-bit Windows Uyumlu Win32 Fonksiyon İmzaları (Access Violation / Çökme Koruması)
user32.GetForegroundWindow.restype = ctypes.c_void_p
user32.GetForegroundWindow.argtypes = []

user32.GetWindowTextLengthW.restype = ctypes.c_int
user32.GetWindowTextLengthW.argtypes = [ctypes.c_void_p]

user32.GetWindowTextW.restype = ctypes.c_int
user32.GetWindowTextW.argtypes = [ctypes.c_void_p, ctypes.c_wchar_p, ctypes.c_int]

user32.OpenClipboard.argtypes = [ctypes.c_void_p]
user32.OpenClipboard.restype = ctypes.c_bool

user32.CloseClipboard.argtypes = []
user32.CloseClipboard.restype = ctypes.c_bool

user32.EmptyClipboard.argtypes = []
user32.EmptyClipboard.restype = ctypes.c_bool

user32.IsClipboardFormatAvailable.argtypes = [ctypes.c_uint]
user32.IsClipboardFormatAvailable.restype = ctypes.c_bool

user32.GetClipboardData.argtypes = [ctypes.c_uint]
user32.GetClipboardData.restype = ctypes.c_void_p

kernel32.GlobalLock.argtypes = [ctypes.c_void_p]
kernel32.GlobalLock.restype = ctypes.c_void_p

kernel32.GlobalUnlock.argtypes = [ctypes.c_void_p]
kernel32.GlobalUnlock.restype = ctypes.c_bool

# Uyku Modunu Önleme Sabitleri (Uzun süreli işlemlerde ekran kapanmasını önler)
ES_CONTINUOUS = 0x80000000
ES_SYSTEM_REQUIRED = 0x00000001
ES_DISPLAY_REQUIRED = 0x00000002

MOUSEEVENTF_LEFTDOWN = 0x0002
MOUSEEVENTF_LEFTUP = 0x0004
KEYEVENTF_KEYUP = 0x0002
KEYEVENTF_UNICODE = 0x0004

VK_BACK = 0x08
VK_RETURN = 0x0D
VK_ESCAPE = 0x1B
VK_CONTROL = 0x11
VK_A = 0x41

# OpenCV desteği kontrolü
try:
    import cv2  # type: ignore
    HAS_OPENCV = True
except (ImportError, ModuleNotFoundError):
    HAS_OPENCV = False

class ScreenController:
    def __init__(self, confidence=0.75):
        self.confidence = confidence

    def prevent_sleep(self, enable=True):
        """Uzun süren işlemlerde Windows'un uykuya geçmesini veya ekranı kapatmasını önler."""
        if enable:
            kernel32.SetThreadExecutionState(ES_CONTINUOUS | ES_SYSTEM_REQUIRED | ES_DISPLAY_REQUIRED)
        else:
            kernel32.SetThreadExecutionState(ES_CONTINUOUS)

    def grab_screen(self, bbox=None):
        """
        Tüm ekranın veya belirli bir bölgenin görüntüsünü PIL Image olarak alır.
        Windows GDI / Desktop DC meşguliyeti veya anlık ekran kilitlenmelerinde
        'OSError: screen grab failed' hatasını önlemek için yeniden deneme ve
        çökme koruması içerir.
        """
        for attempt in range(4):
            try:
                return ImageGrab.grab(bbox=bbox, all_screens=True)
            except Exception:
                try:
                    return ImageGrab.grab(bbox=bbox)
                except Exception:
                    time.sleep(0.15)

        # Son çare: Programın çökmesini önlemek için ekran boyutunda güvenli görsel dön
        try:
            w = user32.GetSystemMetrics(0)
            h = user32.GetSystemMetrics(1)
            if bbox:
                w = max(10, bbox[2] - bbox[0])
                h = max(10, bbox[3] - bbox[1])
            return Image.new("RGB", (w, h), color=(240, 240, 240))
        except Exception:
            return Image.new("RGB", (100, 100), color=(240, 240, 240))

    def get_active_window_title(self):
        """Mevcut aktif pencerenin başlığını döndürür."""
        try:
            hwnd = user32.GetForegroundWindow()
            if not hwnd:
                return ""
            length = user32.GetWindowTextLengthW(hwnd)
            if length > 0:
                buff = ctypes.create_unicode_buffer(length + 1)
                user32.GetWindowTextW(hwnd, buff, length + 1)
                return buff.value
        except Exception:
            pass
        return ""

    def wait_for_screen_change(self, bbox=None, timeout=12.0, poll_interval=0.35, min_diff=2.5, settle_time=0.8, should_stop_callback=None):
        """
        Belirtilen ekran bölgesinde (veya tüm ekranda) görsel bir değişiklik olmasını bekler.
        UYAP sorguyu ekrana getirdiğinde veya yeni pencere açıldığında bunu anında algılar.
        Değişiklik algılandıktan sonra arayüzün tam oturması için settle_time kadar bekler.

        Parametreler:
        - bbox: (x1, y1, x2, y2) veya None (tüm ekran)
        - timeout: Azami bekleme süresi (saniye)
        - poll_interval: Ekranı denetleme sıklığı (saniye)
        - min_diff: Ortalama piksel farkı eşiği (0-255 arası)
        - settle_time: Değişiklik algılandıktan sonra ekranın oturması için bekleme (saniye)
        - should_stop_callback: Durdurma isteğini denetleyen lambda/fonksiyon

        Döndürür: Değişiklik olduysa True, zaman aşımına uğradıysa False.
        """
        try:
            initial = self.grab_screen(bbox=bbox).convert('L')
        except Exception:
            time.sleep(settle_time)
            return True

        start_time = time.time()
        while time.time() - start_time < timeout:
            if should_stop_callback and should_stop_callback():
                return False

            time.sleep(poll_interval)
            try:
                current = self.grab_screen(bbox=bbox).convert('L')
                diff = ImageChops.difference(initial, current)
                stat = ImageStat.Stat(diff)
                mean_diff = stat.mean[0]
                if mean_diff >= min_diff:
                    # Ekranda belirgin bir görsel değişiklik oldu!
                    if settle_time > 0:
                        time.sleep(settle_time)
                    return True
            except Exception:
                pass

        return False

    def match_template(self, screen_img, template_img, confidence=None):
        """
        Şablon görselini ekranda arar.
        Bulursa (x, y, w, h) döndürür, bulamazsa None.
        """
        if confidence is None:
            confidence = self.confidence

        if isinstance(screen_img, str):
            screen_img = Image.open(screen_img)
        if isinstance(template_img, str):
            if not os.path.exists(template_img):
                return None
            template_img = Image.open(template_img)

        # Gri tonlamaya çevir
        s_gray = screen_img.convert('L')
        t_gray = template_img.convert('L')

        tw, th = t_gray.size
        sw, sh = s_gray.size

        if sw < tw or sh < th:
            return None

        # 1. OpenCV varsa en hızlı şekilde matchTemplate kullan
        if HAS_OPENCV:
            s_arr = np.array(s_gray)
            t_arr = np.array(t_gray)
            res = cv2.matchTemplate(s_arr, t_arr, cv2.TM_CCOEFF_NORMED)
            min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(res)
            if max_val >= confidence:
                return (max_loc[0], max_loc[1], tw, th)

            # Hafif ölçek toleransı (%90 ve %110)
            for scale in [0.9, 1.1]:
                nw, nh = int(tw * scale), int(th * scale)
                if nw > 5 and nh > 5 and nw <= sw and nh <= sh:
                    t_scaled = cv2.resize(t_arr, (nw, nh))
                    res_s = cv2.matchTemplate(s_arr, t_scaled, cv2.TM_CCOEFF_NORMED)
                    _, max_val_s, _, max_loc_s = cv2.minMaxLoc(res_s)
                    if max_val_s >= confidence:
                        return (max_loc_s[0], max_loc_s[1], nw, nh)
            return None

        # 2. OpenCV yoksa: NumPy tabanlı hızlı normalized SSD / Correlation
        s_arr = np.array(s_gray, dtype=np.float32)
        t_arr = np.array(t_gray, dtype=np.float32)

        # Hız için 2x küçülterek kaba arama yap
        step = 2
        s_small = s_arr[::step, ::step]
        t_small = t_arr[::step, ::step]
        stw, sth = t_small.shape[1], t_small.shape[0]
        ssw, ssh = s_small.shape[1], s_small.shape[0]

        if ssw < stw or ssh < sth:
            return None

        t_mean = t_small.mean()
        t_norm = t_small - t_mean
        t_std = np.linalg.norm(t_norm)
        if t_std == 0:
            return None

        best_corr = -1
        best_loc = None

        # Kayan pencere ile arama (NumPy vektörize)
        for y in range(0, ssh - sth + 1, 2):
            for x in range(0, ssw - stw + 1, 2):
                patch = s_small[y:y+sth, x:x+stw]
                p_norm = patch - patch.mean()
                p_std = np.linalg.norm(p_norm)
                if p_std > 0:
                    corr = np.sum(t_norm * p_norm) / (t_std * p_std)
                    if corr > best_corr:
                        best_corr = corr
                        best_loc = (x * step, y * step)

        if best_corr >= confidence and best_loc is not None:
            return (best_loc[0], best_loc[1], tw, th)

        return None

    def wait_for_template(self, template_path, timeout=12.0, poll_interval=0.35, confidence=None):
        """
        Belirtilen şablon ekranda belirene kadar bekler.
        Belirdiğinde merkez koordinatlarını (center_x, center_y) döndürür.
        Zaman aşımına uğrarsa None döndürür.
        """
        if not os.path.exists(template_path):
            return None

        start_time = time.time()
        while time.time() - start_time < timeout:
            screen = self.grab_screen()
            match = self.match_template(screen, template_path, confidence=confidence)
            if match:
                x, y, w, h = match
                return (x + w // 2, y + h // 2)
            time.sleep(poll_interval)
        return None

    def move_to(self, x, y):
        """Fareyi (x, y) koordinatına taşır."""
        user32.SetCursorPos(int(x), int(y))

    def click(self, x=None, y=None, delay=0.1):
        """Belirtilen koordinata veya mevcut konuma tıklar."""
        if x is not None and y is not None:
            self.move_to(x, y)
            time.sleep(0.05)
        user32.mouse_event(MOUSEEVENTF_LEFTDOWN, 0, 0, 0, 0)
        time.sleep(delay)
        user32.mouse_event(MOUSEEVENTF_LEFTUP, 0, 0, 0, 0)
        time.sleep(0.05)

    def double_click(self, x=None, y=None):
        """Çift tıklar."""
        self.click(x, y, delay=0.05)
        time.sleep(0.08)
        self.click(x, y, delay=0.05)

    def press_key(self, vk_code):
        """Tek bir tuşa basıp bırakır."""
        user32.keybd_event(vk_code, 0, 0, 0)
        time.sleep(0.05)
        user32.keybd_event(vk_code, 0, KEYEVENTF_KEYUP, 0)
        time.sleep(0.05)

    def press_esc(self):
        """ESC tuşuna basar (pencereleri kapatmak için)."""
        self.press_key(VK_ESCAPE)

    def clear_text_field(self):
        """Mevcut alandaki metni temizler (Ctrl+A, Backspace)."""
        # Ctrl Down
        user32.keybd_event(VK_CONTROL, 0, 0, 0)
        time.sleep(0.02)
        # A Down & Up
        user32.keybd_event(VK_A, 0, 0, 0)
        time.sleep(0.02)
        user32.keybd_event(VK_A, 0, KEYEVENTF_KEYUP, 0)
        time.sleep(0.02)
        # Ctrl Up
        user32.keybd_event(VK_CONTROL, 0, KEYEVENTF_KEYUP, 0)
        time.sleep(0.05)
        # Backspace
        self.press_key(VK_BACK)
        time.sleep(0.05)

    def get_clipboard_text(self):
        """
        Windows panosundaki (clipboard) metni Win32 API ile 64-bit güvenli şekilde okur.
        UYAP kopyalama yaparken oluşabilecek kilit çakışmalarını önlemek için yeniden deneme yapar.
        ctypes.wstring_at kullanarak Access Violation çökmesini %100 engeller.
        """
        CF_UNICODETEXT = 13
        text = ""

        for attempt in range(12):
            try:
                if user32.OpenClipboard(None):
                    try:
                        if user32.IsClipboardFormatAvailable(CF_UNICODETEXT):
                            h_mem = user32.GetClipboardData(CF_UNICODETEXT)
                            if h_mem:
                                data_ptr = kernel32.GlobalLock(h_mem)
                                if data_ptr:
                                    try:
                                        # 64-bit pointer'dan sıfır hatayla Unicode metin okuma
                                        val = ctypes.wstring_at(data_ptr)
                                        if val:
                                            text = val
                                            break
                                    finally:
                                        kernel32.GlobalUnlock(h_mem)
                    finally:
                        user32.CloseClipboard()
            except Exception:
                pass
            time.sleep(0.04)

        return text

    def clear_clipboard(self):
        """Windows panosunu güvenle temizler."""
        for attempt in range(6):
            try:
                if user32.OpenClipboard(None):
                    try:
                        user32.EmptyClipboard()
                        return True
                    finally:
                        user32.CloseClipboard()
            except Exception:
                pass
            time.sleep(0.03)
        return False

    def bring_window_to_front(self, keywords=None):
        """
        Başlığında belirtilen anahtar kelimeler geçen pencereyi (örneğin UYAP)
        Windows üzerinde bulur, restore eder ve ekranın en önüne getirir.
        """
        if keywords is None:
            keywords = ["uyap", "ilamat", "adli kontrol", "para ceza"]

        target_hwnd = [None]

        def enum_handler(hwnd, extra):
            if user32.IsWindowVisible(hwnd):
                length = user32.GetWindowTextLengthW(hwnd)
                if length > 0:
                    buff = ctypes.create_unicode_buffer(length + 1)
                    user32.GetWindowTextW(hwnd, buff, length + 1)
                    title = buff.value.lower()
                    if any(kw.lower() in title for kw in keywords):
                        target_hwnd[0] = hwnd
                        return False
            return True

        WNDENUMPROC = ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.c_void_p, ctypes.c_void_p)
        user32.EnumWindows(WNDENUMPROC(enum_handler), 0)

        hwnd = target_hwnd[0]
        if hwnd:
            SW_RESTORE = 9
            user32.ShowWindow(hwnd, SW_RESTORE)
            time.sleep(0.05)
            user32.SetForegroundWindow(hwnd)
            time.sleep(0.15)
            return True
        return False

    def select_all_and_copy(self, x=None, y=None):
        """
        Belirtilen alana (veya UYAP tablosuna) tıklar, panoyu temizler,
        UYAP Java Swing JTable uyumluluğu için:
        1. Tablo hücresine tıklar.
        2. Ctrl+Home ile tablonun en başına gider.
        3. Ctrl+Shift+End ile baştan sona tüm tabloyu seçer.
        4. Ctrl+C ile panoya kopyalar.
        5. Eğer yetmezse standart Ctrl+A ve Ctrl+C dener.
        """
        VK_CONTROL = 0x11
        VK_SHIFT = 0x10
        VK_HOME = 0x24
        VK_END = 0x23
        VK_C = 0x43
        VK_A = 0x41

        if x is not None and y is not None:
            self.click(x, y, delay=0.06)
            time.sleep(0.15)

        self.clear_clipboard()
        time.sleep(0.06)

        # 1. YÖNTEM: Java JTable standardı (Ctrl+Home -> Ctrl+Shift+End -> Ctrl+C)
        try:
            # Ctrl + Home
            user32.keybd_event(VK_CONTROL, 0, 0, 0)
            time.sleep(0.03)
            user32.keybd_event(VK_HOME, 0, 0, 0)
            time.sleep(0.03)
            user32.keybd_event(VK_HOME, 0, KEYEVENTF_KEYUP, 0)
            time.sleep(0.03)
            user32.keybd_event(VK_CONTROL, 0, KEYEVENTF_KEYUP, 0)
            time.sleep(0.08)

            # Ctrl + Shift + End (Tüm tablo satırlarını seç)
            user32.keybd_event(VK_CONTROL, 0, 0, 0)
            user32.keybd_event(VK_SHIFT, 0, 0, 0)
            time.sleep(0.03)
            user32.keybd_event(VK_END, 0, 0, 0)
            time.sleep(0.03)
            user32.keybd_event(VK_END, 0, KEYEVENTF_KEYUP, 0)
            time.sleep(0.03)
            user32.keybd_event(VK_SHIFT, 0, KEYEVENTF_KEYUP, 0)
            user32.keybd_event(VK_CONTROL, 0, KEYEVENTF_KEYUP, 0)
            time.sleep(0.1)

            # Ctrl + C (Kopyala)
            user32.keybd_event(VK_CONTROL, 0, 0, 0)
            time.sleep(0.03)
            user32.keybd_event(VK_C, 0, 0, 0)
            time.sleep(0.03)
            user32.keybd_event(VK_C, 0, KEYEVENTF_KEYUP, 0)
            time.sleep(0.03)
            user32.keybd_event(VK_CONTROL, 0, KEYEVENTF_KEYUP, 0)
            time.sleep(0.2)
        finally:
            user32.keybd_event(VK_SHIFT, 0, KEYEVENTF_KEYUP, 0)
            user32.keybd_event(VK_CONTROL, 0, KEYEVENTF_KEYUP, 0)

        text = self.get_clipboard_text()
        if text and len(text.strip().splitlines()) >= 2:
            return text

        # 2. YÖNTEM: Klasik Ctrl+A ve Ctrl+C (Yedek)
        try:
            user32.keybd_event(VK_CONTROL, 0, 0, 0)
            time.sleep(0.03)
            user32.keybd_event(VK_A, 0, 0, 0)
            time.sleep(0.03)
            user32.keybd_event(VK_A, 0, KEYEVENTF_KEYUP, 0)
            time.sleep(0.03)
            user32.keybd_event(VK_C, 0, 0, 0)
            time.sleep(0.03)
            user32.keybd_event(VK_C, 0, KEYEVENTF_KEYUP, 0)
            time.sleep(0.03)
            user32.keybd_event(VK_CONTROL, 0, KEYEVENTF_KEYUP, 0)
            time.sleep(0.2)
        finally:
            user32.keybd_event(VK_CONTROL, 0, KEYEVENTF_KEYUP, 0)

        return self.get_clipboard_text()

    def type_unicode(self, text, char_delay=0.03):
        """
        Türkçe karakterleri ve özel sembolleri bozmadan doğrudan Win32 Unicode ile yazar.
        """
        for char in text:
            code = ord(char)
            user32.keybd_event(0, code, KEYEVENTF_UNICODE, 0)
            time.sleep(0.01)
            user32.keybd_event(0, code, KEYEVENTF_UNICODE | KEYEVENTF_KEYUP, 0)
            time.sleep(char_delay)

    def clear_and_type(self, x, y, text):
        """Alana tıklar, mevcut yazıyı siler ve yeni metni yazar."""
        self.click(x, y)
        time.sleep(0.1)
        self.clear_text_field()
        time.sleep(0.1)
        self.type_unicode(text)
        time.sleep(0.1)

