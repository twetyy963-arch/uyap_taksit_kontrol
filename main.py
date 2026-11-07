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

from gui import UyapApp

def main():
    app = UyapApp()
    app.mainloop()

if __name__ == "__main__":
    main()

