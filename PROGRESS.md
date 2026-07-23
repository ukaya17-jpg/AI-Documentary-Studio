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

**Kullanıcı onayı alındı (2026-07-22):** Department yapısıyla başlanması,
Learning Layer'ın ertelenmesi onaylandı. Thinking Layer henüz başlanmadı,
Department yapısı bitince ayrıca ele alınacak.

## FAZ 2 / Adım 1 — Department yapısı: TAMAMLANDI

Saf organizasyonel taşıma, davranış değişmedi. Yeni yapı:
`app/departments/{research,creative,production,growth}/` (her biri paket).

- [x] **Growth**: `seo_generator.py` taşındı (en düşük riskli ilk adım).
- [x] **Research**: `intent_analyzer.py`, `research_planner.py`,
      `outline_generator.py` taşındı.
- [x] **Creative**: `scene_planner.py`, `script_generator.py`,
      `storyboard_generator.py` taşındı.
- [x] **Production**: `asset_generator.py`, `asset_downloader.py`,
      `audio_renderer.py`, `timeline_builder.py`, `video_renderer.py` taşındı.

`app/services/documentary_llm_utils.py` (Research+Creative arası paylaşılan
LLM JSON helper'ı) ve `app/prompts/storyboard/` (içerik, kod değil) planlandığı
gibi yerinde kaldı — sadece 12 servis dosyası taşındı. `app/services/` artık
sadece legacy MoneyPrinterTurbo servislerini (material/voice/video/llm/...)
içeriyor.

Her adımda: `default_pipeline.py` import'ları + ilgili test dosyalarının
import/patch yolları güncellendi, o servisin testi + `test_default_pipeline.py`
(mock wiring) + tam suite çalıştırıldı, sonra commit. 4 department = 4 ayrı
commit. Ayrıca Faz 1'den kalan izlenmeyen `app/pipeline/__init__.py` bu sırada
fark edilip git'e eklendi.

**Son doğrulama:** Tam suite hâlâ yeşil (531 passed, 11 skipped). Ayrıca
gerçek `streamlit run` + headless-Chromium ile webui açıldı, "AI Documentary
Studio (Beta)" bölümü genişletildi — traceback/import hatası yok, console
hatası yok, tüm alanlar (konu/dil/kategori/pacing/buton) görünüyor. Davranış
değişmediği için gerçek API ile yeniden render **gerekmedi**.

## FAZ 2 / Adım 2 — Thinking Layer: TASARIM (onaylandı, kodlama başlıyor)

Kodlamadan önce sunulan tasarım planı, kullanıcı onayı ile:

**Yeni paket:** `app/thinking/` — `app/departments/`'ın yanında, bir department
değil, ayrı bir "katman". İçinde `idea_generator.py` ve `quality_critic.py`.

**`idea_generator`** — ham/belirsiz kullanıcı girdisini düzgün bir belgesel
konusuna çevirir. Kategori veya dil belirlemez (bu IntentAnalyzer'ın işi,
çakışma yaratılmadı). Girdi: `raw_input: str`. Çıktı: `IdeaCandidate` modeli
(`app/models/idea.py`): `topic: str`, `angle: str`. **Pipeline'ın dışında,
`run_pipeline(topic=...)`'ın önünde** — WebUI serbest metin girdisini
`idea_generator`'a verip çıkan `topic`'i `run_pipeline`'a geçirecek;
`run_pipeline`'ın imzası değişmiyor, mevcut testler/gerçek e2e akışı kırılmıyor.
Gerçek LLM çağrısı yapıyor (küçük prompt, ucuz); hata olursa ham girdiyi
olduğu gibi `topic` yaparak geçer (fallback).

Örnek: "Japonya neden güvenli?" → `{"topic": "Japonya'yı Bu Kadar Güvenli
Yapan Nedir?", "angle": "Düşük suç oranının arkasındaki kültürel, tarihi ve
toplumsal dinamikleri ortaya çıkarıyoruz."}`. **Not:** bu örnek, mevcut 4
sabit kategorinin (travel/history/space/psychology) "toplum/kültür" gibi
konuları tam karşılamadığını gösteriyor — idea_generator'ın çözeceği bir şey
değil, kategori şemasının bilinen bir sınırı, kapsam dışı bırakıldı.

**`quality_critic`** — tamamlanmış bir `DocumentaryProject`'i (outline+script+
seo) değerlendirir. Girdi: `DocumentaryProject`. Çıktı: `QualityVerdict`
modeli (`app/models/quality.py`): `coherence_score`, `pacing_fit_score`,
`seo_quality_score` (1-5), `overall_score` (3'ünün ortalaması), `passed`
(`overall_score >= 3.0`, sabit eşik), `issues: list[str]`. Gerçek LLM çağrısı
yapıyor. **v1'de pipeline'a otomatik/zorunlu aşama olarak bağlanmıyor** —
bağımsız `evaluate_project()` fonksiyonu olarak kalıyor, çünkü "başarısız
olursa ne olsun" (durdur/yeniden dene/sadece uyar) sorusu henüz cevaplı değil
ve bunu icat etmek daha büyük, ayrı bir mimari karar. LLM/parse hatasında
sessizce `None` döner + log uyarısı, pipeline hiçbir zaman etkilenmez.

**Kabul kriterleri:** her iki servis de mock LLM ile test edilecek — başarılı
parse, fallback/hata davranışı, boş girdi kontrolü (idea_generator) ve eşik
hesaplama doğruluğu (quality_critic).

## FAZ 2 / Adım 2 — Thinking Layer: UYGULANDI

- [x] `app/models/idea.py` (`IdeaCandidate`: topic, angle) ve
      `app/models/quality.py` (`QualityVerdict` + `QUALITY_PASS_THRESHOLD = 3.0`).
- [x] `app/thinking/idea_generator.py`: `generate_idea(raw_input) -> IdeaCandidate`.
      Gerçek LLM çağrısı, hata/boş sonuçta ham girdiyi olduğu gibi geçirir
      (fallback + log uyarısı). Boş/whitespace girdi LLM'e hiç gitmeden
      `ValueError` fırlatır. 5 test, hepsi yeşil.
- [x] `app/thinking/quality_critic.py`: `evaluate_project(project) -> QualityVerdict | None`.
      Gerçek LLM çağrısı (outline+script+seo context), `overall_score` =
      3 alt-skorun ortalaması, `passed = overall_score >= 3.0`. Hata/eksik/
      aralık-dışı skor durumunda **hiçbir zaman exception fırlatmaz** —
      `None` döner + log uyarısı. **Pipeline'a otomatik/zorunlu aşama olarak
      bağlanmadı** — bağımsız, isteğe bağlı çağrılan bir fonksiyon (onaylanan
      tasarım kararı: "başarısız olursa ne olsun" sorusu henüz cevaplı değil,
      bunu icat etmek ayrı bir mimari karar, gerçek kullanım verisi
      birikmeden ertelendi — Learning Layer ile aynı gerekçe). 6 test,
      hepsi yeşil.
- [x] Test/suite: her iki servis de ilk denemede yeşil geçti (kırmızı test
      yok bu turda). Tam suite: **542 passed, 11 skipped.**

## FAZ 2 / Adım 2b — idea_generator → WebUI entegrasyonu (Plan 1): TAMAMLANDI

Önce plan raporu sunuldu (nereye, nasıl bağlanacağı, kenar durumu, stil
tercihi), kullanıcı onayı alındı, sonra kodlandı.

- [x] `webui/Main.py`: konu kutusunun yanına `icon=":material/auto_awesome:"`
      ile **"Refine Topic"** butonu eklendi — **tamamen opt-in**, varsayılan
      "konu yaz + Generate" akışı hiç değişmedi, otomatik/zorunlu çağrı yok.
      Butona basılınca gerçek `idea_generator.generate_idea()` çağrısı
      yapılıyor, sonuç (`topic` + `angle`) bir bilgi kutusunda "Kabul Et"/
      "Reddet" seçenekleriyle gösteriliyor.
- [x] Kenar durum: öneri, kullanıcının yazdığıyla birebir aynıysa (idea_generator'ın
      kendi LLM-hata fallback'i bu durumu tetikleyebilir) boş bir öneri kutusu
      yerine nötr bir mesaj gösteriliyor ("konu zaten net").
- [x] **Gerçek bir Streamlit kısıtı bulundu ve düzeltildi:** `st.session_state[key]`,
      o `key`'e sahip widget aynı script çalışmasında instantiate edildikten
      SONRA değiştirilemiyor (`StreamlitAPIException`). "Kabul Et" butonu artık
      ayrı bir `documentary_topic_override` anahtarına yazıp `st.rerun()`
      çağırıyor; bu override, bir SONRAKİ çalışmada, `documentary_topic`
      widget'ı instantiate edilmeden ÖNCE uygulanıyor. Bu hata gerçek
      headless-Chromium testinde yakalandı (mock/statik inceleme ile
      bulunamazdı), ilk denemede kırmızıydı, düzeltilip yeşile çevrildi.
- [x] Gerçek tarayıcı ile uçtan uca doğrulandı (gerçek LLM çağrısı, mock değil):
      "Japonya neden güvenli?" yazıldı → Refine Topic'e basıldı → öneri kutusu
      çıktı → Kabul Et'e basıldı → konu kutusu gerçekten güncellendi
      ("Japonya Neden Bu Kadar Güvenli?"), traceback/console hatası yok.
- [x] 6 yeni UI string'i baştan 9 locale dosyasına eklendi (önceki i18n parity
      dersinden öğrenilerek) — `test_webui_i18n.py` bu turda hiç kırmızı çıkmadı.
- [x] Tam suite: **542 passed, 11 skipped.**

## FAZ 2 / Adım 2c — quality_critic → Pipeline entegrasyonu (Plan 2): TAMAMLANDI

Onay alındı, plan uygulandı.

- [x] `DocumentaryProject`'e opsiyonel `quality_verdict: QualityVerdict | None = None`
      alanı eklendi (geriye dönük uyumlu, varsayılan `None`).
- [x] `default_pipeline.run_pipeline()`: VideoRenderer'dan (stage 12) hemen sonra,
      `return`'den önce `quality_critic.evaluate_project(project)` çağrılıyor.
      **Asla engellemiyor** — `final_video_path` bundan önce zaten set edilmiş
      oluyor, verdict `None` gelse bile pipeline normal döner (ayrı test bunu
      doğruluyor: `test_final_video_path_is_set_even_when_quality_review_is_unavailable`).
- [x] `test_default_pipeline.py` güncellendi: `quality_critic.evaluate_project`
      artık mock'lanıyor (önceden mock'lanmıyordu — eklenmeseydi wiring testi
      gerçek bir LLM çağrısı yapmaya çalışırdı, ciddi bir gözden kaçırma
      olurdu, fark edilip düzeltildi).
- [x] `webui/Main.py`: `st.video()` altına "Kalite Notu" — `overall_score/5`
      + geçti/uyarı ikonu + 3 alt-skor + `issues` varsa açılır liste. Video
      **hiçbir zaman** verdict'e göre gizlenmiyor/engellenmiyor.
- [x] Doğrulama iki parçalı yapıldı: (1) webui üzerinden gerçek uçtan uca
      üretim ("The Great Wall of China", gerçek OpenAI+Pexels+ElevenLabs+
      quality_critic) — DOM'da "Quality Note" metni doğrulandı, traceback/
      console hatası yok; (2) Streamlit'in scroll container'ı yüzünden
      tam sayfa ekran görüntüsü kesildiği için, aynı render kodu daha önce
      gerçek bir `quality_critic` çalıştırmasından (Roma projesi) elde
      edilmiş gerçek verilerle izole bir script'te tekrar çalıştırılıp
      görsel olarak da doğrulandı (skor/ikon/alt-skorlar/issues listesi
      doğru render oluyor).
- [x] Tam suite: **543 passed, 11 skipped.**

## GECE OTURUMU — dal: `overnight/knowledge-engine` (2026-07-22 gece → sabah)

