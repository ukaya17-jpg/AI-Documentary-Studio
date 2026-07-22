# AI Documentary Studio — İlerleme Günlüğü

Bu dosya, MoneyPrinterTurbo üzerine inşa edilen "AI Documentary Studio" pipeline'ının
kurulum ve geliştirme sürecini kaydeder. Önceki sunucu sıfırlandığı için kod kaybolmuştu;
bu günlük sıfırdan başlıyor.

## FAZ 0 — Ortam kurulumu

- [x] Bağımlılıklar: `.venv` zaten `uv` ile senkronize edilmişti, `requirements.txt`
      içindeki tüm paketler (streamlit, moviepy, openai, edge_tts, fastapi, loguru,
      google-genai, dashscope, redis, litellm, ...) import edilebiliyor. `pip` venv
      içinde yok (uv kullanılıyor), ekstra kurulum gerekmedi.
- [x] `config.toml`: Ortamda API key'leri dolu bir `config.toml` bulundu (Pexels,
      Pixabay, OpenAI key'leri gerçek görünüyordu). Kullanıcıya soruldu, kullanıcı
      "direkt üzerine yaz, key'ler kaybolsun" dedi → `config.example.toml`'dan boş
      iskelet olarak yeniden oluşturuldu. `[ui]` altına okunabilir altyazı ayarları
      eklendi: `font_name = "MicrosoftYaHeiBold.ttc"` (sans-serif, cursive değil),
      `subtitle_background_enabled = true`, `rounded_subtitle_background = true`.
      Kullanıcı kendi API key'lerini girecek.
- [x] WebUI doğrulaması: `streamlit run webui/Main.py` geçici bir portta (8577)
      başlatıldı, HTTP 200 döndü, log'da hata/traceback yok. Test instance durduruldu.
      Not: ortamda zaten 8501 portunda ayrı, önceden başlatılmış bir streamlit süreci
      var — bu bana ait değil, dokunulmadı.

## FAZ 1 — Documentary pipeline (devam ediyor)

- [x] `app/config/profile_dimensions.py`: `TopicCategory` (travel/history/space/
      psychology), `Pacing` (short/long), `Language` enum'ları + `PACING_SCENE_SPEC`
      (short=4 sahne x5s, long=7 sahne x8s) + `resolve_topic_category`/`resolve_pacing`
      yardımcıları.
- [x] `app/config/templates/__init__.py`: 4 kategori için `PROFILE_PROMPTS` (style/
      opening_hook/section_guidance/closing rehberi) + `get_template()`.
      **Not:** Kullanıcının bahsettiği `documentary_tr.py` önceki (kaybolan) oturumdan
      kalma bir referanstı, bu temiz repoda mevcut değildi — mimari sıfırdan, spec'e
      uygun şekilde tasarlandı.
- [x] `app/models/`: `research_plan.py`, `outline.py`, `scene.py`, `script.py`,
      `storyboard.py`, `asset.py`, `audio.py`, `timeline.py`, `seo.py`,
      `documentary_project.py` — düz "Plan" tabanlı pydantic modelleri, Project+
      Metadata katmanı yok. `DocumentaryProject` her aşamanın çıktısını doğrudan
      alan olarak tutuyor.
- [x] Test: `test/services/test_documentary_models.py` (8 test) — tüm modeller,
      enum çözümleme ve template fallback'i kapsıyor. **YEŞİL.**

- [x] `app/services/intent_analyzer.py`: dil (auto → Türkçe karakter heuristiği)
      ve topic category (LLM sınıflandırma + keyword heuristik fallback,
      override her zaman kazanır) çözümü. Paylaşılan `documentary_llm_utils.py`
      (`generate_json`) tüm JSON üreten aşamalarca kullanılıyor.
- [x] `app/services/research_planner.py`: LLM'den key_questions/key_facts/angles
      brief'i üretir. **Not:** Canlı web araması yok (böyle bir araç bu repoda
      bağlı değil) — LLM'in kendi bilgisini yapılandırıyor, gerçek kaynak
      taraması yapmıyor.
- [x] `app/services/outline_generator.py`: kategori şablonuna göre title/hook/
      sections(+importance 1-5)/closing outline'ı üretir.
- [x] `app/services/scene_planner.py`: **LLM çağrısı yok**, saf mantık.
      Pacing'e göre sahne sayısı/süresi (short=4x5s, long=7x8s), importance'a
      göre en yüksek puanlı bölümler orijinal anlatı sırasıyla seçiliyor.
- [x] `app/services/script_generator.py`: sahne başına ~2.3 kelime/sn hedefiyle
      anlatım metni üretir; LLM bir sahneyi atlarsa narration_beat'e düşer.
