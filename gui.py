# -*- coding: utf-8 -*-
"""
UYAP Taksit Kontrol Robotu - Modern Kullanıcı Arayüzü (GUI)
Tkinter ve ttk ile modern, tepkisel ve kullanıcı dostu masaüstü arayüzü.
"""
import os
import time
import threading
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import pandas as pd

from config import DEFAULT_IMAGE_DIR, DEFAULT_EXCEL_OUTPUT, STARTUP_COUNTDOWN
from pdf_reader import PdfReader
from ocr_engine import OcrEngine
from uyap_bot import UyapBot

class UyapApp(tk.Tk):
    def __init__(self):
        super().__init__()

        self.title("UYAP Taksitli Dosya Kontrol Robotu")
        self.geometry("1100, 720")
        self.minsize(950, 600)

        # Temel Nesneler
        self.ocr_engine = OcrEngine()
        self.pdf_reader = PdfReader(ocr_engine=self.ocr_engine)
        self.bot = UyapBot(image_dir=DEFAULT_IMAGE_DIR, ocr_engine=self.ocr_engine)

        self.loaded_cases = []
        self.results_data = []
        self.worker_thread = None

        # Stil ve Arayüz Kurulumu
        self._setup_style()
        self._create_widgets()

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
            text="TPI İlamat Listesi Otomatik Kontrol, OCR Tablo Okuma ve Excel Raporlama Sistemi",
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
            padx=20,
            pady=6,
            cursor="hand2",
            state=tk.DISABLED,
            command=self.start_automation
        )
        self.btn_start.pack(side=tk.LEFT, padx=(0, 10))

        self.btn_stop = tk.Button(
            btn_row,
            text="⏹ Durdur (Acil)",
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
        self.btn_stop.pack(side=tk.LEFT, padx=(0, 10))

        self.btn_export = tk.Button(
            btn_row,
            text="📊 Excel Raporu Aç / Kaydet",
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

        # 3. ORTA BÖLÜM: CANLI TABLO VE LOG PANELİ (PanedWindow)
        paned = tk.PanedWindow(main_container, orient=tk.VERTICAL, bg=self.COLOR_BG, sashwidth=4)
        paned.pack(fill=tk.BOTH, expand=True)

        # Canlı Tablo Kartı
        table_card = tk.LabelFrame(
            paned,
            text=" Çekilen Taksit Bilgileri ",
            font=("Segoe UI", 10, "bold"),
            bg=self.COLOR_CARD,
            fg=self.COLOR_DARK,
            padx=8,
            pady=6
        )
        paned.add(table_card, height=320)

        # Treeview Tablosu
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

        # Tablo etiketleri (Başarılı yeşil, Hata kırmızı/turuncu)
        self.tree.tag_configure("ok", foreground="#2E7D32")
        self.tree.tag_configure("error", foreground="#C62828")
        self.tree.tag_configure("warn", foreground="#EF6C00")

        # Canlı Log Kartı
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
            cases = self.pdf_reader.load_case_list(file_path)
            if not cases:
                # Eğer PDF doğrudan okunamadıysa kullanıcıya bilgi ver
                messagebox.showwarning(
                    "Liste Bulunamadı",
                    "Dosyada uygun ilamat numarası formatı tespit edilemedi.\n"
                    "Lütfen dosyanın TPI listesi içerdiğinden emin olun."
                )
                self.lbl_file_status.config(text="Dosyada ilamat numarası bulunamadı.")
                return

            self.loaded_cases = cases
            count = len(cases)
            self.lbl_file_status.config(
                text=f"✔ {os.path.basename(file_path)} (Toplam {count} adet dosya yüklendi)"
            )
            self.log(f"Başarıyla {count} dosya ayrıştırıldı. İlk 3 dosya: {cases[:3]}")
            self.btn_start.config(state=tk.NORMAL)

        except Exception as e:
            messagebox.showerror("Okuma Hatası", f"Dosya okunurken bir hata oluştu:\n{str(e)}")
            self.lbl_file_status.config(text="Hata oluştu.")

    def start_automation(self):
        """Otomasyonu arka planda başlatır."""
        if not self.loaded_cases:
            messagebox.showinfo("Bilgi", "Lütfen önce bir dosya listesi yükleyin.")
            return

        # Kaldığı yerden devam etme kontrolü
        processed_count = len(self.results_data)
        cases_to_run = self.loaded_cases

        if 0 < processed_count < len(self.loaded_cases):
            resume = messagebox.askyesno(
                "Kaldığı Yerden Devam Edilsin mi?",
                f"Daha önce {processed_count} adet dosya işlenmiş görünüyor.\n\n"
                f"Kaldığınız {processed_count + 1}. dosyadan devam etmek ister misiniz?\n"
                f"(Hayır derseniz tablo sıfırlanıp 1. dosyadan başlanır.)"
            )
            if resume:
                cases_to_run = self.loaded_cases[processed_count:]
            else:
                for row in self.tree.get_children():
                    self.tree.delete(row)
                self.results_data.clear()
        else:
            for row in self.tree.get_children():
                self.tree.delete(row)
            self.results_data.clear()

        # Kullanıcıya UYAP hatırlatması yap
        resp = messagebox.askyesno(
            "UYAP Hazır mı?",
            "UYAP sistemi açık ve 'İlamat Dosyası Arama' ekranında mı?\n\n"
            "Robot başladığında fareyi kontrol edecektir.\n"
            "Devam etmek istiyor musunuz?"
        )
        if not resp:
            return

        # Arayüzü güncelle
        self.btn_start.config(state=tk.DISABLED)
        self.btn_select_file.config(state=tk.DISABLED)
        self.btn_stop.config(state=tk.NORMAL)
        self.btn_export.config(state=tk.DISABLED)

        # İlerleme çubuğunu ayarla
        self.progress_bar["maximum"] = len(self.loaded_cases)
        self.progress_bar["value"] = len(self.results_data)

        # Arka plan iş parçacığını başlat
        self.worker_thread = threading.Thread(
            target=self._run_worker,
            args=(cases_to_run,),
            daemon=True
        )
        self.worker_thread.start()

    def _run_worker(self, cases_to_run):
        """Arka plan robot çalışma döngüsü."""
        # Kullanıcının rahatça UYAP penceresine geçebilmesi için 5 saniyelik geri sayım
        for i in range(STARTUP_COUNTDOWN, 0, -1):
            self.log(f"UYAP penceresine geçiniz... Robotun başlamasına {i} saniye!")
            self.after(0, lambda sec=i: self.lbl_progress.config(
                text=f"⏳ Lütfen UYAP ekranını açın... Başlamaya {sec} saniye!"
            ))
            time.sleep(1.0)

        self.after(0, lambda: self.lbl_progress.config(text="Robot çalışıyor... Dosyalar taranıyor."))
        desktop = os.path.join(os.environ.get("USERPROFILE", "C:\\Users\\Administrator"), "Desktop")
        interim_excel_path = os.path.join(desktop, "taksit_kontrol_GUNCEL.xlsx")

        def row_callback(result_dict, current_idx, total):
            def _update():
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
                self.results_data.append(result_dict)
                self.progress_bar["value"] = len(self.results_data)
                self.lbl_progress.config(
                    text=f"İşleniyor: {len(self.results_data)} / {len(self.loaded_cases)} (Son: {result_dict.get('dosya_no')})"
                )

                # HER 10 DOSYADA BİR OTOMATİK YEDEK KAYIT (Elektrik/Sistem kesintilerine karşı güvence)
                if len(self.results_data) % 10 == 0:
                    try:
                        df_temp = pd.DataFrame(self.results_data)
                        df_temp.columns = [
                            "Dosya No", "Sırası", "Miktarı", "Taksit No",
                            "Son Ödeme Tarihi", "Son Ödediği Tarih", "İşlem Durumu"
                        ]
                        df_temp.to_excel(interim_excel_path, index=False)
                    except Exception:
                        pass

            self.after(0, _update)

        def finish_callback(results):
            def _finish():
                self.btn_start.config(state=tk.NORMAL)
                self.btn_select_file.config(state=tk.NORMAL)
                self.btn_stop.config(state=tk.DISABLED)
                self.btn_export.config(state=tk.NORMAL)
                self.lbl_progress.config(text=f"Tamamlandı! Toplam {len(self.results_data)} dosya kontrol edildi.")
                self.auto_export_excel(self.results_data)
            self.after(0, _finish)

        self.bot.run_batch(
            cases_to_run,
            row_callback=row_callback,
            log_callback=self.log,
            finish_callback=finish_callback
        )

    def stop_automation(self):
        """Kullanıcı durdur butonuna bastığında."""
        self.log("Durdurma isteği gönderildi...")
        self.bot.stop()
        self.btn_stop.config(state=tk.DISABLED)

    def auto_export_excel(self, results):
        """İşlem bittiğinde otomatik masaüstüne Excel kaydeder."""
        if not results:
            return

        try:
            df = pd.DataFrame(results)
            # Sütun isimlerini Türkçeleştir
            df.columns = [
                "Dosya No",
                "Sırası",
                "Miktarı",
                "Taksit No",
                "Son Ödeme Tarihi",
                "Son Ödediği Tarih",
                "İşlem Durumu"
            ]
            desktop = os.path.join(os.environ.get("USERPROFILE", "C:\\Users\\Administrator"), "Desktop")
            output_file = os.path.join(desktop, f"taksit_kontrol_{time.strftime('%Y%m%d_%H%M%S')}.xlsx")
            df.to_excel(output_file, index=False)
            self.log(f"Otomatik Excel raporu kaydedildi: {output_file}")
            messagebox.showinfo("Tamamlandı", f"Kontrol tamamlandı!\nRapor kaydedildi:\n{output_file}")
        except Exception as e:
            self.log(f"Excel kayıt hatası: {str(e)}")

    def export_excel(self):
        """Kullanıcının manuel Excel kaydetmesi veya açması."""
        if not self.results_data:
            messagebox.showinfo("Bilgi", "Kaydedilecek sonuç verisi bulunamadı.")
            return

        save_path = filedialog.asksaveasfilename(
            title="Excel Raporunu Kaydet",
            defaultextension=".xlsx",
            filetypes=[("Excel Dosyası", "*.xlsx")],
            initialfile=f"taksit_kontrol_{time.strftime('%Y%m%d_%H%M%S')}.xlsx"
        )
        if not save_path:
            return

        try:
            df = pd.DataFrame(self.results_data)
            df.columns = [
                "Dosya No",
                "Sırası",
                "Miktarı",
                "Taksit No",
                "Son Ödeme Tarihi",
                "Son Ödediği Tarih",
                "İşlem Durumu"
            ]
            df.to_excel(save_path, index=False)
            messagebox.showinfo("Başarılı", f"Rapor başarıyla kaydedildi:\n{save_path}")
        except Exception as e:
            messagebox.showerror("Hata", f"Excel kaydedilirken hata oluştu:\n{str(e)}")

if __name__ == "__main__":
    app = UyapApp()
    app.mainloop()

