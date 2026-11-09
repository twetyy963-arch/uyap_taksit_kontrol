# -*- coding: utf-8 -*-
"""
UYAP Taksit Kontrol Robotu - Modern Kullanıcı Arayüzü (GUI)
Tkinter ve ttk ile modern, tepkisel, önizlemeli ve kullanıcı dostu masaüstü arayüzü.
"""
import os
import time
import json
import threading
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import pandas as pd
import ctypes
from ctypes import wintypes
import winsound

user32 = ctypes.windll.user32

from config import DEFAULT_IMAGE_DIR, DEFAULT_EXCEL_OUTPUT, STARTUP_COUNTDOWN, IMAGE_FILES, USER_DESKTOP, resolve_image_file
from pdf_reader import PdfReader
from ocr_engine import OcrEngine
from uyap_bot import UyapBot

STATE_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "son_durum.json")

class UyapApp(tk.Tk):
    def __init__(self):
        super().__init__()

        self.title("UYAP Taksitli Dosya Kontrol Robotu")
        self.geometry("1100x750")
        self.minsize(950, 620)

        # Temel Nesneler
        self.current_image_dir = DEFAULT_IMAGE_DIR
        self.ocr_engine = OcrEngine()
        self.pdf_reader = PdfReader(ocr_engine=self.ocr_engine)
        self.bot = UyapBot(image_dir=self.current_image_dir, ocr_engine=self.ocr_engine)

        self.loaded_cases = []
        self.loaded_raw_text = ""
        self.results_data = []
        self.worker_thread = None

        # Stil ve Arayüz Kurulumu
        self._setup_style()
        self._create_widgets()
        self._check_image_dir_status()
        self._update_calib_status_label()

        # Global Klavye Kısayolu (ESC / F5 ile Her Yerden Durdurma ve Pencereyi Öne Getirme)
        self.bind("<Escape>", lambda e: self._handle_esc_press())
        self.bind("<F5>", lambda e: self._handle_esc_press())
        self._start_hotkey_listener()

    def _setup_style(self):
        self.configure(bg="#F4F6F9")
        self.style = ttk.Style(self)
        try:
            self.style.theme_use("clam")
        except Exception:
            pass

        # Renk Paleti
        self.COLOR_PRIMARY = "#1E88E5"
        self.COLOR_SUCCESS = "#2E7D32"
        self.COLOR_DANGER = "#C62828"
        self.COLOR_DARK = "#263238"
        self.COLOR_BG = "#F4F6F9"
        self.COLOR_CARD = "#FFFFFF"

        # Tablo Stili
        self.style.configure(
            "Treeview.Heading",
            font=("Segoe UI", 10, "bold"),
            background="#ECEFF1",
            foreground="#37474F",
            padding=6
        )
        self.style.configure(
            "Treeview",
            font=("Segoe UI", 10),
            rowheight=26,
            background="#FFFFFF",
            fieldbackground="#FFFFFF"
        )
        self.style.map("Treeview", background=[("selected", "#BBDEFB")], foreground=[("selected", "#0D47A1")])

        # Sekme (Notebook) Stili
        self.style.configure(
            "TNotebook.Tab",
            font=("Segoe UI", 10, "bold"),
            padding=[14, 6],
            background="#CFD8DC",
            foreground="#37474F"
        )
        self.style.map("TNotebook.Tab", background=[("selected", "#1E88E5")], foreground=[("selected", "#FFFFFF")])

    def _create_widgets(self):
        # 1. BAŞLIK PANELİ
        header_frame = tk.Frame(self, bg=self.COLOR_DARK, height=70)
        header_frame.pack(fill=tk.X, side=tk.TOP)

        title_lbl = tk.Label(
            header_frame,
            text="⚖ UYAP Taksitli Dosya Kontrol Robotu",
            font=("Segoe UI", 16, "bold"),
            fg="#FFFFFF",
            bg=self.COLOR_DARK
        )
        title_lbl.pack(anchor="w", padx=20, pady=(12, 2))

        subtitle_lbl = tk.Label(
            header_frame,
            text="TPI İlamat Listesi Otomatik Kontrol, OCR Tablo Okuma, Liste Önizleme ve Excel Raporlama",
            font=("Segoe UI", 9),
            fg="#B0BEC5",
            bg=self.COLOR_DARK
        )
        subtitle_lbl.pack(anchor="w", padx=20, pady=(0, 10))

        # 2. ANA İÇERİK KONTEYNERİ
        main_container = tk.Frame(self, bg=self.COLOR_BG)
        main_container.pack(fill=tk.BOTH, expand=True, padx=15, pady=12)

        # Üst Kontrol Kartı (Dosya Seçimi + Butonlar)
        control_card = tk.LabelFrame(
            main_container,
            text=" Kontrol ve Dosya Seçimi ",
            font=("Segoe UI", 10, "bold"),
            bg=self.COLOR_CARD,
            fg=self.COLOR_DARK,
            padx=12,
            pady=10
        )
        control_card.pack(fill=tk.X, pady=(0, 10))

        # Dosya Seçme Satırı
        file_row = tk.Frame(control_card, bg=self.COLOR_CARD)
        file_row.pack(fill=tk.X, pady=4)

        self.btn_select_file = tk.Button(
            file_row,
            text="📁 PDF / Liste Dosyası Seç",
            font=("Segoe UI", 10, "bold"),
            bg=self.COLOR_PRIMARY,
            fg="#FFFFFF",
            activebackground="#1565C0",
            relief=tk.FLAT,
            padx=14,
            pady=6,
            cursor="hand2",
            command=self.select_pdf_file
        )
        self.btn_select_file.pack(side=tk.LEFT, padx=(0, 10))

        self.lbl_file_status = tk.Label(
            file_row,
            text="Henüz dosya seçilmedi.",
            font=("Segoe UI", 10),
            bg=self.COLOR_CARD,
            fg="#546E7A"
        )
        self.lbl_file_status.pack(side=tk.LEFT, padx=5)

        # Buton Görselleri ve Algılama Modu Satırı
        image_row = tk.Frame(control_card, bg=self.COLOR_CARD)
        image_row.pack(fill=tk.X, pady=(4, 2))

        self.btn_select_images = tk.Button(
            image_row,
            text="🖼 Görseller Klasörü",
            font=("Segoe UI", 9, "bold"),
            bg="#546E7A",
            fg="#FFFFFF",
            relief=tk.FLAT,
            padx=10,
            pady=4,
            cursor="hand2",
            command=self.select_image_folder
        )
        self.btn_select_images.pack(side=tk.LEFT, padx=(0, 10))

        self.lbl_image_status = tk.Label(
            image_row,
            text="Görseller taranıyor...",
            font=("Segoe UI", 9),
            bg=self.COLOR_CARD,
            fg="#37474F"
        )
        self.lbl_image_status.pack(side=tk.LEFT, padx=5)

        self.btn_test_screen = tk.Button(
            image_row,
            text="🔍 UYAP Ekranını Test Et",
            font=("Segoe UI", 9, "bold"),
            bg="#00838F",
            fg="#FFFFFF",
            relief=tk.FLAT,
            padx=10,
            pady=4,
            cursor="hand2",
            command=self.test_screen_detection_dialog
        )
        self.btn_test_screen.pack(side=tk.RIGHT, padx=5)

        # Manuel Kalibrasyon (Ekranda Yer Gösterme) Satırı
        calib_row = tk.Frame(control_card, bg=self.COLOR_CARD)
        calib_row.pack(fill=tk.X, pady=(4, 2))

        self.btn_open_calib = tk.Button(
            calib_row,
            text="🎯 Ekranda Yerleri Göster (Kalibrasyon Sihirbazı)",
            font=("Segoe UI", 9, "bold"),
            bg="#6A1B9A",
            fg="#FFFFFF",
            activebackground="#4A148C",
            relief=tk.FLAT,
            padx=12,
            pady=4,
            cursor="hand2",
            command=self.open_calibration_wizard
        )
        self.btn_open_calib.pack(side=tk.LEFT, padx=(0, 10))

        self.lbl_calib_status = tk.Label(
            calib_row,
            text="Kalibrasyon durumu kontrol ediliyor...",
            font=("Segoe UI", 9, "bold"),
            bg=self.COLOR_CARD,
            fg="#37474F"
        )
        self.lbl_calib_status.pack(side=tk.LEFT, padx=5)

        self.btn_clear_calib = tk.Button(
            calib_row,
            text="🗑 Sıfırla",
            font=("Segoe UI", 8),
            bg="#ECEFF1",
            fg="#546E7A",
            relief=tk.FLAT,
            padx=6,
            pady=2,
            cursor="hand2",
            command=self.clear_calibration
        )
        self.btn_clear_calib.pack(side=tk.LEFT, padx=5)

        # Çalışma Hızı ve UYAP Donma Koruması Satırı
        # Otomatik Akıllı Hız Modu Bilgisi
        speed_row = tk.Frame(control_card, bg=self.COLOR_CARD)
        speed_row.pack(fill=tk.X, pady=(6, 2))

        lbl_speed = tk.Label(
            speed_row,
            text="⚡ Çalışma Modu: Akıllı Dinamik Takip (UYAP Ekranı Geldikçe Otomatik İlerler - Boş Bekleme Yok)",
            font=("Segoe UI", 9, "bold"),
            bg="#E8F5E9",
            fg="#2E7D32",
            padx=10,
            pady=4,
            relief=tk.FLAT
        )
        lbl_speed.pack(side=tk.LEFT)

        self.speed_var = tk.StringVar(value="hizli")

        # Eylem Butonları Satırı
        btn_row = tk.Frame(control_card, bg=self.COLOR_CARD)
        btn_row.pack(fill=tk.X, pady=(10, 4))

        self.btn_start = tk.Button(
            btn_row,
            text="▶ Kontrolü Başlat",
            font=("Segoe UI", 11, "bold"),
            bg=self.COLOR_SUCCESS,
            fg="#FFFFFF",
            activebackground="#1B5E20",
            relief=tk.FLAT,
            padx=18,
            pady=6,
            cursor="hand2",
            state=tk.DISABLED,
            command=self.start_automation
        )
        self.btn_start.pack(side=tk.LEFT, padx=(0, 8))

        self.btn_restart = tk.Button(
            btn_row,
            text="🔄 Baştan Başlat",
            font=("Segoe UI", 10, "bold"),
            bg="#546E7A",
            fg="#FFFFFF",
            activebackground="#37474F",
            relief=tk.FLAT,
            padx=12,
            pady=6,
            cursor="hand2",
            state=tk.DISABLED,
            command=lambda: self.start_automation(force_restart=True)
        )
        self.btn_restart.pack(side=tk.LEFT, padx=(0, 8))

        self.btn_view_preview = tk.Button(
            btn_row,
            text="📋 Yüklenen Listeyi İncele",
            font=("Segoe UI", 10, "bold"),
            bg="#0288D1",
            fg="#FFFFFF",
            activebackground="#0277BD",
            relief=tk.FLAT,
            padx=12,
            pady=6,
            cursor="hand2",
            state=tk.DISABLED,
            command=lambda: self.notebook.select(self.tab_preview)
        )
        self.btn_view_preview.pack(side=tk.LEFT, padx=(0, 8))

        self.btn_stop = tk.Button(
            btn_row,
            text="⏹ Durdur (ESC)",
            font=("Segoe UI", 11, "bold"),
            bg=self.COLOR_DANGER,
            fg="#FFFFFF",
            activebackground="#B71C1C",
            relief=tk.FLAT,
            padx=16,
            pady=6,
            cursor="hand2",
            state=tk.DISABLED,
            command=self.stop_automation
        )
        self.btn_stop.pack(side=tk.LEFT, padx=(0, 8))

        self.btn_export = tk.Button(
            btn_row,
            text="📊 Canlı Sonuçları Excel'e Aktar",
            font=("Segoe UI", 10, "bold"),
            bg="#37474F",
            fg="#FFFFFF",
            activebackground="#263238",
            relief=tk.FLAT,
            padx=14,
            pady=6,
            cursor="hand2",
            state=tk.DISABLED,
            command=self.export_excel
        )
        self.btn_export.pack(side=tk.RIGHT)

        # Şuradan İtibaren Sorgula (Başlangıç Noktası Seçimi)
        start_opt_frame = tk.Frame(control_card, bg=self.COLOR_CARD)
        start_opt_frame.pack(fill=tk.X, pady=(6, 2))

        tk.Label(
            start_opt_frame,
            text="📍 Şuradan İtibaren Sorgula:",
            font=("Segoe UI", 9, "bold"),
            bg=self.COLOR_CARD,
            fg="#1565C0"
        ).pack(side=tk.LEFT, padx=(0, 6))

        self.start_from_var = tk.StringVar(value="1")
        self.entry_start_from = ttk.Entry(start_opt_frame, textvariable=self.start_from_var, width=18, font=("Segoe UI", 9, "bold"))
        self.entry_start_from.pack(side=tk.LEFT, padx=(0, 6))

        tk.Label(
            start_opt_frame,
            text="(İster Sıra No: örn: 250, ister Dosya No: örn: 2024/2-61040 yazabilirsiniz)",
            font=("Segoe UI", 8),
            bg=self.COLOR_CARD,
            fg="#78909C"
        ).pack(side=tk.LEFT)

        # İlerleme Çubuğu ve Durum
        progress_row = tk.Frame(control_card, bg=self.COLOR_CARD)
        progress_row.pack(fill=tk.X, pady=(8, 2))

        self.progress_bar = ttk.Progressbar(progress_row, orient="horizontal", mode="determinate")
        self.progress_bar.pack(fill=tk.X, side=tk.TOP, pady=2)

        self.lbl_progress = tk.Label(
            progress_row,
            text="Durum: Bekliyor",
            font=("Segoe UI", 9),
            bg=self.COLOR_CARD,
            fg="#455A64"
        )
        self.lbl_progress.pack(anchor="w")

        # 3. ORTA BÖLÜM: SEKME PANELİ (NOTEBOOK) VE LOG PANELİ (PanedWindow)
        paned = tk.PanedWindow(main_container, orient=tk.VERTICAL, bg=self.COLOR_BG, sashwidth=4)
        paned.pack(fill=tk.BOTH, expand=True)

        self.notebook = ttk.Notebook(paned)
        paned.add(self.notebook, height=360)

        # -------------------------------------------------------------
        # SEKME 1: YÜKLENEN DOSYA LİSTESİ ÖNİZLEME (PREVIEW TAB)
        # -------------------------------------------------------------
        self.tab_preview = ttk.Frame(self.notebook)
        self.notebook.add(self.tab_preview, text=" 📋 Yüklenen Dosya Listesi (Önizleme) ")

        # Önizleme Üst Filtre / Arama Araç Çubuğu
        preview_toolbar = tk.Frame(self.tab_preview, bg=self.COLOR_CARD, padx=8, pady=6)
        preview_toolbar.pack(fill=tk.X, side=tk.TOP)

        tk.Label(
            preview_toolbar,
            text="🔍 Listede Ara:",
            font=("Segoe UI", 10, "bold"),
            bg=self.COLOR_CARD,
            fg=self.COLOR_DARK
        ).pack(side=tk.LEFT, padx=(0, 6))

        self.preview_search_var = tk.StringVar()
        self.preview_search_var.trace_add("write", self._filter_preview_tree)
        self.entry_preview_search = ttk.Entry(preview_toolbar, textvariable=self.preview_search_var, width=25, font=("Segoe UI", 10))
        self.entry_preview_search.pack(side=tk.LEFT, padx=(0, 15))

        self.lbl_preview_count = tk.Label(
            preview_toolbar,
            text="Henüz dosya yüklenmedi (0 Dosya)",
            font=("Segoe UI", 10, "bold"),
            bg=self.COLOR_CARD,
            fg=self.COLOR_PRIMARY
        )
        self.lbl_preview_count.pack(side=tk.LEFT, padx=5)

        self.btn_start_from_selected = tk.Button(
            preview_toolbar,
            text="▶ Seçili Dosyadan İtibaren Başlat",
            font=("Segoe UI", 9, "bold"),
            bg="#2E7D32",
            fg="#FFFFFF",
            relief=tk.FLAT,
            padx=10,
            pady=3,
            cursor="hand2",
            command=self._start_from_selected_preview
        )
        self.btn_start_from_selected.pack(side=tk.LEFT, padx=12)

        self.btn_export_preview = tk.Button(
            preview_toolbar,
            text="📥 Bu Listeyi Excel'e Aktar",
            font=("Segoe UI", 9, "bold"),
            bg="#455A64",
            fg="#FFFFFF",
            relief=tk.FLAT,
            padx=10,
            pady=3,
            cursor="hand2",
            command=self._export_preview_to_excel
        )
        self.btn_export_preview.pack(side=tk.RIGHT, padx=4)

        self.btn_copy_preview = tk.Button(
            preview_toolbar,
            text="📋 Numaraları Kopyala",
            font=("Segoe UI", 9, "bold"),
            bg="#546E7A",
            fg="#FFFFFF",
            relief=tk.FLAT,
            padx=10,
            pady=3,
            cursor="hand2",
            command=self._copy_preview_numbers
        )
        self.btn_copy_preview.pack(side=tk.RIGHT, padx=4)

        # Önizleme Tablosu Frame
        preview_table_frame = tk.Frame(self.tab_preview, bg=self.COLOR_CARD)
        preview_table_frame.pack(fill=tk.BOTH, expand=True, padx=4, pady=4)

        preview_cols = ("sira", "dosya_no", "yil", "no")
        self.preview_tree = ttk.Treeview(preview_table_frame, columns=preview_cols, show="headings", selectmode="extended")
        self.preview_tree.heading("sira", text="Sıra No")
        self.preview_tree.heading("dosya_no", text="İlamat Dosya Numarası (UYAP Formatı)")
        self.preview_tree.heading("yil", text="Yıl")
        self.preview_tree.heading("no", text="İlamat No")

        self.preview_tree.column("sira", width=90, anchor="center")
        self.preview_tree.column("dosya_no", width=340, anchor="center")
        self.preview_tree.column("yil", width=140, anchor="center")
        self.preview_tree.column("no", width=180, anchor="center")

        preview_scroll_y = ttk.Scrollbar(preview_table_frame, orient=tk.VERTICAL, command=self.preview_tree.yview)
        self.preview_tree.configure(yscrollcommand=preview_scroll_y.set)
        preview_scroll_y.pack(side=tk.RIGHT, fill=tk.Y)
        self.preview_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self.preview_tree.bind("<Double-1>", lambda e: self._start_from_selected_preview())

        # -------------------------------------------------------------
        # SEKME 2: CANLI KONTROL VE TAKSİT SONUÇLARI (RESULTS TAB)
        # -------------------------------------------------------------
        self.tab_results = ttk.Frame(self.notebook)
        self.notebook.add(self.tab_results, text=" ⚡ UYAP Canlı Kontrol Sonuçları ")

        table_card = tk.Frame(self.tab_results, bg=self.COLOR_CARD)
        table_card.pack(fill=tk.BOTH, expand=True, padx=4, pady=4)

        columns = ("dosya_no", "sirasi", "miktari", "taksit_no", "son_odeme", "son_odedigi", "durum")
        self.tree = ttk.Treeview(table_card, columns=columns, show="headings", selectmode="browse")

        self.tree.heading("dosya_no", text="Dosya No")
        self.tree.heading("sirasi", text="Sırası")
        self.tree.heading("miktari", text="Miktarı")
        self.tree.heading("taksit_no", text="Taksit No")
        self.tree.heading("son_odeme", text="Vade / Son Ödeme")
        self.tree.heading("son_odedigi", text="Son Ödediği Tarih")
        self.tree.heading("durum", text="İşlem Durumu")

        self.tree.column("dosya_no", width=140, anchor="center")
        self.tree.column("sirasi", width=60, anchor="center")
        self.tree.column("miktari", width=110, anchor="e")
        self.tree.column("taksit_no", width=80, anchor="center")
        self.tree.column("son_odeme", width=130, anchor="center")
        self.tree.column("son_odedigi", width=130, anchor="center")
        self.tree.column("durum", width=260, anchor="w")

        tree_scroll_y = ttk.Scrollbar(table_card, orient=tk.VERTICAL, command=self.tree.yview)
        self.tree.configure(yscrollcommand=tree_scroll_y.set)
        tree_scroll_y.pack(side=tk.RIGHT, fill=tk.Y)
        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        self.tree.tag_configure("ok", foreground="#2E7D32")
        self.tree.tag_configure("error", foreground="#C62828")
        self.tree.tag_configure("warn", foreground="#EF6C00")

        # -------------------------------------------------------------
        # SEKME 3: PDF HAM METNİ (RAW TEXT TAB)
        # -------------------------------------------------------------
        self.tab_raw_text = ttk.Frame(self.notebook)
        self.notebook.add(self.tab_raw_text, text=" 📄 PDF Ham Metni ")

        raw_frame = tk.Frame(self.tab_raw_text, bg=self.COLOR_CARD, padx=6, pady=6)
        raw_frame.pack(fill=tk.BOTH, expand=True)

        self.txt_raw_text = tk.Text(
            raw_frame,
            font=("Consolas", 10),
            bg="#263238",
            fg="#ECEFF1",
            wrap=tk.WORD,
            state=tk.DISABLED
        )
        raw_scroll = ttk.Scrollbar(raw_frame, orient=tk.VERTICAL, command=self.txt_raw_text.yview)
        self.txt_raw_text.configure(yscrollcommand=raw_scroll.set)
        raw_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        self.txt_raw_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        # Canlı Log Kartı (Alt Panel)
        log_card = tk.LabelFrame(
            paned,
            text=" Canlı İşlem Günlüğü (Log) ",
            font=("Segoe UI", 10, "bold"),
            bg=self.COLOR_CARD,
            fg=self.COLOR_DARK,
            padx=8,
            pady=6
        )
        paned.add(log_card, height=160)

        self.log_text = tk.Text(
            log_card,
            font=("Consolas", 9),
            bg="#263238",
            fg="#ECEFF1",
            wrap=tk.WORD,
            state=tk.DISABLED
        )
        log_scroll = ttk.Scrollbar(log_card, orient=tk.VERTICAL, command=self.log_text.yview)
        self.log_text.configure(yscrollcommand=log_scroll.set)
        log_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        self.log_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

    def log(self, message):
        """Arayüzdeki log ekranına mesaj ekler."""
        def _append():
            self.log_text.configure(state=tk.NORMAL)
            self.log_text.insert(tk.END, message + "\n")
            self.log_text.see(tk.END)
            self.log_text.configure(state=tk.DISABLED)
        self.after(0, _append)

    def _check_image_dir_status(self):
        """Referans buton görsellerinin klasörünü ve sayısını denetler."""
        found_count = 0
        total = len(IMAGE_FILES)
        for key in IMAGE_FILES:
            resolved = resolve_image_file(self.current_image_dir, key)
            if resolved and os.path.exists(resolved):
                found_count += 1

        if found_count == total:
            status_text = f"✔ {found_count}/{total} Referans Görsel Hazır (Hibrit Mod)"
            color = "#2E7D32"
        elif found_count > 0:
            status_text = f"⚠ {found_count}/{total} Görsel Mevcut (Kalanlar İçin Akıllı OCR Devrede)"
            color = "#E65100"
        else:
            status_text = "ℹ Görseller Klasörde Yok (Akıllı Windows OCR Otomatik Devrede)"
            color = "#0277BD"

        self.lbl_image_status.config(text=status_text, fg=color)

    def select_image_folder(self):
        """Kullanıcının referans buton görsellerinin bulunduğu klasörü seçmesini sağlar."""
        init_dir = self.current_image_dir if os.path.exists(self.current_image_dir) else USER_DESKTOP
        folder = filedialog.askdirectory(
            title="Referans Buton Görsellerinin Bulunduğu Klasörü Seçin",
            initialdir=init_dir
        )
        if not folder:
            return
        self.current_image_dir = folder
        self.bot.image_dir = folder
        self.log(f"Görseller klasörü güncellendi: {folder}")
        self._check_image_dir_status()

    def test_screen_detection_dialog(self):
        """Kullanıcının UYAP ekranındaki butonları test eder ve sonucu gösterir."""
        self.log("Ekran algılama testi başlatılıyor...")
        res = self.bot.test_screen_detection()
        lines = []
        found_any = False
        names = {
            "arama": "1. İlamat Dosya Arama Butonu",
            "dosya_no": "2. Dosya No Alanı",
            "sorgula": "3. Sorgula Butonu",
            "ayrinti": "4. Dosya Ayrıntı Butonu",
            "infaz": "5. Para Cezası İnfaz Butonu"
        }
        for k in ["arama", "dosya_no", "sorgula", "ayrinti", "infaz"]:
            info = res.get(k, {})
            name = names.get(k, k)
            if info.get("bulundu"):
                found_any = True
                lines.append(f"✔ {name}: Algılandı ({info.get('yontem')})")
            else:
                lines.append(f"❌ {name}: Ekranda görülemedi")

        msg = "\n".join(lines)
        if found_any:
            messagebox.showinfo(
                "Ekran Testi Sonucu",
                f"Ekranda tespit edilen UYAP alanları:\n\n{msg}\n\nRobot ekranınızı başarıyla okuyor! 'Kontrolü Başlat' butonuna basabilirsiniz."
            )
        else:
            messagebox.showwarning(
                "Ekran Testi Uyarısı",
                f"Ekranda hiçbir UYAP butonu tespit edilemedi:\n\n{msg}\n\nLütfen UYAP penceresini açıp ekranda görünür hale getirdikten sonra testi tekrar deneyin."
            )

    def _update_calib_status_label(self):
        """Kalibrasyon durum etiketini günceller."""
        if self.bot.calibration.is_calibrated():
            self.lbl_calib_status.config(
                text="✔ Özel Yerler Kayıtlı (0 Hata Garantili Mod)",
                fg="#2E7D32"
            )
            self.btn_clear_calib.pack(side=tk.LEFT, padx=5)
        else:
            self.lbl_calib_status.config(
                text="ℹ Özel Yer Gösterilmedi (Otomatik OCR / Şablon Modu)",
                fg="#0288D1"
            )
            self.btn_clear_calib.pack_forget()

    def clear_calibration(self):
        """Kayıtlı kalibrasyonu siler ve otomatik moda döner."""
        if messagebox.askyesno("Kalibrasyonu Sıfırla", "Kayıtlı özel yerleri silip otomatik OCR moduna dönmek istiyor musunuz?"):
            self.bot.calibration.clear()
            self._update_calib_status_label()
            self.log("Özel kalibrasyon koordinatları temizlendi. Otomatik OCR modu devrede.")

    def open_calibration_wizard(self):
        """Kullanıcının UYAP üzerindeki buton konumlarını bir kez gösterdiği sihirbazı açar."""
        from calibration_manager import CALIBRATION_STEPS
        import ctypes

        user32 = ctypes.windll.user32
        VK_F2 = 0x71
        VK_SPACE = 0x20

        wiz = tk.Toplevel(self)
        wiz.title("🎯 UYAP Ekranında Yerleri Gösterme Sihirbazı")
        wiz.geometry("560x380")
        wiz.resizable(False, False)
        wiz.attributes("-topmost", True)
        wiz.configure(bg="#FAFAFA")

        step_idx = [0]
        collected = dict(self.bot.calibration.coordinates)
        is_active = [True]

        header = tk.Frame(wiz, bg="#6A1B9A", padx=15, pady=10)
        header.pack(fill=tk.X)

        title_lbl = tk.Label(
            header,
            text="🎯 UYAP Buton Konumlarını Kaydetme Sihirbazı",
            font=("Segoe UI", 12, "bold"),
            fg="#FFFFFF",
            bg="#6A1B9A"
        )
        title_lbl.pack(anchor="w")

        sub_lbl = tk.Label(
            header,
            text="Farenizi UYAP'taki alanın üzerine getirin ve klavyenizden [F2] veya [Boşluk] tuşuna basın.",
            font=("Segoe UI", 9),
            fg="#E1BEE7",
            bg="#6A1B9A"
        )
        sub_lbl.pack(anchor="w")

        content = tk.Frame(wiz, bg="#FAFAFA", padx=20, pady=15)
        content.pack(fill=tk.BOTH, expand=True)

        step_prog_lbl = tk.Label(
            content,
            text=f"Adım 1 / {len(CALIBRATION_STEPS)}",
            font=("Segoe UI", 10, "bold"),
            fg="#6A1B9A",
            bg="#FAFAFA"
        )
        step_prog_lbl.pack(anchor="w")

        step_title_lbl = tk.Label(
            content,
            text="",
            font=("Segoe UI", 13, "bold"),
            fg="#263238",
            bg="#FAFAFA"
        )
        step_title_lbl.pack(anchor="w", pady=(4, 6))

        step_desc_lbl = tk.Label(
            content,
            text="",
            font=("Segoe UI", 10),
            fg="#455A64",
            bg="#FAFAFA",
            wraplength=500,
            justify=tk.LEFT
        )
        step_desc_lbl.pack(anchor="w", pady=(0, 15))

        coords_lbl = tk.Label(
            content,
            text="📍 Mevcut Fare Konumu: X: 0, Y: 0",
            font=("Consolas", 11, "bold"),
            fg="#1565C0",
            bg="#E3F2FD",
            padx=10,
            pady=8,
            relief=tk.SOLID,
            bd=1
        )
        coords_lbl.pack(fill=tk.X, pady=(0, 15))

        btn_box = tk.Frame(content, bg="#FAFAFA")
        btn_box.pack(fill=tk.X)

        def save_current_pos():
            if step_idx[0] >= len(CALIBRATION_STEPS):
                return
            x, y = self.bot.calibration.get_cursor_pos()
            key = CALIBRATION_STEPS[step_idx[0]]["key"]
            collected[key] = [x, y]
            self.bot.calibration.play_beep()
            self.log(f"✔ Kalibre Edildi [{key}]: X:{x}, Y:{y}")
            step_idx[0] += 1
            if step_idx[0] < len(CALIBRATION_STEPS):
                update_step_ui()
            else:
                finish_calibration()

        btn_save = tk.Button(
            btn_box,
            text="📌 Bu Konumu Kaydet [F2 veya Boşluk]",
            font=("Segoe UI", 10, "bold"),
            bg="#2E7D32",
            fg="#FFFFFF",
            relief=tk.FLAT,
            padx=15,
            pady=6,
            cursor="hand2",
            command=save_current_pos
        )
        btn_save.pack(side=tk.LEFT, padx=(0, 10))

        def update_step_ui():
            cur = CALIBRATION_STEPS[step_idx[0]]
            step_prog_lbl.config(text=f"Adım {step_idx[0] + 1} / {len(CALIBRATION_STEPS)}")
            step_title_lbl.config(text=cur["title"])
            step_desc_lbl.config(text=cur["desc"])

        def test_points():
            """Kaydedilen noktaları sırayla ziyaret eder."""
            import time
            for step in CALIBRATION_STEPS:
                k = step["key"]
                if k in collected:
                    pt = collected[k]
                    self.bot.controller.move_to(pt[0], pt[1])
                    time.sleep(0.7)

        def finish_calibration():
            is_active[0] = False
            self.bot.calibration.save(collected)
            self._update_calib_status_label()
            step_prog_lbl.config(text="✔ Kalibrasyon Başarıyla Tamamlandı!", fg="#2E7D32")
            step_title_lbl.config(text="Tüm UYAP Yerleri Kaydedildi")
            step_desc_lbl.config(text="Robot artık dosya ararken, sorgularken, ayrıntıya girerken, infaz sekmesine geçerken ve pencereleri 'Kapat' butonlarıyla kapatırken doğrudan gösterdiğiniz bu yerlere tıklayacaktır.")
            coords_lbl.config(text=f"Tüm {len(CALIBRATION_STEPS)} nokta başarıyla kayıt altına alındı.", bg="#E8F5E9", fg="#2E7D32")
            btn_save.config(text="✔ Tamamla ve Kapat", bg="#1E88E5", command=wiz.destroy)

            btn_test = tk.Button(
                btn_box,
                text="▶ Kayıtlı Yerleri Test Et",
                font=("Segoe UI", 9, "bold"),
                bg="#455A64",
                fg="#FFFFFF",
                relief=tk.FLAT,
                padx=10,
                pady=6,
                cursor="hand2",
                command=test_points
            )
            btn_test.pack(side=tk.LEFT)

        update_step_ui()

        # Klavye F2 / Space dinleyici ve fare izleyici döngüsü
        was_f2 = [False]
        was_space = [False]

        def poll_loop():
            if not is_active[0] or not wiz.winfo_exists():
                return
            x, y = self.bot.calibration.get_cursor_pos()
            coords_lbl.config(text=f"📍 Mevcut Fare Konumu: X: {x}, Y: {y}")

            is_f2 = bool(user32.GetAsyncKeyState(VK_F2) & 0x8000)
            is_space = bool(user32.GetAsyncKeyState(VK_SPACE) & 0x8000)

            if is_f2 and not was_f2[0]:
                save_current_pos()
            elif is_space and not was_space[0]:
                save_current_pos()

            was_f2[0] = is_f2
            was_space[0] = is_space

            wiz.after(50, poll_loop)

        wiz.after(100, poll_loop)

        def on_close():
            is_active[0] = False
            wiz.destroy()
        wiz.protocol("WM_DELETE_WINDOW", on_close)

    def _populate_preview_tree(self, cases):
        """Yüklenen tüm dosyaları önizleme tablosuna yazar."""
        self.preview_tree.delete(*self.preview_tree.get_children())
        for idx, c in enumerate(cases, start=1):
            parts = c.split("/")
            yil = parts[0] if len(parts) > 1 else "-"
            num_part = parts[1].replace("2-", "") if len(parts) > 1 else parts[0]
            self.preview_tree.insert("", tk.END, values=(idx, c, yil, num_part))

        total = len(cases)
        self.lbl_preview_count.config(text=f"✔ Toplam {total} Adet İlamat Dosyası Yüklendi")

    def _filter_preview_tree(self, *args):
        """Önizleme tablosunda arama/filtreleme yapar."""
        q = self.preview_search_var.get().strip().lower()
        self.preview_tree.delete(*self.preview_tree.get_children())
        match_count = 0
        for idx, c in enumerate(self.loaded_cases, start=1):
            if not q or q in c.lower() or q in str(idx):
                parts = c.split("/")
                yil = parts[0] if len(parts) > 1 else "-"
                num_part = parts[1].replace("2-", "") if len(parts) > 1 else parts[0]
                self.preview_tree.insert("", tk.END, values=(idx, c, yil, num_part))
                match_count += 1
        total = len(self.loaded_cases)
        self.lbl_preview_count.config(text=f"Gösterilen: {match_count} / Toplam {total} Dosya")

    def _copy_preview_numbers(self):
        """Önizleme tablosundaki numaraları panoya kopyalar."""
        if not self.loaded_cases:
            messagebox.showinfo("Bilgi", "Kopyalanacak dosya listesi bulunmuyor.")
            return
        text = "\n".join(self.loaded_cases)
        self.clipboard_clear()
        self.clipboard_append(text)
        messagebox.showinfo("Başarılı", f"Toplam {len(self.loaded_cases)} adet ilamat numarası panoya kopyalandı!")

    def _export_preview_to_excel(self):
        """Yüklenen önizleme dosya listesini Excel'e aktarır."""
        if not self.loaded_cases:
            messagebox.showinfo("Bilgi", "Aktarılacak liste bulunmuyor.")
            return

        save_path = filedialog.asksaveasfilename(
            title="Yüklenen Listeyi Excel Olarak Kaydet",
            defaultextension=".xlsx",
            initialfile="yuklenen_tpi_listesi.xlsx",
            filetypes=[("Excel Dosyası", "*.xlsx")]
        )
        if not save_path:
            return

        rows = []
        for idx, c in enumerate(self.loaded_cases, start=1):
            parts = c.split("/")
            yil = parts[0] if len(parts) > 1 else "-"
            num_part = parts[1].replace("2-", "") if len(parts) > 1 else parts[0]
            rows.append({
                "Sıra No": idx,
                "İlamat Dosya No": c,
                "Yıl": yil,
                "İlamat No": num_part
            })

        try:
            df = pd.DataFrame(rows)
            df.to_excel(save_path, index=False)
            messagebox.showinfo("Başarılı", f"Toplam {len(rows)} adet dosya Excel'e kaydedildi:\n{save_path}")
        except Exception as e:
            messagebox.showerror("Hata", f"Excel kaydedilirken hata oluştu:\n{str(e)}")

    def select_pdf_file(self):
        """Kullanıcının PDF veya liste dosyasını seçmesini sağlar."""
        file_path = filedialog.askopenfilename(
            title="TPI Liste Dosyasını Seçin",
            filetypes=[
                ("Tüm Desteklenenler", "*.pdf;*.png;*.jpg;*.txt"),
                ("PDF Dosyaları", "*.pdf"),
                ("Görsel Dosyaları", "*.png;*.jpg;*.jpeg"),
                ("Metin Dosyaları", "*.txt")
            ]
        )
        if not file_path:
            return

        self.log(f"Dosya seçildi: {file_path}")
        self.lbl_file_status.config(text=f"Okunuyor: {os.path.basename(file_path)}...")
        self.update_idletasks()

        try:
            # 1. Ham metni çıkar
            raw_text = self.pdf_reader.extract_text_from_pdf(file_path)
            # 2. İlamat numaralarını ayrıştır
            cases = self.pdf_reader.parse_case_numbers(raw_text)

            if not cases:
                messagebox.showwarning(
                    "Liste Bulunamadı",
                    "Dosyada uygun ilamat numarası formatı tespit edilemedi.\n"
                    "Lütfen dosyanın TPI listesi içerdiğinden emin olun."
                )
                self.lbl_file_status.config(text="Dosyada ilamat numarası bulunamadı.")
                return

            self.loaded_cases = cases
            self.loaded_raw_text = raw_text
            count = len(cases)

            # Önizleme tablosunu doldur
            self._populate_preview_tree(cases)

            # Ham metin sekmesini doldur
            self.txt_raw_text.configure(state=tk.NORMAL)
            self.txt_raw_text.delete("1.0", tk.END)
            self.txt_raw_text.insert(tk.END, f"=== DOSYA: {os.path.basename(file_path)} (TOPLAM {count} İLAMAT TESPİT EDİLDİ) ===\n\n")
            self.txt_raw_text.insert(tk.END, raw_text)
            self.txt_raw_text.configure(state=tk.DISABLED)

            # Arayüz durumunu güncelle
            self.lbl_file_status.config(
                text=f"✔ {os.path.basename(file_path)} (Toplam {count} adet dosya yüklendi)"
            )
            self.btn_view_preview.config(
                text=f"📋 Yüklenen Listeyi İncele ({count})",
                state=tk.NORMAL
            )
            self.btn_start.config(text="▶ Kontrolü Başlat", state=tk.NORMAL)
            self.btn_restart.config(state=tk.DISABLED)

            # Önceki oturumda nerede kalındığını denetle ve otomatik öner
            state = self._load_progress_state()
            all_cases = getattr(self, "loaded_cases", [])
            if state and state.get("son_dosya_no") and all_cases:
                son_no = state.get("son_dosya_no")
                match_idx = next((i for i, c in enumerate(all_cases) if self.ocr_engine.normalize_text(son_no) in self.ocr_engine.normalize_text(c)), None)
                if match_idx is not None and match_idx + 1 < len(all_cases):
                    next_start = match_idx + 2  # 1-based sonraki sıra
                    self.start_from_var.set(str(next_start))
                    self.log(f"💡 [Hafıza] Önceki oturumda en son {match_idx + 1}. dosya ({son_no}) işlenmişti.")
                    self.log(f"👉 Başlangıç noktası otomatik olarak {next_start}. dosya ({all_cases[match_idx + 1]}) olarak ayarlandı. İsterseniz değiştirebilirsiniz.")
                elif state.get("son_sira") and int(state["son_sira"]) < len(all_cases):
                    next_start = int(state["son_sira"]) + 1
                    self.start_from_var.set(str(next_start))
                    self.log(f"💡 [Hafıza] Önceki oturumda en son {state['son_sira']}. dosya işlenmişti. Başlangıç {next_start}. dosya olarak ayarlandı.")

            # KULLANICININ DOĞRULAYABİLMESİ İÇİN OTOMATİK ÖNİZLEME SEKMESİNİ AÇ
            self.notebook.select(self.tab_preview)

            first_preview = cases[:3] if len(cases) >= 3 else cases
            last_preview = cases[-3:] if len(cases) >= 3 else cases
            self.log(f"Başarıyla {count} dosya yüklendi ve Önizleme sekmesine aktarıldı.\n  İlk dosyalar: {first_preview}\n  Son dosyalar: {last_preview}")

        except Exception as e:
            messagebox.showerror("Okuma Hatası", f"Dosya okunurken bir hata oluştu:\n{str(e)}")
            self.lbl_file_status.config(text="Hata oluştu.")

    def _start_hotkey_listener(self):
        """Windows genelinde F5 ve F6 tuşlarını dinleyen arka plan thread'ini başlatır."""
        t = threading.Thread(target=self._listen_global_hotkeys, daemon=True)
        t.start()

    def _listen_global_hotkeys(self):
        """Win32 API ile arka planda ESC, F5, F6, F8 ve Mouse FailSafe denetler."""
        VK_ESCAPE = 0x1B
        VK_F5 = 0x74
        VK_F6 = 0x75
        VK_F8 = 0x77
        VK_PAUSE = 0x13

        while True:
            try:
                # Tuş basımlarını anlık kontrol et (Öncelikli olarak ESC)
                esc_down = bool(user32.GetAsyncKeyState(VK_ESCAPE) & 0x8000)
                f5_down = bool(user32.GetAsyncKeyState(VK_F5) & 0x8000)
                f6_down = bool(user32.GetAsyncKeyState(VK_F6) & 0x8000)
                f8_down = bool(user32.GetAsyncKeyState(VK_F8) & 0x8000)
                pause_down = bool(user32.GetAsyncKeyState(VK_PAUSE) & 0x8000)

                # Mouse Failsafe: Fare ekranın sol-üst köşesine (0,0) çekildiğinde anında durdur
                pt = wintypes.POINT()
                user32.GetCursorPos(ctypes.byref(pt))
                mouse_failsafe = (pt.x <= 15 and pt.y <= 15)

                if esc_down or f5_down or f6_down or f8_down or pause_down or mouse_failsafe:
                    # 1. ANINDA VE BEKLEMEDEN BOTU DURDUR (Tkinter kuyruğunu beklemez, sıfır gecikmeyle durdurur)
                    if self.bot:
                        self.bot.stop()

                    # Tuşun bırakılmasını bekle
                    while (bool(user32.GetAsyncKeyState(VK_ESCAPE) & 0x8000) or
                           bool(user32.GetAsyncKeyState(VK_F5) & 0x8000) or
                           bool(user32.GetAsyncKeyState(VK_F6) & 0x8000) or
                           bool(user32.GetAsyncKeyState(VK_F8) & 0x8000)):
                        time.sleep(0.04)

                    self.after(0, self._handle_esc_press)
            except Exception:
                pass
            time.sleep(0.05)

    def _handle_esc_press(self):
        """ESC veya kısayol basıldığında: robotu durdurur ve pencereyi anında öne getirir."""
        try:
            winsound.MessageBeep(winsound.MB_ICONEXCLAMATION)
        except Exception:
            pass

        self.deiconify()
        self.lift()
        self.state('normal')
        try:
            hwnd = self.winfo_id()
            user32.SetForegroundWindow(hwnd)
        except Exception:
            pass

        self.log("⏸ [ESC Kısayolu] Robot duraklatıldı! Pencere öne getirildi.")
        self.stop_automation(is_hotkey=True)

    def _save_progress_state(self, case_no, idx):
        """Son işlenen dosya numarasını ve sıra indeksini diske kaydeder."""
        try:
            with open(STATE_FILE, "w", encoding="utf-8") as f:
                json.dump({
                    "son_dosya_no": case_no,
                    "son_sira": idx,
                    "tarih": time.strftime("%Y-%m-%d %H:%M:%S")
                }, f, indent=2, ensure_ascii=False)
        except Exception:
            pass

    def _load_progress_state(self):
        """Diskte kayıtlı son durum bilgisini okur."""
        if os.path.exists(STATE_FILE):
            try:
                with open(STATE_FILE, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                pass
        return None

    def _start_from_selected_preview(self):
        """Önizleme listesinde seçili olan dosyadan itibaren kontrolü başlatır."""
        selected = self.preview_tree.selection()
        if not selected:
            messagebox.showinfo("Bilgi", "Lütfen listeden başlamak istediğiniz dosyayı seçin.")
            return

        item = self.preview_tree.item(selected[0])
        vals = item.get("values", [])
        if not vals:
            return

        sira = str(vals[0])
        dosya_no = str(vals[1])

        self.start_from_var.set(sira)
        resp = messagebox.askyesno(
            "Buradan Başlatılsın mı?",
            f"Kontrol işlemi:\n\n"
            f"Sıra: {sira}\n"
            f"Dosya No: {dosya_no}\n\n"
            f"dosyasından itibaren başlatılsın mı?"
        )
        if resp:
            self.start_automation()

    def start_automation(self, force_restart=False):
        """
        Otomasyonu başlatır.
        - Kullanıcı 'Şuradan İtibaren Sorgula' alanına sıra no (örn: 250) veya dosya no (örn: 2024/2-61040)
          yazmışsa veya listeden seçmişse doğrudan o dosyadan başlar!
        - force_restart=True ise 1. sıradan başlar ve tabloyu sıfırlar.
        """
        if not self.loaded_cases:
            messagebox.showinfo("Bilgi", "Lütfen önce bir dosya listesi yükleyin.")
            return

        start_val = self.start_from_var.get().strip()
        start_idx = 0

        if force_restart:
            start_idx = 0
            self.start_from_var.set("1")
        elif start_val:
            if start_val.isdigit():
                start_idx = max(0, int(start_val) - 1)
                if start_idx >= len(self.loaded_cases):
                    messagebox.showwarning("Geçersiz Sıra", f"Girdiğiniz sıra no ({start_val}) listedeki toplam dosya sayısından ({len(self.loaded_cases)}) büyük!")
                    return
            else:
                # Dosya numarası olarak ara
                norm_target = self.ocr_engine.normalize_text(start_val)
                found = next((i for i, c in enumerate(self.loaded_cases) if norm_target in self.ocr_engine.normalize_text(c)), None)
                if found is not None:
                    start_idx = found
                else:
                    messagebox.showwarning("Dosya Bulunamadı", f"'{start_val}' numaralı dosya listede bulunamadı!\nLütfen geçerli bir sıra numarası (örn: 250) veya dosya numarası girin.")
                    return
        elif len(self.results_data) > 0:
            start_idx = len(self.results_data)

        cases_to_run = self.loaded_cases[start_idx:]
        if not cases_to_run:
            messagebox.showinfo("Bilgi", "Başlangıç noktası sonrasında işlenecek dosya kalmadı.")
            return

        # Eğer baştan başlıyorsa tabloyu sıfırla, belirli bir sıradan devam ediyorsa eski sonuçları koru
        if start_idx == 0:
            for row in self.tree.get_children():
                self.tree.delete(row)
            self.results_data.clear()

        self.log(f"▶ Kontrol başlatılıyor: {start_idx + 1}. dosya ({cases_to_run[0]}) ile başlanıyor (Kalan {len(cases_to_run)} dosya)...")

        # Otomasyon başlayınca otomatik CANLI SONUÇLAR sekmesine geç
        self.notebook.select(self.tab_results)

        # Arayüzü güncelle
        self.btn_start.config(state=tk.DISABLED)
        self.btn_restart.config(state=tk.DISABLED)
        self.btn_select_file.config(state=tk.DISABLED)
        self.btn_stop.config(state=tk.NORMAL)
        self.btn_export.config(state=tk.DISABLED)

        # Robot hız profilini ayarla
        selected_speed = self.speed_var.get()
        self.bot.set_speed_profile(selected_speed)

        # İlerleme çubuğunu ayarla
        self.progress_bar["maximum"] = len(self.loaded_cases)
        self.progress_bar["value"] = start_idx
        self.lbl_progress.config(
            text=f"İşleniyor: {start_idx} / {len(self.loaded_cases)} (Başlangıç: {cases_to_run[0]})"
        )

        # Arka plan iş parçacığını başlat
        self.worker_thread = threading.Thread(
            target=self._run_worker,
            args=(cases_to_run, start_idx),
            daemon=True
        )
        self.worker_thread.start()

    def _run_worker(self, cases_to_run, start_idx=0):
        """Arka plan robot çalışma döngüsü."""
        for i in range(STARTUP_COUNTDOWN, 0, -1):
            self.log(f"UYAP penceresine geçiniz... Robotun başlamasına {i} saniye!")
            self.after(0, lambda sec=i: self.lbl_progress.config(
                text=f"⏳ Lütfen UYAP ekranını açın... Başlamaya {sec} saniye!"
            ))
            time.sleep(1.0)

        # UYAP penceresini bulup ekranın en önüne getir ve kendi penceremizi küçült
        # Böylece robot UYAP üzerindeki butonlara ve tablolara sıfır engelle tıklar
        self.bot.controller.bring_window_to_front()
        time.sleep(0.3)
        self.after(0, self.iconify)
        time.sleep(0.4)

        self.after(0, lambda: self.lbl_progress.config(text="Robot çalışıyor... Dosyalar taranıyor."))
        desktop = os.path.join(os.environ.get("USERPROFILE", "C:\\Users\\Administrator"), "Desktop")
        interim_excel_path = os.path.join(desktop, "taksit_kontrol_GUNCEL.xlsx")
        backup_dir = os.path.join(desktop, "taksit_yedekler")
        os.makedirs(backup_dir, exist_ok=True)

        # 1. OTOMATİK GÜVENLİK YEDEĞİ: Masaüstünde önceki oturumdan kalan dosya varsa ASLA SİLME, YEDEKLE!
        if os.path.exists(interim_excel_path):
            try:
                if os.path.getsize(interim_excel_path) > 500:
                    safety_backup = os.path.join(backup_dir, f"otomatik_guvenlik_yedegi_{time.strftime('%Y%m%d_%H%M%S')}.xlsx")
                    import shutil
                    shutil.copy2(interim_excel_path, safety_backup)
                    self.log(f"🛡 Güvenlik Koruması: Önceki Excel tablosu yedeklendi: {os.path.basename(safety_backup)}")
            except Exception:
                pass

        # 2. ÖNCEKİ KAYITLARI OKU VE KORU (ÜZERİNE YAZIP YOK ETMEYİ %100 ENGELLER)
        existing_records_df = None
        if os.path.exists(interim_excel_path):
            try:
                df_read = pd.read_excel(interim_excel_path)
                if df_read is not None and len(df_read) > 0 and "Dosya No" in df_read.columns:
                    existing_records_df = df_read
                    self.log(f"ℹ Mevcut tablodan {len(df_read)} kayıt koruma altına alındı (yeni tarananlar üstüne eklenecek).")
            except Exception:
                pass

        def row_callback(result_dict, current_idx, total):
            # 1. ARKA PLANDA HER DOSYADA MEVCUT KAYITLARLA BİRLEŞTİREREK EXCEL (.xlsx) GÜNCELLE
            try:
                self.results_data.append(result_dict)
                df_new = pd.DataFrame(self.results_data)
                key_map = {
                    "dosya_no": "Dosya No",
                    "sirasi": "Sırası",
                    "miktari": "Miktarı",
                    "taksit_no": "Taksit No",
                    "son_odeme_tarihi": "Son Ödeme Tarihi",
                    "son_odedigi_tarih": "Son Ödediği Tarih",
                    "durum": "İşlem Durumu"
                }
                df_new = df_new.rename(columns=key_map)

                # Eski taranmış veriler varsa birleştir (asla silinmez)
                if existing_records_df is not None and len(existing_records_df) > 0:
                    combined = pd.concat([existing_records_df, df_new], ignore_index=True)
                    combined = combined.drop_duplicates(subset=["Dosya No"], keep="last")
                else:
                    combined = df_new

                tmp_excel = interim_excel_path + ".tmp"
                combined.to_excel(tmp_excel, index=False)
                if os.path.exists(tmp_excel):
                    os.replace(tmp_excel, interim_excel_path)
            except Exception:
                pass

            def _update():
                current_global = start_idx + current_idx
                tag = "ok" if "Başarılı" in result_dict.get("durum", "") else "error"
                if "Tüm Taksitler" in result_dict.get("durum", ""):
                    tag = "warn"

                self.tree.insert(
                    "",
                    tk.END,
                    values=(
                        result_dict.get("dosya_no", "-"),
                        result_dict.get("sirasi", "-"),
                        result_dict.get("miktari", "-"),
                        result_dict.get("taksit_no", "-"),
                        result_dict.get("son_odeme_tarihi", "-"),
                        result_dict.get("son_odedigi_tarih", "-"),
                        result_dict.get("durum", "-")
                    ),
                    tags=(tag,)
                )
                self.progress_bar["value"] = current_global
                self.lbl_progress.config(
                    text=f"İşleniyor: {current_global} / {len(self.loaded_cases)} (Son: {result_dict.get('dosya_no')})"
                )

                # Son işlenen dosyayı oturum hafızasına kaydet
                self._save_progress_state(result_dict.get("dosya_no"), current_global)

                # Her 20 dosyada bir taksit_yedekler klasörüne de zaman damgalı bağımsız kopya at
                if len(self.results_data) % 20 == 0:
                    try:
                        backup_dir = os.path.join(desktop, "taksit_yedekler")
                        os.makedirs(backup_dir, exist_ok=True)
                        backup_file = os.path.join(backup_dir, f"yedek_{time.strftime('%Y%m%d_%H%M%S')}.xlsx")
                        df_current.to_excel(backup_file, index=False)
                    except Exception:
                        pass

            self.after(0, _update)

        def finish_callback(results):
            def _finish():
                # İşlem bittiğinde penceremizi geri aç ve öne getir
                self.deiconify()
                self.lift()
                self.state('normal')
                self.btn_select_file.config(state=tk.NORMAL)
                self.btn_stop.config(state=tk.DISABLED)
                self.btn_export.config(state=tk.NORMAL)

                kalan = len(self.loaded_cases) - len(self.results_data)
                if kalan > 0:
                    # Bir sonraki dosyanın numarasını başlangıç alanına yaz
                    next_idx = len(self.results_data) + 1
                    self.start_from_var.set(str(next_idx))
                    self.btn_start.config(
                        text=f"▶ Kaldığı Yerden Devam Et ({kalan} Dosya)",
                        state=tk.NORMAL,
                        bg=self.COLOR_SUCCESS
                    )
                    self.btn_restart.config(state=tk.NORMAL)
                    self.lbl_progress.config(
                        text=f"Duraklatıldı! {len(self.results_data)} / {len(self.loaded_cases)} tamamlandı. (Sıradaki: {next_idx}. dosya)"
                    )
                else:
                    self.start_from_var.set("1")
                    self.btn_start.config(text="▶ Kontrolü Başlat", state=tk.NORMAL)
                    self.btn_restart.config(state=tk.DISABLED)
                    self.lbl_progress.config(text=f"Tüm Liste Tamamlandı! Toplam {len(self.results_data)} dosya kontrol edildi.")
                    self.auto_export_excel(self.results_data)
            self.after(0, _finish)

        try:
            self.bot.run_batch(
                cases_to_run,
                row_callback=row_callback,
                log_callback=self.log,
                finish_callback=finish_callback
            )
        except Exception as ex:
            import traceback
            err_str = traceback.format_exc()
            self.log(f"❌ Beklenmedik Çalışma Hatası: {ex}")
            try:
                with open("hata_raporu.log", "a", encoding="utf-8") as f:
                    f.write(f"\n--- HATA RAPORU ({time.strftime('%Y-%m-%d %H:%M:%S')}) ---\n")
                    f.write(err_str)
            except Exception:
                pass
            self.after(0, lambda: messagebox.showerror(
                "Çalışma Hatası",
                f"Robot çalışırken bir hata oluştu:\n\n{ex}\n\nAyrıntılar 'hata_raporu.log' dosyasına kaydedildi."
            ))

    def stop_automation(self, is_hotkey=False):
        """Kullanıcı durdur butonuna bastığında veya F5'e basıldığında."""
        self.bot.stop()
        self.btn_stop.config(state=tk.DISABLED)
        self.deiconify()
        self.lift()
        self.state('normal')

        kalan = len(self.loaded_cases) - len(self.results_data)
        if kalan > 0:
            self.btn_start.config(
                text=f"▶ Kaldığı Yerden Devam Et ({kalan} Dosya)",
                state=tk.NORMAL,
                bg=self.COLOR_SUCCESS
            )
            self.btn_restart.config(state=tk.NORMAL)
            msg = f"⏸ Robot durduruldu ({len(self.results_data)} dosya tamamlandı, {kalan} dosya kaldı). 'Kaldığı Yerden Devam Et' butonuyla devam edebilirsiniz."
        else:
            self.btn_start.config(text="▶ Kontrolü Başlat", state=tk.NORMAL)
            self.btn_restart.config(state=tk.DISABLED)

            # Önceki oturumda nerede kalındığını denetle ve otomatik öner
            state = self._load_progress_state()
            all_cases = getattr(self, "loaded_cases", [])
            if state and state.get("son_dosya_no") and all_cases:
                son_no = state.get("son_dosya_no")
                match_idx = next((i for i, c in enumerate(all_cases) if self.ocr_engine.normalize_text(son_no) in self.ocr_engine.normalize_text(c)), None)
                if match_idx is not None and match_idx + 1 < len(all_cases):
                    next_start = match_idx + 2  # 1-based sonraki sıra
                    self.start_from_var.set(str(next_start))
                    self.log(f"💡 [Hafıza] Önceki oturumda en son {match_idx + 1}. dosya ({son_no}) işlenmişti.")
                    self.log(f"👉 Başlangıç noktası otomatik olarak {next_start}. dosya ({all_cases[match_idx + 1]}) olarak ayarlandı. İsterseniz değiştirebilirsiniz.")
                elif state.get("son_sira") and int(state["son_sira"]) < len(all_cases):
                    next_start = int(state["son_sira"]) + 1
                    self.start_from_var.set(str(next_start))
                    self.log(f"💡 [Hafıza] Önceki oturumda en son {state['son_sira']}. dosya işlenmişti. Başlangıç {next_start}. dosya olarak ayarlandı.")
            msg = "İşlem tamamlandı!"

        self.lbl_progress.config(text=msg)
        self.log(msg)

    def export_excel(self):
        """Excel raporunu kullanıcının istediği yere kaydeder."""
        if not self.results_data:
            messagebox.showinfo("Bilgi", "Henüz kaydedilecek bir sonuç bulunmuyor.")
            return

        file_path = filedialog.asksaveasfilename(
            title="Excel Raporunu Kaydet",
            defaultextension=".xlsx",
            initialfile="uyap_taksit_kontrol_raporu.xlsx",
            filetypes=[("Excel Dosyası", "*.xlsx")]
        )
        if not file_path:
            return

        try:
            df = pd.DataFrame(self.results_data)
            df.columns = [
                "Dosya No", "Sırası", "Miktarı", "Taksit No",
                "Son Ödeme Tarihi", "Son Ödediği Tarih", "İşlem Durumu"
            ]
            df.to_excel(file_path, index=False)
            messagebox.showinfo("Başarılı", f"Rapor başarıyla kaydedildi:\n{file_path}")
        except Exception as e:
            messagebox.showerror("Hata", f"Excel kaydedilirken bir hata oluştu:\n{str(e)}")

    def auto_export_excel(self, results):
        """İşlem bittiğinde otomatik masaüstüne Excel yedeği atar."""
        if not results:
            return
        try:
            df = pd.DataFrame(results)
            df.columns = [
                "Dosya No", "Sırası", "Miktarı", "Taksit No",
                "Son Ödeme Tarihi", "Son Ödediği Tarih", "İşlem Durumu"
            ]
            df.to_excel(DEFAULT_EXCEL_OUTPUT, index=False)
            self.log(f"Otomatik rapor masaüstüne kaydedildi: {DEFAULT_EXCEL_OUTPUT}")
            messagebox.showinfo(
                "İşlem Tamamlandı",
                f"Tüm dosyalar tarandı!\n\nRapor masaüstünüze kaydedildi:\n{DEFAULT_EXCEL_OUTPUT}"
            )
        except Exception as e:
            self.log(f"Otomatik rapor kaydetme hatası: {str(e)}")