- [x] `app/services/storyboard_generator.py` + `app/prompts/storyboard/`:
      kategoriye göre görsel/çekim rehberi (travel/history/space/psychology),
      sahne başı 1 çekim + 3-5 stok görüntü arama terimi.
- [x] `app/services/asset_generator.py` + `asset_downloader.py`: storyboard'u
      sahne sıralı arama listesine çevirir; indirme **legacy `material.py`**
      (`download_videos`, `match_script_order=True`) üzerinden yeniden yazılmadan
      yapılıyor.
- [x] `app/services/audio_renderer.py`: **legacy `voice.py`** (`tts()`,
      `create_subtitle()`, `get_audio_duration()`) üzerinden sarmalayıcı.
- [x] `app/services/timeline_builder.py`: **legacy `video.py`**
      (`combine_videos()`) üzerinden sarmalayıcı.
- [x] `app/services/seo_generator.py`: yeni prompt yazmak yerine mevcut
      `llm.generate_social_metadata()` (title/caption/hashtags, kendi retry ve
      heuristic fallback'i ile) yeniden kullanılıyor.
- [x] **`app/services/video.py` düzeltmesi:** `generate_video()` içindeki son
      `write_videofile` çağrısına `ffmpeg_params=["-movflags", "+faststart"]`
      eklendi (moov atom sorunu — bazı player'lar dosya tam inmeden ses
      pistini algılayamıyordu). Bu düzeltme legacy pipeline dahil **her**
      üretilen videoya uygulanıyor. Mevcut 41 testlik `test_video.py` paketi
      hâlâ yeşil.
- [x] `app/services/video_renderer.py`: **legacy `video.py`**
      (`generate_video()`) üzerinden sarmalayıcı; BGM mix başarısız olursa
      uyarı logluyor ama anlatı-only video üretmeye devam ediyor.
- [x] `app/pipeline/default_pipeline.py`: `run_pipeline()` — 12 aşamayı sırayla
      çağıran orkestratör (Intent→Research→Outline→Scene→Script→Storyboard→
      Asset→AssetDownload→Audio→Timeline→SEO→VideoRenderer).
- [x] Test: her servis için ayrı unit test dosyası + `test_default_pipeline.py`
      (tüm zincirin mock LLM/medya I/O ile uçtan uca kablo testi). **Toplam
      test/services paketi: 503 test, hepsi YEŞİL** (11 skip — gerçek API/
      FFmpeg gerektiren entegrasyon testleri, ortamda zaten öyleydi).

- [x] `webui/Main.py`: "AI Documentary Studio (Beta)" bölümü eklendi — konu,
      dil, topic category (auto + override), pacing seçicileri, ses adı,
      "Generate Documentary" butonu, `st.video()` ile sonuç + SEO metadata
      gösterimi. Bilinçli olarak legacy arka-plan task manager'dan bağımsız
      tutuldu (senkron çalışıyor, `st.spinner` ile) — "hızlı uygulama"
      talebiyle uyumlu.
      Gerçek headless-Chromium (Playwright) oturumuyla doğrulandı: traceback
      yok, console hatası yok, tüm alanlar (konu/dil/kategori/pacing/buton)
      görünüyor. `i18n` parity testi (`test_webui_i18n.py`) kırmızı çıktı
      (yeni key'leri sadece en/tr'ye eklemiştim) → 9 locale dosyasının hepsine
      çeviri eklendi, test tekrar yeşile döndü.
      **Toplam test/services paketi hâlâ 503 test, hepsi YEŞİL.**

## FAZ 1 — Durum: kod tamamlandı, gerçek uçtan-uca üretim key bekliyor

12 aşamanın tamamı (Intent→Research→Outline→Scene→Script→Storyboard→Asset→
AssetDownload→Audio→Timeline→SEO→VideoRenderer) yazıldı, birim test edildi
(mock LLM/medya I/O) ve webui'ye bağlandı. Ayrıca gerçek `_generate_response`
çağrı yoluna kadar bir "gerçek" smoke test yapıldı: config.toml'da hiçbir LLM
key'i olmadan `run_pipeline()` çağrıldı, beklendiği gibi 3 deneme sonrası
temiz bir `ValueError` ile başarısız oldu (çökme/traceback yok) — bu da
config okuma, provider çözümleme ve hata yayılımı zincirinin doğru
çalıştığını kanıtlıyor.

**Güncelleme — gerçek uçtan uca test TAMAMLANDI (2026-07-22):** Kullanıcı
`config.toml`'a gerçek key girdi (OpenAI, Pexels, Pixabay, ElevenLabs).
`run_pipeline()` gerçek OpenAI + gerçek Pexels indirme + gerçek ElevenLabs
TTS ile (hiç mock yok), konu "The Fall of the Roman Empire", pacing=short,
uçtan uca çalıştırıldı — 12 aşama da başarıyla tamamlandı, ~185 saniye sürdü.

`ffprobe` doğrulaması:
- video: h264, 1080x1920, 30fps, süre 20.87s
- audio: aac, 44100Hz, stereo
- format: süre 20.87s, boyut 9,137,074 byte, bit_rate ~3.5 Mbps
- moov atom offset 32, mdat offset 24032 → **moov mdat'tan önce, faststart
  doğru çalışıyor**
- `ffmpeg volumedetect`: mean_volume -16.0 dB, max_volume -3.5 dB (kliplenme
  yok, makul seviye)

**Bu gerçek çalıştırma sırasında bir kusur bulundu ve düzeltildi:**
`default_pipeline.py`, render aşamasında çıplak `VideoParams(...)` oluşturuyordu
ve Faz 0'da `config.toml [ui]`'a yazdığım okunabilir altyazı ayarlarını
(`MicrosoftYaHeiBold.ttc`, arka plan, yuvarlak köşe) hiç okumuyordu — üretilen
videoda şemanın sabit varsayılanı (`STHeitiMedium.ttc`) kullanılmıştı. Legacy
WebUI formu her widget değerini elle `params` üzerine yazıyor, benim pipeline'ım
bunu yapmıyordu. Düzeltme: `video_renderer.build_video_params()` eklendi,
`config.ui`'dan font/renk/boyut/arka plan ayarlarını okuyor (webui/Main.py'deki
`DEFAULT_SUBTITLE_SETTINGS` ile aynı fallback mantığı, import edilemediği için
yerelde tekrar tanımlandı). Var olan gerçek asset'lerle (yeni API çağrısı
yapmadan) yeniden render edilip log'da `font: .../MicrosoftYaHeiBold.ttc`
göründüğü doğrulandı, ikinci `ffprobe`/faststart kontrolü de geçti. 3 yeni
test eklendi, tüm suite (531 passed, 11 skipped) hâlâ yeşil.