**Uyarı/tutarsızlık notu:** Kullanıcı bu görevi "önceki mesajımdaki 6 maddelik
plan" ve "PROGRESS.md'deki Bölüm 12 öncelik sırası / Thumbnail Engine"
referanslarıyla verdi. **Bu ikisi de elimdeki gerçek konuşma geçmişinde ve bu
dosyada mevcut değil** — kontrol ettim, PROGRESS.md'de "Bölüm 12" veya
"Thumbnail Engine" diye bir bölüm yok. Muhtemelen farklı bir oturuma ait bir
referans. İcat etmedim; "Knowledge Engine" hedefinin kendisi yeterince açık
olduğu için 6 maddelik analizi kendim sentezleyip aşağıya yazdım. Sabah bu
notu görün — eğer gerçekten başka bir yerde böyle bir plan/bölüm varsa bana
gösterin, yoksa bu bir hafıza karışıklığıydı.

### Knowledge Engine — Plan (kendi kendine onaylandı, kodlamaya geçiliyor)

**1) research_planner'ın mevcut durumu:** `app/departments/research/research_planner.py`
saf LLM tabanlı — kendi docstring'i bile "gerçek web araması yok, LLM'in
kendi bilgisini yapılandırıyoruz" diyor. `generate_research_plan(topic,
topic_category, language) -> ResearchPlan` tek bir `generate_json()` çağrısı
yapıyor, hiçbir dış kaynağa bakmıyor.

**2) API seçimi:** Yeni bir arama API key'i yok, kullanıcı ücretsiz/key
gerektirmeyen seçeneği istedi → **DuckDuckGo Instant Answer API**
(`https://api.duckduckgo.com/?format=json`, key gerektirmiyor).
**Dürüst sınırlama:** Bu genel bir web arama API'si DEĞİL — sadece bilinen
varlıklar/konular için kısa bir "Abstract" (Wikipedia özeti gibi) döndürüyor;
niş/çok spesifik/bileşik sorgularda sıklıkla boş dönüyor. **OTONOM KARAR:**
Boş sonucu hata değil, normal durum olarak ele alıyorum (sessizce mevcut
LLM-only davranışa düşüyor) — ücretli bir SERP API'si (Google/Bing/Serper/
Tavily) gerçek, sıralı arama sonuçları döndürüp kaliteyi ciddi artırabilir,
**sabah değerlendirin.**

**3) Entegrasyon noktası:** `research_planner.generate_research_plan()`
içine, LLM çağrısından ÖNCE bir `web_search.search_web(topic)` çağrısı.
Sonuç bulunursa, prompt'a "doğrulanmış kaynak metni" olarak enjekte ediliyor
+ LLM'e "bu kaynakla çelişen key_facts üretme" talimatı veriliyor. **Tek LLM
çağrısı** (araştırma + temel fact-check aynı çağrıda) — **OTONOM KARAR:**
ayrı bir "doğrulama" LLM çağrısı eklemek yerine (maliyeti ikiye katlardı) tek
çağrıda grounding+fact-check birleştirildi; en tutucu/en az maliyetli seçenek.

**4) Somut örnek:** Konu "The Fall of the Roman Empire" → DuckDuckGo'dan
gerçek bir Abstract dönerse (Roma İmparatorluğu bilinen bir konu, dönme
ihtimali yüksek), prompt'a şu şekilde ekleniyor:
```
Verified web source (https://en.wikipedia.org/wiki/...):
<DuckDuckGo'nun gerçek abstract metni>
Prefer key_facts that are consistent with this source. Do not include
key_facts that contradict it.
```
Niş bir konuda (örn. çok spesifik bir yerel olay) muhtemelen `None` döner,
davranış mevcut LLM-only haliyle birebir aynı kalır.

**5) Maliyet:** DuckDuckGo çağrısı **ücretsiz, key yok** — sınırsız test
edilebilir. Sadece gerçek OpenAI+DuckDuckGo birlikte uçtan uca doğrulama
"gerçek API bütçesi"nden (gece max 3) sayılacak.

**6) Model/kod değişikliği kapsamı — OTONOM KARAR:** Yeni bir "Project+
Metadata" katmanı ya da ayrı bir "FactCheck" modeli **kurmuyorum** — mevcut
`ResearchPlan`'a 2 opsiyonel alan ekliyorum (`source_snippet`, `source_url`,
ikisi de varsayılan `""`), geriye dönük tam uyumlu. Yeni servis dosyası
`app/services/web_search.py` (department-özel değil, `documentary_llm_utils.py`
gibi paylaşılan altyapı — ileride başka departmanlar da kullanabilir).
Küçük, izole ekleme; büyük refactor yok.

### Knowledge Engine — UYGULANDI, TEST EDİLDİ, GERÇEK API İLE DOĞRULANDI

- [x] `app/models/web_search.py` (`WebSearchResult`) + `app/services/web_search.py`
      (`search_web(query) -> WebSearchResult | None`, DuckDuckGo Instant Answer
      API, ücretsiz/key yok, asla exception fırlatmıyor). 5 test, mock'lu
      (`requests.get` mock'landı — mevcut `material.py` konvansiyonuyla aynı,
      test suite'inde gerçek ağ çağrısı yok). Ayrıca **ücretsiz** gerçek
      çağrılarla doğrulandı: "Roman Empire" → gerçek Wikipedia özeti,
      anlamsız niş sorgu → `None`.
- [x] `ResearchPlan`'a `source_snippet`/`source_url` (opsiyonel, varsayılan
      `""`) eklendi — geriye dönük tam uyumlu.
- [x] `research_planner.generate_research_plan()`: LLM çağrısından önce
      `web_search.search_web(topic)`; sonuç bulunursa tek LLM çağrısında
      hem grounding hem "bu kaynakla çelişme" talimatı veriliyor. 4 yeni test
      + 3 mevcut test `web_search.search_web` mock'u eklenerek güncellendi.
- [x] Tam suite: **551 passed, 11 skipped.**
- [x] **Gerçek API doğrulaması (1/3 bütçe kullanıldı):** "The Fall of the
      Roman Empire" konusuyla gerçek OpenAI + gerçek DuckDuckGo grounding
      ile `generate_research_plan()` çalıştırıldı.

**Somut önce/sonra karşılaştırması — bu özelliğin gerçekten işe yaradığının
kanıtı:** Daha önce (Faz 2 Thinking Layer bölümünde) `quality_critic`, aynı
"Roma İmparatorluğu'nun çöküşü" konusuyla üretilen script'i şu gerekçeyle
düşük puanlamıştı: *"Narration does not reach... 476 CE... Odoacer, Romulus
Augustulus..."* — yani script bu somut olaylara hiç değinmiyordu (o script,
grounding olmadan üretilmişti). **Şimdi, grounding ile üretilen `key_facts`
listesi bu üç olayı da açıkça içeriyor:**
> "In 476 CE, the Germanic commander Odoacer deposed the young western
> emperor Romulus Augustulus; this date is often used as the conventional
> marker for the fall of the Western Roman Empire."

Bu, quality_critic'in bulduğu gerçek bir eksikliği, Knowledge Engine'in
gerçekten kapattığını gösteriyor — spekülatif değil, aynı konuda ölçülmüş.

**Kalan gerçek API bütçesi: 2/3.**

## GECE OTURUMU 2 — dal: `overnight/thumbnail-and-backlog`

Kullanıcı "Thumbnail Engine" hedefini netleştirdi (önceki gece bulunamayan
referansın çözümü: kullanıcı bunu şimdi açıkça tanımladı). Görev sırası:
A) Thumbnail Engine (plan onaylandı) → B) Story Engine (Hook/Retention/
Callback) → C) SEO Engine genişletme. Her biri kendi plan+kendi-kendine-onay
+kod+test döngüsüyle, sırayla, aynı anda birden fazlasına girilmeyecek.

### A) Thumbnail Engine — PLAN (kullanıcı tarafından onaylandı)

- **Mevcut yetenek kontrolü:** `grep` ile doğrulandı, sıfır mevcut thumbnail/
  görsel-üretim kodu (bkz. önceki mesaj).
- **Yöntem:** AI görsel üretimi DEĞİL — storyboard/asset'lerden gerçek bir
  kareyi çıkarıp üzerine SEO başlığını bindirmek. Gerekçe: $0 maliyet, yeni
  bağımlılık yok, video içeriğiyle tutarlı, bu oturumun tüm felsefesiyle
  (mevcut kodu genişlet, küçük/izole/geri alınabilir ekleme) uyumlu.
- **Entegrasyon noktası:** VideoRenderer (stage 12) sonrası, `quality_critic`
  ile aynı bölge. Yeni alan: `DocumentaryProject.thumbnail_path: str = ""`.
- **Kritik detay (plan aşamasında mockup'ta keşfedildi):** Kare `final.mp4`
  değil, `timeline.combined_video_path`'ten (altyazı yakılmadan önce)
  çıkarılmalı — yoksa eski altyazı yeni başlıkla çakışıyor.
- **Departman:** `app/departments/growth/thumbnail_generator.py` (SEO ile
  aynı departman — ikisi de "tıklama/izlenme" kaygısı).

**OTONOM KARAR 1 (gece kuralı gereği):** "En güçlü kare" seçimi için sahne
önem derecesine göre haritalama (scene→timeline zaman damgası eşleştirmesi)
YAPMIYORUM — bu, timeline'ın hangi sahnenin hangi zaman aralığına denk
geldiğini kesin izlemeyi gerektirir (şu an `combine_videos()` legacy kodu bu
eşlemeyi dışarı vermiyor, döngü/kırpma nedeniyle güvenilir de değil). Bunun
yerine **en tutucu/basit seçenek**: kombine videonun (`ffprobe` ile ölçülen)
toplam süresinin tam ortasından tek bir kare. Sabah değerlendirin: sahne-
önemine göre kare seçimi gerçek bir iyileştirme olur ama timeline'a scene
index/zaman aralığı meta verisi eklemeyi gerektirir (ayrı, daha büyük bir
değişiklik).

**OTONOM KARAR 2:** Metin bindirme için MoviePy (`TextClip`/
`CompositeVideoClip`) kullanmıyorum — bu, video-render pipeline'ı için
tasarlanmış, tek bir statik görsel için gereksiz ağır. Bunun yerine PIL
(`Pillow`, zaten `voice.py`/`video.py` bağımlılıkları üzerinden mevcut)
doğrudan kullanılıyor — daha hafif, daha basit, tek görsel kompozisyonu için
yeterli. Font: `config.ui.get("font_name", "BeVietnamPro-Bold.ttf")` —
`video_renderer.build_video_params`'daki aynı mantık.

**Maliyet:** ~$0, ~2-5 saniye (ffmpeg kare çıkarma + PIL kompozisyon).
Yeni LLM/API çağrısı yok — mevcut SEO başlığı yeniden kullanılıyor.

### A) Thumbnail Engine — TAMAMLANDI

- [x] `app/departments/growth/thumbnail_generator.py`: `generate_thumbnail()`
      — asla exception fırlatmıyor (`quality_verdict` ile aynı desen), her
      hatada `""` döner.
- [x] `DocumentaryProject.thumbnail_path: str = ""` eklendi, `default_pipeline`
      VideoRenderer+quality_critic sonrası çağırıyor.
- [x] 12 test (thumbnail_generator) + 2 yeni wiring testi
      (`test_default_pipeline.py`) — hepsi ilk denemede yeşil.
- [x] WebUI: video'nun yanında `st.image()` önizlemesi (Kalite Notu ile aynı
      desen), 9 dile i18n eklendi, webui hatasız açıldığını doğruladım.
- [x] Tam suite: **559 passed, 11 skipped.**
- [x] **Gerçek doğrulama (yeni API maliyeti YOK — mevcut gerçek `combined.mp4`
      kullanıldı):** Roma projesinin gerçek kombine videosundan gerçek bir
      thumbnail üretildi.

