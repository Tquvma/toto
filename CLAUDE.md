# Spor Toto Tahmin Projesi

Kullanıcıyla **Türkçe** konuş. Her hafta Spor Toto'nun 15 maçlık programı için derin araştırma yapılır, olasılıklar tahmin edilir, kupon önerilir ve sonuçlar takip edilir. Kullanıcı "her şeyi tam araştıralım" dedi: yüzeysel tahmin değil, kaynaklı analiz bekliyor.

## Güncel durum (her adımda güncelle)
- **10. hafta kapandı (22 Ekim'de işlendi):** 111211211222112. Kullanıcının analizsiz kendi kuponu K10 (72 kolon, 720 TL) **14/15** bildi (tek kaçak Kocaeli–Göztepe), ikramiye 1.941 TL, **net +1.221 TL**. Sezon (8–10) net ~+723 TL. Bu haftanın JSON'unda `final` ve `halk` yok.
- **9. hafta kapandı (17 Ekim'de işlendi):** 100220212010210, N 11/15, S2 8/15, −620 TL. Kalibrasyon: bağımsızlık modeli sürpriz sonucunda kazananları 1,5–2 kat fazla tahmin etti (8. haftada favori sonucunda az). Halk kolonları bağımlı, sürpriz senaryolarının ödemesi modelin üstünde. Ayrıntı: 9. hafta md "Sonuçlar".
- **11. hafta (kapanış 23 Ekim 19:55), bu haftalık strateji:** Kullanıcı bu hafta **~500 TL bütçe** istedi (stratejiler hafta hafta değişebilir, her hafta bütçeyi sor). Bulut oturumunda (toto.py olmadan, WebSearch/WebFetch ile) hazırlanan öneri, 48 kolon / 480 TL: `10 2 1 2 1 12 1 2 102 1 12 1 1 1 12` (üçlü: GS–FB; çiftliler: Alanya–Kocaeli 1-0, Göztepe–Çorum 1-2, Monaco–Lille 1-2, Napoli–Roma 1-2). Ucuz alternatif: 36 kolon / 360 TL (Napoli–Roma üçlü, Alanya ve Monaco banko 1). Riskli bankolar: Barça–Real (García sakat, Koundé şüpheli), PSG–Lyon, Konya–Gençler, Gaziantep–Erzurum. 23 Ekim 14:00'te son kontrol hatırlatması var. Oynanan kuponu kullanıcıdan teyit et.
- **Sıradaki iş:** 11. hafta son kontrol ve oynanan kuponun kaydı; `kazanc` modeline halk bağımlılığı eklemeyi düşün.
- **Strateji (9 Ekim 2026'dan beri):** Kullanıcı "fiyata kota koymadan 15 bilmeye çalışalım, öyle devam edelim" dedi. Ölçüt artık **15 bilme olasılığı**, fiyat sınırı yok. Uygulama: tek bilet tavanı (2.500 kolon; genelde 7 üçlü = 2.187 kolon). Birden fazla bilet verimsiz (3 kat para, ~2 kat 15 şansı), sadece seçenek olarak tabloda göster. Getiriyi ve 15 tutunca ödeme dağılımını yine göster, 15'ten biraz vazgeçip getiriyi ~%100'e çıkaran bir alternatif (bu hafta D) sun.
- **9. hafta kuponu N, 54 kolon / 540 TL, OYNANDI (kullanıcı teyit etti, 9 Ekim 17:35):** `1 2 1 2 2 1-0-2 1-0-2 1 2 2 1 1 1-2 1 1-0-2`. 15 %0,21, 14+ %2,0, 13+ %8,8, getiri ~%29. 15'i ancak tüm favoriler kazanınca tutturur, o zaman ~5.000 kişiyle paylaşılır (~11 bin TL). Alternatif N2 (değerli): 15 %0,17, getiri ~%46. Gün içindeki sıra: L (1.440 TL) → I (tek bilet maks, 21.870 TL, 15 %2,87) → J (3 bilet, 21.330 TL, 15 %3,02) → N. **Ders:** "540 TL düşürelim" "toplam 540 TL olsun" demekti, eksiltme diye anlaşıldı. Tutar ifadelerinde "X TL'ye mi, X TL mi?" netleştir. Kullanıcının gerçekte neyi yatırdığını teyit et.
- **Ek sürpriz kuponu S2 OYNANDI (9 Ekim 18:26), haftanın toplamı 620 TL (N 540 + S2 80).** Öneriler: S2 `1 2 2 1 1-2 2 2 1 1-2 2 1 1 2 1 1-2` (80 TL, 15 1/17.600, tutarsa ~1,8 M TL), S1 `1 1 1-2 2 1-2 2 2 1 2 2 1 1 2 1 1-2` (80 TL, 1/6.300, ~156 bin), T4 (40 TL). N ile ayrık. Kullanıcının hangisini oynadığını teyit et (JSON `surpriz_kuponlari.oynandi`). Araçlar: `kesin_kazanc.py <hafta.json> "<secimler>"...` (küçük kuponlarda örneklemesiz tam getiri ve 15 tutunca ödeme dağılımı; MC'yle uyumlu) ve `surpriz_ara.py <hafta.json> <cikti.json> <kolonlar> <p15_esikleri> --ayrik "<oynanan>"` (8 çekirdekte ~20 dk). **Model riski:** sürpriz kombinasyonlarında bağımsızlık ve α=1,15 getiriyi şişirir. Bağımsız ajan analizi: makul getiri modelin ~%40–80'i. Sürpriz kuponlarını piyango bileti olarak sun.
- **Yöntem (9 Ekim): çok biletli kupon.** Bir bilete yazılamayan tutarlar (2 ve 3'lerin çarpımı olmayan kolon sayıları) birkaç ayrık sisteme bölünerek oynanır. Tabandan az olası bir blok çıkarılıp tabanın bir tekini saptıran olası bir blok eklenince aynı ya da daha az parayla 15 olasılığı artabiliyor (J: −540 TL, 15 %2,87 → %3,02). Araçlar: `kupon_kisalt.py <hafta.json> "<taban>" <hedef_kolon> [cikti.json]` (arama, ~30 sn) ve `coklu_bilet.py <hafta.json> "<bilet1>" "<bilet2>" ...` (tam 15/14+/13+ ve 4 tohumlu kazanç). Tek biletten fazla kolon için de aynı yöntem kullanılabilir.
- **8. hafta dersi:** H ve 144 kolonluk kupon 14/15 bildi, ama aşırı favori haftasıydı (15 bilen 2.580 kişi, 14 ikramiyesi 417 TL). Kullanıcı 144 kolonu oynadı (~1.562 TL, küçük kâr), "bilmemiz önemliydi" dedi. Halk kolonları favorilerde bağımsızlık varsayımından kalabalık: `kazanc` modelinde α=1,15.
- **Yöntem dersi (8 Ekim):** ≤144 kolon gibi dar bütçede tekli değişiklik yapan yerel arama takılıyor. Boyut takası hamlesi (bir maç küçülürken diğeri büyür) ve eşik kısıtı şart. Kısıtsız `kar` araması 13+'sı %2 olan piyango kuponlarına kayıyor (gürültülü getiri %500+). Aday kuponları 4 bağımsız tohumla doğrula. Betikler `araclar/` altında: `kupon_ara.py` (kısıtsız çok başlangıçlı arama), `kupon_ara_kisitli.py <hafta.json> <cikti.json> <sinir> <esik,esik> [onceki.json...]` (13+ kısıtlı kâr araması), **`kupon_ara_p15.py <hafta.json> <cikti.json> <sinir> <esik,esik>` (15 olasılığı kısıtlı kâr araması; 2.500 kolonda ~10 sn)**, `kupon_degerlendir.py <hafta.json> <adaylar.json...>` (Pareto + duyarlılık), `kupon_dogrula.py <hafta.json> <deger.json>` (4 tohum). Adaylar `[{"secimler":[...]}]` biçiminde JSON.
- Kullanıcının oynama geçmişi: 8. haftada 1.440 TL. 9. haftada önce 1.440 TL planlandı. 9 Ekim akşamı "fiyata kota koymadan 15" dedi, ama 21.870 TL'lik öneriyi görünce toplamı 540 TL'ye indirdi, yanına 80 TL'lik sürpriz kuponu (S2) ekledi. "Fiyat sınırı yok" demesi gerçek bütçesini göstermiyor. Büyük kuponu karşılaştırma olarak göster, gerçek bütçesini sor.

## Dosyalar
- `haftalar/<sezon>_<hafta>.md`: haftalık analiz (özet tablo, kuponlar, grup/puan durumu, maç maç analiz, güncelleme listesi, sonuçlar, kaynaklar). Örnek: `haftalar/2026-2027_08.md`
- `haftalar/<sezon>_<hafta>.json`: makine verisi (maçlar, `piyasa`/`elo`/`final` olasılıkları, oranlar, `kuponlar`, `sonuc`)
- `takip.md`: sezon takibi (bizim isabetimiz ve resmi sonuç/ikramiye tablosu)
- `araclar/toto.py`: veri aracı (sadece standart kütüphane; bu makinede numpy yok)

## Haftalık akış
1. Önceki haftayı kapat: `python araclar/toto.py sonuc haftalar/<önceki>.json`. Çıktıyı md'deki "Sonuçlar" bölümüne ve `takip.md`'ye işle (resmi tabloya yeni satır ekle).
2. Yeni program (önceki hafta kapanınca açılır): `python araclar/toto.py program --yaz`, sonra `lig` etiketlerini düzelt (API'nin grup adları yanlış olabiliyor).
3. Oranlar: `python araclar/toto.py oranlar haftalar/X.json --statsbet`. Nesine bülteni maçlardan yaklaşık 2–3 gün önce açılır. `--statsbet` sadece milli maçlarda otomatik çalışır.
4. Milli takım haftasıysa: `python araclar/toto.py elo haftalar/X.json`
5. Araştırma, her maç için: puan durumu, son form, sakat/cezalı, teknik direktör, motivasyon (derece/düşme/kupa), rotasyon (araya giren maçlar), saha/seyirci. Skorları WebSearch özetinden değil ESPN API'den doğrula.
6. `final` olasılıklarını JSON'a yaz: piyasa ağırlıklı (Pinnacle varsa ~%80, yoksa ~%70) + Elo/model + haber düzeltmesi.
7. **Halkın yüzdeleri:** `python araclar/toto.py halk haftalar/X.json` (Nesine "% Tercih"). Kapanışa yakın tekrar çek, yüzdeler gün içinde değişir.
8. **Kupon (9 Ekim'den beri hedef 15 bilmek):** Fiyat sınırı yok, sınır tek bilet (2.500 kolon). Ana kupon `oner --hedef 15 --kolon 2500` (tek bilete sığan en yüksek 15 olasılığı). Bütçe tablosu için `oner --hedef 15 --tara`. Sonra `kupon_ara_p15.py` ile 15 eşikli kâr araması yap ve 15'ten az vazgeçip getiriyi belirgin artıran bir alternatif göster. Her kuponda 15 tutunca ödeme dağılımını (medyan, çeyrekler) ve getiriyi yaz. Kullanıcı tek bilete yazılamayan bir tutar isterse `kupon_kisalt.py` ile çok biletli çözüm bul, `coklu_bilet.py` ile doğrula. Devir varsa `kazanc --devir` ver. Seçilen kuponu JSON'da `kuponlar` + `oynanan_kupon` alanına, md'nin en üstüne ve `takip.md`'ye yaz. (8. haftadaki 13+/kâr odaklı yöntem için bkz. 8. hafta md "Kazanç analizi".)
9. Kapanış günü (ilk maçtan önce) son güncelleme: oranlar, halkın yüzdeleri, ilk 11 haberleri, araya giren maç sonuçları.

## Oyun kuralları (resmi oyun planı)
- 15 maç, **normal süre** sonucu geçerli (uzatma ve penaltı sayılmaz). 1 = ev sahibi, 0 = beraberlik, 2 = deplasman.
- İkramiye dağılımı: 15 bilen %35, 14 bilen %20, 13 bilen %20, 12 bilen %25. Bilen yoksa devreder.
- Kapanış: programdaki ilk maçın başlama saati. Bir bilette en fazla 2.500 kolon.
- Kolon bedeli **10 TL** (Mart 2025'ten beri). Değişirse `toto.py` içindeki `KOLON_BEDELI`'yi güncelle.
- İptal/ertelenen maç: noter çekilişi (iki takımın son 5 lig maçına göre 10 top).
- İkramiye bilenler arasında paylaşılır: favori haftalarında ödül düşük, sürpriz haftalarında yüksek.

## Veri kaynakları
- Spor Toto API: `https://webapi.sportoto.gov.tr/api/GameRound`, `api/GameMatch/GetGameMatches/?gameRoundId=<id>`, `api/GameResult/GetGameResultByGameRoundId?Id=<id>` (Origin/Referer başlığı gerekiyor). Sonuç kodu `fullTimeWin`: 1/0/2.
- Nesine: `https://bulten.nesine.com/api/bulten/getprebultenfull` (GT 1 = futbol, MTID 1 = maç sonucu)
- Nesine Spor Toto: `https://st.nesine.com/v2/Program` (aktif program, maç başına `percentage1/0/2` = halkın % tercihi). Geçmiş programlar bu uç noktadan alınamıyor, o yüzden her hafta JSON'a kaydet (`halk` alanı).
- statsbet.org: `https://statsbet.org/football/matches/<ev>-vs-<dep>-<YYYY-MM-DD>` (İngilizce slug; Pinnacle/1xBet/bet365). bet365 1.5/3.0/1.5 değeri sitenin yer tutucusudur.
- ESPN: `https://site.api.espn.com/apis/site/v2/sports/soccer/<lig>/scoreboard?dates=YYYYMMDD` (canlı skor ve DraftKings oranı; lig kodları: uefa.nations, tur.1, eng.1, esp.1, ita.1, ger.1, fra.1)
- eloratings.net: `World.tsv`, `en.teams.tsv`, `<Takım>.tsv`. **Tarafsız sahadaki maçlarda kazanan önce yazılır**, modeli bu maçlarla fit etme.

## Tuzaklar
- Türkiye'de betexplorer, oddsportal gibi bahis sitelerine erişim engelli (SSL/sertifika hatası). WebFetch de yerel ağdan çıktığı için engelleniyor. statsbet, ESPN ve Nesine çalışıyor. clubelo API'si kapalı.
- **Cowork oturumunda (Ekim 2026) hem bilgisayardaki kabukta hem bulutta ağ kapalı** (`toto.py` çekemiyor). Çözüm: Chrome'da nesine.com açıp `fetch('https://st.nesine.com/v2/Program')` ve `fetch('https://bulten.nesine.com/api/bulten/getprebultenfull')`, statsbet.org açıp `/football/matches/<slug>` sayfalarını JS ile çekip `statsbet_oranlari` regex'iyle ayrıştırmak. Veriyi JSON'a python ile yaz. Uzun aramalar (kupon_ara_kisitli) bulutta çalışır, bilgisayardaki kabukta arka plan süreci yaşamıyor.
- **Claude Code masaüstü oturumunda (9 Ekim 2026) kabuktan ağ çalışıyor**, `toto.py` doğrudan çekiyor. Nesine bülteni sıkıştırmasız istekte bağlantıyı sıfırlıyordu; `istek()` artık gzip istiyor. Kulüp maçlarında statsbet otomatik değil: JSON'daki `statsbet.url` ile çekilmeli.
- WebSearch özetleri canlı ya da yeni biten maçlarda yanlış skor verebiliyor.
- Git Bash'teki `/c/...` yollarını Windows Python okuyamaz: `cygpath -w` kullan ya da PowerShell'den çalıştır.

## Model notları
- Elo modeli (toto.py): sıralı lojistik, A=0.5261, B=0.3376 (ev sahibi), C=0.6546. 2010 sonrası UEFA takımlarının resmi ev maçlarıyla (n=2769) fit edildi, kalibrasyonu iyi. Elo farkı 500'ü aşan maçlarda piyasadan fazla emin çıkar (ör. İspanya–Çekya: Elo %95, piyasa %78), piyasaya yakın dur.
- Uluslar Ligi'nde ev avantajı daha küçük (B≈0.26) ve beraberlik oranı ~%25.
- Milli takım haftalarında kadro rotasyonu kritik (ör. Klopp'un Almanya'sı Eylül ve Ekim için iki ayrı kadro kurdu).
- **Paylaşımlı ikramiye modeli (`kazanc`):** Havuz ≈ KDV sonrası hasılatın %59'u (yasal tavan), yani kolon başına ~5 TL ikramiye. Halkın ortalama geri dönüşü ~%50. Halk kolonları Nesine yüzdeleriyle bağımsız sayılır. 8. haftada büyüklük olarak 7. haftanın gerçek kazanan sayılarıyla uyumluydu.
- 8. hafta bulguları: Halk favorileri fazla oynuyor. Favori ağırlıklı kuponların beklenen getirisi ~%65–75, en iyi isabetli+değerli kupon ~%90, saf değer kuponu ~%130+ (ama isabeti düşük). 40 M TL devir getiriyi ~+28 puan artırır.
- Her hafta sonunda tahmini ve gerçek kazanan sayılarını karşılaştırıp modeli kalibre et (halkın kolon sayısı, bağımlılık).
