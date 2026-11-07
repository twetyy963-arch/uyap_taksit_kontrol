# UYAP Taksitli Dosya Kontrol Robotu

Bu program; UYAP ortamında ceza infaz bürolarındaki taksitlendirilmiş para cezası ilam dosyalarını otomatik olarak tarayan, ödenmemiş ilk taksit bilgilerini (sırası, miktarı, vadesi ve bir önceki taksitin son ödeme tarihiyle birlikte) tespit edip tablo haline getiren güvenli bir **RPA (Robotik Süreç Otomasyonu)** programıdır.

---

## 🔒 Güvenlik ve Gizlilik Garantisi

* **%100 Çevrimdışı (Offline):** Sistem hiçbir sunucuya, buluta veya harici adrese veri aktarmaz; tamamen bilgisayarınızda yerel çalışır.
* **Sıfır Veri Sızıntısı:** Dosyalarda yer alan şahsi bilgiler (T.C., Ad-Soyad, suç türü vb.) asla hafızaya alınmaz. Sadece talep edilen `Dosya No, Sırası, Miktarı, Taksit No, Son Ödeme Tarihi, Son Ödediği Tarih` alanları işlenir.
* **UYAP Dostu Davranış:** UYAP veritabanına veya sistemine müdahale etmez; ekran üzerinde insan gibi fareyle tıklama ve klavye girişi yapar.
* **Akıllı Donma ve Aşama Koruması:** UYAP donduğunda veya butonlar geç geldiğinde körü körüne tıklamaz; ilgili ekranın gelmesini sabırla bekler. Zaman aşımına uğrarsa açık pencereleri kapatıp ana arama ekranına geri döner ve sıradaki dosyaya geçer.

---

## 📁 Proje Dosya Yapısı

* **`main.py`**: Programın ana çalıştırıcısı.
* **`gui.py`**: Modern, canlı işlem günlüğü (log) ve takip tablosu içeren kullanıcı arayüzü.
* **`uyap_bot.py`**: Arama, sorgulama, ayrıntı, infaz sekmesi, uyarı kontrolü ve güvenli sıfırlama (recovery) motoru.
* **`ocr_engine.py`**: Windows yerel Türkçe OCR (`Windows.Media.Ocr`) motoru ile taksit tablosunu analiz eden modül.
* **`pdf_reader.py`**: TPI PDF listesindeki yıl gruplarını (`2022/2-18399`, `2024/2-21843` vb.) ve alt satırlardaki devam eden dosyaları hatasız çıkaran modül.
* **`screen_control.py`**: Ekran görüntüsü alma, buton şablon eşleme ve klavye/fare yönetim modülü.
* **`config.py`**: Buton dosya adları, zaman aşımları ve bekleme ayarları.
* **`baslat.bat`**: Programı çift tıklamayla masaüstünden çalıştırma dosyası.
* **`kurulum.bat`**: Gerekli Python kütüphanelerini tek tıkla kurma yardımcısı.

---

## 🚀 Nasıl Kullanılır?

1. **Görsellerin Kontrolü:**  
   `C:\Users\Administrator\Desktop\program` klasöründe şu görsellerin yer aldığından emin olun:
   * `1 - ilamat dosyası arama.png`
   * `2- dosya no.png`
   * `3- sorgula.png`
   * `4- dosya ayrıntı bilgileri.png`
   * `5- para cezası infaz.png`
   * `6-taksit mahsup uyarı.png`
   * `7- ödendiği tarih boş olan.png`

2. **Programı Başlatma:**  
   Proje klasöründeki **`baslat.bat`** dosyasına çift tıklayın.

3. **Liste Yükleme:**  
   Açılan ekranda **"📁 PDF / Liste Dosyası Seç"** butonuna tıklayarak TPI dosyanızı seçin. Program kaç adet dosya bulduğunu ekranda gösterecektir.

4. **UYAP Hazırlığı:**  
   UYAP ekranını açın ve **"İlamat Dosyası Arama"** ekranına getirin.

5. **Kontrolü Başlatma:**  
   Program arayüzündeki **"▶ Kontrolü Başlat"** butonuna basın. Robot sırayla dosyaları sorgulayacak, taksit tablolarını okuyacak ve canlı olarak ekranda listeleyecektir.

6. **Sonuç Raporu:**  
   İşlem bittiğinde sonuçlar otomatik olarak Masaüstünüze `taksit_kontrol_YYYYAAGG_SSDDSS.xlsx` adıyla Excel formatında kaydedilecektir.