**Gerçek bir sınırlama bulundu (dürüstçe not düşüyorum, düzeltmedim):** Uzun
SEO başlıkları ("Rome Didn't Fall Overnight—Here's What Cracked the Empire")
3 satır sınırında kesiliyor, son kelime ("Empire") görünmüyor. Sabah
değerlendirin — olası çözümler: font boyutunu dinamik küçültmek, ya da
thumbnail için SEO başlığından ayrı, daha kısa bir "headline" üretmek
(muhtemelen `seo_generator`'a küçük bir ek alan gerektirir).

**Durum: Task A tamamen bitti. Task B'ye (Story Engine) geçiliyor.**

### B) Story Engine (Hook/Retention/Callback) — PLAN (kendi kendine onaylandı)

**Kök neden (gerçek veriyle doğrulanmış):** `quality_critic`'in Roma
projesinde bulduğu gerçek sorun — *"The hook and closing promised by the
outline are absent from the narration"* — `script_generator.py`'nin kod
okumasıyla doğrulandı: `build_script_prompt()`/`generate_script()` hiçbir
zaman `outline.hook`/`outline.closing`'i görmüyor, sadece `scene_plan` ve
`topic` alıyor. Yani sorun "LLM'in şansı" değil, **prompt'a o bilginin hiç
verilmemesi.**

**OTONOM KARAR:** Kullanıcı "Hook/Retention/Callback alt-motorları" dedi —
bunu 3 ayrı yeni servis/dosya (örn. ayrı bir "Retention Engine" modülü)
olarak İNŞA ETMİYORUM. En tutucu/geri alınabilir seçenek: mevcut
`script_generator.py`'yi genişletmek — tek bir prompt bloğunda üç kavramı
da (Hook/Retention/Callback) açıkça adlandırılmış talimatlar olarak
kodlamak. Gerekçe: (1) kök neden zaten tek bir noktada (script prompt'u
outline'ı görmüyor), üç ayrı modül bu tek noktayı çözmek için gereksiz
soyutlama olurdu; (2) "Retention" kavramının somut, ayrı bir veri yapısı
gerektirmeyen, saf prompt-mühendisliği ile ifade edilebilir bir talimat
olması (yeni maliyet/karmaşıklık yok).

**Somut değişiklik:**
- `build_script_prompt(scene_plan, topic, language, custom_system_prompt,
  outline=None)` — yeni opsiyonel `outline` parametresi.
- `outline.hook` varsa: "scene 0'ın anlatımı bu hook'u açılışta kullanmalı"
  talimatı.
- Birden fazla sahne varsa: "Retention" — sahnelerin çoğu tam çözülmüş bir
  ifadeyle değil, ileriye çeken bir detay/gerilim/açık soruyla bitmeli
  (genel anlatım tekniği, outline'a bağımlı değil).
- `outline.closing` varsa: "son sahnenin anlatımı hook'a geri dönmeli ve/veya
  bu closing beat'i vermeli" talimatı.
- `generate_script()` aynı `outline` parametresini alıp geçiriyor.
- `default_pipeline.py`: `script_generator.generate_script(project.scene_plan,
  topic, language=..., outline=project.outline)`.

**Maliyet:** $0 ek maliyet — aynı tek LLM çağrısı, sadece prompt'a birkaç
satır ekleniyor. Yeni API/bağımlılık yok.

**Durum: Plan onaylandı, kodlanıyor.**

### B) Story Engine — TAMAMLANDI

- [x] `script_generator.build_script_prompt()`/`generate_script()` yeni
      opsiyonel `outline` parametresi alıyor; Hook/Retention/Callback
      talimatları tek prompt'a ekleniyor.
- [x] `default_pipeline.py`: `script_generator.generate_script(...,
      outline=project.outline)`.
- [x] 12 test (script_generator, önceden 5'ti) + pipeline wiring assertion
      — bir kırmızı test çıktı (**benim test tasarım hatam**: tek-sahne
      olmayan bir plan için "Story craft requirements" bloğunun tamamen
      yokluğunu bekliyordum, ama Retention outline'dan bağımsız olduğu için
      çok-sahneli planda her zaman ekleniyor — kodun kendisi doğruydu, testi
      düzelttim), sonra hepsi yeşil.
- [x] Tam suite: **566 passed, 11 skipped.**
- [x] **Gerçek doğrulama (1/5 gece bütçesi kullanıldı):** Aynı gerçek Roma
      outline'ı (gerçek hook: "...Odoacer... Romulus Augustulus... 476 CE...")
      ile `generate_script()` yeniden çalıştırıldı. **Yeni script'in ilk
      satırı** artık "In 476, Odoacer deposed Rome's boy emperor" ile
      açılıyor, **son satırı** "by 476, western authority simply unraveled"
      ile kapanıyor — `quality_critic`'in bulduğu gerçek eksikliği somut
      olarak kapattığını kanıtlıyor.

**Kalan gerçek API bütçesi: 4/5.**

**Durum: Task B tamamen bitti. Task C'ye (SEO Engine genişletme) geçiliyor.**

### C) SEO Engine genişletme — PLAN (kendi kendine onaylandı) + önemli bir gerçek bulgu

**Önemli dürüst bulgu (kodlamadan önce fark ettim):** Bu pipeline'ın ürettiği
videolar **dikey, kısa (9:16, 20-56s) — YouTube Shorts/TikTok/Reels formatı**
(`seo_generator` zaten varsayılan olarak `platform="youtube_shorts"`
kullanıyor). **YouTube "chapters" (bölümler) ve "end screen" (bitiş ekranı)
resmi olarak sadece uzun-format videolarda çalışan özellikler** — Shorts'ta
chapters hiç desteklenmiyor, end screen de aynı şekilde uzun video arayüzüne
özel. Yani kullanıcının istediği bu iki özelliği "gerçekten YouTube'da
işlevsel bir chapters/end-screen" gibi sunmak yanıltıcı olurdu.

**OTONOM KARAR:** Bunları **platforma otomatik enjekte edilen** özellikler
olarak değil, **üreticiye (kullanıcıya) manuel kullanması için sunulan
danışman/öneri metaveri alanları** olarak uyguluyorum — tıpkı
`quality_verdict` gibi bilgilendirici, hiçbir şeyi otomatik yapmıyor.
`chapters` alanı, video uzun-format olarak yayınlanırsa gerçekten işe
yarayabilir (sahne süre/başlıklarından deterministik, LLM çağrısı yok);
Shorts'ta kullanılamayacağını hem kodda hem burada açıkça belirtiyorum.

**Somut değişiklik:**
- `SeoMetadata`'ya 3 opsiyonel alan: `chapters: list[str]`,
  `end_screen_suggestion: str`, `pinned_comment: str` — hepsi varsayılan
  boş, geriye dönük uyumlu.
- `generate_chapters(scene_plan)`: **LLM çağrısı yok**, `scene_plan`'daki
  sahne süre/başlıklarından deterministik "MM:SS Başlık" listesi
  (`scene_planner.py` ile aynı "saf mantık" felsefesi).
- Yeni, küçük, izole bir LLM çağrısı (**+1 çağrı, maliyet artışı — dürüstçe
  belirtiyorum**): `end_screen_suggestion` + `pinned_comment`'i TEK çağrıda
  üretiyor. Mevcut `llm.generate_social_metadata()`'yı (legacy, başka
  çağıranları da var) değiştirmek yerine yeni bir fonksiyon — legacy paylaşılan
  koda dokunmamak için en izole seçenek.
- `generate_seo_metadata()` yeni opsiyonel `scene_plan` parametresi alıyor.
- `default_pipeline.py`: `seo_generator.generate_seo_metadata(topic,
  project.script, language=..., scene_plan=project.scene_plan)`.

**Maliyet:** Chapters $0 (deterministik). Engagement metadata (end_screen+
pinned_comment) +1 LLM çağrısı, küçük prompt — SEO aşamasının maliyetini
yaklaşık ikiye katlıyor ama pipeline'ın toplam ~6 LLM çağrısına göre küçük
bir artış.

**Durum: Plan onaylandı, kodlanıyor.**

### C) SEO Engine genişletme — TAMAMLANDI

- [x] `SeoMetadata`'ya `chapters`/`end_screen_suggestion`/`pinned_comment`
      eklendi (opsiyonel, geriye dönük uyumlu).
- [x] `generate_chapters()`: LLM'siz, deterministik. `generate_engagement_metadata()`:
      yeni izole 1 LLM çağrısı, asla exception fırlatmıyor.
- [x] `default_pipeline.py` ve webui güncellendi (SEO Extras expander'ı,
      chapters için "sadece uzun formatta işlevsel" uyarısı dahil).
- [x] 7 yeni/güncellenmiş test + 1 wiring assertion, hepsi ilk denemede
      yeşil. Tam suite: **572 passed, 11 skipped.**
- [x] **Gerçek doğrulama (2/5 gece bütçesi kullanıldı):** Gerçek Roma
      projesinin `scene_plan`+`script`'i ile çalıştırıldı — chapters doğru
      kümülatif zaman damgaları üretti, `end_screen_suggestion` ve
      `pinned_comment` gerçek, konuyla tutarlı çıktılar verdi.
- [x] WebUI: SEO Extras expander'ı eklendi, 9 dile i18n, webui hatasız
      açıldığını doğruladım.

**Kalan gerçek API bütçesi: 3/5.**

## GECE OTURUMU 2 — ÖZET (sabah incelemesi için)

**Üç görev de (A, B, C) sırayla, plan→onay→kod→test→gerçek-doğrulama→commit
döngüsüyle tamamlandı.** Aynı anda birden fazla büyük özelliğe girilmedi.

| Görev | Durum | Gerçek API kullanımı |
|---|---|---|
| A) Thumbnail Engine | Tamamlandı | 0 (mevcut gerçek video kullanıldı) |
| B) Story Engine (Hook/Retention/Callback) | Tamamlandı | 1/5 |
| C) SEO Engine genişletme (chapters/end-screen/pinned comment) | Tamamlandı | 2/5 |