**Faz 1 artık tamamen tamamlandı** — kod, mock testler, gerçek API testi ve
bulunan kusurun düzeltmesi dahil.

## FAZ 2 — Content OS genişletmesi: TASLAK PLAN (onay bekleniyor)

Önceki oturumdan kalan "Content OS" vizyonunun (Thinking Layer / Department
yapısı / Learning Layer) tam ayrıntısı kaybolduğu için, aşağıdaki plan benim
yorumumdur — başlamadan önce onayınızı istiyorum.

**1) Department yapısı (organizasyonel, düşük risk, önce bu)**
Mevcut servisleri mantıksal "departman" gruplarına taşı (davranış değişmez,
sadece modül yerleşimi):
- Research Dept: intent_analyzer, research_planner, outline_generator
- Creative Dept: scene_planner, script_generator, storyboard_generator
- Production Dept: asset_generator, asset_downloader, audio_renderer,
  timeline_builder, video_renderer
- Growth Dept: seo_generator (+ ileride: yayınlama/analytics)
Test edilebilirlik: mevcut testler import yollarını güncelleyip yeşil kalmalı.

**2) Thinking Layer (orta risk)**
Tek bir documentary run'ının üstünde oturan, "sıradaki ne olsun" ve "bu çıktı
yeterince iyi mi" sorularını cevaplayan meta katman:
- `idea_generator.py`: niş/kategori bazlı aday konu üretir.
- `quality_critic.py`: tamamlanmış bir `DocumentaryProject`'i (script tutarlılığı,
  pacing uyumu, SEO kalitesi) puanlar, yayın öncesi eşik koyar.
Faz 1 ile aynı desende (mock LLM ile test edilebilir) yazılabilir.

**3) Learning Layer (yüksek risk / erken olabilir)**
Yayınlanan videoların gerçek performansını (izlenme, etkileşim) toplayıp
Thinking Layer'ın gelecekteki konu/prompt kararlarına geri besleyen katman.
**Bunun için gerçek bir yayınlama + analytics entegrasyonu (örn. YouTube
Data API) gerekiyor — ki bu henüz yok.** Önerim: bu katmanı şimdi kod
yazmadan ertelemek, Faz 1 birkaç gerçek video yayınlayıp geri bildirim
verisi biriktirene kadar beklemek. Aksi halde besleyecek gerçek sinyali
olmayan, test edilemeyen bir iskelet inşa etmiş oluruz.

**KARAR BEKLENİYOR:** Yukarıdaki yorum/sıralama doğru mu, yoksa "Content OS"
vizyonunuzda gözden kaçırdığım somut bir gereksinim var mı? Onay verirseniz
1) ile başlarım.

## FAZ 2 — Content OS genişletmesi

Başlanmadı. FAZ 1 sağlam bir şekilde bitmeden başlanmayacak. Faz 2 planı burada
kullanıcı onayı beklenerek yazılacak.

## Karar bekleyen noktalar

Şu an yok.
