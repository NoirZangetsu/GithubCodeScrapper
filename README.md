# GithubCodeScrapper

**Description:** Bu proje, GitHub API'sini kullanarak Flutter repository'lerinden .dart dosyalarını çekip yorumları temizleyerek fine-tuning için uygun CSV veri seti oluşturur.

## Özellikler
- GitHub API'si üzerinden "flutter" anahtar kelimesiyle repository araması yapar.
- Her repository'deki dosya ağacını (recursive) çekerek yalnızca `.dart` uzantılı dosyaları hedef alır.
- Dosya içeriklerini Base64 kodlamasından çözer.
- Kod içerisindeki tek satır (`//`) ve çok satırlı (`/* ... */`) yorumları kaldırır.
- Elde edilen veriyi prompt–completion formatında tek metin haline getirerek CSV dosyasına kaydeder.
- API rate limitlerini dikkate alarak istekler arasında bekleme süreleri uygular.

## Gereksinimler
- **Python 3.6+**
- `requests` kütüphanesi (diğer modüller Python’un standart kütüphanesinden)