**Toplam gerçek API kullanımı: 2/5** (Thumbnail Engine hiç kullanmadı,
mevcut gerçek asset'leri yeniden kullandı). **Kalan bütçe: 3/5, kullanılmadı.**

**Otonom kararlar (özet, detaylar yukarıda):**
1. Thumbnail: sahne-önemine göre kare seçimi yerine video ortası (basit,
   timeline meta verisi gerektirmiyor).
2. Thumbnail: MoviePy yerine PIL (tek statik görsel için daha hafif).
3. Story Engine: 3 ayrı yeni modül yerine mevcut `script_generator`'ı
   genişletme (kök neden tek noktaydı).
4. SEO Engine: chapters/end-screen'i otomatik platform aksiyonu değil,
   üreticiye danışman metaveri olarak sunma (Shorts formatında resmi
   olarak çalışmıyorlar).
5. SEO Engine: yeni engagement metadata için ayrı izole LLM çağrısı,
   paylaşılan legacy `llm.py` koduna dokunmama.

**Gerçek bulgular (spekülatif değil, ölçülmüş):**
- Thumbnail: uzun SEO başlıkları 3 satırda kesiliyor (sabah değerlendirin).
- Story Engine: gerçek Roma script'i artık hook/callback'i (476 CE,
  Odoacer) gerçekten içeriyor — `quality_critic`'in bulduğu kusur kapandı.
- SEO Engine: chapters/end-screen'in Shorts'ta gerçek platform işlevi
  olmadığı doğrulandı (dokümantasyon/kod yorumlarında açıkça belirtildi).

**Kırmızı test geçmişi:** Sadece 1 kırmızı test oldu, tamamı **benim test
tasarım hatamdı** (Retention talimatının outline'dan bağımsız olduğunu
unutup yanlış bir "hiç yok" assertion'ı yazmıştım) — kodun kendisinde hata
yoktu. Anında düzeltildi, devam edildi.

**Tam suite son durum: 572 passed, 11 skipped.**

**Push denemesi:** `git push fork overnight/thumbnail-and-backlog` denendi,
beklendiği gibi kimlik doğrulama isteğiyle karşılaşıldı (bu ortamda GitHub
credential'ı yok). Kural 4 gereği atlandı — token/şifre üretilmeye veya
tahmin edilmeye çalışılmadı. **Dal sadece yerelde, main'e hiç dokunulmadı.**
Sabah manuel push gerekiyor: `git push fork overnight/thumbnail-and-backlog`.

## Thumbnail başlık kesilme düzeltmesi (kullanıcı talebiyle, gündüz)

Önce plan sunuldu (mevcut kod gösterildi, A/B seçenekleri karşılaştırıldı),
kullanıcı **A: dinamik font küçültme + "..." son çare** seçeneğini onayladı.

- [x] `_overlay_title()`: artık sabit font_size ile bir kez sarıp fazla
      satırları sessizce silmek yerine, `_font_scales()` (1.0→0.6, %5
      adımlarla) her adımda `_wrap_text()` ile yeniden satırlıyor, 3 satıra
      sığınca duruyor. Alt sınırda hâlâ sığmıyorsa `_truncate_with_ellipsis()`
      3. satırı "..." ile kesiyor (sessiz silme yok).
- [x] 18 test (önceden 12'ydi) — yeni pure-function testleri (`_font_scales`,
      `_wrap_text`, `_truncate_with_ellipsis`, gerçek font ile) + 2 gerçek
      PIL render testi (mock yok, gerçek `BeVietnamPro-Bold.ttf`). Tam suite:
      **583 passed, 11 skipped.**
- [x] **Gerçek doğrulama (yeni API maliyeti yok):** Roma başlığı artık
      "Empire" kelimesi dahil tam 3 satıra sığıyor; aşırı uzun uydurma bir
      başlık da (son çare yolunu test etmek için) düzgünce "..." ile
      kesiliyor, çökme yok. İki gerçek görsel de kullanıcıya gösterildi.

**Güncelleme:** `overnight/thumbnail-and-backlog` dalı kullanıcı tarafından
`main`'e fast-forward merge edildi (`6579afd`), main üzerinde tam suite
tekrar doğrulandı (583 passed, 11 skipped). `git push fork main` bu ortamda
kimlik bilgisi olmadığı için başarısız oldu (`fork/main` hâlâ eski
`09df0cd`'de) — kullanıcı kendi makinesinden push edecek.

## project.json kalıcılığı (kullanıcı talebiyle)

**Sebep:** Kullanıcı gerçek bir Çanakkale (Gallipoli) projesinin
`StoryboardGenerator` çıktısını (`search_terms`, hangi asset indirildi,
timeline'da hangi klip hangi sahneye denk geliyor) sorduğunda, bu bilginin
**hiçbir yerde kalıcı olarak durmadığını** keşfettik — `DocumentaryProject`
sadece Streamlit'in bellek-içi `session_state`'inde tutuluyordu, diske hiç
yazılmıyordu. O projenin verisi geri kurtarılamadı (kullanıcı bunu kabul
etti, gerekirse yeniden üretilecek).

- [x] `default_pipeline.py`: `_save_project_snapshot(project)` — düz
      `project.model_dump_json(indent=2)`, yeni şema yok. Her aşamadan
      sonra artımlı çağrılıyor + `finally` bloğunda garantili son çağrı
      (başarılı/başarısız fark etmeksizin, bir aşama exception fırlatsa
      bile o ana kadarki durum diskte kalıyor). Asla exception fırlatmıyor.
      Çıktı: `storage/tasks/<id>/project.json`.
- [x] 7 yeni/güncellenmiş test: izole `_save_project_snapshot` testleri
      (geçerli JSON, yazma hatasında bile exception fırlatmıyor) + pipeline
      wiring testleri (gerçek storyboard/asset verisiyle dosyanın
      oluştuğu, bir aşama patlarsa bile önceki aşamaların diskte kaldığı).
      Tam suite: **587 passed, 11 skipped.**
- [x] **Gerçek doğrulama:** Yeni, ucuz gerçek bir üretim (mock yok,
      pacing=short, konu "Why Octopuses Are So Intelligent") çalıştırıldı.
      `storage/tasks/project-json-snapshot-check/project.json` oluştu,
      içinde her sahnenin gerçek `search_terms`'i, hangi indirilen asset
      dosyasının (içerik hash'i) kullanıldığı, ve timeline'daki sahne↔klip
      eşlemesi eksiksiz görünüyor — tam olarak Çanakkale projesinde
      kurtaramadığımız bilgi türü artık her üretimde kalıcı.

## Storyboard arama terimi kalitesi düzeltmesi (kullanıcı talebiyle, gündüz)

Gerçek bir Çanakkale Savaşı üretiminde `search_terms`/asset kareleri manuel
incelendi: `old map` teriminin Pexels'ten alakasız bir Orta Asya haritası ve
harita bile olmayan soyut bir doku döndürdüğü, `soldier statue`/`warship
silhouette` gibi terimlerin de konudan kopuk sonuçlar getirdiği gözlemlendi.
Kök neden araştırıldı ve onaylandı, ardından düzeltildi:

- [x] **Kök neden:** `app/prompts/storyboard/__init__.py`'deki kategori
      şablonu (`TopicCategory.history`: "old maps, monuments, ruins,
      statues...") LLM tarafından konudan bağımsız, birebir kopyalanıyordu;
      prompt'ta ne `topic` ne de `research_plan.key_facts` vardı, tek girdi
      sahne başlığı + tek satır anlatımdı.
- [x] `storyboard_generator.py`: `generate_storyboard()`/
      `build_storyboard_prompt()`'a opsiyonel `topic`/`key_facts` parametreleri
      eklendi (geriye dönük uyumlu, varsayılan boş), prompt başına "Documentary
      topic: ..." + "Context facts: ..." bloğu ve açık bir özgüllük talimatı
      ("avoid single generic nouns...anchor each term in this topic's
      specific era/place/proper nouns") eklendi.
- [x] `default_pipeline.py`: storyboard çağrısına `topic=project.topic`,
      `key_facts=project.research_plan.key_facts[:3]` geçildi.
- [x] 4 yeni test (`test_storyboard_generator.py`) + wiring assertion
      (`test_default_pipeline.py`, topic/key_facts kwargs kontrolü). Tam
      suite: **588 passed, 11 skipped.**
- [x] **Gerçek doğrulama (2 tam üretim, gerçek API bütçesinden düşüldü):**
      Aynı "Çanakkale Savaşı" konusu (tr, pacing=short) düzeltme öncesi ve
      sonrası iki kez uçtan uca üretildi. Terimler `old map` / `warship
      silhouette` / `rocky coastline` / `soldier statue` →
      `Ottoman-era map Dardanelles` / `Dardanelles coastal fort` /
      `Gallipoli coastline` / `Conkbayiri memorial` oldu; final videodan
      çıkarılan karelerde 4 sahneden 3'ü artık net konu eşleşmesi gösterdi
      (gerçek bir kıyı tabyası, Gelibolu tipi uçurumlu kıyı, asker anıtı).

**Kalan sınırlama:** Storyboard search terms artık topic+key_facts ile
grounded, kategori şablonundaki jenerik örnek kelime kopyalama sorunu
çözüldü. Kalan sınırlama: Pexels'in bazı çok spesifik tarihi görsel
türlerinde (örn. dönem haritaları) sınırlı kapsamı var — bu bir
stok-kütüphane veri sınırı, kod sorunu değil, kabul edilebilir seviyede.

**Push denemesi:** `git push origin main` denendi (commit `746d274`),
beklendiği gibi kimlik doğrulama isteğiyle karşılaşıldı (bu ortamda GitHub
credential'ı yok, `origin` tek remote — daha önceki oturumlardaki "fork"
remote'u bu klonda mevcut değil). Kural 4 gereği atlandı — token/şifre
üretilmeye veya tahmin edilmeye çalışılmadı. **Commit sadece yerelde,
`origin/main`'in 1 commit ilerisinde.** Push için manuel kimlik doğrulama
gerekiyor.

## Visual Engine — storyboard prompt'una görsel-stil rehberliği (kullanıcı talebiyle, gündüz)

Önce plan istendi: kullanıcının önerdiği 10 sinematografi kavramından
(Lens/Camera Movement/Lighting/Composition/Color Palette/Mood/Time/Weather/
Transition/Aspect Ratio/Visual Style) hangilerinin gerçek bir tüketicisi
olacağı (Pexels/Pixabay'in tek gerçek girdisi serbest metin `search_term` —
yapısal filtre yok) analiz edildi. Aspect Ratio ve Transition'ın zaten
`VideoAspect`/`VideoTransitionMode` (video-geneli, `app/models/schema.py`)
olarak var olduğu, Lens/Composition/Mood'un stok kütüphanelerde gerçek bir
arama sinyali taşımadığı (dolayısıyla eklenirse "süs alan" veya sorgu
kirliliği olacağı) tespit edildi. Kullanıcı **Camera Movement, Lighting,
Weather, Color Palette, Visual Style**'ı onayladı — **yeni model/şema alanı
olmadan**, mevcut `search_terms` string'lerinin içine dokunacak şekilde.

- [x] `storyboard_generator.py` → `build_storyboard_prompt()`: mevcut
      özgüllük talimatının hemen ardına, bu 5 kategoriden **en fazla bir**
      modifiyeri her terime eklemesini isteyen bir cümle eklendi ("aerial
      Gallipoli coastline" gibi). Açıkça "do not stack more than one such
      modifier" uyarısı var — birden fazla modifiyer üst üste binerse sorgu
      aşırı daralıp 0 sonuç riski doğurabileceği için.
- [x] **Gerçek doğrulama (3. tam üretim, gerçek API bütçesinden düşüldü):**
      Aynı "Çanakkale Savaşı" ile tekrar üretildi. Terimler tam olarak tek
      modifiyerle geldi (`archival Dardanelles map`, `archival Nusret
      minelayer`, `aerial Anzac Cove`, `backlit Atatürk statue Gallipoli`),
      hiçbiri 0 sonuç döndürmedi (16-20 sonuç/terim). Kareler: **2/4 mükemmel**
      (`aerial Anzac Cove` → gerçek drone çekimi çakıllı Gelibolu kıyısı;
      `backlit Atatürk statue Gallipoli` → gün batımında Atatürk heykeli,
      iki Türk bayrağıyla — kişi + ışık talimatı ikisi de tuttu), **1/4 kısmi**
      (`archival Nusret minelayer` → doğru ülke/tema ama modern tekne, WWI
      mayın gemisi değil), **1/4 değişmedi** (`archival Dardanelles map` →
      üç turdur aynı Pexels videosu, Japonya/Nepal temalı kitap-harita
      dokusu — artık doğrulanmış bir stok-kütüphane kapsam sınırı, prompt
      sorunu değil).
- [x] 1 yeni test (`test_includes_visual_style_guidance_with_one_modifier_cap`).
      Şema/model değişikliği yok, yeni LLM çağrısı yok (aynı tek storyboard
      çağrısına eklenen birkaç cümle).
- [x] **`shot_type` bulgusu — bilinçli olarak dokunulmadı:** Kullanıcı
      `shot_type`'ın hiçbir yerde okunmadığını (`asset_generator.py:16`
      sadece `search_terms[0]`'ı kullanıyor) doğrulattı ve karar bana
      bırakıldı. **Tutucu seçenek seçildi: dokunulmadı.** Gerekçe: bu commit
      zaten `search_terms`'e kamera hareketi/açı kavramını (aerial/drone/pan)
      doğrudan prompt üzerinden gömüyor — `shot_type`'ı da aynı anda
      `search_terms`'e bağlamak aynı kavramı iki ayrı, senkronize edilmesi
      gereken mekanizmadan üretmek anlamına gelir ve tek commit'te iki
      değişkeni birden gerçek API'ye sürer (bir regresyon olursa hangisinin
      sebep olduğu belirsizleşir). `shot_type` hâlâ tüketicisiz — **ayrı,
      izole bir görev olarak bırakıldı**, istenirse ileride ele alınabilir.

## Merge: project.json kalıcılığı + Visual Engine (kullanıcı talebiyle)

`main` origin'den 2 commit ileri gitmişti (`e9b4fee` project.json kalıcılığı
+ `8c87360` progress notu) ve yerel dal 4 commit ilerideydi (`746d274`,
`ec4cdd5`, `3e30f44`, `0e9f088` — storyboard grounding + Visual Engine).
`git merge origin/main` çakıştı: `PROGRESS.md` (bu bölüm) ve
`default_pipeline.py` (aynı fonksiyonun iki farklı genişlemesi — biri her
aşamadan sonra `_save_project_snapshot()` çağıran `try/finally` sarmalayıcı,
diğeri storyboard çağrısına `topic`/`key_facts` ekleyen satırlar).

- [x] `default_pipeline.py`: origin'in `try/finally` + her-aşama-sonrası
      `_save_project_snapshot()` iskeleti korunarak, stage 6 (storyboard)
      çağrısına yerel dalın `topic=project.topic`,
      `key_facts=project.research_plan.key_facts[:3]` argümanları eklendi.
      İki özellik de aynı fonksiyonda bir arada — biri diğerini ezmedi.
- [x] `test/services/test_default_pipeline.py`: git otomatik birleştirdi
      (çakışma çıkmadı), hem `_save_project_snapshot` testleri hem
      storyboard `topic`/`key_facts` kwargs assertion'ı bir arada duruyor.
- [x] `PROGRESS.md`: iki dalın notları kronolojik sırayla art arda kondu
      (thumbnail fix → 6579afd fast-forward merge → project.json kalıcılığı
      → storyboard grounding düzeltmesi → Visual Engine), hiçbir madde
      silinmedi.

## Tone'u bağımsız bir boyut haline getirmek (kullanıcı talebiyle, Format genişlemesinin önkoşulu)

Önce plan istendi: `PROFILE_PROMPTS`'ta tonun `TopicCategory`'ye sabit
gömülü olduğu (travel=cinematic, history=credibility, space=epic,
psychology=scientific) ve — beklenmedik bulgu — bunu sadece `outline_generator`
ile `research_planner`'ın gerçekten okuduğu, `script_generator`'ın (asıl
seslendirme metnini yazan yer) hiç ton sinyali almadığı, `storyboard_generator`'ın
ise tamamen ayrı bir görsel-rehber sistemi (`SHOT_GUIDANCE`) kullandığı
tespit edildi. Kullanıcı planı onayladı ve **script_generator'ı da kapsama
almamı** istedi (ADIM 0: özelliğin en önemli tüketicisini dışarıda
bırakmamak için); storyboard'a bilinçli olarak dokunulmadı.

- [x] `profile_dimensions.py`: `Tone` enum'ı + `DEFAULT_TONE_BY_CATEGORY`
      (eski 1:1 eşleme, birebir) + `resolve_tone(topic_category, override)`
      (`resolve_pacing` ile aynı desen: override kazanır, geçersiz override
      kategori varsayılanına düşer).
- [x] `templates/__init__.py`: `PROFILE_PROMPTS` anahtarları `TopicCategory`
      → `Tone` olarak yeniden adlandırıldı, **metin içeriği birebir aynı**.
- [x] `outline_generator.py` / `research_planner.py`: `topic_category`
      parametresi `tone` ile değiştirildi.
- [x] `script_generator.py`: yeni opsiyonel `tone` parametresi +
      `TONE_VOICE_GUIDANCE` — tone verildiğinde prompt'a "Voice: ..." satırı
      ekleniyor (tone verilmezse eskisiyle birebir aynı, çünkü bu servis
      zaten daha önce hiç ton bilmiyordu).
- [x] `DocumentaryProject.tone`, `default_pipeline.py`'de intent'ten hemen
      sonra çözülüyor (`resolve_tone` `topic_category`'ye bağımlı olduğu
      için `resolved_pacing` gibi en baştan değil, stage 1'den sonra).
- [x] **Regresyon testleri (kritik onay şartıydı):** `outline_generator` ve
      `research_planner`'ın 4 kategori için ürettiği prompt'lar, refactor
      öncesi koddan yakalanan **birebir string'lerle** karşılaştırıldı —
      tam eşleşme. `script_generator`'da tone verilmezse "Voice:" satırının
      hiç eklenmediği ayrıca doğrulandı. Tam suite: **608 passed, 11
      skipped** (önceden 593).
- [x] **Gerçek doğrulama (ucuz — sadece metin aşamaları, video/ses/asset
      atlandı):** "The Grand Canyon" (travel kategorisi) konusu iki kez
      gerçek API ile üretildi — biri varsayılan tonla (cinematic), biri
      `tone=scientific` override'ıyla. Sonuç sadece anlatım sesini değil,
      **belgeselin tüm açısını** değiştirdi:
      - Varsayılan (cinematic): "At sunrise on the South Rim, the canyon
        surfaces slowly from blue shadow... the Colorado stops being an
        idea; warm air carries its voice."
      - Override (scientific): outline başlığı "The Grand Canyon: Rim,
        River, and Deep Time"'dan "The Grand Canyon: What Awe Does to the
        Mind"'e döndü; script: "Imagine the rim test: 277 miles, 18 wide,
        mile deep—your brain stumbles... awe doesn't erase worries; it puts
        them in proportion."
      İki script `!=` doğrulandı (birebir farklı). `tone` `research_planner`
      ve `outline_generator`'ı da etkilediği için override sadece sesi değil
      araştırma/outline açısını da gerçekten değiştiriyor — beklenenden
      daha güçlü, dürüstçe not düşülen bir sonuç.

## Format boyutu (kullanıcı talebiyle) — SADECE Educational, gerisi bilinçli olarak ertelendi

Önce plan istendi: Format'ın Pacing'den ("ne kadar uzun/hızlı") ve Tone'dan
("nasıl söyleniyor") bağımsız, üçüncü bir eksen ("ne tür içerik") olduğu
netleştirildi. Dört aday formattan (Podcast/Educational/Kids/Corporate)
sadece **Educational**'ın bu fazda düşük riskli olduğu, diğer üçünün ayrı
kararlar gerektirdiği tespit edildi ve kullanıcı bunu onayladı:

- [x] `profile_dimensions.py`: `Format` enum'ı — **bilinçli olarak sadece
      `educational` değeri var**, podcast/kids/corporate için yer tutucu
      eklenmedi (ADIM 0: arkasında gerçek davranış olmayan enum değeri
      eklemek de bir tür süs alan). `resolve_format()` — Tone'un aksine
      kategoriye bağlı bir varsayılanı yok, `None` = "format uygulanmadı".
- [x] `script_generator.py`: opsiyonel `format` parametresi + `FORMAT_GUIDANCE`
      — "teknik terimi ilk geçtiği yerde tanımla, her sahneyi tek cümlelik
      bir çıkarım/mini-özetle kapat" talimatı. Tone'un "Voice:" satırıyla
      birlikte var olabiliyor (birbirini ezmiyor).
- [x] `DocumentaryProject.format` + `default_pipeline.py`: pacing gibi en
      baştan çözülüyor (tone'un aksine topic_category'ye bağımlı değil),
      **sadece script aşamasına** geçiliyor — research/outline'a bilinçli
      olarak dokunulmadı.
- [x] Regresyon: `format=None` iken (tone olsun olmasın) prompt'ta hiç
      "Format:" satırı yok — eskisiyle birebir aynı. Tam suite: **616
      passed, 11 skipped** (önceden 608).
- [x] **Gerçek doğrulama (ucuz — sadece metin aşamaları, video/ses atlandı):**
      "How Black Holes Form" (space/epic) konusu iki kez üretildi. Varsayılan:
      "Crush the Sun to six kilometers, and it becomes a black hole—nature
      does this when giant stars die." (terim tanımı yok, 4 kısa satır).
      `format=educational` (aynı epic tonla): her teknik terim satır içinde
      tanımlanıyor — "event horizon, the boundary where escape velocity, the
      speed needed to break free, outruns light itself", "fusion, energy
      made by merging atoms", "gravitational waves, ripples in spacetime, the
      fabric of space and time" — ve kapanışta açık bir özet paragrafı var
      ("Black holes form when gravity compresses matter past the universe's
      ultimate escape limit..."). Epic ton korunmuş, pedagojik yapı (tanım +
      özet) eklenmiş — Tone ve Format'ın gerçekten bağımsız çalıştığının
      kanıtı.

**Backlog'a bilinçli olarak ertelenenler (dokunulmadı):**
- **Podcast (audio-only) — mimari kırılma noktaları:** Pipeline 12 aşamayı
  koşulsuz sırayla çalıştırıyor, hiçbir aşama atlanabilir yazılmamış.
  `default_pipeline.py`'deki thumbnail çağrısı `project.timeline.combined_video_path`'e
  None-check'siz erişiyor (`project.timeline` yoksa **AttributeError ile
  çöker**). `video_renderer.render_final_video()` `timeline: Timeline`'ı
  zorunlu alıyor. `DocumentaryProject.final_video_path` tek "bitiş çizgisi",
  ayrı bir `final_audio_path` kavramı yok — model tamamen video-merkezli.
  `seo_generator`'ın docstring'i açıkça "primary output is short vertical
  video" diyor. Çözüm "birkaç if/else" değil — ayrı bir `run_audio_pipeline()`
  veya modelde opsiyonel video alanları + her aşamaya None-guard gerektirir.
  **Ayrı, büyük bir plan/onay turu gerekiyor.**
- **Kids — moderasyon eksikliği:** Kod tabanında `moderation`/`age_appropriate`/
  `content_filter`/`nsfw`/`profanity` gibi HİÇBİR güvenlik mekanizması yok
  (tüm `app/` taraması sıfır sonuç verdi). "Basitleştirilmiş dil" talimatı
  eklemek çocuk güvenliği GARANTİSİ vermez, LLM'in kendi güvenlik katmanına
  güvenmek anlamına gelir. `quality_critic` da yaş uygunluğu skorlamıyor.
  **Sıfırdan bir güvenlik tasarımı gerekiyor, script talimatından ibaret değil.**
- ~~**Corporate — Tone/Format sınırı netleşmedi.**~~ Çözüldü, bkz. aşağıdaki
  "Corporate format eklendi" bölümü.

## Corporate format eklendi (kullanıcı talebiyle) — Educational ile birebir aynı desen

Önce Tone/Format sınırı sorusu netleştirildi (plan onayı istendi, sonra
uygulandı): "resmi dil" ihtiyacı `Tone.credibility`'ye ("measured,
authoritative, and precise -- like a trusted history documentary narrator")
yakın görünüyordu ama o metin kasıtlı olarak history kategorisine demirlenmiş
bir *ses* tanımı, Corporate'in ihtiyacı ise ses değil **yapısal davranış**
(pazarlama dilinden kaçınma, üçüncü şahıs anlatım, veri/istatistik vurgusu) —
yani Educational'ın "terimleri tanımla" kuralıyla aynı kategoride bir Format
kuralı, yeni bir Tone üyesi değil. Ayrıca orthogonality testi de bunu
doğruladı: Educational nasıl her Tone ile birleşebiliyorsa (epic-toned
educational documentary), Corporate da öyle olmalı.

- [x] `profile_dimensions.py`: `Format` enum'ına `corporate = "corporate"`
      eklendi, docstring güncellendi (artık educational + corporate
      implemented, podcast/kids hâlâ ertelendi).
- [x] `script_generator.py`: `FORMAT_GUIDANCE[Format.corporate]` — "structure
      this as a corporate/institutional narrative -- avoid promotional or
      salesy language, use a neutral third-person voice instead of direct
      address, and ground claims in concrete data, figures, or verifiable
      facts rather than vague claims of excellence".
- [x] Webui: değişiklik gerekmedi — `format_options = ["standard"] + [f.value
      for f in Format]` enum'ı iterate ettiği için yeni değer dropdown'a
      otomatik düştü.
- [x] Regresyon: `format=None` ve `format=educational` davranışları hiç
      değişmedi (`test_all_formats_have_guidance` gibi mevcut testler yeni
      enum üyesini otomatik kapsıyor). 4 yeni Corporate testi eklendi. Tam
      suite: **620 passed, 11 skipped** (önceden 616).
- [x] **Gerçek doğrulama (ucuz — gerçek OpenAI API, sadece script aşaması,
      video/ses/scene-plan üretimi atlandı):** "Acme Corporation's New
      Manufacturing Facility" konusu (3 sahne) iki kez `generate_script()`
      ile üretildi. `format=None`: pazarlama diliyle dolu ve dolaylı ikinci
      şahıs hissi veren cümleler — "built for a future that's already
      arriving", "the real test starts right now", "the promise is new
      opportunity, and a community watching what Acme builds next" (somut
      rakam yok, "the promise"/"the real test" gibi belirsiz iddialar).
      `format=corporate` (aynı konu, aynı sahne planı): "Acme Corporation
      opened its **240,000-square-foot** manufacturing facility today,
      beginning a **phased startup**...", "**six automated lines** are
      designed for **1.2 million units annually**, with sensor data shaping
      the next expansion decision", "adds **320 full-time roles** and
      supplier contracts, as county officials track training outcomes" —
      pazarlama dili yok, üçüncü şahıs/nötr anlatım, her cümlede somut
      rakam/veri. Talep edilen üç kural da (pazarlama dilinden kaçınma,
      üçüncü şahıs, veri vurgusu) gerçek üretimde doğrulandı.

## Webui'ye Tone/Format seçicileri (kullanıcı talebiyle)

Mevcut `Dil`/`Konu Kategorisi`/`Temp` satırının (col1-col3) hemen altına
ikinci bir satır (col4/col5): `Ton` (`auto` + 5 Tone değeri) ve `Format`
(`standard` + `educational`) — `Konu Kategorisi`nin "auto" deseniyle birebir
aynı. Backend'de değişiklik gerekmedi (`run_pipeline()` `tone`/`format`
kwargs'ı zaten önceki iki adımda eklenmişti).

- [x] `webui/Main.py`: yeni seçiciler + `run_pipeline()` çağrısına
      `tone=(None if tone=="auto" else tone)`, `format=(None if
      format_choice=="standard" else format_choice)`.
- [x] Format yardım metninde kullanıcının istediği netleştirme: "standard"
      Tone'un "auto"su gibi kategori varsayılanına düşmüyor, hiçbir ek
      rehberlik uygulamıyor (Format'ın kategori-bazlı varsayılanı yok).
- [x] i18n: 4 yeni key (`Documentary Tone`/`Tone Help`/`Format`/`Format
      Help`) **9 dilin hepsine baştan** eklendi — `test_webui_i18n.py`'nin
      AST tabanlı parite testi ilk denemede yeşil (geçen seferki "sona
      bırakma" dersinden ders çıkarıldı). Tam suite: **616 passed** (test
      sayısı değişmedi, i18n subtest'leri 4508→4564).
- [x] **Gerçek tarayıcı testi (gerçek API, mock yok):** `.venv` içinden
      Streamlit ayrı bir portta (8590, mevcut 8501'e dokunulmadı) başlatıldı,
      Node/Playwright (npx cache'inden, `chromium-cli` bu ortamda yok) ile
      headless Chromium üzerinden sürüldü. Onboarding tur overlay'i
      kapatıldı, "AI Documentary Studio (Beta)" açıldı, konu "How Rainbows
      Form" + Dil "en" + **Ton "scientific"** + **Format "educational"**
      seçildi, "Belgesel Oluştur"a tıklandı. 12 aşama da gerçek OpenAI +
      Pexels + ElevenLabs TTS ile hatasız tamamlandı (~6 dakika), "Belgesel
      başarıyla oluşturuldu" göründü. `project.json` doğrulaması:
      `topic_category: "space"` (varsayılan tonu "epic" olurdu) ama
      `tone: "scientific"` — **override kategori varsayılanını gerçekten
      ezdi**. Üretilen script hem bilimsel sesi hem pedagojik yapıyı
      gösteriyor: "each raindrop **refracts, or bends**, sunlight...",
      "**wavelengths, different kinds of visible light** our eyes read as
      color" (terim tanımları) ve kapanışta net bir özet cümlesi. Konsol
      hatası yok (`console --errors` boş). Test sunucusu ve tüm
      Playwright/Chromium süreçleri iş bitince temizlendi.

## Publishing Engine — manuel tetikleme, mevcut upload_post.py sarmalandı (kullanıcı talebiyle)

Önce plan istendi ve onaylandı. Araştırma: `app/services/upload_post.py`
gerçek, test edilmiş bir entegrasyon (Upload-Post.com'a sarmalayıcı; TikTok/
Instagram/YouTube Shorts) ama sadece legacy `task.py` tekil-video akışına
bağlıydı — yeni `default_pipeline.py`'ye hiç bağlı değildi.
`app/departments/growth/__init__.py`'nin boş olması ve `PROGRESS.md`'de
zaten "Growth Dept: seo_generator (+ ileride: yayınlama/analytics)" diye not
düşülmüş olması, yeni bir modülün tam olarak burada yaşaması gerektiğini
gösteriyordu.

**Kritik tasarım kararı (kullanıcıya soruldu):** yayınlama gerçek hesaplara
gerçekten, geri alınamaz şekilde içerik gönderdiği için — Corporate/Format
gibi saf metin değişikliklerinden farklı bir risk sınıfı — otomatik mi yoksa
manuel onaylı mı tetiklenmeli? **Kullanıcı manuel onayı seçti.** Bu yüzden:

- [x] `app/departments/growth/publisher.py`: `publish_project(project,
      platforms=None, youtube_privacy_status=None)` — `upload_post.
      cross_post_video()`'yu sarmalıyor, `project.final_video_path` +
      `project.seo.title/description/hashtags` kullanıyor.
      `is_configured()=False` veya `final_video_path` boşsa erken döner,
      ağ çağrısı yapmaz. `youtube_privacy_status` parametre olarak geçiliyor
      (paylaşılan `upload_post_service` singleton'ına **yazılmıyor** —
      aksi halde webui'deki tek seferlik bir seçim, legacy `task.py`'nin
      otomatik cross-post davranışını da kalıcı olarak değiştirirdi).
      `project`'i **mutate etmiyor**, `PublishResult` döndürüyor — kararı
      çağıran (webui) veriyor.
- [x] `app/models/publish.py`: `PublishResult` (success/request_id/error/
      platforms/published_at). `DocumentaryProject.publish_result:
      PublishResult | None = None` — hiçbir zaman otomatik set edilmiyor,
      sadece kullanıcı elle "Yayınla"ya tıklarsa dolduruluyor.
- [x] `webui/Main.py`: `_render_publish_section()` — `default_pipeline.
      run_pipeline()`'a **hiç dokunulmadı** (publish, pipeline'ın bir
      parçası değil, ayrı bir fonksiyon). Video/thumbnail/SEO gösterildikten
      sonra: platform çoklu-seçim kutusu (varsayılan: config'teki
      `upload_post_platforms`), "youtube" seçiliyse gizlilik dropdown'u
      (varsayılan: config'teki `upload_post_youtube_privacy_status`),
      "Yayınla" butonu (platform seçilmeden tıklanamaz), sonuç mesajı,
      ve "zaten yayınlandı: {zaman} → {platformlar}" uyarısı (session state
      üzerinden, engellemeden — tekrar yayınlamaya izin veriyor).
      `upload_post_service.is_configured()=False` ise buton yerine
      yapılandırma uyarısı gösteriliyor.
- [x] i18n: 10 yeni key (`Documentary Publish*`) **9 dilin hepsine baştan**
      eklendi, `test_webui_i18n.py` ilk denemede yeşil.
- [x] Regresyon: `default_pipeline.py` ve legacy `task.py`/`upload_post.py`
      hiç değişmedi. Yeni `test/services/test_publisher.py` (11 test):
      unconfigured/missing-video erken dönüş, project mutate edilmiyor,
      platform varsayılanı, SEO alanlarının doğru eşlenmesi, YouTube-extra
      sadece "youtube" platformdayken ekleniyor, `youtube_privacy_status`
      parametresinin config varsayılanını ezmesi, başarı/başarısızlık
      sonuç şekli. Tam suite: **631 passed, 11 skipped** (önceden 620).
- [ ] **Gerçek doğrulama yapılamadı:** bu ortamda `upload_post_enabled=false`,
      `upload_post_api_key=""` — yani gerçek bir Upload-Post hesabı/API key'i
      yok. Gerçek bir platforma post atmak geri alınamaz bir eylem olduğu
      için mock'suz bir doğrulama **bilerek yapılmadı**. Doğrulama sadece
      mock'lu testlerle ve `is_configured()=False` durumunun webui'de doğru
      davrandığının (butonun yerine uyarı çıkması) manuel gözlemiyle
      yapıldı. Gerçek bir yayın testi için kullanıcının kendi Upload-Post
      API key'ini sağlayıp açıkça istemesi gerekiyor.

## Bilinen teknik sınırlar (konsolide liste)

Koda dağılmış, tek tek not düşülmüş ama bir araya toplanmamış küçük/orta
teknik borç kalemleri — Podcast/Kids gibi büyük, onay bekleyen özellik
kararlarından farklı olarak, bunların hepsi **çalışıyor**, sadece ya
kusurlu/eksik bir davranışları ya da netleşmemiş bir kalibrasyonları var.
Her biri koddan doğrulandı (bu oturumda, kullanıcı talebiyle); ayrıca
`PROGRESS.md`'nin tamamı "not/sınırlama/kalan sınırlama" ifadeleri için
tekrar tarandı — bu taramada bulunan ama **zaten sonradan düzeltilmiş**
maddeler (ör. thumbnail başlık kesilmesi, bkz. "Thumbnail başlık kesilme
düzeltmesi" bölümü) bilinçli olarak bu listeye alınmadı.

**Özet tablo** (risk/etki × düzeltme karmaşıklığı → önerilen öncelik):

| # | Madde | Risk/Etki | Karmaşıklık | Öncelik |
|---|---|---|---|---|
| 1 | Üç ayrı dil listesi | Düşük-Orta (bakım riski) | Orta (isim + test bağımlılığı) | Düşük |
| 2 | `estimate_words` taban sınırı | Çok düşük bugün (ölü kod) | Trivial | Düşük (ön koşul niteliğinde) |
| 3 | `QUALITY_PASS_THRESHOLD` kalibrasyonu | Çok düşük (hiçbir kararı tetiklemiyor) | Belirsiz/yüksek (gerçek veri gerekir) | En düşük |
| 4 | Altyazı font varsayılanı ikiliği | Orta (sessiz, taze kurulumda gerçek sapma) | Trivial-Küçük | **Yüksek** (efor/etki oranı en iyi) |
| 5 | `shot_type`/`search_terms[1:]` tüketilmiyor | Orta (gereksiz LLM token maliyeti) | Küçük-Orta | Orta |
| 6 | `TopicCategory` 4 kategori sınırı | Orta (yanlış ton/şablon riski) | Büyük (yeni tasarım kararı) | Düşük (bu oturumda) |
| 7 | Research grounding sessiz düşüş | ~~Yüksek~~ **Orta** (Wikipedia fallback eklendi, GÖREV 4 — kapsam sorunu büyük ölçüde çözüldü, şeffaflık eksikliği duruyor) | Küçük-Orta (şeffaflık) | Orta (Yüksek'ten düşürüldü) |
| 8 | Pexels tarihi görsel kapsam sınırı | Düşük (zaten kabul edilmiş) | Kodla çözülemez (veri sınırı) | En düşük |

- [ ] **Üç ayrı "dil" kavramı, birbirini karşılamıyor:**
  1. `webui/Main.py:87` `locales = utils.load_locales(i18n_dir)` → arayüz
     çeviri dili, 9 dil (de/en/es/id/pt/ru/tr/vi/zh).
  2. `webui/Main.py:1162` `support_locales` → **legacy** tekil-video
     pipeline'ının "Script Language" seçici listesi, 11 locale kodu
     (zh-CN/zh-HK/zh-TW/de-DE/en-US/es-ES/fr-FR/ru-RU/vi-VN/th-TH/tr-TR).
  3. `app/config/profile_dimensions.py:49-52` `Language` enum → Documentary
     Studio'nun kendi konu dili, sadece 3 değer (auto/tr/en).
  Bu üçü birbirini kapsamıyor: `support_locales`'te olup arayüz çeviri
  listesinde olmayan diller var (fr-FR, th-TH — bu dillerde arayüz asla
  gösterilemez, sadece legacy script dili olarak seçilebilir), tersine "id"
  (Endonezyaca) arayüz dili ama `support_locales`'te karşılığı yok. Üçü de
  ayrı amaçlara hizmet ettiği için bu "hata" değil ama isim benzerliği
  (`locales` / `support_locales` / `Language`) kafa karıştırıcı — yeni bir
  dil eklerken hangisinin güncellenmesi gerektiği kolayca atlanabilir.
  **Risk/Etki:** Düşük-Orta — bugün aktif bir hata/çökme yok, sadece gelecekte
  yeni dil eklerken üç listeden birinin unutulma riski. **Karmaşıklık:** Orta
  — `test_webui_i18n.py:152-167` `support_locales` adını AST ile birebir
  arıyor, isim değişikliği bu testi kırar; üçünü birleştirmek/yeniden
  adlandırmak dikkatli bir refactor gerektirir. **Öncelik:** Düşük.
- [ ] **`script_generator.py:89` kelime hedefi taban sınırı canlı değil:**
  `target_words = max(5, round(scene.duration_seconds * _WORDS_PER_SECOND))`
  — taban olan 5, sadece `duration_seconds` ~2.2s altına düştüğünde devreye
  girer. `PACING_SCENE_SPEC` bugün sadece 5.0s (short) ve 8.0s (long) üretiyor
  (`scene_planner.py`'de her sahneye pacing'in **sabit** süresi atanıyor,
  importance'a göre değişmiyor) — ikisi de tabanın çok üzerinde (12/18
  kelime). Yani taban şu an **hiçbir zaman tetiklenmiyor**, ölü kod gibi
  davranıyor; sadece ileride sahne süresi importance-ağırlıklı/değişken hale
  gelirse (ör. çok kısa bir sahne) anlam kazanır — o zaman da taban tüm kısa
  sahneleri aynı 5 kelimeye düzleyip pacing'in ayırt ediciliğini kaybettirir.
  **Risk/Etki:** Çok düşük bugün (tetiklenmiyor); sahne süresi değişken hale
  gelirse Orta. **Karmaşıklık:** Trivial — tek satırlık sabit/formül
  değişikliği. **Öncelik:** Düşük, ama sahne süresi importance-ağırlıklı hale
  getirilecekse bu maddenin **önce** ele alınması gereken bir ön koşul.
- [ ] **`QUALITY_PASS_THRESHOLD = 3.0`** (`app/models/quality.py`) hiç
  kalibre edilmedi — `quality_critic` pipeline'a otomatik/zorunlu
  bağlanmadığı için (`default_pipeline.py:219`, "informational only, never
  blocks") `passed` alanı hiçbir kararı tetiklemiyor, sadece log'a yazılıyor.
  Düşük öncelik: gerçek eşik ancak `passed=False` bir şeyi gerçekten
  durdurmaya/tekrar denetmeye başladığında anlam kazanacak.
  **Risk/Etki:** Çok düşük — hiçbir karara bağlı değil. **Karmaşıklık:**
  Sayının kendisini değiştirmek trivial ama "doğru" eşiği bulmak gerçek
  kullanım verisi/insan etiketlemesi gerektirir, basit değil. **Öncelik:**
  En düşük — zaten bilinçli olarak `quality_critic`'in pipeline'a bağlanacağı
  ana kadar ertelenmiş.
- [ ] **Altyazı font varsayılanı iki yerde farklı, sadece biri yorumla
  belgelenmiş:** `webui/Main.py:99-101` `DEFAULT_SUBTITLE_SETTINGS["font_name"]`
  = `"MicrosoftYaHeiBold.ttc"` (FAZ 0'dan kalma, CJK-ağırlıklı), `video_renderer.py:19-25`
  `_DEFAULT_SUBTITLE_SETTINGS["font_name"]` = `"BeVietnamPro-Bold.ttf"` —
  kasıtlı bir sapma, kod yorumunda açıklanmış ("this pipeline defaults to a
  plain sans-serif ... instead of a CJK-weighted font"). **Pratikte ölü
  değil:** `config.example.toml:345`'te `font_name` satırı yorum satırı
  (`# font_name = ...`) olduğu için, hiç dokunmamış taze bir kurulumda
  `config.ui`'da bu key hiç olmuyor ve her iki fallback da gerçekten devreye
  giriyor — webui'nin gösterdiği/varsaydığı varsayılan ile videoya gerçekten
  gömülen font o durumda **gerçekten farklı** oluyor, bu fark kullanıcıya
  arayüzde hiç görünmüyor.
  **Risk/Etki:** Orta — sadece kozmetik değil, taze kurulumlarda sessiz bir
  UI/render sapması. **Karmaşıklık:** Trivial-Küçük — tek satırlık değer
  eşitleme (`webui/Main.py`'nin varsayılanını da `BeVietnamPro-Bold.ttf`
  yapmak, proje zaten bu yöne evrilmiş: thumbnail + video_renderer ikisi de
  bunu kullanıyor). **Öncelik:** **Yüksek** — listede efor/etki oranı en iyi
  kalem, tek satırlık bir düzeltme gerçek bir sapmayı kapatıyor.
- [ ] **`shot_type` ve `search_terms[1:]` üretiliyor ama hiç tüketilmiyor:**
  `storyboard_generator.py` LLM'den her shot için `shot_type` (wide/close-up/
  aerial/...) ve bir `search_terms` **listesi** üretiyor
  (`app/models/storyboard.py:7-8`), ama `asset_generator.py:16` sadece
  `shot.search_terms[0]`'ı okuyor — `shot_type` hiç okunmuyor, listedeki
  1'den sonraki terimler de hiç kullanılmıyor. Daha önce bir oturumda
  bilinçli olarak dokunulmamıştı (bkz. yukarıda "`shot_type` bulgusu"), aynı
  kalıp `search_terms[1:]` için de geçerli — LLM zaten bunları üretiyor,
  token maliyeti var ama karşılığı kullanılmıyor.
  **Risk/Etki:** Orta — gerçek bir maliyet var (üretilip atılan token'lar)
  ama görünür bir hata/kalite kaybı yaratmıyor. **Karmaşıklık:** Küçük-Orta
  — `search_terms[1:]` için 0-sonuç durumunda fallback eklemek küçük bir
  değişiklik; `shot_type`'ı da aynı anda bağlamak iki değişkeni birden
  gerçek API'ye sürer (önceki oturumda tam bu yüzden bilinçli olarak
  ayrılmıştı). **Öncelik:** Orta — iki değişikliği ayrı commit'lerde ele
  almak (önce `search_terms[1:]` fallback, sonra `shot_type`) önerilir,
  kullanıcı onayı olmadan dokunulmamalı.
- [ ] **`TopicCategory`'nin 4 sabit kategorisi (travel/history/space/
  psychology) her konuyu karşılamıyor:** `idea_generator` örneğinde
  doğrulanmış ("Japonya neden güvenli?" → toplum/kültür konusu, 4 kategoriden
  hiçbirine tam oturmuyor). Bilinçli olarak kapsam dışı bırakılmıştı;
  kategori şemasının kendisinin genişletilmesi ayrı bir karar gerektiriyor.
  **Risk/Etki:** Orta — kapsam dışı konularda kategori-bazlı ton/prompt
  şablonu (`PROFILE_PROMPTS`, `DEFAULT_TONE_BY_CATEGORY`) yanlış bir
  varsayılana düşebilir. **Karmaşıklık:** Büyük — yeni kategori eklemek her
  kategorinin şablonunu, tone eşlemesini, testleri ve gerçek doğrulamayı
  gerektirir. **Öncelik:** Düşük (bu oturumda) — Podcast/Kids/Corporate ile
  aynı kategoride, ayrı bir plan/onay turu gerektiriyor.
- [x] ~~**Research grounding niş konularda sessizce LLM-only'e düşüyor**~~
  **Kısmen çözüldü (GÖREV 4, gece oturumu):** `web_search.search_web()`
  artık DuckDuckGo boş dönerse Wikipedia REST API'sine düşüyor (bkz. "GÖREV
  4 — Knowledge Engine güçlendirme"), kapsam ciddi genişledi (Wikipedia'da
  makalesi olan hemen her konu). **Ama madde hâlâ tamamen kapanmadı:**
  `research_planner.py` hâlâ ikisi de (DuckDuckGo + Wikipedia) `None`
  dönerse sessizce saf LLM bilgisine düşüyor — kullanıcıya/`ResearchPlan`'a
  hâlâ hiçbir "bu belgesel doğrulanmış kaynak olmadan üretildi" sinyali
  verilmiyor. **Risk/Etki:** Artık Orta (önceden Yüksek) — kapsam
  genişlemesi halüsinasyon riskini azalttı ama şeffaflık eksikliği duruyor.
  **Karmaşıklık:** Küçük-Orta (`ResearchPlan`'a `grounded: bool` alanı +
  webui'de görünür uyarı) — bilinçli olarak bu oturumda yapılmadı, ayrı bir
  onay gerektirir. **Öncelik:** Orta (Yüksek'ten düşürüldü, kapsam sorunu
  büyük ölçüde çözüldüğü için).
- [ ] **Pexels'in çok spesifik tarihi görsel türlerinde (ör. dönem
  haritaları) sınırlı kapsamı:** Storyboard search terms artık topic+
  key_facts ile grounded (jenerik kelime kopyalama sorunu çözüldü), ama
  Pexels'in kendisi bazı niş tarihi görsel türlerini yeterince
  kapsamıyor — bu bir stok-kütüphane veri sınırı, kod sorunu değil; önceki
  bir oturumda **zaten "kabul edilebilir seviyede" olarak kapatılmıştı**.
  **Risk/Etki:** Düşük — zaten kabul edilmiş, aksiyon beklenmiyor.
  **Karmaşıklık:** Kodla çözülemez (veri sınırı); farklı/ek bir stok
  sağlayıcı (tarihi arşiv görselleri sunan) eklemek Büyük bir değişiklik
  olurdu. **Öncelik:** En düşük — sadece envanterde eksiksizlik için not
  düşülüyor, aksiyon önerilmiyor.

## GECE OTURUMU (genişletilmiş) — Görev 1 başka bir ajanda (Hermes/Codex, tmux `work`), Görev 3-8 burada

Kullanıcı, GÖREV 1'in (tekrarlayan kare + altyazı gecikmesi düzeltmesi) aynı
makinede ayrı bir tmux oturumunda çalışan başka bir AI ajanı (Hermes,
OpenAI Codex/gpt-5.5 tabanlı) tarafından ele alındığını netleştirdi. Bu
oturum GÖREV 1'e **hiç dokunmuyor** — özellikle `app/services/video.py`
(`combine_videos`), `audio_renderer.py`, ve altyazı birleştirme (`_merge_subtitle_files`)
ile ilgili hiçbir koda dokunulmadı/dokunulmayacak.

**Çakışma riskini azaltma (kodlamadan önce):**
- [x] `git branch -a` + `git status`: tek bir clone var
      (`/root/MoneyPrinterTurbo/AI-Documentary-Studio`), Hermes de aynı
      dizini paylaşıyor (ayrı bir clone yok, `find / -iname AI-Documentary-Studio`
      tek sonuç verdi). `git status` sadece benim önceki commit'lenmemiş
      `PROGRESS.md` değişikliğimi gösteriyordu — Hermes henüz dosya
      düzeyinde bir değişiklik yapmamış (muhtemelen aylık Codex kotası
      dolduğu için rate-limit döngüsünde takılı, `tmux capture-pane`
      ile doğrulandı).
- [x] Paylaşılan checkout'ta `git checkout -b` yapmak yerine (bu, Hermes'in
      dizinini de etkileyebilirdi — aynı `.git`, aynı working tree),
      **tamamen izole bir `git worktree`** oluşturuldu:
      `/root/MoneyPrinterTurbo/ai-documentary-studio-claude-tasks`,
      dal adı `overnight/claude-tasks-3to8` (isim çakışması yoktu, önerilen
      isim kullanıldı). `.venv`, `config.toml` orijinal dizine symlink'lendi
      (aynı bağımlılıklar/API key'ler); `storage/` **symlink yapılmadı** —
      ilk denemede symlink edilince `os.path.realpath` bazlı testler
      (`test_local_material_filename_resolved_to_absolute_path`,
      `test_task_query_returns_relative_url_without_mutating_state`) iki
      dizin adı farklı olduğu için başarısız oldu; gerçek, bağımsız boş bir
      `storage/` dizini oluşturulunca tam suite tekrar **631 passed, 11
      skipped** oldu (regresyon değil, saf worktree-path artefaktıydı).
- [x] Push stratejisi: worktree'den `git push origin overnight/claude-tasks-3to8:main`
      (uzak `main`'i fast-forward ediyor, orijinal dizindeki checked-out
      `main` dalına dokunmuyor — iki worktree aynı `.git`'i paylaştığı için
      yerel `refs/heads/main`'i değiştirmek riskliydi, bu yüzden sadece
      remote ref güncelleniyor). Her görev öncesi `git fetch origin` ile
      Hermes'in bir şey push'layıp push'lamadığı kontrol ediliyor.
- [x] SSH push doğrulandı: `git@github.com:ukaya17-jpg/AI-Documentary-Studio.git`
      üzerinden token'sız push gerçekten çalıştı (bu bölümden önceki
      commit `2fd6fa0` ile test edildi).

### GÖREV 3 — Instagram yayınlama desteği

**Bulgu: altyapı zaten tamdı, kod değişikliği gerekmedi.**
- `webui/Main.py:3936` `known_platforms = ["tiktok", "instagram", "youtube"]`
  — Instagram **zaten** seçilebilir bir checkbox olarak multiselect'te
  duruyordu (kullanıcının "belki UI'a yansımamıştır" endişesi doğrulanmadı).
- `app/departments/growth/publisher.py` zaten tam platform-agnostik:
  `youtube_extra` sadece `"youtube"` platformlar listesindeyse dolduruluyor
  (`publisher.py:58-59`), Instagram (tek başına veya TikTok/YouTube ile
  birlikte) hiçbir özel dala girmeden generic `title`/`cross_post_video()`
  akışından geçiyor.
- [x] 3 yeni test eklendi: `test_instagram_only_publish_succeeds_with_no_youtube_extra`,
      `test_instagram_combined_with_youtube_still_gets_youtube_extra`
      (`test_publisher.py`) + `test_known_platforms_include_instagram_tiktok_and_youtube`
      (yeni `test_webui_publish_platforms.py`, `test_webui_i18n.py`'deki AST
      tabanlı desenle aynı — Streamlit'i gerçekten çalıştırmadan
      `known_platforms` listesini koddan doğruluyor).
- [x] Gerçek yayın denemesi **yapılmadı** (kullanıcı talebi: geri alınamaz/
      herkese açık eylem, sadece mock'lu test). Tam suite: **634 passed, 11
      skipped** (önceden 631).
- [x] `config.toml`'daki `upload_post_platforms` **bilinçli olarak
      değiştirilmedi** — kullanıcının kendi Upload-Post hesap tercihi,
      webui'deki multiselect zaten config varsayılanından bağımsız olarak
      Instagram'ı seçilebilir kılıyor.

### GÖREV 4 — Knowledge Engine güçlendirme: Wikipedia REST API fallback

**Araştırma:** DuckDuckGo Instant Answer niş/spesifik konularda sıklıkla
`None` dönüyor (bilinen bir sınır, `PROGRESS.md`'nin "Bilinen teknik
sınırlar" bölümünde zaten madde #7 olarak kayıtlı). Wikipedia'nın kendi REST
API'si (`/w/rest.php/v1/search/page` + `/api/rest_v1/page/summary/{title}`)
ücretsiz, key gerektirmiyor, ve kapsamı DuckDuckGo'dan çok daha geniş
(Wikipedia'da makalesi olan hemen her konu) — **araştırma sonucu: eklemeye
değer, eklendi.**

- [x] `app/services/web_search.py`: mevcut DuckDuckGo mantığı `_search_duckduckgo()`
      adıyla ayrı bir fonksiyona çıkarıldı, yeni `_search_wikipedia(query,
      language)` eklendi (önce arama endpoint'i ile en iyi eşleşen sayfa
      başlığını buluyor, sonra summary endpoint'inden `extract` metnini
      çekiyor). `search_web(query, language="")` artık önce DuckDuckGo'yu
      deniyor, o `None` dönerse Wikipedia'ya düşüyor — **aynı "bulunamazsa
      sessizce `None`" deseni korundu**, `research_planner.py` tarafında
      hiçbir ek değişiklik gerekmedi (zaten `None`'ı normal kabul ediyordu).
- [x] `research_planner.generate_research_plan()` artık `language`'i
      `search_web()`'e geçiriyor (`web_search.search_web(topic,
      language=language)`) — Wikipedia'nın doğru dil alt alanını (tr/en)
      seçebilmesi için gerekliydi, önceden `language` hiç iletilmiyordu.
      `Language` enum'ının sadece `auto`→(`tr`|`en`) ürettiği doğrulandı
      (`intent_analyzer.detect_language()`), bu yüzden Wikipedia tarafı
      sadece tr/en'i destekliyor, tanınmayan her şey `en`'e düşüyor.
- [x] 8 yeni test: `test_web_search.py`'de `TestWikipediaFallback` (7 test:
      DuckDuckGo boşken Wikipedia'ya düşme, DuckDuckGo başarılıyken
      Wikipedia'nın hiç çağrılmaması, sayfa bulunamama, boş extract, tr/en
      alt alan seçimi, ağ hatası) + `test_research_planner.py`'de
      `test_passes_language_through_to_search_web`. Tam suite: **642
      passed, 11 skipped** (önceden 634).
- [x] **Gerçek doğrulama (ücretsiz, key'siz API'ler — LLM/ödeme maliyeti
      yok):** "Nusret Ottoman minelayer ship" (bu projenin kendi storyboard
      örneklerinde geçen bir konu) ile test edildi. DuckDuckGo Instant
      Answer beklendiği gibi boş döndü. **İlk denemede Wikipedia isteği 403
      Forbidden döndü** — gerçek bir bulgu: Wikimedia'nın API politikası
      açıklayıcı bir `User-Agent` header'ı olmayan istekleri reddediyor
      (`requests`'in varsayılan `python-requests/x.y` User-Agent'ı
      yetmiyor). Mock'lu testler bunu hiç yakalayamazdı çünkü gerçek HTTP
      davranışını simüle etmiyorlardı. Düzeltme: `_WIKIPEDIA_HEADERS`
      sabiti eklendi, her iki Wikipedia isteğine de geçiliyor. Düzeltme
      sonrası aynı sorgu gerçek bir özet döndürdü: "Ottoman minelayer Nusret
      ... served as a minelayer during the Gallipoli Campaign..."
      (`https://en.wikipedia.org/wiki/Ottoman_minelayer_Nusret`). Türkçe
      yönlendirme de ayrıca doğrulandı: "Nusret mayın gemisi" (`language="tr"`)
      → `tr.wikipedia.org/wiki/Nusret`'ten gerçek bir Türkçe özet döndü.
      Tam suite düzeltme sonrası da **642 passed, 11 skipped** (header
      eklemek test edilen davranışı değiştirmedi, sadece gerçek isteği
      düzeltti).

### GÖREV 1 — Hermes'in kotası bitti, GÖREV 1 tamamen bu oturuma geçti (EN YÜKSEK ÖNCELİK)

Kullanıcı sabah GÖREV 1'in (tekrarlayan kare + altyazı gecikmesi) çözüldüğünü
kendi gözüyle teyit edecek — bu yüzden en derin, en somut teşhis + düzeltme +
gerçek doğrulama bu iki maddeye ayrıldı.

**1a. Tekrarlayan kareler — kök neden bulundu, `default_pipeline.py`'de düzeltildi.**

Kanıt zinciri (Görev 5 için yapılan gerçek "The Psychology of Deja Vu"
üretiminden, GÖREV 1'e geçmeden önce zaten elde edilmişti):
- Gerçek TTS ses süresi (ölçüldü): **40.39s**.
- `scene_plan.total_duration` (short pacing, asset indirme aşamasının
  kullandığı TAHMİN): **20.0s** — TTS henüz çalışmadığı için stage 8 (asset
  download) bunu tahmin olarak kullanıyor (`default_pipeline.py`, eski yorum:
  "TTS hasn't run yet at this point, so the scene duration budget is used as
  the audio-duration estimate").
- Gerçek script **78 kelime** üretti, hedef sadece **48 kelime**'ydi
  (4 sahne × 12 kelime @ `_WORDS_PER_SECOND=2.3`) — LLM hedefi **%62 aştı**.
- Sonuç: gerçek ses tahminin **2.02 katı** uzun çıktı.
- `app/services/video.py:combine_videos()`'da bu tam olarak belgelenmiş bir
  davranış: `# loop processed clips until the video duration covers the
  audio duration` — indirilen görüntü toplam gerçek ses süresini
  karşılamazsa `itertools.cycle(base_clips)` ile **aynı klipler baştan
  tekrar tekrar ekleniyor**. Bu, "tekrarlayan kare" şikayetinin doğrudan
  mekanizması.
- **Düzeltme (OTONOM KARAR, tutucu/geri alınabilir):** `default_pipeline.py`'de
  yeni `_ASSET_DOWNLOAD_DURATION_SAFETY_MULTIPLIER = 2.0` sabiti eklendi;
  stage 8'de `asset_downloader.download_assets()`'e artık
  `scene_plan.total_duration * 2.0` gönderiliyor (önceden çıplak
  `scene_plan.total_duration`). En kötü ihtimalle birkaç ekstra ücretsiz
  Pexels indirmesi — video.py/combine_videos'a, audio_renderer.py'ye HİÇ
  dokunulmadı (asıl kaynağı, tahmin/gerçek süre uyuşmazlığını, en erken
  noktada düzeltmek daha güvenli/tersine çevrilebilir bir seçenekti).
  `test_default_pipeline.py`'deki ilgili assertion güncellendi (sabit
  çarpanı referans alarak, hardcode etmeden).

**1b. Altyazı gecikmesi — kök neden bulundu, `voice.py`'de düzeltildi.**

- `render_narration()` tüm anlatımı **tek bir TTS çağrısıyla** sentezliyor
  (sahne sahne değil) — yani sahneler arası "kayma birikmesi" hipotezi
  **doğrulanmadı** (böyle bir birleştirme adımı yok).
- Gerçek kök neden: ElevenLabs (`voice.py:elevenlabs_tts()`) düz
  `/v1/text-to-speech/{voice_id}` endpoint'ini kullanıyordu — bu endpoint
  **hiç kelime/karakter zamanlaması döndürmüyor**. Bu yüzden altyazı
  zamanlaması `populate_legacy_submaker_with_full_text()` ile **karakter
  sayısı oranına göre tahmin ediliyordu** (gerçek TTS duraklamalarını,
  hız değişimlerini hesaba katmadan) — sadece metnin SONU gerçek ses
  süresine sabitleniyor, aradaki her cümlenin başlangıç/bitişi tahmini.
  Gerçek bir SRT'de bunun somut izi bulundu: `subtitle.srt`'de tırnak
  işaretinden ibaret bir "cümle" sadece **88ms** sürüyordu (satır 12,
  `00:00:20,858 --> 00:00:20,946`) — karakter-oranlı model noktalama
  parçalarını gerçekçi olmayan şekilde zamanlıyor.
  `video.py:generate_video()`'nun `SubtitlesClip`'i doğrudan SRT
  zaman damgalarını kullandığı doğrulandı (ek bir yeniden hesaplama yok) —
  yani sorun tamamen SRT üretiminde, video birleştirmede değil.
- **Düzeltme (araştırıldı, ElevenLabs'ın resmi API dokümantasyonu
  WebFetch ile doğrulandı):** ElevenLabs'ın `/v1/text-to-speech/{voice_id}/with-timestamps`
  endpoint'i **gerçek karakter-seviyesi zaman damgası** döndürüyor
  (`alignment.characters` + `character_start_times_seconds` +
  `character_end_times_seconds`). `elevenlabs_tts()` artık bu endpoint'i
  kullanıyor, `audio_base64`'ü decode ediyor, ve yeni
  `populate_legacy_submaker_with_character_alignment()` fonksiyonuyla her
  cümleyi GERÇEK zaman damgalarına sabitliyor. **Güvenlik ağı:** hizalanan
  metin orijinal script'le birebir eşleşmezse (nadir bir normalizasyon
  farkı ihtimaline karşı) fonksiyon `None` dönüyor ve kod otomatik olarak
  eski `populate_legacy_submaker_with_full_text()` yöntemine düşüyor —
  **regresyon riski yok, sadece iyileştirme.**
- 7 yeni test (`test_voice.py`): gerçek hizalama başarı senaryosu, hizalama
  yokken/eşleşmezken fallback, `populate_legacy_submaker_with_character_alignment`
  için 3 doğrudan birim testi (doğru sabitleme, metin uyuşmazlığında `None`,
  boş girdi). Tam suite: **646 passed, 11 skipped** (önceden 642).

## Karar bekleyen noktalar

SSH push artık gerçekten çalışıyor (`git@github.com:...`, token'sız) —
önceki "manuel push bekliyor" notu artık geçersiz. Podcast (mimari), Kids
(güvenlik tasarımı), Analytics/Learning Layer (gerçek yayın verisi yok) —
üçü de kullanıcıdan ayrı onay bekleyen, bu gece oturumunda da **bilinçli
olarak dokunulmayan** konular (Corporate çözüldü, yukarıya bkz.).
Publishing Engine kodu ve mock'lu testleri tamam, ama **gerçek bir platforma
yayın doğrulaması kullanıcının Upload-Post kimlik bilgilerini sağlamasını
bekliyor** (yukarıya bkz.).
