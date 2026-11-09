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

1. **Programı Başlatma:**  
   Arka planda siyah CMD komut penceresinin görünmemesi için klasördeki **`baslat.vbs`** dosyasına çift tıklayın (veya `baslat.bat`).

2. **Liste Yükleme ve Önizleme:**  
   * **"📁 PDF / Liste Dosyası Seç"** butonuna basarak dosyanızı seçin.
   * **"📋 Yüklenen Dosyalar Önizleme"** sekmesinde taranan **1.324 dosyanın tamamını** inceleyebilir, arama kutusundan istediğiniz dosyayı teyit edebilirsiniz.

3. **Yerleri Tanıtma (🎯 Kalibrasyon Sihirbazı - Önerilen ve En Hızlı Yöntem):**
   * UYAP ekranını açın ve görünür hale getirin.
   * Program arayüzündeki mor renkli **"🎯 Ekranda Yerleri Göster (Kalibrasyon Sihirbazı)"** butonuna basın.
   * Sırasıyla şu 6 noktayı farenizle gösterip **[Boşluk]** veya **[F2]** tuşuna basarak kaydedin:
     1. **İlamat Dosya Arama** Butonu
     2. **Dosya No** Giriş Kutusu
     3. **Sorgula** Butonu
     4. **Dosya Ayrıntı Bilgileri** Butonu *(Robot sorgulama sonucunda buraya tek tıklayacaktır)*
     5. **Para Cezası İnfaz** Sekmesi
     6. **Taksit Tablosu** Bölgesi
   * Bu işlem sadece bir kez yapılır; koordinatlar kaydedildiği için sıfır gecikmeyle çalışır.

4. **Alternatif Hibrit Mod (Otomatik OCR & Şablon):**
   * Eğer koordinat göstermezseniz, robot ekrandaki butonları Windows OCR ve akıllı eşleme ile ("dosya" veya "dosyası" ayrımına takılmadan) otomatik olarak bulur.

5. **Dinamik Ekran Değişim Takibi & Donma Koruması:**
   * **Akıllı Görsel Takip:** Robot sabit sürelere bağımlı değildir; "Sorgula"ya veya "Dosya Ayrıntı Bilgileri"ne bastığında ekrandaki görsel değişimi (sonuç satırının gelmesini, yeni pencerenin açılmasını) piksel farkıyla dinamik olarak izler.
   * **Esnek Bekleme (15 - 25 Saniye):** UYAP yanıt verene kadar sabırla bekler (Sakin modda 15 saniyeye, Yavaş modda 25 saniyeye kadar). Ekran değiştiğinde ve arayüz oturduğunda hemen bir sonraki adıma geçer; boş ekrana asla tıklamaz.
   * **⏱ Robot Hızı Seçenekleri:**
     * **🐢 Sakin / Güvenli (Önerilen - Akıllı Takipli):** Ekran takibi + 15 sn tavan bekleme süresiyle donmayı tamamen engeller.
     * **🛡 Yavaş (UYAP Donuyorsa / Ekstra Beklemeli):** 25 saniyeye kadar tavan bekleme ve ekstra uzun adımlarla en ağır günlerde dahi UYAP'ı yormaz.
     * **⚡ Hızlı:** Seri çalışan hızlı bağlantılar için.

6. **Otomatik 'Mahsup Bilgileri Güncellendi' Yakalayıcı:**
   * Dosya açıldığında veya Para Cezası İnfaz sekmesine geçildiğinde ekrana gelen *"Mahsup bilgileri güncellendi"* vb. açılır kutularda robot ekrandaki **[Tamam]** butonunu veya açılır pencereyi anında algılar, butona basıp Enter ve Boşluk ile onaylayarak pencereyi kapatır. Bu uyarı her dosyada çıkmadığı için kalibrasyon sihirbazında yer göstermenize gerek yoktur; sistem otomatik algılar.

7. **Kontrolü Başlatma:**  
   Yeşil renkli **"▶ Kontrolü Başlat"** butonuna basın. Robot her dosyayı sırayla sorgulayacak, ayrıntısına girecek, taksit durumunu tahlil edecek ve Excel olarak kaydedecektir. Çıkmak için farenizi ekranın sol üst köşesine çekebilirsiniz.

