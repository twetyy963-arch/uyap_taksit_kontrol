# -*- coding: utf-8 -*-
"""
UYAP Taksit Kontrol Robotu - Başlatıcı (Main Entry Point)
"""
import sys
import os

# Dizin yollarını ayarla
current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.insert(0, current_dir)

import time
import traceback
import threading

def _global_exception_handler(exc_type, exc_value, exc_traceback):
    err_str = "".join(traceback.format_exception(exc_type, exc_value, exc_traceback))
    try:
        log_path = os.path.join(current_dir, "hata_raporu.log")
        with open(log_path, "a", encoding="utf-8") as f:
            f.write(f"\n--- KRİTİK ÇÖKME HATASI ({time.strftime('%Y-%m-%d %H:%M:%S')}) ---\n")
            f.write(err_str)
    except Exception:
        pass

sys.excepthook = _global_exception_handler
if hasattr(threading, "excepthook"):
    threading.excepthook = lambda args: _global_exception_handler(args.exc_type, args.exc_value, args.exc_traceback)

from gui import UyapApp

def main():
    app = UyapApp()
    app.mainloop()

if __name__ == "__main__":
    main()

