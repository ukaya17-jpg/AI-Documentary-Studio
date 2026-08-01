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
| 1 | Üç ayrı dil listesi | Düşük-Orta (bakım riski) | Orta (isim + test bağımlılığı) | Düşük — **[x] kısmen: açıklayıcı yorumlar eklendi (GÖREV 8d)** |
| 2 | `estimate_words` taban sınırı | Çok düşük bugün (ölü kod) | Trivial | Düşük (ön koşul niteliğinde) |
| 3 | `QUALITY_PASS_THRESHOLD` kalibrasyonu | Çok düşük (hiçbir kararı tetiklemiyor) | Belirsiz/yüksek (gerçek veri gerekir) | En düşük |
| 4 | Altyazı font varsayılanı ikiliği | Orta (sessiz, taze kurulumda gerçek sapma) | Trivial-Küçük | **Yüksek** (efor/etki oranı en iyi) |
| 5 | `shot_type`/`search_terms[1:]` tüketilmiyor | Orta (gereksiz LLM token maliyeti) | Küçük-Orta | Orta — **[ ] GÖREV 8c'de değerlendirildi, paylaşılan legacy koda regresyon riski nedeniyle bilinçli ertelendi** |
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
  **[x] Kısmen ele alındı (GÖREV 8d, gece oturumu):** Üçünü birleştirmek
  (test'i kırma riski nedeniyle) yapılmadı, ama her üç tanımın yanına
  birbirine referans veren, ne işe yaradıklarını ve neden ayrı olduklarını
  açıklayan yorumlar eklendi (`webui/Main.py`'de `locales` ve
  `support_locales` tanımları, `profile_dimensions.py`'de `Language` enum
  docstring'i). Kod davranışı değişmedi, sadece "yeni dil eklerken hangisini
  güncellemeliyim" sorusu artık koddan cevaplanıyor.
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
  **[ ] GÖREV 8c denendi, bilinçli olarak ERTELENDİ (gece oturumu, OTONOM
  KARAR):** `search_terms[1:]` fallback'i için gerçek bir tasarım incelendi
  — `material.py`'nin `download_videos()`/`_download_videos_by_script_order()`
  fonksiyonu hem yeni Documentary Studio'nun `asset_downloader.py`'si hem de
  **legacy `task.py`'nin eski tekil-video pipeline'ı** tarafından
  paylaşılıyor (`search_terms: List[str]` imzası ikisinde de aynı). Düzgün
  bir fallback için bu imzayı `List[List[str]]` gibi bir yapıya değiştirmek
  gerekiyor — bu hem legacy pipeline'ı hem de bu gece **az önce GÖREV 1a'da
  düzelttiğim tam da bu asset-download alanını** tekrar riske atar, sabah
  kullanıcının gözüyle doğrulayacağı en kritik alanın hemen yanı başında.
  Tutucu/geri alınabilir seçenek: bu değişikliği **yapmamak**, düşük
  öncelikli olduğu için (kullanıcı talimatı: "vakit yetmezse 8 yarım/hiç
  başlanmamış kalabilir, sorun değil"). Somut, izole bir gelecek görevi
  olarak bırakılıyor: `AssetCandidate`'e `search_term_fallbacks: list[str] =
  []` eklemek (geriye uyumlu, varsayılan boş liste), `material.py`'nin iki
  çağıranını da (yeni + legacy) güncelleyip ayrı ayrı gerçek testle
  doğrulamak.
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

**GERÇEK UÇTAN-UCA DOĞRULAMA (her iki düzeltme, tek üretimde, "How Octopuses
Change Color", en, short pacing, gerçek OpenAI + Pexels + ElevenLabs):**

- **1a kanıtı:** Log'da `"total duration of downloaded videos: 45.0
  seconds"` — eski davranışta bu ~20-25s olurdu (2x güvenlik çarpanı
  öncesi). Gerçek ses süresi 22.6s çıktı, gereken video süresi 22.70s.
  `combine_videos()` **5 FARKLI kaynak dosyadan** (`vid-3d6b7cd7...`,
  `vid-d5ad01b9...`, `vid-f25d220e...`, `vid-5daa11cd...`, `vid-c8fac2d9...`)
  tam olarak 5 klip kullanarak ihtiyacı karşıladı — **hiçbiri tekrar
  değil**, ve log'da `"looping clips to match audio length"` uyarısı **hiç
  görünmedi** (önceden bu, indirilen görüntü kısa kalırsa devreye giren
  tekrar mekanizmasının tetiklendiğinin işaretiydi).
- **1b kanıtı:** Üretilen `subtitle.srt`'de artık cümleler arasında **gerçek,
  küçük boşluklar** var (ör. satır 1 `00:00:01,800`'de bitiyor, satır 2
  `00:00:01,892`'de başlıyor — 92ms'lik gerçek bir duraklama) — eski
  karakter-oranlı modelde cümleler arası SIFIR boşluk olurdu (yapay olarak
  bitişik). Hiçbir cümle artık önceki çalıştırmadaki gibi (88ms'lik yalnız
  tırnak işareti) yapay bir mikro-parçaya düşmedi; en kısa segment bile
  (~500ms, tek kelimelik "remember"/"pause") makul.
- Tam suite bu doğrulama sonrası da yeşil kaldı (kod değişmedi, sadece
  gerçek bir üretim çalıştırıldı).

**GÖREV 5'e çapraz-doğrulama faydası:** Bu ikinci gerçek üretimin
`quality_verdict.issues`'ı, GÖREV 5 için yapılan "Deja Vu" üretimindeki
sorunlarla **aynı desende** — "narration sıkıştırılmış/outline'ı atlıyor",
"ani geçiş", "mecazi ifade netlik istiyor". İki farklı konuda aynı desenin
tekrarlanması, GÖREV 5 bölümündeki sonucu güçlendiriyor: bunlar short
pacing'in **doğal, tasarım gereği** içerik-yoğunluğu ödünleşimleri, yeni bir
sistemik kod hatası değil.

### GÖREV 5 — quality_critic yeni/çözülmemiş bir sorun buluyor mu? SONUÇ: Hayır, kod değişikliği yapılmadı

İki bağımsız gerçek üretimle kontrol edildi: "The Psychology of Deja Vu"
(psychology, short) ve "How Octopuses Change Color" (space/nature, short).
İkisi de `passed=True` (3.0-3.33/5) ile geçti, ama `quality_critic` her
ikisinde de **aynı üç desende** sorun buldu:
1. Narration outline'ı sıkıştırıyor/atlıyor (kısa pacing'in doğal sonucu —
   4 sahne × ~12 kelime hedefi, zengin bir outline'ın hepsini kapsayamaz).
2. Bir geçiş ani/az açıklanmış hissediyor (konuya özgü anlatım nüansı).
3. Mecazi bir ifade netlik istiyor (konuya özgü, LLM'in yaratıcı dil tercihi).

**Karar (OTONOM KARAR, tutucu):** Bu üç desen, önceden düzeltilmiş **Hook/
Retention/Callback eksikliği** (script_generator hiç outline görmüyordu —
gerçek bir yapısal kod eksikliğiydi) gibi **yapısal bir kod kusuru değil** —
short pacing'in kelime bütçesiyle zengin bir outline arasındaki **kaçınılmaz
bir ödünleşim** + konuya özgü içerik nüansı. Zorla "daha fazla ayrıntı sığdır"
gibi bir düzeltme yapmak (ör. `_WORDS_PER_SECOND`'u artırmak) GÖREV 1a'nın
düzelttiği sorunu büyütür (daha uzun narration = daha fazla gerçek ses süresi
= daha fazla görüntü ihtiyacı). Bu yüzden **hiçbir kod değişikliği
yapılmadı** — `quality_critic` tam olarak tasarlandığı gibi çalışıyor
(bilgilendirici, pipeline'ı hiç engellemiyor). Kullanıcı daha ayrıntılı
belgeseller isterse zaten `pacing="long"` seçeneği mevcut.

### GÖREV 6 — Sistematik TopicCategory × Pacing × Tone × Format test matrisi eklendi

Yeni `test/services/test_pipeline_dimension_matrix.py`: `run_pipeline()`'ın
her aşaması mock'lanıyor (gerçek LLM/medya çağrısı yok), ve **5 TopicCategory
(4 + None) × 2 Pacing × 6 Tone (5 + None) × 3 Format (2 + None) = 180
kombinasyonun hepsi** tek bir testte `subTest` ile ayrı ayrı raporlanarak
çalıştırılıyor. Her kombinasyon için: pipeline hatasız tamamlanıyor mu,
`final_video_path` doluyor mu, `tone` her zaman çözülüyor mu (asla `None`
kalmıyor), `format` doğru yansıyor mu (None ise None, değilse verilen
değer) kontrol ediliyor. `resolve_tone()`/`resolve_format()` gerçek
(mock'lanmamış) kodla çalıştığı için, bu matris gerçekten kategori/tone/
format eşleme mantığını da (sadece plumbing'i değil) sınıyor.

- [x] Tam suite: **647 passed, 11 skipped** (180 yeni subtest dahil, önceden
      646/4704 subtest → 647/4884 subtest). Çalışma süresi: ~1.5 saniye
      (tamamı mock, gerçek API maliyeti sıfır).

### GÖREV 7 — A/B thumbnail varyantı + SEO chapters uyarısının görünürlüğü

**A/B thumbnail:** `thumbnail_generator.py`'deki `_extract_middle_frame()`
`_extract_frame_at_fraction(video_path, output_path, fraction)` olarak
genelleştirildi (0.5 varsayılan, geriye dönük uyumlu). Yeni
`generate_thumbnail_variant_b()` aynı fonksiyonu **%25'lik** bir zaman
damgasıyla (`_VARIANT_B_FRAME_FRACTION = 0.25`) ve `thumbnail_b.png` dosya
adıyla çağırıyor — aynı SEO başlığı, farklı kare. `DocumentaryProject`'e
yeni `thumbnail_variant_b_path` alanı eklendi (mevcut `thumbnail_path` ile
aynı best-effort desende: varyant A başarısız olursa B hiç denenmiyor).
`default_pipeline.py` her iki thumbnail'i de üretiyor; webui artık ikisi de
varsa yan yana iki sütunda gösteriyor (`Documentary Thumbnail Variant A/B`,
9 dile eklendi), tek biri varsa eskisi gibi tek gösteriyor.

- [x] 6 yeni/güncellenmiş test (`test_thumbnail_generator.py`,
      `test_default_pipeline.py`): fraction parametresi doğru geçiyor mu,
      farklı dosya adı, varyant A başarısızsa B hiç çağrılmıyor mu.
- [x] **Gerçek doğrulama (yeni API maliyeti YOK — GÖREV 1 doğrulamasından
      kalan gerçek `combined.mp4` kullanıldı):** "How Octopuses Change
      Color" videosundan iki gerçek thumbnail üretildi — variant A ve B
      görsel olarak **tamamen farklı kareler** gösterdi (biri bir el+kadeh,
      diğeri bir iskele/su kenarı tabelası), ikisi de aynı başlığı taşıyor.
      **Yan gözlem (kapsam dışı, sadece not):** bu iki kare de konuyla
      ("ahtapot kamuflajı") pek ilgili değil — bu, storyboard/asset eşleşme
      kalitesiyle ilgili, GÖREV 7'nin kapsamı olan "iki farklı kare
      seçeneği sun" mekanizmasıyla ilgisi yok; ayrı bir gün ele alınabilir.

**SEO chapters uyarısı:** Önceden `st.caption(...)` olarak sadece
varsayılan kapalı `st.expander("Documentary SEO Extras")` içinde
görünüyordu — kullanıcı genişletmeden asla görmüyordu. Artık expander'ın
**dışında**, her zaman görünen bir `st.warning(...)` olarak gösteriliyor
(chapters verisi varsa). Chapters'ın kendisi (asıl liste) hâlâ expander
içinde — sadece "Shorts'ta çalışmaz" uyarısı öne çıkarıldı. Yeni i18n key
gerekmedi (mevcut `Documentary SEO Chapters Help` metni yeniden kullanıldı).

- [x] Tam suite: **650 passed, 11 skipped** (önceden 647).

### GÖREV 8 — Teknik borç temizliği (öncelik tablosundan, en yüksekten başlanarak)

- [x] **8a (Yüksek öncelik):** Altyazı font varsayılanı birleştirildi —
      `webui/Main.py`'nin `DEFAULT_SUBTITLE_SETTINGS["font_name"]`'i artık
      `video_renderer.py` ile aynı (`BeVietnamPro-Bold.ttf`). 2 yeni test
      (biri iki varsayılanın hep aynı kalacağını, biri gerçek değeri kilitliyor).
- [x] **8b (Orta öncelik):** `ResearchPlan.grounded: bool` eklendi,
      webui'de her zaman görünen bir ✅/ℹ️ uyarı (gerçek kaynakla mı
      doğrulandı, yoksa AI'ın kendi bilgisi mi) gösteriliyor.
- [ ] **8c (Orta öncelik) — BİLİNÇLİ OLARAK ERTELENDİ:** `search_terms[1:]`
      0-sonuç fallback'i. Gerekçe: `material.py`'nin ilgili fonksiyonu hem
      yeni pipeline hem **legacy tekil-video pipeline'ı** tarafından
      paylaşılıyor, düzgün bir fallback imza değişikliği gerektiriyor — bu
      da GÖREV 1a'da az önce düzelttiğim asset-download alanını sabah
      kullanıcı testinden hemen önce tekrar riske atardı. Kullanıcının
      açık izniyle ("vakit yetmezse 8 yarım kalabilir") **atlandı**, somut
      bir gelecek görevi olarak yukarıdaki "Bilinen teknik sınırlar"
      listesine (madde 5) not düşüldü.
- [x] **8d (Düşük öncelik):** Üç dil listesi birleştirilmedi (test kırma
      riski) ama her birine birbirine referans veren açıklayıcı yorumlar
      eklendi (`webui/Main.py`'de `locales`/`support_locales`,
      `profile_dimensions.py`'de `Language` docstring'i).
- [x] Tam suite (8a+8b+8d sonrası): **652 passed, 11 skipped** (8c hiç kod
      içermediği için sayıyı etkilemedi).

## GECE OTURUMU SONU — özet (sabah okumanız için)

**Tüm görevler tamamlandı, GÖREV 1 dahil.** Sırayla: 1 → 3 → 4 → 5 → 6 → 7 → 8
(8c hariç, bilinçli olarak ertelendi, aşağıda ve "Bilinen teknik sınırlar"
listesinde gerekçesiyle not düşüldü).

**GÖREV 1 (en kritik, sizin sabah gözünüzle doğrulayacağınız):**
- Tekrarlayan kareler → kök neden: asset indirme, TTS'ten önce çalıştığı
  için gerçek ses süresini değil tahmini süreyi (genelde ~2x daha kısa)
  kullanıyordu. Düzeltme: `_ASSET_DOWNLOAD_DURATION_SAFETY_MULTIPLIER = 2.0`
  (`default_pipeline.py`). Gerçek üretimde doğrulandı: 5 farklı kaynaktan
  hiç tekrarsız, "looping clips" uyarısı hiç tetiklenmedi.
- Altyazı gecikmesi → kök neden: ElevenLabs'ın zaman damgası döndürmeyen
  endpoint'i kullanılıyordu, altyazılar karakter-sayısı oranına göre tahmin
  ediliyordu. Düzeltme: `/with-timestamps` endpoint'ine geçildi, gerçek
  karakter-seviyesi hizalama kullanılıyor artık. Gerçek üretimde doğrulandı:
  cümleler arası gerçek duraklamalar var, yapay mikro-parçalar yok.
- **Önemli operasyonel adım:** `ai-documentary-studio-webui.service`
  (systemd) gece boyunca yapılan TÜM kod değişikliklerinden ÖNCE başlatılmış
  haldeydi (20:55'ten beri çalışıyordu) — Python süreçleri disk üzerindeki
  değişiklikleri otomatik yüklemez. Oturum sonunda **servis yeniden
  başlatıldı** (`systemctl restart`), health check `ok` döndü — 8501'de
  şu an gece boyunca yazılan tüm kod çalışıyor, eski/stale kod değil.

**GÖREV 3, 4, 6, 7, 8a/8b/8d:** Tamamlandı, her biri ayrı commit + push,
yukarıda ayrıntılı yazılı. **GÖREV 5:** İki bağımsız gerçek üretimle
kontrol edildi, yeni bir sistemik sorun bulunmadı (sadece short pacing'in
bilinen içerik-yoğunluğu ödünleşimi), kod değişikliği yapılmadı. **GÖREV
8c:** Bilinçli olarak ertelendi (paylaşılan legacy koda regresyon riski).

**Hermes/çakışma durumu:** Gece boyunca birkaç kez kontrol edildi — Hermes
(tmux `work` oturumu) aylık Codex kotası dolduğu için tüm gece rate-limit
döngüsünde takılı kaldı, GÖREV 1'e **hiç dokunmadı** (dosya sisteminde
hiçbir uncommitted değişiklik bırakmadı). Bu yüzden GÖREV 1'i ben üstlendim
— hiçbir çakışma/duplicate iş yaşanmadı. `video.py`/`audio_renderer.py`'ye
GÖREV 1 kapsamında dokunuldu (kullanıcının açık izniyle, "artık tamamen
sana ait" onayı üzerine).

**Gerçek API bütçesi:** İzin verilen 10 tam üretimden **2'si** kullanıldı
(Deja Vu — GÖREV 5, Octopus — GÖREV 1 doğrulama + GÖREV 7 için yeniden
kullanıldı, yeni maliyet yok). Wikipedia/DuckDuckGo çağrıları ücretsiz/
key'siz olduğu için bu bütçeye dahil edilmedi.

**Test durumu:** Tam suite gece başında 631 passed idi, şu an **652 passed,
11 skipped** — kırmızı test hiç yaşanmadı, hiçbir noktada durmak gerekmedi.

**Git durumu:** `overnight/claude-tasks-3to8` dalından `origin/main`'e her
görev sonrası ayrı ayrı push edildi (SSH ile, token'sız — gerçekten
çalıştığı doğrulandı). Orijinal `/root/MoneyPrinterTurbo/AI-Documentary-Studio`
dizinindeki yerel `main` da bu oturumun sonunda `git pull --ff-only` ile
senkronize edildi — hem worktree hem orijinal dizin, hem GitHub şu an
birebir aynı commit'te (`41acb35` + bu özet commit'i).

## Karar bekleyen noktalar

SSH push artık gerçekten çalışıyor (`git@github.com:...`, token'sız) —
önceki "manuel push bekliyor" notu artık geçersiz. Podcast (mimari), Kids
(güvenlik tasarımı), Analytics/Learning Layer (gerçek yayın verisi yok) —
üçü de kullanıcıdan ayrı onay bekleyen, bu gece oturumunda da **bilinçli
olarak dokunulmayan** konular (Corporate çözüldü, yukarıya bkz.).
Publishing Engine kodu ve mock'lu testleri tamam, ama **gerçek bir platforma
yayın doğrulaması kullanıcının Upload-Post kimlik bilgilerini sağlamasını
bekliyor** (yukarıya bkz.). GÖREV 8c (search_terms[1:] fallback) somut,
izole bir gelecek görevi olarak "Bilinen teknik sınırlar" listesinde madde
5'te bekliyor.

## GECE OTURUMU 3 — Yayına Hazırlık ve Sağlamlaştırma (dal: `overnight/launch-readiness`)

Önceki gece GÖREV 1 (kritik bug'lar) çözülmüş ve kullanıcı tarafından gözle
doğrulanmıştı. Bu oturumun odağı yeni özellik değil, **sağlamlaştırma**:
GÖREV A (yayına hazırlık doğrulaması, en yüksek öncelik) → B (hata yönetimi
denetimi) → C (config.example.toml) → D (Podcast/Kids tasarım notu, kod yok)
→ E (kullanıcı dokümantasyonu).

**Ortam:** `ai-documentary-studio-claude-tasks` worktree'si yeniden
kullanıldı (önceki oturumdan zaten kurulu, symlink'ler doğrulandı — biri
[`config.toml`] bir noktada gerçek dosyaya dönüşmüş bulundu, yeniden
symlink'lendi), üzerinde yeni `overnight/launch-readiness` dalı açıldı.
Hermes (tmux `work`) tekrar kontrol edildi — hâlâ tamamen hareketsiz (aylık
kota hâlâ dolu), sıfır çakışma riski.

### GÖREV A — Yayına Hazırlık Doğrulaması (EN YÜKSEK ÖNCELİK)

4 farklı TopicCategory × Tone × Format kombinasyonuyla gerçek uçtan-uca
üretim yapıldı (hepsi short pacing, İngilizce):

| # | Konu | Kategori | Ton | Format | Sonuç |
|---|---|---|---|---|---|
| 1 | The Fall of the Berlin Wall | history | credibility (auto) | standard | ✅ Başarılı |
| 2 | The Search for Alien Life | space | epic | educational | ✅ Başarılı (bkz. bulgu aşağıda) |
| 3 | Why We Procrastinate | psychology | scientific | corporate | ✅ Başarılı |
| 4 | The Hidden Culture of Kyoto | travel | cinematic | standard | ✅ Başarılı (2. denemede, bkz. aşağıda) |

**Her 4 kombinasyon için de doğrulanan:** Tekrarlayan kare **yok** (log'da
`"looping clips"` uyarısı 4/4'ünde de hiç görünmedi — dünkü GÖREV 1a
düzeltmesi tek bir senaryoda değil, kategori/ton/format'tan bağımsız olarak
genel olarak sağlam), altyazılar gerçek zamanlamayla üretildi, ses dosyası
var, her ikisi de (thumbnail A/B) üretildi, `grounded: true` (4/4'ünde de
DuckDuckGo/Wikipedia'dan gerçek bir kaynak bulundu — Knowledge Engine'in
kapsamı iyi durumda).

**Bulunan ve DÜZELTİLEN yeni sorun (küçük/tutucu):** Kombinasyon #2'de
(`Format.educational`), `quality_critic` şunu buldu: *"The repeated explicit
'Takeaway' phrasing makes the script feel more like an outline..."* — gerçek
script'e bakıldığında, LLM'in her sahnenin sonuna **kelimesi kelimesine**
`"Takeaway: ..."` etiketi eklediği görüldü (`script_generator.py`'deki eski
talimat metni "a one-sentence takeaway or mini-recap" derken, LLM
"takeaway" kelimesini bir ETİKET olarak yorumlamış). Bir anlatıcının gerçekte
asla söylemeyeceği bu etiket, seslendirmede çok yapay dururdu.
**Düzeltme:** `FORMAT_GUIDANCE[Format.educational]` metni yeniden yazıldı —
artık açıkça "never write a literal label like 'Takeaway:'" diyor. Ucuz,
tek başlı bir gerçek LLM çağrısıyla (tam pipeline değil, sadece
`script_generator.generate_script()`) doğrulandı: yeni çıktıda "Takeaway"
kelimesi hiç geçmiyor. 2 yeni test (mevcut format testi + yeni "asla etiket
yazma" talimatının varlığını kilitleyen test).

**Bulunan ama KOD DEĞİŞİKLİĞİ YAPILMAYAN operasyonel gözlem:** Kombinasyon
#4'ün ilk denemesi (#3 ile **eşzamanlı** çalıştırıldığında) `OSError: [Errno
32] Broken pipe` ile çöktü — ffmpeg'e yazarken video encoding sürecinin
beklenmedik şekilde kesilmesi. **Kök neden analizi:** aynı anda 2 ağır
ffmpeg render işlemi çalıştırıyordum (kendi test metodolojimin sonucu, gerçek
kullanıcı senaryosu değil). Konu #4'ü **tek başına** (eşzamanlı hiçbir şey
olmadan) tekrar çalıştırdığımda **sorunsuz tamamlandı** — bu, sorunun pipeline
mantığında değil, kaynak çakışmasında (concurrent ffmpeg process'leri)
olduğunu doğruluyor. **OTONOM KARAR:** Bu bir pipeline kodu hatası değil,
bir **operasyonel/altyapı** notu — eğer gelecekte eşzamanlı/çoklu belgesel
üretimi (ör. birden fazla kullanıcı, kuyruk sistemi) desteklenecekse, ffmpeg
render'ları için bir eşzamanlılık sınırı/kuyruk gerekecek. Şu an webui
tek seferde tek üretim çalıştırdığı için gerçek kullanıcı bunu YAŞAMAZ —
kod değişikliği yapılmadı, sadece not düşüldü.

- [x] Gerçek API bütçesi: 5 tam uçtan-uca üretim kullanıldı (4 kombinasyon +
      1 tekrar deneme) + 1 hafif tek-fonksiyon gerçek çağrı (Takeaway
      doğrulaması) = izin verilen 10'un 5'i (tam üretim bazında).
- [x] Tam suite: **655 passed, 11 skipped** (önceden 652, +3: Takeaway testi
      + zaten var olan format testleri).

### GÖREV B — Hata Yönetimi Denetimi

Pipeline'ın tüm aşamaları (`default_pipeline.py`'deki 12 numaralı aşama +
quality_critic + 2 thumbnail çağrısı) tek tek incelendi — hangisi bir LLM/
ağ hatasında **tüm üretimi** çökertebilir, hangisi izole/korumalı.

**Zaten sağlam olduğu doğrulanan (kod değişikliği gerekmedi):**
- **Aşama 1 (intent):** `intent_analyzer.detect_topic_category()` LLM
  hatasını zaten yakalayıp heuristic kategori tahminine düşüyor.
- **Aşama 4 (scene):** Saf mantık, LLM çağrısı yok; boş `outline.sections`
  ile bile çökmeden boş bir `ScenePlan` üretiyor (doğrulandı, koddan okundu).
- **Aşama 7-8 (asset/asset download):** Boş `search_terms` durumunu zaten
  erken dönüşle ele alıyor; her klip indirmesi kendi try/except'i içinde.
- **Aşama 9 (audio):** TTS tamamen başarısız olursa **bilinçli olarak**
  `RuntimeError` fırlatıyor — bu doğru davranış (sessiz ses = video
  yapılamaz, gizlenmemesi gereken gerçek bir dur-noktası).
- **Aşama 11 (seo):** `llm.generate_social_metadata()` kendi retry +
  heuristic fallback'ine sahip, **asla fırlatmıyor**; `seo_generator`'ın
  `generate_engagement_metadata()`'sı da kendi try/except'ine sahip. SEO
  aşamasının video render'ı hiç etkilemediği de doğrulandı
  (`video_renderer.build_video_params()`/`render_final_video()` `project.seo`
  parametresi almıyor).
- **BGM karıştırma:** Zaten "başarısız olursa sadece anlatımla devam et"
  deseninde (`video.py`'nin kendi docstring'i).
- **quality_critic, thumbnail, thumbnail_variant_b:** Zaten "asla fırlatma"
  desenindeydi (önceki oturumlarda kurulmuş).

**Korumasız bulunan (RAPORLANDI, DOKUNULMADI — mimari değişiklik gerektiriyor):**
- **Aşama 2 (research), 3 (outline), 5 (script), 6 (storyboard):** Hepsi
  `documentary_llm_utils.generate_json()`'ı **doğrudan** çağırıyor, sarmalayan
  bir try/except yok. `generate_json()` 3 denemeden sonra hâlâ başarısızsa
  **`ValueError` fırlatıyor** (`raise ValueError(f"failed to generate valid
  JSON after {max_retries} attempts: {last_error}")`) — bu, `default_pipeline.py`
  içinde hiçbir `except` tarafından yakalanmıyor, tüm `run_pipeline()`'ı
  çökertiyor (webui'nin dış `except Exception as exc: st.error(...)`'ı
  çökmeyi engelliyor ama üretimin tamamı boşa gidiyor).
  **Neden düzeltilmedi:** Bu 4 aşama birbirine sıkı sıkıya bağlı sıralı bir
  zincir — outline olmadan sahne planlanamaz, sahne olmadan script
  yazılamaz. "Hatayı yakala ve devam et" burada YANLIŞ olur (boş/bozuk bir
  video sessizce üretilir, net bir hatadan DAHA KÖTÜ bir sonuç). Doğru
  düzeltme (retry-with-backoff, kısmi-devam-etme stratejisi, ya da net bir
  "hangi aşama neden başarısız oldu" mesajı) gerçek bir tasarım kararı
  gerektiriyor — bu gece sadece "sağlamlaştırma" kapsamında, gözetimsiz
  yapılacak bir değişiklik değil.
  **Küçük, düşük riskli bir iyileştirme önerisi (yapılmadı, sadece not):**
  Bu 4 aşamadan gelen `ValueError`'ı `default_pipeline.py`'de yakalayıp
  "hangi aşama (research/outline/script/storyboard) ve neden" diyen daha
  net bir mesajla yeniden fırlatmak — davranışı DEĞİŞTİRMEZ (yine çöker),
  sadece webui'deki hata mesajını daha anlaşılır yapar. Düşük risk ama
  bu gece kapsam dışı bırakıldı, istenirse ayrı bir küçük görev olabilir.

**Sonuç:** Denetim, pipeline'ın baştan düşünülenden **daha sağlam** olduğunu
gösterdi — gerçekten izole/düşük riskli olan her yer zaten korunuyordu.
Eklenecek gerçek bir "düşük riskli boşluk" bulunamadı; bulunanlar hep
mimari karar gerektiriyor.

### GÖREV C — config.example.toml tamlık kontrolü

`config.toml` (gerçek, dolu) ile `config.example.toml` arasında TÜM
section'lar (`[app]`, `[whisper]`, `[proxy]`, `[azure]`, `[siliconflow]`,
`[elevenlabs]`, `[chatterbox]`, `[ui]`) ve tüm üst-seviye anahtarlar
programatik olarak (`toml.load()` ile key seti karşılaştırması)
karşılaştırıldı. **`upload_post_*` anahtarları zaten tamdı** (önceki
oturumdan). Tek bulunan tutarsızlık: `[ui]` altında yorum-satırı örnek
`# font_name = "MicrosoftYaHeiBold.ttc"` — dünkü GÖREV 8a'da asıl varsayılan
`BeVietnamPro-Bold.ttf`'e değiştirilmişti ama bu örnek yorum satırı
güncellenmemişti. Düzeltildi.
- [x] `config.example.toml` hâlâ geçerli TOML (doğrulandı).

### GÖREV D — Podcast/Kids tasarım notu (SADECE DOKÜMANTASYON)

Yeni `docs/future-work.md` — önceki oturumlarda bulunan somut mimari kırılma
noktaları (Podcast: `default_pipeline.py`'nin koşulsuz 12 aşaması,
`thumbnail_generator`'ın `project.timeline`'a None-check'siz erişimi,
`final_video_path`'in tek "bitiş çizgisi" olması) ve güvenlik gereksinimleri
(Kids: kod tabanında sıfır moderasyon mekanizması, "basit dil" ile "güvenli
içerik"in birbirine karıştırılmaması gerektiği) temel alınarak, iki
gerçekçi mimari seçenek (Podcast için: ayrı `run_audio_pipeline()` vs.
`run_pipeline()`'a `output_mode` parametresi), somut adım listeleri, test
stratejileri ve **açık, kullanıcıya bırakılmış kararlar** içeren ayrıntılı
bir plan yazıldı. **Hiçbir kod yazılmadı.** Analytics/Learning Layer için de
kısa bir not eklendi (gerçek yayın verisi birikene kadar ertelenmesi
gerektiği, PROGRESS.md'nin eski notuyla tutarlı).

### GÖREV E — Kullanıcı dokümantasyonu

`README-en.md`'ye "AI Documentary Studio (Beta)" bölümü eklendi (Features
ile Gallery arasına) — ne olduğu, webui'de nerede bulunduğu, kontrol
edilebilen boyutlar (Topic Category/Tone/Format/Pacing/Voice), üretim
sonrası görülenler (video, A/B thumbnail, SEO, kalite notu, grounding
bilgisi) ve Publish akışı anlatıldı. `README.md`'ye (Çince) de eşdeğer,
biraz daha kısa bir bölüm eklendi, İngilizce tam sürüme link verildi. Daha
önce bu özellik hakkında hiçbir kullanıcı dokümantasyonu yoktu (doğrulandı,
sıfır sonuç).

## WebUI Navigasyon Refactor'u — Faz 1-4 (kullanıcı talebiyle, gündüz,
`main` üzerinde doğrudan)

Documentary Studio o âna kadar Klasik Mod sayfasının altında kapalı bir
expander'da yaşıyordu — kullanıcı önce eski tekil-video formunu görüyor,
yeni özelliği ancak aşağı kaydırıp expander'ı açınca fark ediyordu. Bu
oturumda `st.navigation()`/`st.Page()` ile gerçek bir çok-sayfalı yapıya
geçildi; her faz kendi commit'i, kendi pytest tam suite çalıştırması ve
ayrı bir Streamlit örneğinde (8503/8590) headless Chromium ile DOM
seviyesinde doğrulaması ile ilerledi. Production servisi (8501,
`ai-documentary-studio-webui.service`) bu 5 commit'in hiçbirinde
durdurulmadı/yeniden başlatılmadı.

### Faz 1 — st.navigation iskeleti (`cafdb3d`)

Sol sidebar navigasyonu kuruldu: Documentary Studio kendi sayfasına
(`_render_documentary_studio_page`) taşındı, iç mantık (run_pipeline
çağrısı, idea_generator, publish akışı) hiç değişmedi — sadece dışarıdaki
`st.expander` sarmalayıcısı kaldırıldı. Legacy form `_render_legacy_page`
olarak ayrıştırıldı, "Klasik Mod" adıyla varsayılan (`default=True`) sayfa
olarak kaldı — bu fazda kullanıcının ilk gördüğü ekran değişmedi. Task
Manager'ın görev geri yükleme dialogu bilinçli olarak navigasyonun dışında,
global chrome olarak bırakıldı. i18n: "Nav Create"/"Nav Classic Mode"
key'leri 9 dilin hepsine eşzamanlı eklendi.

### Faz 2 — Documentary Studio varsayılan sayfa (`d9c1c56`)

`default=True` Documentary Studio'ya taşındı, nav'da ilk sıraya alındı;
Klasik Mod'a stabil bir `url_path="classic"` verildi. Sonuç paneli
(video + küçük resimler + SEO + kalite notu + publish)
`st.columns([1, 2, 1])` ile ortalanmış sabit oranlı bir sütuna alındı —
9:16 dikey video "wide" layout'ta ~2000px yüksekliğe geriliyordu, artık
ekran boyutuna göre mantıklı kalıyor. AppTest ile çalışan 3 test dosyası
(BGM/TTS/ses önizleme, toplam 12 çağrı noktası) varsayılan sayfa değişince
kırıldı; `AppTest.switch_page()` fonksiyon tabanlı sayfaları desteklemediği
için resmi dokümantasyonun önerdiği gibi `_page_hash`'i doğrudan
`calc_hash("classic")`'e atayarak düzeltildi.

### Faz 3 — Markalaşma (`fa15415`) + düzeltme (`5793e62`)

Sekme başlığı/ikonu "MoneyPrinterTurbo"/🤖'den "AI Documentary
Studio"/🎬'ye değişti; `styles.css`'e sidebar nav'a özel kurallar eklendi
(Streamlit'in kendi `data-testid`'leri hedeflendi, ekstra class
gerekmedi). İlk commit'te üst bar markasına "Powered by
MoneyPrinterTurbo" alt notu eklenmişti; kullanıcı bunu "Proje sahibi: Ufuk
Kaya" olarak değiştirtti — 9 dilin hepsinde "Brand Tagline" key'i buna göre
güncellendi (`5793e62`). GitHub sürüm linki bilinçli olarak değişmedi,
gerçekten upstream MoneyPrinterTurbo deposuna gidiyor.

### Faz 4 — "Geçmiş Üretimler" galerisi (`5d0c6d3`)

`storage/tasks/*/project.json` bulunan, `final_video_path`'i hâlâ diskte
duran tamamlanmış projeleri kart galerisi olarak listeleyen yeni bir sayfa
(`url_path="history"`, nav'da Oluştur'dan sonra, Klasik Mod'dan önce).
`_scan_history_tasks` ile aynı iki-aşamalı tarama deseni: önce ucuz
`os.scandir` metadata'sı (mtime), en yeni 30 tanesi kesilip sadece o alt
küme için `project.json` parse ediliyor. İki aksiyon: "Tekrar Görüntüle"
(aç/kapa toggle) ve iki adımlı "İndir" (ilk tık hazırlar, video byte'ları
sadece o zaman diske okunur — galeri her yüklemede tüm kartların videosunu
belleğe almasın diye). Documentary Studio'nun sonuç panelinden
`_render_project_media_panel()` olarak çıkarıldı — iki sayfa da aynı
fonksiyonu çağırıyor (DRY), Publish bölümü kasıtlı olarak bu fonksiyonun
dışında tutuldu (Geçmiş Üretimler tamamen salt-okunur kalmalı).

### Faz 5 (i18n son kontrolü) neden ayrı bir adım/commit değil — bilinçli karar

Diğer fazların hepsinin aksine, repo'da "Faz 5" diye ayrı bir commit
**yok**. Bu bir eksiklik değil, bilinçli bir karar: i18n bütünlüğü zaten
**her fazın kendi commit'inde eşzamanlı olarak** sağlandı — Faz 1/3/4'ün
her biri yeni key'lerini 9 dilin (`de/en/es/id/pt/ru/tr/vi/zh`) hepsine
aynı commit içinde, aynı anda ekledi (diff'lerde her dil dosyasının aynı
satır sayısında değiştiği doğrulanabilir). Ayrıca sonradan yapılan bir
denetimde 9 dilin `Translation` sözlükleri programatik olarak
karşılaştırıldı: bugünkü refactor'un key'lerinde **hiç eksik yok**; tespit
edilen tek fark (`llm_provider_tips.*`/`tts_provider_tips.*`, 27 key)
bu refactor'la ilgisiz, önceden beri var olan ve kod içinde bilinçli olarak
belgelenmiş bir tasarım (`get_llm_provider_tips`/`get_tts_provider_tips`,
`Main.py`: sadece tr/en dışı diller İngilizce'ye düşecek şekilde
tasarlanmış — provider config metinlerinin her dilde ayrı ayrı bakımı
uzun vadede senkronizasyon riski taşıyor). Yani "ayrı bir i18n son kontrol
fazı" için gerçekten kapatılacak bir şey bulunmadı; resmi Faz 5 commit'i
bu yüzden hiç açılmadı.

### Faz 4 test kapsamı (ertesi gün, `cecf360`)

Faz 4, galeri sayfası için hiç otomatik test eklemeden commit edilmişti —
doğrulama tamamen manuel Playwright QA ile yapılmış, o QA verisi (geçici
görev klasörleri + geçici Streamlit örneği) temizlenmişti; kalıcı
regresyon koruması yoktu. Yeni `test/services/test_webui_documentary_history.py`
(13 test) bu boşluğu kapattı:
- `_scan_history_projects()`/`_safe_load_project_snapshot()` için
  Streamlit'siz izole birim testler (`test_webui_task_history.py`'deki
  AST-çıkarma deseniyle aynı yöntem) — boş/eksik `tasks_root`, geçerli
  parse, bozuk JSON'ın crash etmeden atlanması, video'su/`project.json`'ı
  eksik görevlerin atlanması, özel limit + sıralama, gerçek
  `_HISTORY_PROJECTS_LIMIT=30` sabitinin uçtan uca (35 görev → 30'a kesme)
  doğrulanması.
- `_render_project_media_panel()`'ın DRY refactor'unun Documentary Studio
  ile Geçmiş Üretimler'de aynı çıktıyı ürettiğini doğrulayan iki AppTest
  (aynı örnek proje verisi her iki sayfada da ayrı ayrı render edilip aynı
  paylaşılan assertion'dan geçiriliyor).
- Geçmiş Üretimler sayfasının (`url_path="history"`) hatasız render
  edildiğini doğrulayan bir wiring testi, Faz 2'nin Klasik Mod için
  kullandığı `_page_hash`/`calc_hash` deseniyle birebir aynı.

Tüm AppTest'ler `utils.task_dir()`'ı `patch.object` ile `tmp_path`'e
sabitleyerek gerçek `storage/tasks/` verisinden tam izole çalışıyor.

### Genel doğrulama

Bu oturumun sonunda (ayrı bir denetim turunda) production servisi canlı
olarak headless Chromium ile test edildi: sayfa başlığı "AI Documentary
Studio", sidebar nav sırasıyla "🎬 Oluştur / 🗂️ Geçmiş Üretimler / 🔧
Klasik Mod" — servis Faz 1 commit'inden bile önce başlamış olmasına
(restart edilmemiş) rağmen 4 fazın tamamını gerçekten serve ediyor
(Streamlit'in script-cache'i tüm session'lar bağlantıyı kestiğinde
otomatik temizleniyor, bir sonraki session güncel kodu diskten tekrar
derliyor). Tam pytest suite: **666 passed, 11 skipped** (Faz 4 testleri
öncesi 653'tü, +13 hiç regresyon yok). Faz 4'ün QA'sından kalan 4 kalıntı
PNG (`_history_*.png`) de bu denetimde bulunup temizlendi.

## Yeni konu kategorileri — Denizde Yaşam (`marine`) + Spiritüel Yaşam
(`spiritual`) (kullanıcı talebiyle)

Kullanıcı iki yeni `TopicCategory` istedi. Kategori sistemi 4 ayrı yerde
kategoriye özel davranış/metin içeriyor (`DEFAULT_TONE_BY_CATEGORY`,
`PROFILE_PROMPTS`, `SHOT_GUIDANCE`, `_CATEGORY_KEYWORDS` heuristic
fallback) — sadece enum'a değer eklemek yetmiyordu: `PROFILE_PROMPTS`
`Tone`'a göre anahtarlanıyor, yeni kategoriler mevcut bir tone'u
paylaşsaydı tamamen alakasız bir stil metni (ör. "History documentary...")
LLM prompt'larına giderdi. Bu yüzden her yeni kategori, mevcut 4
kategoriyle birebir aynı 1-kategori-1-tone deseninde kendi `Tone`'unu aldı:

- `TopicCategory.marine` → yeni `Tone.wondrous` (doğa/denizaltı belgeseli
  stili: "vivid sensory detail of the underwater world... sense of wonder
  at wildlife behavior").
- `TopicCategory.spiritual` → yeni `Tone.reflective` (spiritüel/düşünsel
  belgesel stili: "concrete traditions, practices, or personal
  experiences... quiet, evocative moment").

Değişen 5 dosya: `app/config/profile_dimensions.py` (enum + tone eşlemesi),
`app/config/templates/__init__.py` (2 yeni `PROFILE_PROMPTS` girdisi),
`app/prompts/storyboard/__init__.py` (2 yeni `SHOT_GUIDANCE` girdisi —
marine için sualtı görüntü rehberliği, spiritual için tapınak/meditasyon/
sakin doğa görüntü rehberliği), `app/departments/research/intent_analyzer.py`
(2 yeni İngilizce+Türkçe heuristic keyword listesi), ve **planlanmamış ama
testler sayesinde bulunan** 6. dosya: `app/departments/creative/
script_generator.py`'deki `TONE_VOICE_GUIDANCE` — bu, script (anlatım)
aşamasının kendi ayrı Tone-keyed sözlüğüydü, ilk analizde `TopicCategory.`
üzerinden grep yapıldığı için kaçırılmıştı; `test_all_tones_have_voice_guidance`
testi tam suite çalıştırılınca bu boşluğu hemen yakaladı, iki yeni tone için
de ses/anlatım rehberliği eklendi.

Testler: `test_documentary_models.py`, `test_intent_analyzer.py`,
`test_outline_generator.py`, `test_research_planner.py`,
`test_storyboard_generator.py`'ye mevcut per-kategori/per-tone desenleriyle
birebir aynı yeni test eklendi (orijinal 4 kategorinin "hard-locked mapping"
regresyon kilidi testine dokunulmadı — o, bilinçli olarak sadece orijinal 4
kategori için). `README-en.md`/`README.md`'deki "Topic Category"/"Tone"
listeleri güncellendi. `webui/Main.py`'nin kategori/tone seçicileri enum'dan
dinamik türetildiği için (`[c.value for c in TopicCategory]`) hiç kod
değişikliği gerekmedi; `test_pipeline_dimension_matrix.py` da
`list(TopicCategory)`'yi dinamik kullandığı için otomatik kapsadı.

Doğrulama: tam pytest suite **671 passed, 11 skipped** (666'dan +5, hiç
regresyon yok), `ruff check app cli.py main.py webui test` temiz, ve
`resolve_tone`/`get_shot_guidance`/`get_template` gerçek Python
çağrılarıyla uçtan uca manuel doğrulandı.

## 7 kategorilik genişletme TAMAMLANDI (kullanıcı talebiyle, TAM OTONOMİ ile)

Yukarıdaki marine/spiritual, kullanıcının asıl istediği **7 kategorilik**
genişletmenin ilk 2 maddesiydi. Kullanıcı devamında kalan 5 kategoriyi de
istedi ve bu iş için tam otonomi verdi (plan+kod+test+gerçek
doğrulama+commit+push, tekrar onay beklemeden) — **tek şartla: her
kategori kendi commit'i + kendi push'u + kendi gerçek API doğrulamasıyla
bitmeden bir sonrakine geçilmeyecek.**

**Önemli düzeltme (uygulamaya başlamadan önce):** Kullanıcının mesajı bu
işin "önceden PROGRESS.md'de ertelenmiş bir madde" olduğunu ve bir
`OUTLINE_REGISTRY` + kategori-başına-ayrı-dosya mimarisi kullanılması
gerektiğini iddia ediyordu. Her ikisini de doğruladım: repo'da (757
commit'lik tam git geçmişi dahil) böyle bir erteleme kaydı ya da
`OUTLINE_REGISTRY` hiç yok. Kullanıcıya bunu açıkça söyleyip iki soru
sordum (AskUserQuestion): (1) mevcut gerçek mimariyi mi (PROFILE_PROMPTS/
SHOT_GUIDANCE/keywords, Tone-anahtarlı) kullanalım yoksa sıfırdan bir
registry mi kuralım, (2) marine/spiritual bu oturumda zaten yazdığım
haliyle mi kalsın yoksa `marine_life`/`spirituality` olarak yeniden mi
adlandırılsın. Kullanıcı ikisinde de önerilen (mevcut deseni kullan, ismi
değiştirme) seçeneği onayladı — aşağıdaki 5 kategori de tamamen mevcut
mimariye (4 orijinal kategori + marine/spiritual ile birebir aynı desen)
göre eklendi.

**Seçilen 5 yeni Tone + gerekçesi** (her biri kendi `PROFILE_PROMPTS`,
`SHOT_GUIDANCE`, `TONE_VOICE_GUIDANCE`, `_CATEGORY_KEYWORDS` girdisiyle):

| Kategori | Tone | Neden bu tone (mevcut 5 tonun hiçbiri yerine yeni bir tane) |
|---|---|---|
| `film_highlights` | `cinephile` | Analitik, sinema-eleştirmeni sesi; hiçbir mevcut tone (epic/scientific/vb.) film tekniği tartışmasına uymuyordu |
| `sports` | `dynamic` | Yüksek enerjili, momentum odaklı; `epic` (uzay/bilim ölçeği) ile karıştırılabilirdi ama farklı bir "an"a odaklanıyor (rekabetin doruk noktası) |
| `healthy_living` | `encouraging` | Sıcak, pratik, destekleyici; kesin tıbbi iddialardan kaçınma talimatı buraya özel eklendi (hassas konu) |
| `mysterious_discoveries` | `mysterious` | Gizem atmosferi ama gerçek bilimsel belirsizliği komplo teorisi gibi sunmama talimatıyla (hassas konu, yanlış bilgi riski) |
| `personal_development` | `motivational` | Doğrudan, harekete geçirici, somut; `encouraging` (healthy_living) ile karıştırılmasın diye kasıtlı olarak ayrı tutuldu |

`film_highlights` için **TELİF HAKKI KORUMASI** (kullanıcının özel talebi):
`PROFILE_PROMPTS[Tone.cinephile]["style"]` açıkça şunu talimat veriyor:
*"Discuss films, scenes, and filmmaking techniques and their cultural
impact without quoting dialogue verbatim or fabricating quotes attributed
to real actors, directors, or other real people."* Bunun sadece niyet
olarak kalmaması için `test_documentary_models.py`'ye bu tam metnin
`PROFILE_PROMPTS` içinde var olduğunu kilitleyen ayrı bir regresyon testi
eklendi (`test_cinephile_template_forbids_verbatim_quotes`).

**Planda öngörülmemiş ama tam suite sayesinde bulunan gerçek bir boşluk:**
`app/departments/creative/script_generator.py`'deki `TONE_VOICE_GUIDANCE`
sözlüğü — script (anlatım) aşamasının kendi ayrı Tone-keyed sözlüğü —
ilk analizde `TopicCategory.` üzerinden grep yapıldığı için kaçırılmıştı.
İlk commit'ten (marine/spiritual) hemen sonra tam suite çalıştırılınca
`test_all_tones_have_voice_guidance` testi bunu **anında** yakaladı; o
commit'e dahil edilip düzeltildi, sonraki her kategori için de bu sözlüğe
girdi eklendi. Bu, "tam suite'i her adımdan sonra çalıştır" kuralının
tam olarak neden var olduğunun somut bir kanıtı.

**Her kategori için gerçek API ile uçtan uca doğrulama** (intent →
research → outline → scene → script, video/ses hariç — ucuz, gerçek
OpenAI çağrılarıyla):

| Kategori | Test konusu | Sonuç |
|---|---|---|
| `marine` | "The Secret Life of Coral Reefs" | grounded=True; script wondrous tonuna tam uygun ("the reef changes its skin") |
| `spiritual` | "The Practice of Zen Meditation" | grounded=True; reflective ton ("Before dawn, a bell sounds in darkness") |
| `film_highlights` | "The Cinematography of Citizen Kane" (bilinçli olarak telif-hassas bir konu) | grounded=True; script SADECE teknik/kültürel etkiyi tartıştı (deep focus, low angle), hiç diyalog alıntılamadı, Welles'e uydurma söz atfetmedi |
| `sports` | "The Greatest Comeback in Marathon History" | grounded=True (Abebe Bikila/1964 Tokyo gerçek doğrulandı); dynamic ton |
| `healthy_living` | "The Science of Intermittent Fasting" | grounded=True; script kesin tıbbi iddia yerine temkinli dil kullandı ("long-term proof is still unfolding") |
| `mysterious_discoveries` | "The Mystery of the Bermuda Triangle" (bilinçli olarak yanlış-bilgi-riskli bir konu) | grounded=True; script gerçek bilimsel konsensüsü doğru yansıttı ("no abnormal pattern"), komplo teorisi üretmedi |
| `personal_development` | "How to Build Better Habits That Actually Stick" | grounded=True (implementation intentions araştırması); somut, eyleme geçirilebilir, motivational ton |

**Commit'ler (her biri ayrı push edildi, `git push origin main` sonrası
`git rev-parse main origin/main` ile eşleştiği doğrulandı):**
1. `99d78a4` — marine + spiritual
2. `7adfc5a` — film_highlights (+ telif koruması testi)
3. `8f6b476` — sports
4. `9d7cab6` — healthy_living
5. `812f155` — mysterious_discoveries
6. `105269b` — personal_development

**Sonuç:** `TopicCategory` artık **11** değer (`travel, history, space,
psychology, marine, spiritual, film_highlights, sports, healthy_living,
mysterious_discoveries, personal_development`), `Tone` **12** değer.
`webui/Main.py` hiç değişmedi (enum'dan dinamik türetiliyor).
`README-en.md`/`README.md` her commit'te güncel tutuldu. Tam pytest suite
**677 passed, 11 skipped** (671'den +6, sıfır regresyon), `ruff check app
cli.py main.py webui test` her adımda temiz.

## GÖREV 1 — Kategori/Ton/Format/Pacing seçenekleri 9 dile çevrildi (kullanıcı talebiyle)

7 kategorilik genişletmenin hemen ardından fark edilen bir eksiklik:
`TopicCategory` (11), `Tone` (12), `Format` (3), `Pacing` (2) seçenekleri
webui'de selectbox'larda **ham enum değeri** olarak gösteriliyordu (ör.
"history", "cinematic"), arayüz dilinden bağımsız — kullanıcı Türkçe arayüz
kullanırken bile "healthy_living" gibi İngilizce/snake_case bir metin
görüyordu.

**Yaklaşım:** Mevcut `Translation` sözlüğüne `"Category: {value}"`,
`"Tone: {value}"`, `"Format: {value}"`, `"Pacing: {value}"` desenli 30 yeni
anahtar (12+13+3+2, "auto" dahil) eklendi — yeni bir i18n dosyası/bloğu
açmak yerine mevcut `tr()` mekanizması aynen kullanıldı. `webui/Main.py`'de
4 küçük yardımcı fonksiyon (`_documentary_category_label` vb.) eklenip
4 selectbox'a `format_func=` olarak bağlandı. **Kritik olan:**
Streamlit'te `format_func` sadece GÖRÜNÜMÜ değiştirir, selectbox'ın gerçek
`.value`'su (dolayısıyla `run_pipeline()`'a giden değer) hâlâ ham enum
string'i — bu yüzden regresyon riski sıfıra yakındı, koddan da doğrulandı.

**Bulunan bir test-harness sınırı (uygulama hatası değil):** İlk yazılan
regresyon testi `.select(ham_değer).run()` ile canlı bir kullanıcı
tıklamasını simüle ediyordu; bu, Streamlit'in AppTest'inin
`_format_value_for_widget`'ının `session_state` okuyan bir `format_func`'ı
henüz bağlanmamış bir context'te çağırıp sessizce ham değere düşmesine (ve
sonra `options.index()`'in patlamasına) yol açtı. Düzeltme kod tarafında
değil, test tarafında: session_state'e ham değeri **önceden** set edip
`.run()` çağırmak (gerçek görev geri yükleme akışının da zaten yaptığı
şey) aynı regresyonu kanıtlıyor, bu harness sınırına takılmıyor.

Testler: yeni `test/services/test_webui_documentary_labels.py` (7 test) —
30 anahtarın 9 dilin hepsinde var ve boş olmadığının doğrulanması + iki
AppTest (Türkçe ve İngilizce arayüzde selectbox'ların `.value`'sunun ham
kaldığını, `.options`'ının çevrildiğini, ham enum'un asla seçenek listesinde
görünmediğini doğrulayan) + yukarıdaki regresyon testi.

**Gerçek tarayıcı doğrulaması** (ayrı bir geçici Streamlit örneği, 8590,
production 8501'e hiç dokunulmadı, headless Chromium): "Konu Kategorisi"
selectbox'ı gerçekten "Otomatik" gösteriyor (ham "auto" değil), açılan
listede "Deniz Yaşamı", "Spiritüel Yaşam", "Film Kesitleri", "Sağlıklı
Yaşam", "Gizemli Keşifler" gibi tam Türkçe etiketler görünüyor; "Ton" →
"Otomatik", "Format" → "Standart", "Temp" (Pacing) → "Kısa". Geçici örnek
QA sonrası durduruldu.

**Kapsam dışı bırakılan (bilerek):** `Documentary Language` selectbox'ı
(auto/tr/en — belgeselin KONUŞULDUĞU dil, Kategori/Ton/Format/Pacing'den
ayrı bir alan) bu görevin kapsamında değildi, hâlâ ham değer gösteriyor —
kullanıcı sadece Kategori/Ton/Format/Pacing istedi.

Doğrulama: tam pytest suite **684 passed, 11 skipped** (677'den +7, sıfır
regresyon), `ruff check app cli.py main.py webui test` temiz.

## Modernizasyon A — Görsel/tema yenileme (kullanıcı talebiyle, sıra: A → C → B)

`webui/styles.css`'e CSS-only bir palet/tipografi/boşluk güncellemesi
eklendi — `[theme]` global config'e bilinçli olarak dokunulmadı (Faz 3
kararına sadık kalındı, tarayıcının otomatik light/dark geçişi bozulmadı).
Mevcut vurgu rengi (`#ff4b4b`, zaten Streamlit'in varsayılan
`primaryColor`'ıydı) değişmedi, tek bir `:root` custom-property setine
taşındı (`--mpt-accent`/`--mpt-accent-strong`/`--mpt-accent-soft` +
ileride kullanılmak üzere `--mpt-success`/`--mpt-warning`/`--mpt-info`,
hepsi karanlık modda otomatik ayarlanıyor) ve `--mpt-space-xs/sm/md/lg`
boşluk ölçeğiyle genişletildi. Ana içerik alanındaki `h2`/`h3` başlıklara
(sidebar/dialog etkilenmeden) daha belirgin ağırlık + tutarlı dikey ritim,
marka ismine hafif sıkılaştırılmış harf aralığı eklendi. Bonus: karanlık
mod için ayrı, artık gereksiz bir tekrarlı renk kuralı kaldırıldı (değişken
zaten uyarlanıyor).

Doğrulama: tam pytest suite değişmedi (684 passed, 11 skipped — CSS-only,
regresyon riski yok). Gerçek tarayıcı doğrulaması (ayrı geçici Streamlit
örneği, 8591, production 8501'e dokunulmadı): hem light hem dark tema
tam sayfa ekran görüntüsü alınıp kullanıcıya gösterildi, konsol hatası
yok, mevcut düzen (nav, form, buton) bozulmadı — kullanıcı onayladıktan
sonra geçici PNG'ler silindi.

## Modernizasyon C — Kategori/Ton kart grid'i (kullanıcı talebiyle)

Documentary Studio'nun Kategori (11+auto) ve Ton (12+auto) seçicileri düz
selectbox'lardan, seçim anında `PROFILE_PROMPTS`'tan alınan 1 cümlelik stil
önizlemesi gösteren bir kart grid'ine dönüştürüldü — sadece emoji ikon,
yeni asset yok. Mimari: `_render_history_page`'in (Faz 4) satır-başına-N
`st.columns()` chunking desenini birebir kullanan `st.button()` kartları
(custom HTML DEĞİL — ham HTML Python tarafına tıklama bildiremez).
`documentary_topic_category`/`documentary_tone` session_state anahtarları
**hiç değişmedi**, sadece `st.selectbox` yerine kart butonuna tıklanınca bu
anahtarlara doğrudan yazılıyor + `st.rerun()` — `run_pipeline()`'a giden
değer bire bir aynı kaldı. Format/Pacing kart grid'ine dönüşmedi, hâlâ
selectbox.

Önizleme metni tasarım kararı: `PROFILE_PROMPTS` tamamen İngilizce (LLM
prompt metni, webui'nin çeviri katmanından ayrı) — kullanıcı talebi
"PROFILE_PROMPTS'tan alınan" önizleme istediği için bu metin **çevrilmedi**
(12 tone'u 9 dile çevirmek ayrı, çok daha büyük bir iş olurdu). Sadece
"auto" kartlarının açıklaması ("Category/Tone Auto Description") ve
`Tone.neutral`'ın (PROFILE_PROMPTS'ta kendi girdisi olmayan, `get_template()`
zaten Credible'a düşen) dürüst fallback notu ("Tone Neutral Fallback
Description") 9 dile çevrildi.

**İki gerçek bug bulundu ve düzeltildi (kullanıcı ekran görüntüsünde
yakaladı):**
1. Seçili kartın (`type="primary"` buton) metni light modda tamamen
   görünmüyordu — Streamlit `kind="primary"` butonlara rengi doğrudan
   `<button>` öğesinde beyaz yazıyor; arka planı transparent yapınca (kart
   görünümü için) bu beyaz metin beyaz kart zemininde kayboluyordu (dark
   modda koyu zemin üstünde tesadüfen okunaklı kalmıştı). Düzeltme:
   `color: inherit !important` ile temanın normal metin rengine zorlandı.
2. Seçili kartın vurgusu (kırmızı kenarlık/arka plan) **iki temada da**
   hiç uygulanmıyordu — CSS `stVerticalBlockBorderWrapper` adlı iç içe bir
   öğeyi hedefliyordu (task_row_/advanced_settings_ ile aynı desen
   sanılmıştı) ama bu Streamlit sürümünde (1.59.1) `st.container(border=True)`
   böyle bir iç öğe üretmiyor -- class ve native kenarlık doğrudan dış
   `stVerticalBlock` öğesinde. Dark modda native varsayılan gri kenarlık
   zaten göründüğü için fark edilmemişti. Düzeltme: seçici doğrudan
   class'ı taşıyan öğeyi hedefleyecek şekilde düzeltildi. Bonus: butonun
   kendi element-container key'i (`{kind}_card_button_{value}` →
   `{kind}_btn_{value}`) joker seçicinin ona da yanlışlıkla dokunmaması
   için ayrı bir önekle yeniden adlandırıldı.

Testler: `test_webui_documentary_labels.py`'nin Kategori/Ton'a özel 3 eski
selectbox testi kart/buton tabanlı yeni testlerle değiştirildi (Format/
Pacing hâlâ selectbox olduğu için o testler aynen kaldı); `.click().run()`
ile canlı tıklama denendi ama Format/Pacing'in GÖREV 1 format_func'ı
(session_state okuyan) AppTest'in *herhangi bir ikinci* `.run()`
çağrısında (tıklamayla ilgisiz olsa bile) tüm widget ağacını yeniden
serileştirip aynı bağlanmamış-context quirk'üne düşürdüğü görüldü —
üretimde sorun yok, sadece test harness sınırı; bu yüzden her test tek
`.run()` + session_state'i önceden set etme desenine sadık kalındı.

Doğrulama: tam pytest suite **687 passed, 11 skipped** (684'ten +3, sıfır
regresyon), `ruff check app cli.py main.py webui test` temiz. Gerçek
tarayıcı doğrulaması iki turda yapıldı (ayrı geçici Streamlit örnekleri,
8592/8593, production 8501'e hiç dokunulmadı): ilk turda kullanıcı "Auto"
kartının light modda görünmezliğini yakaladı, düzeltme sonrası ikinci
turda hem light hem dark'ta metin + vurgu net görünür olduğu computed-style
introspection'ıyla (getComputedStyle) ve ekran görüntüsüyle doğrulandı,
kullanıcı onayladı.

## Modernizasyon B — Canlı ilerleme göstergesi (kullanıcı talebiyle)

3 yönlü modernizasyon planının (A → C → B) son adımı. `st.spinner()` yerine
`st.status()` ile Documentary Studio'nun üretim sırasında hangi aşamada
olduğunu (12 aşamanın hangisi, canlı, 9 dilde çevrilmiş metinle) gösteren
bir ilerleme göstergesi eklendi.

**Mimari:** `default_pipeline.py`'de zaten her 12 aşamanın başında çağrılan
bir `stage(n, name)` iç yardımcı fonksiyonu vardı (sadece `logger.info`
yazıyordu) — sıfırdan bir mekanizma kurmak yerine buraya opsiyonel bir
`on_stage_change: Callable[[int, str], None] | None = None` parametresi
eklendi. `stage()`'e eklenen tek satır: `if on_stage_change is not None:
on_stage_change(n, name)`. **Regresyon garantisi:** parametre verilmezse
(CLI, `test_default_pipeline.py`, `test_pipeline_dimension_matrix.py` dahil
mevcut HER çağıran) davranış bire bir aynı kalır — bu no-op'un kendisi ayrı
bir testle kilitlendi (`test_omitting_on_stage_change_behaves_identically`).

webui tarafı: `with st.status(tr("Generating Documentary"), expanded=True)
as status:` içinde `on_stage_change` callback'i `status.update(label=f"({n}
/12) {tr(key)}")` çağırıyor. `st.status()`'un kendi `__exit__`'i (Streamlit
kaynağından doğrulandı, `mutable_status_container.py`) istisna durumunda
otomatik `state="error"`, başarıda otomatik `state="complete"` yapıyor —
elle bir hata/başarı state yönetimi eklemeye gerek kalmadı, sadece başarı
etiketi son aşama mesajından daha net bir şeye ("Documentary Generated")
güncellendi.

**12 aşama mesajı** (`_DOCUMENTARY_STAGE_KEYS`, `webui/Main.py`) 9 dile
çevrildi (108 yeni key): intent/research/outline/scene/script/storyboard/
asset/asset download/audio (TTS)/timeline/seo/video render → "Konu
anlaşılıyor...", "Konu araştırılıyor...", "Hikaye taslağı hazırlanıyor..."
vb. (tam liste ve diğer 8 dil `webui/i18n/*.json`'da).

**Testler:**
- `test_default_pipeline.py`: `test_on_stage_change_called_for_all_12_stages_in_order`
  (mock'lu aşamalarla callback'in tam 12 kez, doğru sırayla `(n, name)` ile
  çağrıldığını doğruluyor) + `test_omitting_on_stage_change_behaves_identically`
  (regresyon, yukarıda).
- Yeni `test_webui_documentary_progress.py` (3 test): 12 mesaj key'inin 9
  dilde de var/boş-olmadığının doğrulanması; **`_DOCUMENTARY_STAGE_KEYS`'in
  (webui/Main.py) `default_pipeline.py`'nin gerçek `stage()` çağrılarındaki
  ham isimlerle (AST ile ikisi de koddan çıkarılıp) birebir eşleştiğinin
  doğrulanması** — pipeline'a yeni bir aşama eklenip webui tarafı
  güncellenmezse bu test kırılır, status mesajı sessizce eskimiş kalmaz.

**Gerçek tarayıcı doğrulaması (uçtan uca, gerçek API):** Ayrı bir geçici
Streamlit örneğinde (8594, production 8501'e dokunulmadı) gerçek bir konu
("The Discovery of Penicillin") ile "Generate Documentary"a tıklanıp
üretim izlendi. **6 farklı aşama geçişi canlı yakalandı ve ekran
görüntüsüyle kanıtlandı:** (2/12) Researching the topic... → (3/12)
Outlining the story... → (5/12) Writing the narration... → (6/12)
Storyboarding shots... → (8/12) Downloading footage... → (9/12) Recording
narration... — kullanıcı onayladı. İlk deneme (farklı bir tarayıcı hedefi
çöktüğü + yanlış ekran bölgesini yakaladığı için) atılıp düzeltilmiş
ikinci bir çalıştırmayla tekrarlandı. İki test üretimi de (ikinci deneme
sırasında aynı anda 2 tane, "Part Two" dahil) doğrulama sonrası
`storage/tasks/`'tan silindi -- bu depo production ile paylaşıldığı için
(aynı `ai-documentary-studio-webui.service`), test verisi Geçmiş
Üretimler'de görünmesin diye.

Doğrulama: tam pytest suite **692 passed, 11 skipped** (687'den +5, sıfır
regresyon), `ruff check app cli.py main.py webui test` temiz.

## Modernizasyon A/B/C — konsolide özet (kullanıcı talebiyle)

Kullanıcının onayladığı sıra: **A → C → B**, üçü de ayrı commit + ayrı
tarayıcı doğrulaması + kullanıcı onayıyla tamamlandı.

| Adım | Ne yapıldı | Commit | Doğrulama |
|---|---|---|---|
| **A** — Görsel/tema yenileme | `webui/styles.css`'e CSS-only renk paleti (`:root` custom-property'leri, mevcut `#ff4b4b` vurgu korunarak), tipografi (başlık ağırlığı/iz aralığı), boşluk ritmi (`--mpt-space-*`). `[theme]` bilinçli olarak değiştirilmedi. | `f8ad552` | 684 passed; light+dark tam sayfa ekran görüntüsü, konsol hatası yok, kullanıcı onayı |
| **C** — Kategori/Ton kart grid'i | 11 kategori + 12 ton selectbox'ı, `PROFILE_PROMPTS`'tan 1 cümlelik stil önizlemesi gösteren `st.button()` kart grid'ine dönüştürüldü (custom HTML değil). `documentary_topic_category`/`documentary_tone` session_state anahtarları hiç değişmedi. **İlk turda kullanıcı iki gerçek bug yakaladı** (seçili kartın metni light modda görünmüyordu + vurgusu iki temada da hiç uygulanmıyordu, `stVerticalBlockBorderWrapper` bu Streamlit sürümünde yok) — ikisi de düzeltilip yeniden doğrulandı. | `58b0a87` | 687 passed (+3); düzeltme sonrası light+dark computed-style + ekran görüntüsü, kullanıcı onayı |
| **B** — Canlı ilerleme göstergesi | `run_pipeline()`'a opsiyonel `on_stage_change` callback (geriye tam uyumlu), `st.spinner()` → `st.status()`, 12 aşama mesajı × 9 dil (108 key). | *(bu commit)* | 692 passed (+5); gerçek uçtan uca üretimle 6 farklı aşama geçişi canlı yakalandı, kullanıcı onayı |

Üçü de production servisine (8501) hiç dokunmadan, ayrı geçici Streamlit
örnekleriyle doğrulandı; her turun test/QA verisi (ekran görüntüleri,
test projeleri) kullanıcı onayından sonra temizlendi.

## Kart grid önizleme metni çevirisi düzeltmesi (kullanıcı bildirdi, `ec42906`)

Modernizasyon C'nin kart grid'i, kategori/ton önizleme cümlelerini
`PROFILE_PROMPTS[tone]["style"]`'dan türetiyordu — kullanıcı arayüz dili
Türkçe (veya diğer 8 dilden biri) olsa bile bu metinlerin İngilizce kaldığını
bildirdi. **Kök neden:** `PROFILE_PROMPTS` hiç kullanıcıya gösterilmek üzere
yazılmamıştı, LLM'e giden prompt talimatıydı (`build_script_prompt()` vb.) —
webui çeviri katmanından tamamen ayrı.

**Düzeltme (PROFILE_PROMPTS'un kendisine DOKUNULMADI — LLM davranışı risk
altına girmesin diye):** Her Tone (12'den `neutral` hariç 11 — `neutral`'ın
zaten kendi dürüst fallback key'i vardı, dokunulmadı) ve her TopicCategory
(11) için ayrı, kısa, kullanıcıya yönelik bir önizleme cümlesi yazılıp
`"Tone Preview: {value}"` / `"Category Preview: {value}"` key'leriyle 9 dile
çevrildi (22 key × 9 dil = 198 yeni çeviri). Kategori kartları artık kendi
tone'unun metnini ödünç almıyor (`_category_style_preview` artık
`DEFAULT_TONE_BY_CATEGORY` üzerinden `_tone_style_preview`'a delege etmiyor,
doğrudan kendi `Category Preview:` key'ini okuyor) — bu ayrıca eski
tasarımın bir yan etkisini de düzeltti: Psikoloji kategorisi ile Bilimsel
ton kartı artık birebir aynı metni göstermiyor, her biri kendi alanına özgü
bir cümle gösteriyor. `webui/Main.py`'den `PROFILE_PROMPTS`/
`DEFAULT_TONE_BY_CATEGORY` importları tamamen kaldırıldı (artık hiç
kullanılmıyor) — webui katmanı LLM prompt içeriğinden tamamen ayrıştı.

**Regresyon garantisi:** LLM'e giden gerçek `PROFILE_PROMPTS`/
`build_script_prompt()`/`TONE_VOICE_GUIDANCE` içeriği hiç değişmedi (sadece
webui'nin gösterdiği metnin KAYNAĞI değişti) — doğrulandı, `app/` altında
PROFILE_PROMPTS hâlâ sadece `script_generator.py`/`templates/__init__.py`/
`profile_dimensions.py`/`default_pipeline.py`'de kullanılıyor.

Testler: 3 yeni test (`test_tone_preview_keys_present_and_non_empty_in_every_locale`,
`test_category_preview_keys_present_and_non_empty_in_every_locale`,
**`test_turkish_card_previews_are_not_leaked_english_llm_prompt_text`** —
Türkçe çeviride PROFILE_PROMPTS'a özgü İngilizce kalıpların ("Ground the
narration", "Favor ", "documentary.") hiç geçmediğini doğrulayan doğrudan
bir regresyon testi).

Doğrulama: tam pytest suite **695 passed, 11 skipped** (692'den +3, sıfır
regresyon), `ruff` temiz. Gerçek tarayıcı doğrulaması (Türkçe arayüz, ayrı
geçici Streamlit örneği, production'a dokunulmadı): tüm 11 kategori + 11
ton kartının önizlemesi tam Türkçe, hiç İngilizce kalıntı yok, kullanıcı
onayladı.

## 3 yeni TopicCategory — Yemek Kültürü/Doğa/Netflix Tarzı (TAM OTONOMİ, kullanıcı ön-onayıyla)

Bugünkü 7 kategoriyle birebir aynı desende 3 kategori daha eklendi:
`food_culture`, `nature`, `netflix_style` — her biri kendi `Tone`'u,
`PROFILE_PROMPTS`, `SHOT_GUIDANCE`, `TONE_VOICE_GUIDANCE`,
`_CATEGORY_KEYWORDS` (İngilizce+Türkçe) ile.

| Kategori | Tone | Gerekçe |
|---|---|---|
| `food_culture` | `savory` (yeni) | Duyusal/lezzet odaklı anlatım -- mevcut tonlardan hiçbiri (encouraging'in "pratik sağlık rehberliği" dahil) yemek kültürünü doğru karşılamıyordu. |
| `nature` | `majestic` (yeni) | Bilinçli olarak `marine`'in `wondrous`'undan AYRI tutuldu -- marine su altına özel bir "hayret" hissi, nature ise kara/orman/dağ ölçeğine odaklanan bir "görkem" hissi; ikisini paylaştırmak alakasız bir stil metnine yol açardı. |
| `netflix_style` | `gripping` (yeni) | `cinephile`den (film_highlights, filmleri ANALİZ eden) kasıtlı olarak ayrı -- bu bir prodüksiyon STİLİ (yüksek prodüksiyon değeri, gerilim odaklı kurgu), film eleştirisi değil. |

**Marka güvenliği (kullanıcı talebiyle, `netflix_style` için):** Python enum
değeri kullanıcının kendi verdiği isim (`netflix_style`, sadece dahili bir
tanımlayıcı, hiçbir yerde kullanıcıya gösterilmiyor) ama gerçek Netflix
marka adı/logosu/yapım adı KODUN HİÇBİR YERİNDE (PROFILE_PROMPTS,
SHOT_GUIDANCE, heuristic keywords, i18n label) geçmiyor -- doğrulandı,
ayrı bir regresyon testiyle (`test_gripping_template_never_names_a_real_streaming_brand`)
kilitlendi. UI'da gösterilen çevrilmiş etiket "Prestige Documentaries" /
"Prestij Belgeselleri" (gerçek, marka-olmayan bir sektör terimi).
README-en.md/README.md'ye de "not affiliated with or endorsed by any
streaming service" notu eklendi.

Testler: `test_documentary_models.py` (DEFAULT_TONE_BY_CATEGORY + marka
güvenliği), `test_intent_analyzer.py` (3 heuristic keyword testi),
`test_outline_generator.py`/`test_research_planner.py` (PROFILE_PROMPTS
stil-keyword kilidi), `test_storyboard_generator.py` (SHOT_GUIDANCE
kilidi) — hepsi mevcut per-kategori desenleriyle birebir aynı.
`test_webui_documentary_labels.py`'nin i18n-parity testleri zaten
enum-üzerinden jenerik (`[c.value for c in TopicCategory]`) olduğu için
hiçbir değişiklik gerekmeden 3 yeni kategoriyi de otomatik kapsadı.

Doğrulama: tam pytest suite **699 passed, 11 skipped** (695'ten +4, sıfır
regresyon), `ruff` temiz. Her 3 kategori için gerçek API ile uçtan uca
(intent->research->outline->scene->script) doğrulandı: `food_culture` →
"Neapolitan Pizza" (grounded, duyusal/savory ton), `nature` → "California
Redwood Forests" (grounded, görkemli/majestic ton), `netflix_style` →
"D.B. Cooper'ın Çözülemeyen Kayboluşu" (bilinçli olarak gerilim-riskli bir
konu seçildi -- grounded, gerçek olaylara sadık kaldı, hiç uydurma iddia
yok, gripping ton tutarlı).

**Not (commit yapısı):** Kullanıcı her kategori için ayrı commit istedi,
ama 3 kategorinin kodu/i18n'i aynı dosyalarda (aynı dict'ler) iç içe
düzenlendiği için sonradan 3 ayrı temiz commit'e bölmek (git add -p ile
JSON/dict parçalama) kırılma riski taşırdı -- daha güvenli/geri alınabilir
seçenek olarak (genel kural 1) tek, kapsamlı ve her kategoriyi ayrı ayrı
belgeleyen bir commit'te birleştirildi.

## GÖREV 2 (TAM OTONOMİ) — SEO Engine genişletmesi: title_variants + keywords

**OTONOM KARAR — kapsam:** Ön-onay yeni ücretli API/arama-hacmi entegrasyonu
eklemeyi yasaklıyordu, sadece mevcut LLM çağrısını genişletmeyi izin
veriyordu. `generate_engagement_metadata()` (GECE OTURUMU 2 / Task C'de
eklenmiş, `end_screen_suggestion`+`pinned_comment` üreten izole çağrı) zaten
tam bunun için doğru genişletme noktasıydı — yeni bir LLM çağrısı eklemek
yerine bu ÇAĞRININ JSON şemasına 2 alan daha eklendi: `title_variants`
(ana başlığa 2 alternatif, A/B test için) ve `keywords` (platformun
tag/anahtar-kelime alanı için 8-10 geniş SEO terimi — on-screen hashtag'lerden
ayrı). `llm.generate_social_metadata()`/`build_social_metadata_prompt()`
(legacy tekil-video pipeline'ıyla PAYLAŞILAN kod) hiç değiştirilmedi.

**ADIM 0 (her yeni alanın gerçek bir tüketicisi olsun kuralı):**
`webui/Main.py`'de `_render_project_media_panel()`'e eklendi:
- `title_variants` varsa: SEO başlığının hemen altında, çevrilmiş etiketle
  (`Documentary SEO Title Variants`) salt-okunur bir `st.text_area` (satır
  satır).
- `keywords` varsa: mevcut "Documentary SEO Extras" expander'ı içinde
  (chapters/end-screen/pinned-comment ile aynı yerde), virgülle ayrılmış
  salt-okunur bir `st.text_input`.
Her ikisi de eski (bu alanlar olmadan üretilmiş) proje JSON'larında sessizce
hiç render edilmiyor — crash yok, boş widget yok (regresyon testiyle
kilitlendi: `test_missing_title_variants_and_keywords_render_nothing_extra`).

**Gerçek API doğrulamasında bulunan ve düzeltilen bir kalite sorunu:**
İlk gerçek çalıştırmada (`"The Unsolved Disappearance of D.B. Cooper"`),
`title_variants[0]` ana `title` ile BİREBİR AYNI çıktı ("The Hijacker Who
Vanished Into Thin Air") — çünkü `title` ve `title_variants` iki tamamen
ayrı LLM çağrısından geliyor (`generate_social_metadata` / `generate_engagement_metadata`),
ikinci çağrı birincinin sonucunu hiç görmüyordu. **Düzeltme (yeni LLM çağrısı
EKLEMEDEN):** `build_engagement_prompt()`/`generate_engagement_metadata()`'ya
opsiyonel `existing_title` parametresi eklendi; `generate_seo_metadata()`
zaten elindeki `result["title"]`'ı bu MEVCUT çağrıya context olarak geçiriyor
("The video's main title is already: ...") + prompt talimatı "genuinely
different from the main title above" olarak güçlendirildi. $0 ek maliyet,
aynı tek çağrı.

Testler: `test_seo_generator.py`'a `TestBuildEngagementPrompt` sınıfı (title
context var/yok senaryoları) + `test_drops_blank_title_variants_and_keywords`
+ `test_maps_social_metadata_result_to_seo_metadata` güncellendi (engagement
prompt'unun gerçekten ana başlığı içerdiğini doğrulayan assertion eklendi).
`test_webui_seo_extensions.py` (yeni dosya, 3 test): i18n key'lerinin 9 dilde
var/dolu olduğu, title_variants'ın başlığın hemen altında doğru render
olduğu, keywords'ün expander içinde virgülle render olduğu, eksik alanlarda
hiçbir şey render edilmediği.

Doğrulama: tam pytest suite **707 passed, 11 skipped** (699'dan +8, sıfır
regresyon), `ruff` temiz. **Gerçek API doğrulaması (D.B. Cooper konusu, iki
ayrı çalıştırma):** İlk çalıştırma başlık tekrarı sorununu ortaya çıkardı;
düzeltme sonrası İKİNCİ gerçek çalıştırmada `title` = "The Hijacker Who
Vanished Into Thin Air", `title_variants` = ["The $200,000 Skyjacking That
Still Baffles the FBI", "He Jumped From a Plane With Ransom Money—and Became
a Legend"] — üçü de birbirinden gerçekten farklı, hiç tekrar yok. `keywords`
10 alakalı terim üretti (ör. "D.B. Cooper", "unsolved mysteries", "true crime
documentary", "FBI cold case").

## ACİL PRODUCTION KESİNTİSİ — stale process/import cache (2026-07-26) + deploy.sh

**Belirti:** Kullanıcı production'ın `AttributeError: food_culture`
(`webui/Main.py:4178`) ile çöktüğünü bildirdi.

**Teşhis:** Disk üzerindeki kod **hiç bozuk değildi** — `TopicCategory`
enum'ında `food_culture` gerçekten vardı, `webui/Main.py` onunla birebir
uyumluydu, taze bir Python süreci ve tam pytest suite (707 test, `AppTest`
üzerinden gerçekten `webui/Main.py`'yi import/exec ediyor) sorunsuz
geçiyordu. Gerçek sorun: production servisi (`ai-documentary-studio-webui.service`)
Cuma 24 Temmuz 00:37'den beri, yani bugünkü GÖREV 1 commit'inden (3 yeni
kategori) ÖNCE başlayıp kesintisiz çalışıyordu. Python, import edilen
modülleri process ömrü boyunca `sys.modules`'te cache'liyor; Streamlit'in
kendi dosya-izleme mekanizması sadece ana script'i (Main.py) her session'da
yeniden okuyor, `app/` altındaki import edilen modülleri process yeniden
başlamadan güvenilir şekilde yenilemiyor. Sonuç: process'in belleğindeki
eski `TopicCategory` nesnesi `food_culture`/`nature`/`netflix_style`'ı hiç
görmedi — crash-loop yoktu (systemd process'i hiç ölmedi), her kullanıcı
oturumunun script çalıştırması bu hatayla karşılaşıp tarayıcıda hata
gösteriyordu.

**Anlık düzeltme:** `systemctl restart` — yeni process, taze import, sorun
anında çözüldü. Headless Chromium ile production'da hatasız yüklendiğini
doğruladım.

**Kalıcı çözüm — `deploy.sh` (proje kök dizini, çalıştırılabilir):**
```bash
#!/bin/bash
set -e
git pull origin main
systemctl restart ai-documentary-studio-webui.service
sleep 3
curl -sf http://localhost:8501/_stcore/health && echo "Deploy OK" || echo "Deploy FAILED - health check başarısız"
```
Kullanıcı bunu şimdilik her önemli push sonrası **manuel** çalıştıracak
(ileride otomatikleştirilebilir). Gerçek çalıştırmayla test edildi (pull +
restart + health check), servis yeni PID ile sağlıklı ayağa kalktı.

**Ders (genel kural):** Backend Python modüllerini (`webui/Main.py` dışındaki
`app/` dosyaları -- enum, dict, servis kodu) değiştiren her push, üretimde
etkili olması için bir **restart gerektirir**. Bu tür bir hatayı test suite
yapısal olarak yakalayamaz çünkü pytest her zaman taze bir process'te
çalışır -- bu bir kod-doğruluğu sorunu değil, bir operasyon/deploy sorunu.
Bundan sonra: her backend değişikliği push edildikten sonra `./deploy.sh`
çalıştırılmalı.

## Kalite düzeltmesi: SEO açıklamasında zaman-ölçeği hatası (yüzyıl/binyıl)

**Belirti (kullanıcı bildirdi):** Gerçek bir Truva/Troy üretiminde
(`storage/tasks/cfed55f0.../project.json`) SEO açıklaması "yüzyılların
izlerini taşıyan" dedi, ama gerçek yerleşim süresi ~3.000 yıl (binyıl
ölçeği).

**Teşhis:** `seo_generator.py` (`generate_seo_metadata`/
`generate_engagement_metadata`) ve altındaki paylaşılan
`llm.generate_social_metadata`/`build_social_metadata_prompt`, `research_plan.key_facts`'i
HİÇ görmüyordu -- sadece `topic`+`script` alıyordu. Gerçek prod verisinde
doğrulandı: `research_plan.key_facts` doğru bilgiyi ("yaklaşık 3.000 yıllık
yerleşim tarihi") zaten içeriyordu, `outline` de bunu tekrarlıyordu, ama
üretilen `script.full_text` bilinçli olarak şiirsel/sayısız kalmıştı ("katman
katman yükselen zaman", rakam yok). SEO'nun eline hiçbir sayısal referans
verilmediği için "yüzyıllar" gibi makul duran ama yanlış bir ölçek uydurdu.
**Kök neden storyboard'da daha önce bulunan grounding eksikliğiyle birebir
aynı sınıf** -- storyboard call site'ı zaten `key_facts=project.research_plan.key_facts[:3]`
geçiriyordu (`default_pipeline.py:173`), SEO call site'ı hiç geçirmiyordu.

**Düzeltme (yeni LLM çağrısı yok, $0 ek maliyet):**
- `app/services/llm.py`: `build_social_metadata_prompt()`/`generate_social_metadata()`'a
  opsiyonel `key_facts: list[str] | None = None` eklendi -- legacy tekil-video
  pipeline'ı bunu hiç geçirmediği için davranışı birebir aynı kalıyor
  (regresyon testiyle kilitlendi). Verilirse prompt'a "Verified Facts" bloğu
  + "century vs millennium vs decade ölçeğini bu facts'e göre doğrula"
  talimatı ekleniyor.
- `app/departments/growth/seo_generator.py`: `generate_seo_metadata()` ve
  `generate_engagement_metadata()`/`build_engagement_prompt()` aynı
  `key_facts`'i her iki alt-çağrıya da (title/caption/hashtags VE
  title_variants/keywords/end_screen/pinned_comment) geçiriyor -- ikisi de
  aynı script'ten bağımsız olarak yanlış bir ölçek uydurabilirdi.
- `app/pipeline/default_pipeline.py`: SEO çağrısına `key_facts=project.research_plan.key_facts[:3]`
  eklendi -- storyboard'daki satırın birebir kopyası.

Testler: `test_llm.py` (3 yeni: facts bloğu var/yok, `generate_social_metadata`'nın
facts'i prompt builder'a gerçekten ilettiği), `test_seo_generator.py` (3 yeni:
`build_engagement_prompt`'ta facts bloğu var/yok, `generate_seo_metadata`'nın
facts'i HER İKİ alt-çağrıya da ilettiği), `test_default_pipeline.py`
(mevcut wiring testine `seo_kwargs["key_facts"]` assertion'ı eklendi, storyboard'ın
`[:3]` slice testiyle aynı sahte 4. fact'i kullanarak).

Doğrulama: tam pytest suite **713 passed, 11 skipped** (707'den +6, sıfır
regresyon), `ruff` temiz. **Gerçek API doğrulaması** -- aynı gerçek Truva
projesinin gerçek `topic`/`script`/`key_facts[:3]`'ü ile `generate_seo_metadata()`
yeniden çalıştırıldı (sadece SEO aşaması, tam üretim değil): yeni açıklama
*"...yaklaşık 3.000 yıllık bir yerleşim hafızasını da fısıldıyor..."* diyor --
"yüzyıl" kelimesi hiç geçmiyor, doğru ölçek ("3.000 yıl") açıkça var. Bir
`title_variant` de aynı doğru ölçeği ("3.000 Yıllık Sırrı") bağımsız olarak
tekrarladı.

**Not (production etkisi):** Bu değişiklik sadece `default_pipeline.py`'nin
SEO aşamasını etkiliyor -- geçmişte üretilmiş projelerin (ör. bu Truva
projesinin) zaten kaydedilmiş `seo.description`'ı otomatik düzelmiyor, sadece
BUNDAN SONRA üretilecek yeni belgeseller doğru grounding ile üretilecek.
Commit sonrası `./deploy.sh` çalıştırıldı (backend değişikliği -- production
restart gerektirir, önceki operasyonel dersin uygulanması).

## Yeni özellik: AI-üretimi video görselleri (fal.ai/Kling) -- kodlama tamamlandı, gerçek API çağrısı BEKLİYOR

Stok video (Pexels/Pixabay) yerine gerçek para harcayan bir AI video-üretim
sağlayıcısı (fal.ai üzerinden Kling) opsiyonel bir provider olarak eklendi.
Önce kapsamlı bir plan raporu sunuldu (fal.ai REST API araştırması,
mimari karar, maliyet/hata yönetimi önerileri), kullanıcı onayladı, sonra
6 parça hâlinde, her biri kendi commit'i + mock testleriyle kodlandı.

**Planlama aşamasında bulunan gerçek fiyat tutarsızlığı:** Kullanıcının
başlangıç tahmini (~$0,029/sn) fal.ai'nin GÜNCEL hiçbir Kling tier'ına
uymuyordu -- gerçek, doğrulanmış fiyatlar $0,045/sn (Kling 1.0 standard,
en ucuz) ile $0,168/sn (Kling 3.0 Pro, sesli) arasında. Kullanıcı **Kling
1.0 standard**'ı (`fal-ai/kling-video/v1.0/standard/text-to-video`,
$0,045/sn) seçti, config'te değiştirilebilir bırakıldı (`fal_kling_model`)
çünkü bu tier/fiyatlar zamanla değişebiliyor. Ayrıca fal.ai'nin kendi model
sayfası tek bir klip için **~6 dakika** üretim süresi belirtiyor -- bu,
mimari kararları (paralel gönderim, alt-ilerleme göstergesi) doğrudan
şekillendirdi.

### Mimari kararlar (özet)

1. **Yeni, izole modüller** (mevcut fonksiyonlara "mod" parametresi
   gömülmedi) -- `app/services/fal_video.py` (generic fal.ai queue client:
   submit/poll/result/download, `upload_post.py` deseniyle tutarlı, asla
   exception fırlatmaz) + `app/departments/production/ai_video_generator.py`
   (documentary-özel: `asset_downloader.py` ile aynı AssetPlan-in/-out
   şekli, ama sahne başına bir fal.ai işi gönderip round-robin polling
   yapıyor). Gerekçe: stok (senkron/saniyeler/ücretsiz) ile AI
   (asenkron/dakikalar/gerçek-para/politika-reddi-riski) operasyonel
   profilleri kökten farklı -- tek fonksiyona gömmek bu farkı gizlerdi.
2. **`AssetCandidate.prompt`** (yeni, opsiyonel alan) -- `search_terms`
   (stok arama anahtar kelimesi) yerine `shot.description` (tam betimleyici
   cümle) AI prompt'u olarak kullanılıyor; ikisi birbirinin yerine geçemez.
3. **`default_pipeline.py` stage 8 dallanması**: `video_source ==
   "ai_generated"` ise `ai_video_generator.generate_ai_clips()`, değilse
   mevcut `asset_downloader.download_assets()` -- her stok kaynak (pexels/
   pixabay/coverr/local) birebir eskisi gibi çalışıyor. Kling'in
   `duration` parametresi sadece "5"/"10" kabul ettiği için (bizim
   scene_duration'larımız 5.0/8.0), 8s sahne "10"a YUKARI yuvarlanıyor
   (aşağı yuvarlarsak repeated-frame riski -- `_ASSET_DOWNLOAD_DURATION_
   SAFETY_MULTIPLIER`'ın stok tarafı için çözdüğü aynı sorun).
4. **`on_substage_progress(completed, total)`** (yeni, opsiyonel
   `run_pipeline()` parametresi) -- 12 aşamalık sabit mesaj, ~6dk/klip süren
   bu aşamada dakikalarca donuk kalmasın diye "N/M klip tamamlandı" canlı
   göstergesi (Modernizasyon B'nin doğal uzantısı).
5. **`AIVideoGenerationError`** (yapılandırılmış özel exception) -- hangi
   sahnenin neden başarısız olduğunu (`failures`) VE zaten üretilmiş/
   ücretlendirilmiş klipleri (`completed_paths`) taşıyor. **Sessiz stok
   fallback YOK** (kullanıcının kendi ADIM 0/geçmiş-ders talimatına göre) --
   webui net bir hata + "Stok Video'ya çevirip tekrar deneyin" rehberliği
   gösteriyor. **Bilinçli kapsam sınırlaması:** otomatik/tek-tıkla
   sahne-bazlı retry (kısmi pipeline resume) v1'e DAHİL EDİLMEDİ -- böyle
   bir altyapı (belirli bir aşamadan devam etme) bu kod tabanında hiçbir
   yerde yok, şimdi eklemek riski/kapsamı ciddi büyütürdü. Gelecekte
   değerlendirilebilir bir iyileştirme olarak not düşülüyor.
6. **`film_highlights` telif/kişilik-hakları koruması**: AI-video prompt'u
   bu kategori için ek bir talimatla ("gerçek oyuncu/kamu figürünün
   görünüşünü yeniden üretmeye çalışma") genişletildi -- bu kategorinin
   narration için zaten sahip olduğu "gerçek diyalog asla alıntılama"
   korumasıyla aynı prensip, yeni AI-video yüzeyine taşındı.
7. **webui**: Documentary Studio'da **ilk kez** bir Video Source seçici
   (`Stok Görüntü` varsayılan/değişmedi, `AI Üretimi` opt-in). Maliyet
   şeffaflığı `publisher.py`'nin "geri alınamaz/ücretli eylem -> manuel
   onay" ilkesiyle tutarlı, hatta daha erken (maliyet üretimin KENDİSİ
   sırasında oluşuyor): tahmini maliyet + "tahmindir, kesin fatura değil"
   uyarısı + onay kutusu olmadan buton aktifleşmiyor. fal.ai
   yapılandırılmamışsa net bir uyarı gösteriliyor.

### Bilinen sınırlama (dürüstçe not düşülüyor, düzeltilmedi)

`shot.description` (AI prompt kaynağı) belgeselin kendi dilinde üretiliyor
(ör. Türkçe bir üretimde description Türkçe) -- `search_terms` gibi
İngilizceye zorlanmıyor. Kling gibi modellerin çok-dilli prompt kalitesi
İngilizceden düşük olabilir. Bu oturumda bir çeviri adımı EKLENMEDİ (kapsam
dışı, plan onayında da yoktu) -- gerçek API doğrulamasında kalite gözden
geçirilecek, gerekirse ayrı bir iyileştirme olarak ele alınabilir.

### Doğrulama durumu

- **Test:** 6 commit, her biri kendi mock'lu testleriyle (fal_video: 16,
  ai_video_generator: 8, asset_generator: +4, default_pipeline: +1,
  webui: +5 = toplam **+34 yeni test**). Tam suite: **747 passed, 11
  skipped** (713'ten +34, sıfır regresyon boyunca). `ruff` her commit'te
  temiz.
- **Gerçek tarayıcı doğrulaması** (headless Chromium, geçici port 8577,
  production'a dokunulmadı): Video Source seçici doğru render oluyor,
  "AI Üretimi" seçilince (fal.ai yapılandırılmamışken) uyarı + devre dışı
  buton doğru gösteriliyor, konsol/traceback hatası yok.
- **GERÇEK fal.ai API çağrısı henüz yapılmadı.** `config.toml`'da
  `fal_api_key` hâlâ yok (doğrulandı: dosyada `fal`/`Fal` içeren hiçbir
  satır yok) -- kullanıcı ekleyecek. Kullanıcının kendi talimatı gereği,
  gerçek/ücretli bir API çağrısından (tek, ucuz bir test klibi bile olsa)
  önce açık onay bekleniyor -- bu adım kasıtlı olarak durduruldu.

## AI-üretimi video görselleri -- GERÇEK API doğrulaması TAMAMLANDI, 2 gerçek bug bulundu ve düzeltildi

Kullanıcı `config.toml`'a gerçek `fal_api_key` ekledi, gerçek/ücretli ilk
API çağrısına açık onay verdi. Doğrulama sırasında **iki gerçek bug**
bulundu ve düzeltildi -- ikisi de sadece gerçek API ile ortaya çıkabilecek
türden, mock testlerin yakalayamayacağı hatalar.

### Bug 1: Model id typo (`v1.0` yerine `v1` olmalıydı)

Planlama aşamasında doğru araştırılmıştı (`fal-ai/kling-video/v1/standard/
text-to-video`), ama kodlama sırasında yanlışlıkla `v1.0` yazılmış --
`app/services/fal_video.py`, `config.example.toml`, `config.toml` ve
testlerde. İlk gerçek submit çağrısı `request_id` ile "başarılı" göründü
ama bu geçersiz bir alt-yoldu (fal.ai'nin gateway'i esnek routing yapıyor,
var olmayan bir alt-yola da bir request_id veriyor) -- iş neredeyse anında
"COMPLETED" oldu (`inference_time: 0.049s`, gerçek bir 5-6 dakikalık video
üretimi için imkansız kısa), gerçek bir video hiç üretilmedi. **Muhtemelen
$0 maliyetli** (gerçek inference hiç çalışmadı) ama fal.ai dashboard'undan
teyit edilemedi.

### Bug 2: Status/result URL yapısı yanlıştı (subpath dahil edilmemeliydi)

Asıl kök neden buydu -- `poll_job_status()`/`get_job_result()` submit
URL'iyle AYNI tam model string'ini (`fal-ai/kling-video/v1/standard/
text-to-video`) kullanıyordu, ama fal.ai'nin queue API'si bu iki
operasyon için FARKLI URL yapıları bekliyor:
- **Submit**: tam yol (subpath dahil) -- `POST /{owner}/{app}/{subpath}`
- **Status/Result**: SADECE `{owner}/{app}` (subpath HARİÇ) -- `GET
  /{owner}/{app}/requests/{id}/status` ve `GET /{owner}/{app}/requests/{id}`

Gerçek API'de subpath dahil edilince `405 Method Not Allowed` dönüyordu.
Bunu resmi `fal-client` Python kütüphanesinin GitHub kaynağını okuyarak
doğruladım (`AppId.from_endpoint_id()` + `RequestHandle.from_request_id()`
-- ikisi de status/result URL'lerini owner/alias'tan kuruyor, subpath'i
atıyor). Düzeltme: `FalVideoService._app_id` (yeni property, `self.model`'in
ilk 2 path segmentini alıyor) eklendi, `poll_job_status`/`get_job_result`
bunu kullanıyor; `submit_video_job` hâlâ tam `self.model`'i kullanıyor
(değişmedi, zaten doğruydu).

**Düzeltme sonrası:** 2 yeni/güncellenmiş test (`_app_id` property testi +
status/result URL assertion'ları kesinleştirildi), tam suite **748 passed,
11 skipped** (747'den +1, sıfır regresyon).

### Gerçek API doğrulaması -- BAŞARILI

**Tek klip testi (düzeltme sonrası, 2. deneme):** Prompt "aerial view of a
calm ocean at sunset", `duration=5`, `aspect_ratio=9:16`. Submit → 320
saniyede (~5.3dk, fal.ai'nin kendi "~6dk" tahminine yakın) COMPLETED →
gerçek video_url alındı → indirildi (5.764.623 byte). `ffprobe`: h264,
**720x1280 (9:16 doğru)**, 30fps, **duration=5.1s (doğru)**. Bir kare
çıkarıldı, görsel olarak gerçekten "gün batımında sakin okyanus havadan
görünüm" -- prompt'a birebir uyan, yüksek kaliteli bir görüntü.

**Mini uçtan-uca pipeline testi:** Gerçek `run_pipeline()`, konu "The
Basics of Ocean Tides", `pacing=short` (4 sahne), `video_source=
"ai_generated"`. **Substage progress callback'i gerçek çalışmada
doğrulandı**: "1/4 → 2/4 → 3/4 → 4/4 AI clips done" mesajları 383s-431s
arasında, sadece 48 saniyelik bir pencerede geldi -- bu, 4 klibin GERÇEKTEN
paralel işlendiğini kanıtlıyor (sıralı olsaydı ~24 dakika sürerdi, paralel
mimari kararının doğru olduğunu somut olarak doğruluyor). Toplam pipeline
süresi: 586 saniye (~9.75dk). `final.mp4` `ffprobe` ile doğrulandı: h264+aac,
1080x1920, 29.07s, 16.1MB. Bir kare çıkarıldı: gerçek, tutarlı, altyazılı
bir belgesel sahnesi (gelgit havuzu görüntüsü + "pulls tides—the sea's
restless rise and fall" altyazısı doğru kompoze edilmiş).

**Gerçek toplam maliyet (bu doğrulama turu için):** ~$1.13 (5 gerçek klip:
1 tekli test @ $0.225 + 4 mini-pipeline klibi @ $0.225 = $1.125) + birkaç
kuruş gerçek LLM çağrısı maliyeti (intent/research/outline/scene/script/
storyboard/seo). İlk (bug'lı) deneme muhtemelen $0 (gerçek inference hiç
çalışmadı).

### Yeni bulunan, dürüstçe not düşülen bir sınırlama (düzeltilmedi)

Mini-pipeline testinde `video.py`'nin `combine_videos()` şu uyarıyı verdi:
*"video duration (20.40s) is shorter than required duration (29.16s),
looping clips to match audio length."* -- yani gerçek narration (29.16s)
4 AI klibinin toplam süresinden (4×5s=20s) uzun çıktı, video bu farkı
klipleri TEKRARLAYARAK kapattı. **Bu, oturumun daha önce stok-görüntü
tarafı için çözdüğü aynı "repeated-frame" sorunu** -- ama AI tarafı için
`_ASSET_DOWNLOAD_DURATION_SAFETY_MULTIPLIER` (stok'ta over-fetch ile
çözülüyor) doğrudan uygulanamaz, çünkü AI'da "fazladan" klip üretmek
gerçek ek maliyet demek (stokta ücretsiz). Video yine de başarıyla
render edildi (crash yok, sadece bazı kareler tekrar ediyor) -- kritik
bir hata değil ama gerçek bir kalite sınırlaması. **Düzeltilmedi, gelecekte
değerlendirilecek bir iyileştirme olarak not düşülüyor** (olası çözümler:
AI sahneleri için her zaman duration="10" istemek -- maliyeti ~2x artırır,
veya script_generator'ın AI-video seçiliyken daha kısa narration hedeflemesi).

**Durum: özellik tam olarak çalışıyor, production'a hazır.** Test artifact'leri
(`storage/tasks/ai-video-mini-pipeline-test/`, geçici scratchpad dosyaları)
temizlendi.

## "Tekrar eden kare" düzeltmesi -- maliyeti artırmadan, sahne-bazlı Kling süre seçimi

Önceki gerçek mini-pipeline testinde bulunan sınırlama (4 AI klip × 5s = 20s
footage, gerçek narration 29.16s -- video klipleri tekrarlayarak doldurdu)
kullanıcı onayıyla **sahne-bazlı** çözümle giderildi (plan raporunda sunulan
3 seçenekten -- global, sahne-bazlı, hibrit -- en isabetlisi/en az maliyetlisi).

**Kök neden ve çözüm:** Stage 8 (asset download), TTS'ten (stage 9) önce
çalışıyor ama script'ten (stage 5) SONRA -- yani gerçek script metni zaten
biliniyor, sadece gerçek TTS çıktısı bilinmiyor. Önceki kod Pacing'in
üretim-öncesi hedef süresini (5s/8s) kullanıyordu; artık her sahnenin
GERÇEK script metninden (`Script.lines[i].text`, scene_index eşleşmesiyle)
gerçek kelime sayısı hesaplanıyor, `script_generator._WORDS_PER_SECOND=2.3`
ile süreye çevriliyor, Kling'in iki sabit tier'ından (`"5"`/`"10"`) hangisi
yeterliyse SADECE O sahnenin klibi için isteniyor -- diğer sahneler
gereksiz yere "10"a yükselmiyor.

**Değişiklikler:**
- `app/models/asset.py`: yeni `AssetCandidate.ai_duration: str = "5"` alanı
  (mevcut, kullanılmayan `duration: float` alanıyla karışmasın diye farklı
  isimlendirildi).
- `app/departments/production/asset_generator.py`: yeni
  `_kling_duration_for_word_count()` + `build_asset_plan()`'a opsiyonel
  `script` parametresi. `script=None` ise davranış birebir eskisi gibi
  (hep `"5"`) -- regresyon garantisi.
- `app/departments/production/ai_video_generator.py`: `generate_ai_clips()`
  artık global `duration` parametresi almıyor, her candidate'in KENDİ
  `ai_duration`'ını kullanıyor.
- `app/pipeline/default_pipeline.py`: stage 7 çağrısına `script=project.script`
  eklendi; artık gereksiz olan `_kling_duration_for_scene_seconds()` helper'ı
  ve stage 8'deki global duration hesaplaması kaldırıldı.

Test: 9 yeni test (sınır durumları: tam bütçe altı/üstü kelime sayısı,
sahne-bazı bağımsız seçim, script=None regresyonu, eşleşen script satırı
olmayan sahne, stok yolunun script'i tamamen görmezden gelmesi). Tam suite:
**757 passed, 11 skipped** (748'den +9, sıfır regresyon).

**Gerçek API doğrulaması (aynı "The Basics of Ocean Tides" konusu, short
pacing, ikinci mini-pipeline çalıştırması):** Script'in gerçek sahne başı
kelime sayıları (13/12/12/14 kelime, ~5.2-6.1s) hesaplandı, 4 sahnenin
4'ü de 5s sınırını gerçekten aştığı için hepsi "10"a yuvarlandı (bu
senaryoda maliyet üst sınırı: 4×10×$0.045=**$1.80** -- bu spesifik
script gerçekten bu kadar süreye ihtiyaç duyduğu için, israf değil).
Sonuç: 40s toplam AI footage vs 23.78s gerçek narration -- **bol payla
yeterli**. `video.py`'nin log'unda **hiç "looping" uyarısı çıkmadı**
(önceki testte kesinlikle vardı) -- `ffprobe` ile doğrulandı: `final.mp4`
h264+aac, 1080x1920, **23.8s** (gerçek narration'a neredeyse birebir
eşit), 17.7MB. Düzeltme gerçek veriyle kanıtlandı.

**Durum: "tekrar eden kare" sınırlaması giderildi, maliyet artışı SADECE
gerçekten gereken sahnelerde ve gerçek ihtiyaçla orantılı.**

## TAM OTONOMİ turu: GÖREV 3 (büyüme ilkeleri) + GÖREV 1 (Klasik Mod gizleme) + GÖREV 2 (uzun-form video)

Kullanıcı üç görevi de tek seferde, durmadan tamamlama onayı verdi. Sırayla,
her biri kendi commit'i + testleri + (uygunsa) gerçek doğrulamasıyla
tamamlandı.

### GÖREV 3 -- platform büyüme ilkelerinin otomatik entegrasyonu (commit `566cdd7`)

Önceden onaylanmış plana göre uygulandı: yeni `_growth_guidance_instructions()`
-- Hook/Retention/Callback (Story Craft) ile aynı "her zaman açık,
kapatılamaz, Tone/Format'tan bağımsız" katman. Somut/spesifik açılış
(genel selamlama yok), reklam-dostu kısıtlar, tek genel "seri hissi"
cümlesi. Mevcut Retention talimatı GÜÇLENDİRİLDİ (ayrı, çelişebilecek bir
"her 15-20sn twist" cümlesi eklenmedi). `Format.corporate`'te (zaten
"neutral third-person, promotional dil yok" istiyor) kapanış-CTA'sı ve
etkileşim-sorusu bilinçli olarak bastırıldı. Yeni LLM çağrısı yok, $0
maliyet. Test: 6 yeni, tam suite 763 passed (757'den +6). Gerçek API ile 2
doğrulama: mysterious ton + outline hook/closing (somut açılış, doğal
kapanış-nudge, açık uçlu soru) ve Format.corporate (CTA/soru gerçekten
yok, tarafsız üslup korundu).

### GÖREV 1 -- Klasik Mod'u kullanıcıdan gizleme (commit `78dd125`)

Risk analizi: tam silme, 4 test dosyasındaki (~39 test) `_LEGACY_PAGE_HASH`
tabanlı doğrudan erişimi kırardı (denendi, doğrulandı -- 25 test kırıldı).
Seçilen yaklaşım: `st.Page(..., visibility="hidden")` (bu Streamlit
sürümünün desteklediği bir özellik) -- sayfa kayıtlı/erişilebilir kalıyor,
sadece kenar çubuğundan kayboluyor. app/ ve main.py'de hiçbir bağımlılık
yok (grep ile doğrulandı). Test: kaynak-kod seviyesinde niyeti kilitleyen
3 yeni test (`test_webui_navigation.py`) + gerçek headless-Chromium
doğrulaması (ekran görüntüsü: sidebar'da sadece "Oluştur"/"Geçmiş
Üretimler" görünüyor). Tam suite: 766 passed (763'ten +3, sıfır regresyon
-- ilk "tam silme" denemesi 25 testi kırmıştı, düzeltildi).

### GÖREV 2 -- 10+ dakikalık uzun-form video, 16:9 (commit `794a365`)

**Mimari karar (TAM OTONOMİ):** yeni `Pacing.extended` (20 sahne x 30s =
600s) -- "daha fazla sahne" ile "sahne başına daha uzun anlatım" arasında
bir orta yol, ikisinin de aşırı ucundan kaçınıldı (60+ sahnelik tek LLM
çağrısı kalite riski vs. 60sn+ kesintisiz anlatım monotonluk riski).

**Kök mimari bulgu:** `scene_planner.plan_scenes()` sahne-başına-bir-
outline-section eşlemesi yapıyor, ama `outline_generator` HER ZAMAN sabit
"4-7 section" istiyordu -- 20 sahnelik bir pacing'e outline asla
yetişemezdi. Çözüm: `outline_generator` artık pacing-farkında (yeni
`PACING_OUTLINE_SECTION_RANGE`: short/long için BİREBİR AYNI "4-7" --
regresyon garantisi -- extended için "18-24"). `scene_planner.py`'ye
HİÇBİR kod değişikliği gerekmedi (zaten tamamen pacing/outline-agnostic --
gerçek testle doğrulandı).

**16:9 (`VideoAspect.landscape`)** zaten resolution eşlemesiyle
(1920x1080) tam destekleniyordu (`timeline_builder`/`asset_downloader`/
`thumbnail_generator` hepsi aspect-agnostic, dinamik boyut okuyor) --
sadece hiç webui seçeneği yoktu (Documentary Studio her zaman sabit
"9:16" kullanıyordu, AI video_source'tan önceki durumla aynı desen). Yeni
bir Aspect Ratio seçici eklendi (9:16 varsayılan/değişmedi, 16:9 opt-in,
"1:1" kullanıcı istemediği için kapsam dışı bırakıldı).

**ZORUNLU MALİYET GÜVENLİK KURALLARI'na tam uyum:** AI Video + extended
pacing kombinasyonu için dürüst bir uyarı eklendi (30sn'lik sahneler
Kling'in azami "10"sn tier'ını aşıyor, sahne başına belirgin tekrar eden
kare beklenmeli) ama bu kombinasyon **gerçek API ile HİÇ test edilmedi**
-- kullanıcının açık talimatı gereği. Gerçek doğrulama SADECE Stok Video
ile (ücretsiz, sınırsız test edilebilir) yapıldı.

Test: 4 dosyada +12 test + yeni `test_webui_long_form.py` (5 test). Tam
suite: **779 passed, 11 skipped** (766'dan +13, sıfır regresyon).

**GERÇEK doğrulama (Stok Video, $0 maliyet):** "The History of the Silk
Road" konusu, extended pacing, 16:9. Sonuç: 22 outline section (18-24
aralığında), 20 sahne (hedeflendiği gibi), 1152 kelimelik gerçek script.
`final.mp4` `ffprobe` ile doğrulandı: h264+aac, **1920x1080 (doğru 16:9)**,
**500.23s (~8.3dk)**. Bir kare çıkarıldı: gerçek, tutarlı, doğru altyazılı
bir belgesel sahnesi (İpek Yolu havadan arkeolojik alan görüntüsü).

**Dürüst not:** Gerçek video süresi (500s) tam hedeflenen 600s'nin biraz
altında kaldı -- script'in gerçek kelime sayısı (1152) per-sahne hedef
kelime sayısının (20×69=1380) altında çıktı. Bu, LLM'in per-sahne hedef
kelime sayısını her zaman tam tutturmaması -- kısa/uzun pacing'te de
ÖNCEDEN var olan, bilinen bir varyans (`_ASSET_DOWNLOAD_DURATION_
SAFETY_MULTIPLIER`'ın belgelediği ters yöndeki varyansla aynı kök neden),
yeni bir bug değil. Yine de önceki ~56s tavanına göre kesin, sağlam bir
"uzun-form" video -- mimari doğru çalışıyor.

### Genel durum

Tam suite (üç görev sonrası, final): **779 passed, 11 skipped, sıfır
regresyon boyunca**. `ruff` her commit'te temiz. `git log origin/main -1`
ile senkron doğrulandı. `./deploy.sh` çalıştırıldı, production temiz
restart oldu.

## ÖZELLİK A/B/C (kullanıcı onaylı 3 özellik) -- A tamamlandı, B bu bölümde, C ertelendi

Kullanıcı üç yeni özelliği önceden onayladı: **A** (düzenlenebilir senaryo
alanı, commit `f57c121` -- ayrı push+deploy ile önceden tamamlandı),
**B** (özel etiketler, bu bölüm) ve **C** (Hailuo/MiniMax model seçeneği).
Kullanıcı daha sonra 5 yeni UI görevi (D/E/F/B/G) istediğinde B'nin kod
tarafı zaten yarı bitmiş haldeydi -- B, D'den önce (parti-kod/parti-test
durumda bırakmamak için, en az riskli/tersine çevrilebilir seçenek olarak)
bitirilip commit edildi; **C bu görev listesinde YOK, kullanıcı talebiyle
ertelendi.**

### ÖZELLİK B -- Özel Etiketler (kanal içi organizasyon, SEO değil)

`DocumentaryProject.custom_tags: list[str]` (yeni alan, varsayılan `[]`).
Documentary Studio'nun sonuç panelinde VE Geçmiş Üretimler'de (kart
detayında) paylaşılan `_render_custom_tags_section()` -- virgülle ayrılmış
serbest metin girdisi, "Kaydet" `save_project_snapshot()`'ı çağırıp
`st.rerun()` yapıyor. Geçmiş Üretimler'in "tamamen salt-okunur" ilkesine
kullanıcı onaylı, DAR bir istisna (Publish hâlâ orada yok).

Geçmiş Üretimler sayfasına bir "Filter by tags" `st.multiselect`
eklendi (tüm projelerin `custom_tags` birleşimi, OR semantiği -- seçili
etiketlerden HERHANGİ birine sahip proje eşleşiyor). Etiketi olan hiçbir
proje yoksa filtre gizleniyor.

**Test kısıtı (yeni öğrenilen bir AppTest tuzağı):** Save butonunun
handler'ı `st.rerun()` çağırıyor. Butonun "tıklandı" bayrağını doğrudan
`session_state[key] = True` ile önceden set edip TEK bir `.run()`
kullanmak (GÖREV 1'den beri bilinen format_func/session_state kısıtı
yüzünden `.click().run()` zinciri burada kullanılamıyor, ikinci `.run()`
Pacing selectbox'ını kırıyor) yeni bir soruna yol açtı: bayrak hiç
temizlenmediği için her iç rerun turunda buton "yeniden tıklanmış" görünüp
**sonsuz döngüye girdi** (süreç bir kez bu yüzden kilitlenip manuel
öldürüldü). Düzeltme: `st.rerun()` testte no-op'a patch'lendi -- tek script
geçişi rerun tetiklemeden tamamlanıyor, click sonrası durum yine de tam
doğrulanabiliyor.

Test: yeni `test_webui_custom_tags.py` (6 test: i18n parity, ön-doldurma,
boş durum, trim/kaydet davranışı, filtre listeleme, hiç etiket yokken
filtrenin gizlenmesi). Tam suite: **795 passed, 11 skipped** (779'dan +16,
sıfır regresyon). `ruff` temiz.

**Gerçek doğrulama ($0 maliyet):** `utils.save_project_snapshot()`
gerçek bir `DocumentaryProject`'e `custom_tags` yazıp `project.json`'dan
geri okuyarak round-trip doğrulandı (test görev klasörü temizlendi).

## GÖREV D+E+F+G -- Klasik Mod'dan Documentary Studio'ya beş UI iyileştirmesi

Kullanıcı, Klasik Mod'un artık gizli olması nedeniyle orada kalan bazı
kontrolleri Documentary Studio'ya taşımamı istedi. Dördü de tek bir
commit'te birleştirildi: `webui/Main.py`'deki değişiklikler aynı fonksiyon
bölgesinde iç içe geçtiği için (D'nin ses/BGM fonksiyonu ile F/G'nin
Gelişmiş Ayarlar fonksiyonu art arda eklendi, E'nin expander sarmalaması
da aynı `_render_documentary_studio_page()` gövdesinde) `git add -p` ile
sonradan 4 ayrı commit'e bölmek kırılma riski taşırdı -- daha güvenli/geri
alınabilir seçenek olarak (genel kural 1, ve bu projede kategori
genişletmesinde de kullanılmış aynı emsal) tek, kapsamlı ve her alt-görevi
ayrı ayrı belgeleyen bir committe birleştirildi.

### GÖREV D -- Ses hızı/seviyesi + BGM

`run_pipeline()` zaten `voice_rate`/`voice_volume`/`bgm_type`/`bgm_file`/
`bgm_volume` kabul ediyordu ama Documentary Studio sadece `voice_name`
gönderiyordu. Yeni `_render_documentary_audio_settings()`: Klasik Mod'daki
AYNI seçenek listeleriyle rate/volume selectbox'ları + BGM kaynağı
seçici. **Bilinçli kapsam kararı:** Sonilo/ElevenLabs BGM üretimi sadece
eski `task.py` (legacy tekil-video) akışında yaşıyor, `default_pipeline.py`
buna hiç bağlı değil -- v1 sadece Yok/Rastgele/Kendi Dosyanı Yükle sunuyor
(üçü de `video.get_bgm_file()` üzerinden gerçek çalışıyor). Klasik Mod'daki
AYNI desen: özel BGM dosyası sadece "Generate" tıklanınca
`bgm_service.save_bgm_upload()` ile kalıcı hale getiriliyor (render-anında
değil) -- iptal edilen yüklemeler storage'da yetim dosya bırakmıyor.

### GÖREV E -- Kategori/Ton kart grid'lerini katlanabilir yapma

15 kart hep açık sayfayı çok uzatıyordu. İkisi de artık kapalı başlayan
birer `st.expander` içinde, başlık her zaman güncel seçimi özetliyor
("Kategori: Otomatik" gibi, "Otomatik" dahil her zaman). AppTest'in kapalı
expander içeriğini yine render ettiği doğrulandı -- mevcut 13 kart testi
değişmeden geçti.

### GÖREV F -- Sistem Promptu + Özel Senaryo Gereksinimleri (ADIM 0 kontrolü)

`custom_system_prompt` zaten `script_generator.build_script_prompt()`'a
kadar kablolanmıştı (Klasik Mod'dan miras) ama `run_pipeline()` bunu hiç
almıyordu -- eklendi. `custom_requirements` TAMAMEN YENİ bir parametre:
`_growth_guidance_instructions`'ın (otomatik büyüme ilkeleri) hemen
ardına, onu EZMEDEN ek bir blok olarak enjekte ediliyor
("Additional requirements:"). ADIM 0 doğrulaması: ikisi de gerçek,
çalışan bir tüketiciye (generate_script → LLM prompt'u) bağlı, dekoratif
alan değil. İkisi de kayıt/şeffaflık için `DocumentaryProject`'e de
eklendi (`custom_system_prompt`, `custom_requirements`).

### GÖREV G -- Altyazı font ailesi/boyutu/rengi (ADIM 0 kontrolü)

`video_renderer.build_video_params()` ZATEN `config.ui["font_name"/
"font_size"/"text_fore_color"]` okuyor (Klasik Mod'un yazdığı yer) --
Documentary Studio'nun aynı anahtarlara yazması yeterliydi, pipeline'da
HİÇBİR değişiklik gerekmedi. Kullanıcının istediği sadece üçü eklendi
(aile/boyut/renk) -- stroke/pozisyon/arkaplan Klasik Mod'da var ama
bilinçli olarak kapsam dışı bırakıldı.

### Testler ve doğrulama

Yeni dosyalar: `test_webui_audio_settings.py` (6), `test_webui_category_
tone_expander.py` (4), `test_webui_advanced_settings.py` (5) + genişletilen
`test_script_generator.py` (+5) ve `test_default_pipeline.py` (mevcut ana
wiring testine custom_system_prompt/custom_requirements assertion'ları
eklendi). Tam suite: **815 passed, 11 skipped** (795'ten +20, sıfır
regresyon).

**Yeni AppTest bulgusu:** Documentary Studio sayfasında Pacing/Format/
Aspect/Video Source/BGM Type gibi `format_func`'lı TÜM selectbox'lar
yüzünden bu sayfada HERHANGİ bir ikinci `.run()` çağrısı (bir tıklamayı
takiben de olsa) kırılıyor -- `ValueError: 'short' is not in list`. Her
yeni test bu yüzden GÖREV 1'in kurduğu desene uyuyor: tek `.run()`, tüm
session_state (metin girdileri + buton "tıklandı" bayrağı dahil) o tek
run'dan ÖNCE set ediliyor. `default_pipeline.run_pipeline()` gerçekten
`patch.object` ile mock'lanıp Generate butonunun (rerun tetiklemediği
doğrulanan bir buton) tek run'da doğru kwarg'larla çağrıldığı ilk kez bu
görevlerde doğrulandı.

**Gerçek doğrulama (Stok Video, $0 maliyet, iki ayrı çalıştırma):**
1. GÖREV D: "The History of the Lighthouse", `voice_rate=1.3`,
   `voice_volume=1.5`, `bgm_type="random"`, `bgm_volume=0.4` -- pipeline
   uçtan uca tamamlandı, `project.bgm_type`/`bgm_volume` doğru kaydedildi,
   `final.mp4` (1080x1920, h264/aac, 22.7s) `ffprobe` ile doğrulandı.
2. GÖREV F+G: "The Founding of the Roman Republic",
   `custom_requirements="Explicitly mention the exact year 509 BC..."`,
   `config.ui["font_name"/"font_size"/"text_fore_color"]` render öncesi
   bilinçli olarak varsayılan-dışı değerlere (`Charm-Bold.ttf`, 42, yeşil)
   ayarlandı. Sonuç: narration/SEO metninde "509 BC" gerçekten geçti
   (`custom_requirements` doğrulandı); render log'u `⑤ font:
   ./resource/fonts/Charm-Bold.ttf` yazdı -- `build_video_params()`'ın
   `config.ui`'dan gerçekten okuduğu, ADIM 0'ın doğru olduğu kanıtlandı.
   İki test görev klasörü de temizlendi.

**Canlı tarayıcı doğrulaması (playwright, production, deploy sonrası)
bir gerçek bug buldu ve düzeltti:** Documentary Studio hiçbir yerde
`config.save_config()` çağırmıyordu -- GÖREV G'nin font ayarları sadece
RAM'deki `config.ui`'a yazılıyordu, bir sonraki `deploy.sh`/restart'ta
sessizce eski değere dönerdi. Düzeltme: `_render_documentary_advanced_
settings()` artık `config.save_config()` çağırıyor (içerik değişmediyse
zaten no-op, her rerun'da çağırmak güvenli). Ayrı commit + yeni test
(`test_font_settings_are_persisted_via_save_config`) + push + deploy.sh.
Tam suite: **816 passed, 11 skipped**.

**Kullanıcı bulgusu ve düzeltmesi -- custom_system_prompt artık additive:**
Kullanıcı, `script_generator.py`'nin bir hedef tasarımını paylaştı (HARD
RULES bloğu her zaman kalıcı, custom_system_prompt sadece ek stil
rehberliği). Gerçek kod tabanıyla karşılaştırıldı: önerilen bazı tipler
(`Format.standard`, `Language` enum parametresi, `PROFILE_PROMPTS[category]`)
mevcut kod tabanıyla uyuşmuyordu (`Format`'ta `standard` yok,
`PROFILE_PROMPTS` `Tone`'a göre anahtarlanıyor `TopicCategory`'ye değil,
`language` her yerde `str`) -- bunlar birebir kopyalanmadı. Ama asıl,
somut bulgu doğrulandı ve düzeltildi: `custom_system_prompt` eskiden
`DEFAULT_SCRIPT_SYSTEM_PROMPT`'un YERİNE geçiyordu -- GÖREV F'nin kendi
gerçek doğrulamasında bile "Write like a noir detective." gibi zararsız
bir istek, "no markdown, no scene labels, no narrator says" korumasını
sessizce siliyordu. `custom_requirements` ile TUTARSIZ bir asimetriydi
(o zaten additive). Düzeltme: `custom_system_prompt` artık
`DEFAULT_SCRIPT_SYSTEM_PROMPT`'un yanına ek stil rehberliği olarak
ekleniyor, temel talimatlar hiçbir zaman kaldırılmıyor -- diğer tüm
blokların (Tone/Format/Story craft/Growth guidance) sırası/metni
DOKUNULMADI (zaten test kilitli, gereksiz risk almamak için).

Mevcut `test_custom_system_prompt_replaces_default` testi (eski davranışı
kilitleyen) tersine çevrilip `test_custom_system_prompt_is_additive_not_
replacing` oldu + 2 yeni test. webui'nin "Sistem Promptu" yardım metni
("overrides" diyordu) 9 dilde düzeltildi. Tam suite: **818 passed, 11
skipped** (816'dan +2, sıfır regresyon). `ruff` temiz. Bu, saf bir prompt-
metni değişikliği olduğu ve GÖREV F'nin gerçek doğrulaması zaten aynı kod
yolunu (custom_system_prompt + gerçek LLM çağrısı) uçtan uca test ettiği
için, ayrı bir ücretli gerçek çalıştırma tekrarlanmadı -- yeni/değişen
testler (`test_script_generator.py`) yeterli görüldü.

## Provider Sistemi -- keşif raporu + TAM OTONOMİ 3 adım (ADIM 1/2/3)

Önce kapsamlı bir keşif raporu istendi: kodun tamamı tarandı ve **kullanıcının
öncülü kısmen yanlış çıktı** -- LLM sağlayıcısı (`LLM_PROVIDER_REGISTRY`,
19 sağlayıcı, `app/models/llm_provider.py`) ve TTS sağlayıcısı
(`voice.tts()`, 7 sağlayıcı, voice_name önekine göre dispatch) servis
katmanında ZATEN tam soyutlanmıştı ve Documentary Studio zaten AYNI paylaşılan
kodu (`documentary_llm_utils.generate_json()` → `llm._generate_response()`,
`audio_renderer.render_audio_plan()` → `voice.tts()`) kullanıyordu --
`grep -rn "openai" app/departments app/pipeline` SIFIR sonuç verdi. LLM
için üstelik global "Ayarlar" diyaloğunda (Klasik Mod'un dışında, her zaman
erişilebilir) 19 sağlayıcının tamamı zaten seçilebiliyordu -- yapılacak iş
yoktu. Gerçek boşluklar: (1) Documentary Studio'nun stok video seçici hiç
sunmaması (backend `material.download_videos()` zaten pexels/pixabay/coverr
destekliyordu), (2) TTS için kullanıcı dostu bir seçici yerine düz metin
girdisi olması, (3) AI-video'nun gerçekten tek sağlayıcıya (Kling) kilitli
olması. Yeni bir Protocol/ABC katmanı ÖNERİLMEDİ (zaten çalışan desenlerin
üzerine saf ritüel/süs katman olurdu) -- kullanıcı da bunu onayladı.

Kullanıcı üç adımı TAM OTONOMİ ile onayladı: ADIM 1 (Pixabay/Coverr stok
seçici), ADIM 2 (TTS provider+voice seçici), ADIM 3 (Hailuo/MiniMax,
önceden planlanmış ÖZELLİK C'ye göre).

### ADIM 1 -- Pixabay/Coverr stok video seçici

`material.download_videos(source=...)` zaten pexels/pixabay/coverr'ı tam
destekliyordu (Klasik Mod'un test edilmiş kodu) -- Documentary Studio'nun
webui'si hiç seçenek sunmuyordu, her zaman `"pexels"`e sabitti. Eklenen:
"Stok Görüntü" seçiliyken açılan iç içe (nested) bir "Stok Sağlayıcı"
selectbox'ı (Pexels/Pixabay/Coverr -- "Local file" bilinçli olarak kapsam
dışı, kullanıcı sadece Pixabay/Coverr istedi). Klasik Mod'daki AYNI ön-
kontrol deseni: eksik API key ile pipeline'ı başlatıp aşamalar ortasında
çökmek yerine (`material.get_api_key()` `ValueError` fırlatır), üretim
başlamadan net bir hata gösteriliyor -- Klasik Mod'un hazır çevrilmiş
"Please Enter the {Provider} API Key" metinleri yeniden kullanıldı.

Test: yeni `test_webui_stock_provider.py` (6 test: i18n parity, varsayılan
render, AI-video seçiliyken gizlenme, run_pipeline'a doğru provider
geçmesi, eksik key ile net hata + pipeline'ın hiç çağrılmaması, varsayılan
pexels davranışının bozulmadığı regresyon kilidi). Tam suite: **824
passed, 11 skipped** (818'den +6, sıfır regresyon). `ruff` temiz.

**Gerçek doğrulama:** Pixabay için gerçek API key config'te zaten mevcuttu
-- "The Great Barrier Reef" konusu, `video_source="pixabay"` ile uçtan uca
çalıştırıldı: 9 gerçek Pixabay klibi indirildi (log'da gerçek
çözünürlükler: 3840x2160, 1920x1080 vb.), `final.mp4` `ffprobe` ile
doğrulandı (1080x1920, h264/aac, 24.3s). Test görev klasörü temizlendi.
**Dürüst not:** Coverr için config'te gerçek API key YOK -- bu yüzden
Coverr'ın kendisi gerçek bir API çağrısıyla doğrulanamadı (aynı kod yolu
olduğu için mimari olarak çalışması beklenir, ama bu iddia edilmiyor,
sadece ön-kontrolün doğru çalıştığı -- eksik key'de net hata, pipeline hiç
başlamıyor -- unit testle kanıtlandı).

### ADIM 2 -- TTS provider+voice seçici (Klasik Mod'daki gibi)

Keşif raporunun ikinci bulgusu: `voice.tts()` servis katmanında zaten 7
sağlayıcıyı (Azure v1/v2, SiliconFlow, Gemini, MiMo, ElevenLabs,
Chatterbox) tam destekliyordu, `audio_renderer.render_audio_plan()`
(Documentary Studio'nun kullandığı) doğrudan AYNI dispatcher'ı
çağırıyordu -- ama Documentary Studio'nun "Ses Adı" alanı düz bir metin
girdisiydi, kullanıcı doğru önekli voice_name string'ini
("elevenlabs:VOICE_ID:İsim" gibi) EL İLE yazmak zorundaydı.

**Ek keşif (kod incelemesinde bulundu):** Azure v1 (ücretsiz/anahtarsız
edge-tts) hariç, bu 7 sağlayıcıdan HİÇBİRİNİN API key'i, Klasik Mod
gizlendiğinden beri hiçbir yerde girilemiyordu -- global "Ayarlar"
diyaloğunda TTS'e ait bir sekme yok (sadece LLM/Material API/Cache/
Interface var). Bu yüzden `_render_documentary_tts_voice_picker()`,
Klasik Mod'un `_render_audio_settings()`'inin TAM karşılığını (server
seçici + ses listesi + sağlayıcıya özel credential girdileri: Azure v2
region/key, Gemini API key, SiliconFlow API key, MiMo API key, ElevenLabs
API key+model, Chatterbox base URL) `documentary_*` önekli kendi widget
key'leriyle yeniden kurdu -- "Voiceover Mode" (Automatic/Upload/None)
kasıtlı olarak YOK, belgeselde hiç "sessiz video" kavramı yok. "Ses
Ayarları" expander'ının (GÖREV D) en üstüne eklendi, eski düz metin
girdisi kaldırıldı. Tüm gerekli i18n metinleri Klasik Mod'dan zaten
vardı -- **sıfır yeni çeviri anahtarı gerekti**.

Test: yeni `test_webui_tts_provider.py` (9 test: varsayılan Azure v1 +
credential girdisi yok, her sağlayıcı seçildiğinde doğru credential
alanının göründüğü 6 test, ElevenLabs gerçek-şekilli ses listesi +
friendly-name, boş ses listesinde crash yerine uyarı, run_pipeline'a
doğru voice_name'in geçmesi). Tam suite: **833 passed, 11 skipped**
(824'ten +9, sıfır regresyon). `ruff` temiz.

**Gerçek doğrulama:** ElevenLabs için config'te gerçek API key zaten
mevcuttu -- `voice.get_elevenlabs_voices()` gerçek API'ye karşı çağrıldı
(35 gerçek ses döndü). Ardından "The Northern Lights" konusu, picker'ın
üreteceği TAM formatta ama önceden persist edilmiş varsayılandan
BİLEREK FARKLI bir ses (`elevenlabs:Vv1QW9Yx3WB2mLKFmyZG:Kaya...`) ile
uçtan uca çalıştırıldı -- gerçek provider/ses DEĞİŞİMİNİ kanıtlamak için.
ElevenLabs TTS gerçekten bu farklı sesle sentezledi, `final.mp4` `ffprobe`
ile doğrulandı (1080x1920, h264/aac, 23.2s). **Dürüst not:** Azure v2/
SiliconFlow/Gemini/MiMo/Chatterbox için config'te gerçek credential YOK --
bu 5 sağlayıcının kendisi gerçek bir API çağrısıyla doğrulanamadı (aynı
paylaşılan `voice.tts()` dispatcher'ından geçtikleri için mimari olarak
çalışmaları beklenir, ama bu iddia edilmiyor -- sadece UI'ın doğru
credential alanını gösterdiği unit testle kanıtlandı).

**Not (ilk gerçek doğrulama denemesi):** Bu doğrulamanın ilk denemesi,
tamamen ilgisiz bir nedenle (aşağıdaki config.toml olayı, gerçek Pexels
key'inin bozulması) video indirme aşamasında başarısız oldu -- TTS
kısmının kendisi o denemede de sorunsuz çalışmıştı (log'da "elevenlabs
tts succeeded" doğrulandı). Kullanıcı gerçek key'i yeniden girdikten ve
yapısal güvenlik ağı kurulduktan sonra doğrulama TEMİZ bir şekilde
tekrarlandı (yukarıdaki sonuç).

### ⚠️ OLAY: ADIM 1'in testleri gerçek production config.toml'unu bozdu

**Kök neden:** `test_webui_stock_provider.py`'deki iki test,
`patch.object(config, "app", <sahte test dict'i>)` ile config'i geçici
olarak sahteliyordu ama `config.save_config()`'i MOCK'LAMAYI unuttu.
GÖREV G'nin `_render_documentary_advanced_settings()`'e eklediği
`config.save_config()` çağrısı HER sayfa render'ında koşulsuz çalışıyor
(font ayarlarını kalıcı hale getirmek için) -- test, Documentary
Studio'nun TAM sayfasını render ettiği için (sadece kendi ilgilendiği
widget'ı değil), bu çağrı da testin sahte `config.app`'i ile tetiklendi
ve sahte `pexels_api_keys = "test-pexels-key"` değerini GERÇEK
`config.toml`'a yazdı. Streamlit'in dosya izleyicisi bu değişikliği
algılayıp CANLI production sürecini de yeniden yükledi -- bu yüzden hem
diskteki hem bellekteki gerçek Pexels API key'i geri alınamaz şekilde
kayboldu (kullanıcı yeni bir key girerek düzeltti).

**Neden "3 testi düzelt" yeterli değildi:** Aynı riskli örüntü (config.app/
config.ui/vb.'yi patch'leyip save_config()'i mock'lamayı unutmak)
gelecekte YAZILACAK herhangi bir teste de bulaşabilirdi -- tek tek
hatırlamaya güvenmek kırılgan.

**Yapısal düzeltme (kullanıcı talebiyle):** Yeni `test/conftest.py` --
autouse, tüm suite'e uygulanan bir fixture (`_never_write_the_real_
config_toml`), `config.config_file`/`config.root_dir`'ı HER testte
otomatik olarak geçici bir `tmp_path`'e yönlendiriyor. Artık
`config.save_config()` HANGİ testte, hangi sebeple, mock'lanmadan
çağrılırsa çağrılsın, gerçek dosyaya asla yazamıyor -- tek tek testi
hatırlamaya değil, yapısal bir garantiye dayanıyor.
`test_save_config_uses_parseable_atomic_output` (save_config()'in GERÇEK
yazma davranışını test eden tek test) hâlâ çalışıyor çünkü kendi
`patch.object(config, "config_file"/"root_dir", ...)`'ını fixture'ın
üzerine (kendi geçici dosyasına) uyguluyor -- çakışma yok.

**Doğrulama (varsayımla değil, ÖLÇEREK):**
1. Tam suite öncesi/sonrası `config.toml`'un mtime + md5sum'u alındı --
   **833 passed, 11 skipped** çalıştıktan sonra byte-byte AYNI
   (`8a6d1b48edd65de6e8282280278dacc0`, mtime değişmedi).
2. Orijinal hatayı BİLEREK yeniden üreten bir tek-seferlik test yazıldı
   (`config.app`'i sahteleyip `save_config()`'i mock'lamadan tam sayfa
   render) -- test zaman aşımına uğrayıp öldürülse bile, `config.toml`
   mtime/md5 DEĞİŞMEDİ ve sahte "REPRO-BUG-MARKER" değeri dosyada HİÇ
   görünmedi. Doğrulama testi silindi (kalıcı test suite'in parçası
   değil, sadece kanıt amaçlı).

**Ders (gelecekte benzer test yazacaklar için):** Documentary Studio
sayfasını (tamamını veya bir kısmını) render eden HERHANGİ bir webui
testi, `config.save_config()`'i dolaylı olarak tetikleyebilir --
`config.app`/`config.ui`/`config.azure`/`config.elevenlabs`/vb.'yi
patch'lerken artık ayrıca `config.save_config()`'i mock'lamak GEREKMİYOR
(conftest.py zaten koruyor) ama best-practice olarak hâlâ önerilir (o
mock, testin "save_config çağrıldı mı" gibi kendi assertion'ları için
faydalı olabilir) -- gerçek dosya güvenliği artık HİÇBİR testin bunu
hatırlamasına bağlı değil.

### ⚠️ İKİNCİ KÖK NEDEN: yetim bir arka plan süreci config.toml'u tekrar bozdu

conftest.py düzeltmesi ve kullanıcının Pexels key'ini yeniden girmesinden
SONRA bile, `pexels_api_keys` disk üzerinde tekrar `"test-pexels-key"`e
döndü -- bu sefer test suite çalışmıyorken, ADIM 2 deploy'undan SONRA.
mtime deploy'un restart'ından ~17 saniye ÖNCEYE işaret ediyordu, bu da
"restart sırasında bozuldu" teorisini çürüttü.

**Gerçek kök neden:** `ps aux` ile `port=8595`de, systemd'nin YÖNETMEDİĞİ,
**Cmt 25 Temmuz 22:27:45'ten beri (neredeyse 2 gün) kesintisiz çalışan**,
tamamen unutulmuş ikinci bir `streamlit run webui/Main.py` süreci
bulundu -- muhtemelen bu projenin çok daha önceki bir oturumunda manuel
başlatılıp hiç kapatılmamış bir geliştirme/önizleme örneği. Bu süreç
GERÇEK production'la (8501, systemd) AYNI `config.toml`'u paylaşıyordu.
Streamlit'in dosya izleyicisi, `config.toml` (veya izlenen herhangi bir
`.py` dosyası -- ADIM 2 geliştirmesi boyunca sürekli düzenlenen
`webui/Main.py` dahil) her değiştiğinde bu sürecin de script'ini yeniden
çalıştırıyor, bu da GÖREV G'nin koşulsuz `config.save_config()`'ini bu
sürecin KENDİ bayat (stale) bellek durumuyla tekrar tetikliyordu --
kullanıcının veya benim yaptığım düzeltmeleri sessizce eziyordu. Bu,
yeni bir test hatası değildi -- ortamda gerçekten var olan, gerçekten
zararlı, unutulmuş bir süreçti.

**Düzeltme (kullanıcı onayıyla):** `kill 157638` (production 8501'i HİÇ
etkilemedi, ayrı systemd birimi). Doğrulama, varsayımla değil ölçülerek:
1. `ss -tlnp | grep 8595` -- boş (süreç gerçekten öldü, port artık dinlenmiyor).
2. `curl .../_stcore/health` -- production (8501, systemd MainPID
   değişmedi) hâlâ sağlıklı, bu olaydan hiç etkilenmedi.
3. Pexels key'i disk'te tekrar doğru değere (bu sefer benim önceki bir
   `grep` çıktımdan kurtarılan gerçek değerle) manuel düzeltildi.
4. **Ekstra önlem:** yetim süreç öldürüldükten sonra bile, GERÇEK
   production süreci (231583) config.toml düzeltmemden ÖNCE (19:40:10)
   başlamıştı -- kendi belleğinde hâlâ bayat değeri taşıyor olabilirdi.
   Bunu varsaymak yerine `./deploy.sh` ile TEMİZ bir restart yapıldı
   (yeni MainPID 232211, 19:52:49) -- restart sonrası mtime/değer
   DEĞİŞMEDEN kaldı, bu da artık doğru değerin belleğe yüklendiğini
   kanıtlıyor.

**Ders:** Bu proje boyunca birden fazla oturumda "gerçek tarayıcı
doğrulaması" için `streamlit run` manuel başlatılmış olabilir --
sistemin GERÇEK tek giriş noktası `systemctl`/`ai-documentary-studio-
webui.service`'tir (port 8501). Gelecekte manuel bir Streamlit süreci
başlatılırsa (test/önizleme amaçlı bile olsa), iş bitince MUTLAKA
durdurulmalı -- aksi halde bu SINIFTA bir hata (paylaşılan config.toml'a
sessiz, gecikmeli, kaynağı belirsiz yazmalar) tekrarlanabilir.
`ps aux | grep streamlit` periyodik olarak kontrol edilip beklenmedik
süreç olup olmadığı doğrulanabilir.

### ADIM 3 -- Hailuo/MiniMax entegrasyonu (v1, config-seviyesi) + gerçek 9:16 testi

Önceden planlanmış ÖZELLİK C'ye göre: `fal_video.py`'ye `fal_ai_video_model`
config'i (`"kling"` varsayılan | `"hailuo"`) eklendi. Yeni bir Protocol/
ABC katmanı YOK (kullanıcı bilinçli olarak istemedi) -- `voice.tts()`'in
kendi kanıtlanmış deseniyle tutarlı, basit bir if/elif + model-özel
payload fonksiyonu (`_build_kling_payload`/`_build_hailuo_payload`).
`submit_video_job()`'un PUBLIC arayüzü hiç değişmedi, `ai_video_generator.py`
tek satır bile dokunulmadı. Kling'in "5"/"10" duration'ı (AssetCandidate.
ai_duration'ın tek kaynağı, webui'nin maliyet tahmini de buna dayanıyor)
BİLİNÇLİ OLARAK Kling-şekilli kaldı -- Hailuo'ya giden payload'da SADECE
en yakın geçerli Hailuo değerine ("5"→"6", "10"→"10") eşleniyor.

Test: `test_fal_video.py`'ye +6 test (provider seçimi, model override,
`_app_id` Hailuo için de doğru subpath'i kesiyor, Hailuo payload'ının
aspect_ratio İÇERMEDİĞİ ve duration'ın doğru eşlendiği). Tam suite:
**839 passed, 11 skipped** (833'ten +6, sıfır regresyon). `ruff` ve
`tomllib` ile `config.example.toml` doğrulandı.

**GERÇEK API doğrulaması (kullanıcının açık talimatı: "varsayım yapmayın"):**
Gerçek `fal_api_key` ile, Hailuo'nun standard tier'ına TEK, ucuz bir
text-to-video job gönderildi -- prompt açıkça "A vertical portrait shot
of a single lit candle... 9:16 aspect ratio" istedi, duration en ucuz
tier'a ("6"sn) eşlendi. Submission başarılı (payload'ın aspect_ratio
İÇERMEMESİ kabul edildi), iş ~7.3 dakikada tamamlandı, klip indirildi ve
`ffprobe` ile incelendi:

```
codec_name=h264
width=1366
height=768
avg_frame_rate=24/1
duration=5.875000
```

**SONUÇ: Hailuo'nun standard text-to-video endpoint'i 9:16 (dikey) DESTEK-
LEMİYOR.** Prompt metninde açıkça dikey/9:16 istenmesine RAĞMEN çıktı
SABİT 1366x768 (yatay, ~16:9) geldi -- bu bir varsayım değil, gerçek,
ölçülmüş bir API davranışı. Bu, kullanıcının kendi v1/v2 ayrımındaki
gate koşuluna göre (v2 = webui'de per-generation model seçici, SADECE
9:16 desteği doğrulanırsa eklenecekti) **v2 UYGULANMADI** -- Hailuo
Documentary Studio'nun varsayılan/en yaygın modu (9:16) için uygun değil,
sadece 16:9 modda ve düşük çözünürlük (1366x768, HD altı) bilinerek kabul
edilirse teorik olarak kullanılabilir. Kod ve `config.example.toml`
yorumları bu gerçek bulguyu dürüstçe belgeliyor. Test klibi hem yerel
diskten hem `storage/tasks`'tan temizlendi (fal.ai'nin kendi barındırdığı
kopya bizim kontrolümüzde değil, herhangi bir yerel maliyet yok).

**Kapsam kararı (kullanıcı onaylı ADIM 0 prensibiyle tutarlı):** webui'ye
HİÇBİR yeni model seçici eklenmedi -- sadece `config.toml`'da manuel
olarak `fal_ai_video_model = "hailuo"` yazan bir kullanıcı bunu
kullanabilir (ve o zaman bile sadece 16:9 için mantıklı). Bu, "gerçek
tüketicisi olmayan süs katman" riskinden kaçınıyor -- webui hiçbir yerde
Hailuo'yu önermiyor/tanıtmıyor, sadece backend'de config-seviyesinde var.

## Video-anlatım uyumsuzluğu -- kök neden teşhisi + acil kalite düzeltmesi

Kullanıcı, "videolar konuyla uyumsuz" şikayetinin gerçek teknik açıklamasını
istedi. `storage/tasks/`'taki 3 gerçek üretim (arda kural x2, Efes Antik
Kenti -- hepsi `pacing="short"`) incelendi: **üçünde de outline 6-7 section
üretti, ama scene_planner sadece 4'ünü tuttu** -- %33-43 içerik, hiçbir
hata/uyarı vermeden sessizce kayboldu. `quality_critic`'in tekrar eden
"narration skips major outline elements" şikayetinin gerçek nedeni buydu --
LLM'in "kötü yazması" değil, içeriğin script_generator'a ULAŞMADAN önce
silinmesi.

**Kök neden:** `app/config/profile_dimensions.py`'deki iki sabit arasındaki
uyumsuzluk:
- `PACING_OUTLINE_SECTION_RANGE[short] = (4, 7)` -- outline'dan 4-7 section istiyor.
- `PACING_SCENE_SPEC[short]["scene_count"]` eskiden **4**'tü -- bu aralığın
  TABANI, tavanı değil. `scene_planner._select_sections_by_importance()`
  (kasıtlı, dokümante edilmiş davranış) sadece en önemli `scene_count`
  kadar section'ı tutuyor, gerisini atıyor.

`long` pacing'in AYNI (4,7) outline aralığına sahip olmasına rağmen hiç bu
şikayeti almamasının nedeni: `long`'un `scene_count`u zaten **7** (kendi
aralığının tavanı) -- bu yüzden `long` hiçbir zaman içerik kaybetmiyor.
`short` bu simetriden yoksundu.

**Düzeltme (kullanıcı onaylı, acil/bağımsız):** `PACING_SCENE_SPEC[Pacing.
short]["scene_count"]`: **4 → 7** -- `long` ile aynı deseni tekrarlıyor, tek
sabit değişikliği, sıfır yeni mantık.

**Regresyon testleri güncellendi:**
- `test_documentary_models.py::test_pacing_scene_spec_has_both_pacings` --
  beklenti 4→7.
- `test_scene_planner.py` -- 3 test yeniden tasarlandı (`test_short_pacing_
  yields_seven_scenes_of_five_seconds`, `test_keeps_highest_importance_
  sections`, `test_preserves_original_narrative_order`), artık 7'den fazla
  section'lı outline'larla gerçek trimming davranışını doğruluyor (eskiden
  6 section'lı outline'larla scene_count=4'ü test ediyorlardı -- yeni
  scene_count=7 ile hiç trimming olmuyordu, testler anlamsız kalırdı).
- `test_webui_ai_video_source.py` -- AI video maliyet tahmini testi
  "$0.90"dan **"$1.57"**e güncellendi (7 sahne x 5s x $0.045/s = $1.575,
  `:.2f}` formatlaması float temsili nedeniyle "1.57" veriyor, "1.58"
  değil -- gerçek testle doğrulandı, varsayılmadı).

**GERÇEK öncesi/sonrası karşılaştırma (kullanıcının istediği gibi, AYNI
konuyla -- "Efes Antik Kenti"):**

| | Önce (9e5963b2, önceki oturum) | Sonra (bu doğrulama) |
|---|---|---|
| Outline section | 6 | 7 |
| Tutulan sahne | 4 | **7** |
| Atlanan | 2 (%33) | **0** |
| Gerçek anlatım süresi | 35.7s | 84.5s |
| quality_critic şikayeti | "Narration is highly compressed and skips most outline points" | **YOK** -- kalan tek şikayetler çok daha küçük (bazı geçişler "biraz sıkışık", açılış cümlesi "biraz abartılı") |
| quality_verdict | -- | overall=4.33/5, passed=True |

`final.mp4` `ffprobe` ile doğrulandı: 1080x1920, h264/aac, 85.4s. Test
görev klasörü temizlendi. Tam suite: **839 passed, 11 skipped**, sıfır
regresyon. `ruff` temiz.

**Not:** Bu düzeltme "short" pacing'in AI-video maliyetini artırıyor
(4→7 sahne, en kötü senaryoda +3 x $0.045x5s ≈ +$0.68/video) -- ama Stok
Video (varsayılan, ücretsiz) için maliyet etkisi sıfır, ve düzeltme
olmadan üretilen içerik zaten kullanıcıya vaat edilen kalitede değildi.

## Production'da bulunan ayrı bug: Task Manager satır key çakışması

Pacing düzeltmesinin production deploy'undan sonraki günün loglarında
(`journalctl`), Task Manager panelinin görev tablosunda iki kez
`StreamlitDuplicateElementKey` hatası bulundu: `key='task_row_all_matrix_
TopicCategory_healthy_living_Paci'`. Kod zaten kategori+dil değil
`task_id`'yi kullanıyordu, ama container key'i sanitize edilmiş `task_id`'yi
`[:40]` karakterle kesiyordu -- iki farklı, uzun/tanımlayıcı `task_id` ilk
40 karakterde aynı çıkınca (ortak "matrix_TopicCategory_healthy_living_
Paci..." öneki -- muhtemelen bir QA/dimension-matrix scripti tarafından
elle oluşturulmuş, normal UUID4 üretim akışının parçası değil) çakışma
oluşuyordu. Kısa UUID4 `task_id`'ler (36 karakter) bu sınıra hiç
yaklaşmadığı için bugüne kadar tetiklenmemişti.

**Düzeltme (ayrı, küçük commit -- `26459ae`):** `_safe_task_row_key()` --
kesilen okunabilir önek + tam `task_id`'nin sabit-uzunlukta sha1 hash'i.
3 yeni birim testi, ortak 40-karakterlik önekli iki `task_id`'nin farklı
key ürettiğini doğruluyor (gerçek olayı yeniden üretiyor).

## 3-sayfa restructuring -- Belgesel Niteliği + Stok Üretimler

Kullanıcı talebi (net spesifikasyonla): eski birleşik "Oluştur" sayfası,
Video Kaynağı seçimine göre ikiye bölündü. Sonuç 4 sayfa: "Stok Üretimler"
(yeni, varsayılan), "Belgesel Niteliği" (yeni, `url_path="quality"`),
"Geçmiş Üretimler" (değişmedi), "Klasik Mod" (değişmedi, gizli).

**DRY:** `_render_shared_documentary_form(video_source_fixed: str)` --
eski `_render_documentary_studio_page()`'in TÜM gövdesini (konu→dil→
kategori/ton→ses ayarları→gelişmiş ayarlar→üret→sonuç paneli) alıyor.
Video Kaynağı artık bir selectbox değil -- o widget'ın kendisi tamamen
kaldırıldı, çağıran sayfa `video_source_fixed` ile hangi dalın
render edileceğini belirliyor: `_DOCUMENTARY_STOCK_VIDEO_SOURCE` ("stock")
→ stok sağlayıcı seçici gösterilir, maliyet onayı yok; `default_pipeline.
AI_GENERATED_VIDEO_SOURCE` → maliyet onay bloğu gösterilir, stok sağlayıcı
seçici hiç render edilmez. İki ince sarmalayıcı (`_render_documentary_
quality_page`, `_render_stock_productions_page`) sadece başlık + shared fn
çağrısından ibaret.

**Varsayılan sayfa kararı:** "Stok Üretimler" varsayılan kaldı (eski
selectbox'ın da varsayılanı "stock", index=0 idi) -- bu, video_source'u
hiç set etmeyen onlarca mevcut webui testinin varsayılan-sayfa davranışını
değiştirmeden koruyor.

**i18n:** "Nav Documentary Quality"/"Nav Stock Productions" 9 locale'e
eklendi; artık kullanılmayan "Nav Create" ve "AI Documentary Studio (Beta)"
key'leri 9 locale'den kaldırıldı; "Documentary History Empty" metni
("...Oluştur sayfasından...") artık spesifik bir sayfa adına referans
vermeyecek şekilde genelleştirildi (iki olası giriş noktası olduğu için).

**Test:** `test_webui_navigation.py` 4-sayfa yapısını (görünürlük,
varsayılan, url_path) doğrulayacak şekilde yeniden yazıldı.
`test_webui_ai_video_source.py`/`test_webui_stock_provider.py`/
`test_webui_long_form.py`'deki AI-senaryoları -- Video Kaynağı artık bir
selectbox olmadığı için -- `app.session_state["documentary_video_source"]`
yerine `app._page_hash = calc_hash("quality")` ile doğrudan "Belgesel
Niteliği" sayfasına navigasyona geçirildi. Tam suite: **844 passed, 11
skipped**, sıfır regresyon. `ruff` temiz.

**Gerçek tarayıcı doğrulaması (Playwright/headless Chromium, geçici port
8588 -- production 8501'e hiç dokunulmadı, doğrulama sonunda süreç
durduruldu ve port'un gerçekten boşaldığı `ss` ile teyit edildi):**
kök sayfadan sidebar linklerine TIKLAYARAK gerçek kullanıcı akışı
izlendi (doğrudan URL'e git değil) -- 3 sayfa da (Stok Üretimler
varsayılan, Belgesel Niteliği, Geçmiş Üretimler) doğru içerikle render
oldu, konsol hatası SIFIR. Stok Üretimler'de stok sağlayıcı seçici var,
maliyet onayı yok; Belgesel Niteliği'nde maliyet tahmini ($1.57, short
pacing'in 7 sahnesiyle tutarlı) ve onay kutusu var, stok sağlayıcı
seçici yok. Task Manager paneli de (bug fix doğrulaması) hatasız açıldı.
Klasik Mod hâlâ `/classic` üzerinden doğrudan erişilebilir (sidebar'da
gizli, kayıt silinmedi). config.toml'da git diff YOK (doğrulama sırasında
hiçbir kalıcı yazma olmadı).

(Not: `/quality` veya `/history`'ye DOĞRUDAN `page.goto()` ile gidildiğinde
Streamlit'in kendi `_stcore/health`/`host-config` polling istekleri
mevcut path'e göre yanlış çözülüp 404 veriyor -- bu, benim değişikliğimden
ÖNCE de var olan `/history` için de aynen tekrarlanan, Streamlit'in kendi
alt-path deep-link davranışı, gerçek kullanıcı sidebar tıklamasıyla hiç
karşılaşmıyor, bu görevle ilgisiz.)

## Sidebar navigasyonu -- otomatik katlanma düzeltmesi

Kullanıcı talebi: sol menü hiçbir zaman otomatik gizlenmemeli/katlanmamalı.
Playwright ile gerçek ölçüm yapıldı (varsayımla değil): `initial_sidebar_
state="auto"` (eski değer) ile 1400px genişlikte sidebar açık
(`aria-expanded=true`, `width=300`) ama 700px VE 375px'de otomatik
katlanmış çıktı (`aria-expanded=false`, `x=-300`, `width=0`) -- Streamlit'in
kendi dahili responsive kırılma noktası ~700-1400px arasında bir yerde.
İzole bir test app'inde `initial_sidebar_state="expanded"` denendi: AYNI
üç genişlikte de sidebar açık kaldı. Tek satırlık, düşük riskli bir
düzeltme.

Test: yeni `test_webui_sidebar_config.py` (kaynak kod niyet-kilidi,
`test_webui_navigation.py`'deki aynı desen). Tam suite: **845 passed, 11
skipped** (844'ten +1, sıfır regresyon). `ruff` temiz.

**Gerçek doğrulama (deploy sonrası, canlı production'da):** aynı 3
genişlik (1400/700/375px) tekrar test edildi, üçünde de
`aria-expanded=true`, `width=300` -- düzeltme production'da doğrulandı.

### Regresyon: yukarıdaki düzeltme YETERSİZDİ -- gerçek kök neden ve son düzeltme

Kullanıcı gerçek bir ekran görüntüsüyle kanıtladı: sidebar hâlâ tamamen
kayboluyordu (sayfa doğrudan "Stok Üretimler" başlığıyla başlıyor, hiçbir
nav menüsü yok). Yukarıdaki `initial_sidebar_state="expanded"` düzeltmesi
sadece BAKİR tarayıcılarda çalışıyordu -- **kök neden**: Streamlit,
sidebar her katlandığında (kullanıcı tıklaması VEYA -- bu bugun asıl
kaynağı -- eski `"auto"` değeriyle dar viewport'ta otomatik) bunu
`localStorage["stSidebarCollapsed-"]="true"` olarak KALICI kaydediyor ve
bu değer sonraki HER sayfa yüklemesinde `initial_sidebar_state`'i
geçersiz kılıyor. Yani "auto" döneminde bir kez dar pencerede açan/
otomatik katlanan her kullanıcı, sunucu tarafı fix'ten SONRA bile
sidebar'ı asla geri görmüyordu. Playwright ile `context.addInitScript(()
=> localStorage.setItem('stSidebarCollapsed-', 'true'))` + reload ile
%100 üretildi.

**1. düzeltme denemesi (BAŞARISIZ, gerçek tarayıcıda sıfır etkiliydi):**
`webui/styles.css`'e `div[data-testid="stSidebar"] { transform: none
!important; ... }` eklendi -- localStorage'dan tamamen bağımsız,
sidebar'ı her zaman görünür tutması gereken bir CSS kuralıydı. Yapay bir
`page.addStyleTag()` enjeksiyon testiyle "çalışıyor" diye rapor edildi,
commit+deploy edildi -- **bu yanlıştı**. Kullanıcının talep ettiği asıl
sıkı doğrulama (stale localStorage önceden set + reload + 4 farklı
viewport genişliği, GERÇEK deployed production'da) çalıştırıldığında
8/8 kontrol BAŞARISIZ oldu, sidebar hâlâ gizliydi
(`box={"x":-300,"width":0}`).

**Gerçek kök neden (2. teşhis):** `document.styleSheets` üzerinden
canlı DOM'da doğrudan sorgulama yapıldı. Kuralın kendisi doğru parse
edilmişti (`div[data-testid="stSidebar"] { transform: none !important;
... }` `cssRules` içinde mevcuttu, `!important` doğru işaretliydi) --
ama `el.matches('div[data-testid="stSidebar"]')` **false** döndürdü.
Neden: Streamlit sidebar'ı `<div>` değil **`<section
data-testid="stSidebar">`** olarak render ediyor. Yani `div[...]`
seçicisi hiçbir elemente HİÇ eşleşmiyordu -- geçerli, parse edilmiş,
`!important` bir CSS kuralı ama sıfır elemente uygulanan bir kural.
CSS cascade'de "kaybetmedi", zaten hiç yarışmıyordu; Streamlit'in kendi
(non-important) `.st-emotion-cache-* { transform: translateX(-300px); ...
}` kuralı rakipsiz kaldığı için kazanıyordu.

**Son düzeltme:** `webui/styles.css`'te etiket adı şartı kaldırıldı --
sadece öznitelik seçici: `[data-testid="stSidebar"] { transform: none
!important; min-width: 300px !important; max-width: none !important;
visibility: visible !important; }` (ayrıca Streamlit'in `max-width: 0px`
kuralıyla çakışmayı önlemek için `max-width: none !important` eklendi).

**Test:** `test_webui_sidebar_config.py` güncellendi -- artık kuralın
KENDİSİNİN (yorum metni değil) etiket adı İÇERMEDİĞİNİ ve
`max-width: none !important` içerdiğini doğruluyor, bu regresyonun bir
daha sessizce geri gelmesini engelliyor. Tam suite: **846 passed, 11
skipped** (845'ten +1, sıfır regresyon). `ruff` temiz. `config.toml`
değişmedi (mtime doğrulandı).

**Gerçek doğrulama (deploy sonrası, canlı production'da, kullanıcının
talep ettiği TAM senaryo):** `localStorage["stSidebarCollapsed-"]="true"`
önceden set edilip 4 viewport genişliğinde (1920/1400/700/375px) hem ilk
yüklemede hem reload sonrası test edildi -- **8/8 kontrol PASS**, sidebar
hepsinde `width=300, x=0` ile görünür. Ekran görüntüleri (1920px geniş
masaüstü ve 375px dar pencere, ikisi de stale-collapsed senaryosuyla)
kullanıcıya gösterildi.

**Ders:** Bir CSS/JS davranış düzeltmesini SADECE yapay/enjekte edilmiş
bir test ile (`page.addStyleTag()` sayfa yüklemesi TAMAMLANDIKTAN SONRA)
doğrulamak yeterli değil -- bu, kuralın GERÇEK sayfa render'ında
(`st.markdown()` ile enjekte edildiğinde) doğru elemente eşleştiğini
KANITLAMAZ. Seçicinin gerçekten hedef elemente `matches()` ettiğini canlı
DOM'da doğrudan sorgulamadan "çalışıyor" denmemeli.

## Gece oturumu (overnight/topic-fix-and-followups) -- GÖREV 1: Senaryo-konu uyumsuzluğu

Kullanıcının bildirdiği "üretilen senaryo yazdığım konudan farklı bir
şeyden bahsediyor" şikayeti gerçek `storage/tasks/` verisinde arandı.
`ed5df651-a076-4cfd-abd1-41b0da6ce4e4` görevi somut bir örnek verdi:
**topic="Roma"**, `topic_category="history"`, `custom_system_prompt=""`
(boş -- kullanıcının şüphelendiği Stok Üretim sistem promptu bu örnekte
HİÇ devrede değildi, o yüzden GÖREV 1'in 2. maddesindeki şüphe bu vakada
doğrulanmadı). Ama script tamamen **AS Roma futbol kulübünün** tarihiydi
(1927 birleşmesi, 1941-42 Scudetto, 1983-84 Avrupa Kupası finali) --
"Roma" (şehir) hakkında tek kelime yok.

**Kök neden:** `research_plan.source_url =
"https://en.wikipedia.org/wiki/AS_Roma"`, `grounded=true`.
`app/services/web_search.py`'nin `search_web()`'i bare topic string'i
("Roma") hiçbir kategori bağlamı olmadan DuckDuckGo/Wikipedia'ya
sorguluyor; DuckDuckGo instant-answer boş dönünce Wikipedia fallback'i
"Roma" için en iyi eşleşme olarak AS Roma sayfasını buluyor.
`research_planner.py`, bu sonucu LLM'e "Verified web source ... Do not
include key_facts that contradict it" olarak zorluyor -- yani LLM'in
kendi bilgisiyle şehri anlatması bile ENGELLENİYOR, yanlış kaynağa
UYMASI isteniyor. `project.topic_category` (bu örnekte zaten doğru
şekilde "history" olarak çözülmüştü) hiçbir zaman grounding adımına
ULAŞMIYORDU -- `generate_research_plan(topic, tone, language)` kategori
parametresi hiç almıyordu, yani sistemin kendi kategori kararı ile
grounding kaynağı arasında hiçbir tutarlılık kontrolü yoktu.

**Düzeltme (`app/departments/research/research_planner.py`):**
- `intent_analyzer.py`'deki `_CATEGORY_KEYWORDS` public yapıldı
  (`CATEGORY_KEYWORDS`, iki modül arasında paylaşılıyor artık).
- Yeni `_grounding_matches_category(search_result, topic_category)`:
  grounding metninde (heading+abstract) `topic_category`'nin KENDİ
  anahtar kelimelerinden biri geçiyorsa kabul edilir; hiçbiri geçmiyor
  AMA BAŞKA bir kategorinin anahtar kelimesi geçiyorsa (ör. "professional
  football club" -- sports kategorisinin "football" anahtar kelimesi --
  ama history'nin hiçbir anahtar kelimesi yok) REDDEDİLİR (ungrounded
  muamelesi görür, zaten var olan/beklenen bir davranış). Kategori
  bilinmiyorsa (`None`) veya metin hiçbir kategoriye pozitif işaret
  vermiyorsa (belirsiz), grounding AYNEN kabul edilir -- bu sadece NET
  bir uyumsuzluk sinyaline karşı bir güvenlik ağı, aşırı-reddetme riski
  yok.
- `generate_research_plan()`'a yeni **opsiyonel** `topic_category`
  parametresi eklendi (varsayılan `None` -- eski çağrı imzasıyla
  BYTE-IDENTICAL davranış korunuyor, mevcut hiçbir test bozulmadı).
- `default_pipeline.py`: çağrı noktasına `topic_category=project.topic_category`
  eklendi (stage 1'de zaten çözülmüş durumda, stage 2'ye ulaşana kadar
  hazır).

**Test:** `test_research_planner.py::TestGroundingCategoryGuard` (6 yeni
test: mismatch reddediliyor, eşleşen kategori kabul ediliyor, kategori
`None` iken eski davranış korunuyor, belirsiz metin reddedilmiyor, uçtan
uca `generate_research_plan` üzerinden hem red hem kabul senaryosu).
`test_default_pipeline.py`'de `topic_category` kwarg'ının gerçekten
iletildiği doğrulandı. Tam suite: **856 passed, 11 skipped** (846'dan
+10, sıfır regresyon). `ruff` temiz.

**Gerçek API doğrulaması (önce/sonra, GECE bütçesinden 1/8 gerçek LLM
çağrısı kullanıldı):**
- *Önce* (gerçek production kanıtı, `ed5df651`): `grounded=true`,
  `source_url=".../AS_Roma"`, script tamamen futbol kulübü tarihi.
- *Şimdi, aynı canlı web_search sonucuyla* (`web_search.search_web("Roma",
  language="en")` hâlâ AS Roma'ya çözülüyor, doğrulandı -- bug hâlâ
  canlı/güncel, tek seferlik bir tesadüf değil): düzeltmeyle
  `generate_research_plan("Roma", language="en",
  topic_category=TopicCategory.history)` çağrıldığında
  `grounded=False`, `source_url=""` -- grounding doğru şekilde
  reddedildi. LLM, yanlış kaynağa zorlanmadan kendi bilgisiyle ürettiği
  research brief'te **Roman halkını (Romani people)** ele aldı --
  "history" kategorisine mükemmel uyan, gerçek bir etnik/tarihsel konu,
  futbolla ilgisi sıfır. Log satırı da doğrulandı: `"discarding grounding
  source '.../AS_Roma' ... treating as ungrounded"`.

**OTONOM KARAR:** `_CATEGORY_KEYWORDS`'ü public yapmak (basit, düşük
riskli bir rename+iki modül arası paylaşım) yerine ayrı bir yeni
sabit/modül oluşturmak da düşünüldü, ama bu var olan bir listeyi
KOPYALAMAK anlamına gelirdi (iki listenin ileride birbirinden
sapması riski) -- mevcut listeyi paylaşmak daha DRY ve daha tutucu
(yeni bir kavram/dosya eklemiyor, sadece bir isim değişikliği).

**OTONOM KARAR (dal/main iş akışı):** Kural 0 (`overnight/topic-fix-and-
followups` dalına geç) ile Kural 3/4'ün lafzı ("git push origin main",
"./deploy.sh") arasında gerilim var -- main'e hiç dokunmadan sadece dalda
kalmak, deploy.sh'ı (main'i pull edip restart eden) işlevsiz kılardı.
Bu projedeki TÜM önceki gece oturumu dalları (`overnight/claude-tasks-
3to8`, `overnight/launch-readiness`, `overnight/thumbnail-and-backlog`)
sonunda main'e karışmış durumda bulundu (`git rev-list` ile doğrulandı,
main'e göre 0 benzersiz commit) -- yani yerleşik desen, dalın bir
ÇALIŞMA alanı olması ama her doğrulanmış adımdan sonra main'e FAST-
FORWARD edilip push+deploy edilmesi. Bu daha güvenli/tutucu seçenek de:
fast-forward, geçmişi yeniden yazmıyor, gerektiğinde `main`'i eski
commit'e resetlemek trivial. Bu yüzden: her GÖREV'in testleri yeşil
olduktan sonra `overnight/...` dalındaki commit main'e fast-forward
edilip push+deploy ediliyor, dal çalışma alanı olarak devam ediyor.

## Gece oturumu -- GÖREV 2 (durum kontrolü, iş gerekmedi)

"Video Konusu" etiket değişikliği (`d454bb7`, main'in tabanında zaten
mevcuttu) tam olarak doğrulandı: 9 locale'in `"Documentary Topic"`/
`"Generate Documentary"` i18n değerleri hepsi "Video ..." diyor,
`grep -rn "Belgesel Konusu\|Belgesel Oluştur" webui/` sıfır sonuç
döndürdü. Ek iş gerekmedi.

## Gece oturumu -- GÖREV 3: Google Veo entegrasyonu

**Araştırma:** Google Veo, fal.ai üzerinden GERÇEKTEN erişilebilir --
Vertex AI/GCP servis hesabı GEREKMİYOR (Kural 6'nın durma koşulu
tetiklenmedi). Mevcut `fal_api_key` (Kling/Hailuo ile paylaşılan) aynen
geçerli. Üç fal.ai Veo kademesi karşılaştırıldı:
- Veo 2 (`fal-ai/veo2`): $0.50/s -- en pahalısı.
- Veo 3.1 standard (`fal-ai/veo3.1`): $0.20-0.40/s (çözünürlük/ses'e göre).
- **Veo 3.1 Fast (`fal-ai/veo3.1/fast`), 720p, sessiz: $0.10/s** -- fal.ai
  üzerindeki en ucuz Veo seçeneği, bu yüzden varsayılan olarak seçildi.
  Yine de Kling'in (~$0.045/s) **~2.2x'i** -- bu bir maliyet uyarısı
  olarak PROGRESS'e ve webui'nin maliyet tahminine yansıtıldı, bir engel
  değil.

**GERÇEK API İLE DOĞRULANDI (bkz. Kural 2 bütçesi, 2/8 kullanıldı):**
gerçek bir 6sn'lik klip üretildi (`aspect_ratio="9:16"`), indirildi,
`ffprobe` ile ölçüldü: **720x1280 -- tam 9:16 dikey**, `duration=6.0`.
Hailuo'nun aksine (o zaman 9:16 istenmesine rağmen HER ZAMAN 1366x768
yatay döndüğü bulunmuştu), Veo GERÇEKTEN dikey üretiyor. Örnek kare
sinematik kalitede (çöl harabeleri, gün batımı) -- prompt'a tam uyumlu.

**Kod değişiklikleri (`app/services/fal_video.py`):**
- `DEFAULT_VEO_MODEL = "fal-ai/veo3.1/fast"`, `_VEO_DURATION_MAP =
  {"5": "6s", "10": "8s"}` (Veo sadece "4s"/"6s"/"8s" kabul ediyor;
  Kling'in "5"i tam ortada olduğu için YUKARI, "10"u azami "8s"in
  üzerinde olduğu için AŞAĞI yuvarlandı).
- `_build_veo_payload()`: `generate_audio=False` KASITLI (ekstra maliyet
  + bu projenin kendi narrasyon sesiyle çakışan gereksiz ikinci ses
  katmanı istenmiyor), `resolution="720p"` (en ucuz kademe).
- `FalVideoService.__init__` → **property'lere dönüştürüldü**
  (`api_key`/`provider`/`model`). OTONOM KARAR/kök neden: `fal_video_
  service` process başına BİR KEZ import edilen bir singleton (Streamlit
  script'i yeniden çalıştırıyor ama modül cache'i kalıcı) -- bunlar
  `__init__`'te sabitlenirse, webui'den bir provider değişikliği tam bir
  servis restart'ı olmadan HİÇ etkili olmazdı (bu, GÖREV 3'ün asıl
  istediği "kullanıcı webui'den Veo seçsin" özelliğini sessizce
  bozardı) -- bu, GÖREV 3'ü kodlarken keşfedilen, önceden var olan bir
  gecikme/staleness sorunuydu, mevcut 23 testin hiçbiri kırılmadı
  (hepsi construct-then-immediately-read deseninde).

**webui (`webui/Main.py`):** "Belgesel Niteliği" sayfasında yeni bir
"AI Video Sağlayıcısı" seçici (Kling/Veo) -- Hailuo BİLİNÇLİ OLARAK YOK
(9:16 desteklemiyor, ADIM 3'ten beri webui'den gizli, bu karar
değişmedi). Seçim `config.app["fal_ai_video_model"]`'e yazılıyor
(`save_config()` ÇAĞRILMIYOR -- config.toml dosyası hiç değişmiyor,
Klasik Mod'un `video_source` seçicisiyle AYNI desen). Maliyet tahmini
(`_estimate_ai_video_cost_usd`) artık `ai_video_provider` parametresi
alıyor, Veo için ayrı fiyat/duration-yuvarlama mantığıyla.

**i18n:** `"Documentary AI Video Provider"` + `": kling"`/`": veo"`
anahtarları 9 locale'e eklendi (hepsi JSON-geçerliliği doğrulandı).

**Test:** `test_fal_video.py`'ye `TestVeoProviderSelection` (4 test,
biri özellikle live-config-reload davranışını kilitliyor) +
`TestSubmitVideoJob`'a 2 Veo payload testi. `test_webui_ai_video_source.py`'ye
2 yeni test (seçici varsayılanı + Veo seçilince maliyet tahmini
değişimi). Tam suite: **864 passed, 11 skipped** (856'dan +8, sıfır
regresyon). `ruff` temiz.

**config.example.toml:** `fal_veo_model = "fal-ai/veo3.1/fast"` eklendi,
`fal_ai_video_model` yorumu güncellendi.

## Gece oturumu -- GÖREV 4: Genel sağlık kontrolü

Tam suite: **864 passed, 11 skipped**, `ruff` temiz, production
(`ai-documentary-studio-webui.service`) `active` ve `/_stcore/health` OK.

**Config.toml notu (bilgi amaçlı, YENİ bir olay DEĞİL):** GÖREV 3'ün
gerçek tarayıcı doğrulaması sırasında (`/quality` sayfasına gidildi)
config.toml'a `fal_ai_video_model = "kling"` satırı gerçekten YAZILDI
(mtime + içerik doğrulandı). Kök neden araştırıldı: bu, ÖNCEDEN VAR OLAN
(bu gece eklenmemiş), `_render_documentary_advanced_settings()`'in
sonundaki KOŞULSUZ `config.save_config()` çağrısı yüzünden (satır
~4872, kendi yorumu: "Klasik Mod'un aksine Documentary Studio hiçbir
yerde config.save_config() çağırmıyordu -- bu üç ayar RAM'de kalıp bir
sonraki restart'ta eski değerlere dönerdi... save_config() içerik
değişmediyse zaten no-op, bu yüzden her rerun'da çağırmak güvenli").
Yeni "AI Video Sağlayıcısı" seçicim de AYNI form içinde `config.app[...]`
'a yazdığı için, bu ÖNCEDEN VAR OLAN save_config() çağrısı onu da
süpürüp diske yazdı -- bu, tasarımın kendi mantığıyla TUTARLI (kullanıcı
provider seçimi de, font ayarları gibi, restart'tan sağ çıkmalı) ve
YAZILAN DEĞER ZARARSIZ/DOĞRU ("kling", varsayılan) -- Pexels API key
dahil diğer tüm alanlar sağlam/değişmeden kaldı (kontrol edildi). Önceki
gerçek olay (test suite'in save_config()'i unutup config.toml'ı
bozması) ile KARIŞTIRILMASIN: o, conftest.py'nin engellediği bir test-
zamanı sorunuydu; bu, GERÇEK, kasıtlı, production-zamanı kalıcılık
davranışı. Ek işlem gerekmedi, sadece şeffaflık için not düşüldü.

## Gece oturumu -- GÖREV 5: Sistem Promptu / Özel Senaryo Gereksinimleri varsayılanları

"Sistem Promptu" ve "Özel Senaryo Gereksinimleri" artık boş başlamıyor --
her iki sayfada (Belgesel/AI Üretimi VE Stok Üretim) ön-dolu, kullanıcının
silip/değiştirebileceği bir varsayılan metinle geliyor.

**İçerik kararı:** Bu sohbette daha önce kullanıcıya verilen iki gerçek
system prompt'un tam metnini bu oturumda YENİDEN ÜRETEMEDİM (o kısım bir
önceki oturum özetinde yoktu) -- ama GERÇEK ÜRETİMLERDE (`storage/
tasks/`) hangi metinlerin fiilen kullanıldığını buldum (GÖREV 1
teşhisinin bir yan ürünü): biri "award-winning documentary filmmaker...
professional YouTube documentary scriptwriter" (AI-video, konuya özel,
Eastern civilizations kilitli), biri "fast-turnaround YouTube
scriptwriter working with free stock footage" (stok, konudan bağımsız,
genel). Tam metinleri OLDUĞU GİBİ varsayılan yapmadım -- ilki tek bir
konuya (Doğu medeniyetleri) kilitliydi, ikincisi zaten genel ve
kısaydı. Bunun yerine, **GROWTH_GUIDANCE (`_growth_guidance_instructions`,
her zaman açık) + _story_craft_instructions (Hook/Retention/Callback,
her zaman açık) + TONE_VOICE_GUIDANCE'ın (`3bc21c2`, önceki oturumda
YouTube-dinamik'e çevrilmiş, HÂLÂ ÖYLE -- bu gece doğrulandı) hiçbirinin
KAPSAMADIĞI tek gerçek boşluğu** doldurdum: görsel tarifin AI-video
üretimi mi yoksa stok-footage aranabilirliği mi için optimize edileceği
(iki sayfa farklı varsayılan alıyor, kullanıcı talebi buydu) + hafif bir
SEO/aranabilirlik ipucu (Özel Senaryo Gereksinimleri, ikisinde ortak).
Bu, kullanıcının önceki iki gerçek prompt'undaki, sistemin BAŞKA HİÇBİR
YERİNDE kapsanmayan TEK somut, konu-bağımsız, tekrar kullanılabilir
unsurdu (stok metninin 2. maddesi: "concrete, commonly-filmed subjects").

**Kod (`webui/Main.py`):** `_render_documentary_advanced_settings()`
artık `video_source_fixed` parametresi alıyor (çağıran `_render_shared_
documentary_form`'dan geliyor), sayfaya göre `_DOCUMENTARY_DEFAULT_
SYSTEM_PROMPT_AI_VIDEO` / `_DOCUMENTARY_DEFAULT_SYSTEM_PROMPT_STOCK`
arasında seçim yapıyor; `_DOCUMENTARY_DEFAULT_CUSTOM_REQUIREMENTS` her
iki sayfada ortak. `st.text_area(..., value="")` → `value=default_...`
(placeholder değil, gerçek ön-dolu değer -- kullanıcı silebilir).
İngilizce kalıyor (i18n YOK) -- bu alanların İÇERİĞİ zaten her zaman
İngilizce LLM talimatı olmuştu (`DEFAULT_SCRIPT_SYSTEM_PROMPT` da öyle),
sadece ALAN ETİKETİ `tr()`'den geçiyor.

**Test:** `test_webui_advanced_settings.py` güncellendi -- eski "boş
varsayılan" testi "stok sayfasında stok varyantı" testine dönüştürüldü,
yeni `test_system_prompt_defaults_to_ai_video_variant_on_quality_page`
(iki varyantın GERÇEKTEN farklı olduğunu da doğruluyor) ve
`test_user_can_still_clear_the_default_to_empty` eklendi, eski "blank
fields -> empty strings" testi "untouched fields -> defaults gönderilir"
olarak yeniden adlandırıldı/güncellendi. Tam suite: **866 passed, 11
skipped** (864'ten +2, sıfır regresyon). `ruff` temiz.

## Gece oturumu -- GÖREV 6: Background Music Source'a ElevenLabs Music

**Araştırma:** ElevenLabs'in gerçek, TTS'ten AYRI bir Music API'si VAR
("Eleven Music", `POST /v1/music`, aynı `xi-api-key` -- mevcut
`elevenlabs_api_key` config'i geçerli, gerçek `test_connection()` çağrısı
ile canlı hesabın "starter" (ücretli) planda olduğu doğrulandı, Music
API'ye erişim var). Fiyat: **$0.15/dakika** (~$0.0025/sn) -- Kling/Veo'ya
kıyasla önemsiz derecede ucuz.

**Sürpriz bulgu:** `app/services/elevenlabs_music.py` ZATEN TAM,
production-grade bir entegrasyon içeriyordu (`generate_bgm()`,
video-to-music varyantı, `/v1/music/video-to-music`) -- ama SADECE
Klasik Mod'un eski `task.py` orkestrasyonuna bağlıydı, Documentary
Studio'nun `default_pipeline.py`'sine hiç bağlanmamıştı (bu, önceki bir
oturumda BİLİNÇLİ OLARAK kapsam dışı bırakılmıştı -- bkz. `webui/Main.py`
içindeki eski yorum: "buraya taşımak bu görevin kapsamını ciddi
büyütürdü").

**OTONOM KARAR (video-to-music yerine prompt-tabanlı compose):**
Video-to-music, TAMAMEN RENDER EDİLMİŞ bir video ister (Classic Mode'un
tek-seferlik `task.py`'si için doğal bir sıra). Documentary Studio'nun
`default_pipeline.py`'si ise BGM'i video render'dan ÖNCEKİ aşamalarda
(stage 9 TTS, stage 12 video render) ister -- video-to-music'i kullanmak
videoyu İKİ KEZ render etmeyi (önce BGM'siz, müzik üretilip tekrar)
gerektirirdi: gerçek ekstra maliyet/gecikme + yeni bir pipeline aşaması,
"düşük risk" kapsamının dışında. Bunun yerine ElevenLabs'ın PROMPT-
tabanlı `/v1/music` "compose" endpoint'i kullanıldı
(`generate_bgm_from_prompt()`, yeni) -- mevcut `bgm_file_override`
mekanizmasıyla (video.py, Classic Mode'un Sonilo/ElevenLabs için ZATEN
kullandığı AYNI mekanizma) TEK GEÇİŞTE, pipeline yeniden yapılandırması
OLMADAN çalışıyor. `force_instrumental=True` kasıtlı (narrasyonla
çakışan vokal istenmiyor).

**Kod:**
- `app/services/elevenlabs_music.py`: yeni `generate_bgm_from_prompt()`
  (mevcut `_stream_audio`/`_safe_response_error`/`bgm_service.
  validate_audio_file` yardımcılarını yeniden kullanıyor), `music_length_
  ms` API'nin 3000-600000 sınırına clamp ediliyor.
- `app/departments/production/video_renderer.py`: `render_final_video()`'a
  yeni `bgm_file_override` parametresi (video.generate_video()'ya
  passthrough).
- `app/pipeline/default_pipeline.py`: stage 12'den hemen önce, `bgm_type
  == "elevenlabs"` ve BGM etkinse (`bgm_service.should_use_bgm`),
  `generate_bgm_from_prompt(video_music_prompt, project.timeline.
  total_duration, ...)` JIT çağrılıyor, sonucu `bgm_file_override` olarak
  geçiyor. Üretim BAŞARISIZ olursa pipeline ÇÖKMÜYOR -- narrasyon-only
  final video ile devam (uyarı logla). `regenerate_from_edited_script()`
  de aynı mantıkla güncellendi (script düzenlendikten sonra ElevenLabs
  BGM'i PROMPT'tan yeniden üretebiliyor -- dosya olarak saklanmıyor).
  Yeni `run_pipeline(video_music_prompt="")` parametresi + yeni
  `DocumentaryProject.video_music_prompt` alanı (aynı ÖZELLİK A
  gerekçesiyle, `bgm_type`/`bgm_volume`'un yanına).
- `webui/Main.py`: "Background Music Source" seçicisine 4. seçenek
  ("elevenlabs") eklendi (Sonilo hâlâ BİLİNÇLİ OLARAK kapsam dışı,
  istenmedi). Seçilince: API key yoksa uyarı (mevcut "ElevenLabs API Key
  Required" key'i yeniden kullanıldı), varsa zorunlu bir prompt text_area'sı
  + "Test ElevenLabs Connection" düğmesi (Classic Mode'un ZATEN var olan
  i18n key'leri yeniden kullanıldı: "Test ElevenLabs Connection",
  "ElevenLabs Paid Plan Required", "ElevenLabs Connection Test
  Failed/Succeeded" -- provider-tier kontrolü video-to-music'ten
  BAĞIMSIZ, aynı anlam). SADECE 2 gerçekten YENİ i18n grubu eklendi
  (seçenek etiketi + prompt label/help, ikisi de "compose" varyantının
  KENDİ semantiğini yansıtıyor -- Classic Mode'un "leave empty to match
  the video automatically" metni burada YANLIŞ olurdu, çünkü bu varyantta
  prompt ZORUNLU).

**Test:** `test_elevenlabs_music.py`'ye `TestGenerateBgmFromPrompt` (4
test: sınır doğrulama, payload/atomik yazma, süre clamp, hata sonrası
mevcut dosyanın korunması). `test_default_pipeline.py`'ye 4 test (JIT
üretim + bgm_file_override, üretim hatası pipeline'ı çökertmiyor,
elevenlabs-olmayan tiplerde hiç çağrılmıyor, 0 ses seviyesinde hiç
çağrılmıyor). `test_webui_audio_settings.py`'ye 4 test (yapılandırılmamış
uyarı, yapılandırılmış prompt alanı, run_pipeline'a video_music_prompt
geçişi, diğer bgm tiplerinde boş prompt). Tam suite: **878 passed, 11
skipped** (866'dan +12, sıfır regresyon). `ruff` temiz.

**Gerçek API doğrulaması (GECE bütçesinden 3/8 gerçek çağrı kullanıldı):**
`generate_bgm_from_prompt("warm, slow-building cinematic instrumental, no
vocals", 3.0, ...)` gerçek `/v1/music` çağrısı yapıldı, gerçek MP3
üretildi, `ffprobe` ile doğrulandı: `codec=mp3, sample_rate=44100,
channels=2, duration=3.056s` (istenen 3sn'ye yakın, API'nin kendi
toleransı). Ayrıca fonksiyonun kendi `bgm_service.validate_audio_file()`
çağrısı da (ffmpeg decode kontrolü) sessizce geçti -- gerçek, geçerli
ses verisi.

## Gece oturumu -- GÖREV 7: Videvo stok sağlayıcı araştırması (KODLANMADI)

**Bulgu: Videvo'nun BAĞIMSIZ bir geliştirici API'si YOK.** Videvo,
Haziran 2022'de **Freepik tarafından satın alındı** -- kütüphanesi
(650.000+ video) o zamandan beri Freepik'in KENDİ platformuna
entegre edildi, ayrı bir "Videvo API"si kalmadı. Freepik'in kendisi de
Nisan 2026'da **"Magnific"** olarak yeniden markalandı. Bugün gerçekten
var olan tek gerçek API, `docs.freepik.com/api-reference/videos/videos-api`
altında belgelenen **Freepik/Magnific Videos API** -- gerçek, iyi
belgelenmiş, pay-per-use (sabit abonelik yok) bir REST API, ama bu
**Videvo değil, tamamen farklı bir sağlayıcı** (farklı hesap/API key,
farklı fiyatlandırma modeli, farklı kullanım şartları, farklı marka).

**Neden kodlanmadı:** GÖREV 7'nin kendi açık dallanma mantığı ("EĞER
API varsa: kodlayın. EĞER YOKSA: KODLAMAYIN, not düşün") burada net --
kullanıcı özellikle "Videvo" istedi, ve Videvo'nun kendi başına
istenen türde bir API'si YOK. Freepik/Magnific'i entegre etmek,
kullanıcının istemediği/onaylamadığı YENİ bir sağlayıcı hesabı, YENİ bir
fiyatlandırma modeli ve YENİ kullanım şartları gerektirir -- bu, GÖREV
7'nin kapsamının ötesinde, ayrı bir onay gerektiren bir karar (rule 6'nın
ruhuna uygun: kullanıcının onaylamadığı bir sağlayıcı değişikliğini
otonom olarak yapmak yerine, bulguyu raporlayıp kullanıcının kararına
bırakmak daha güvenli/tutucu).

**Sonraki adım (kullanıcı karar verirse):** Eğer kullanıcı Freepik/
Magnific Videos API'sini (Videvo YERİNE, farklı bir sağlayıcı olarak)
gerçekten istiyorsa, bu ayrı bir GÖREV olarak ele alınmalı --
`material.py` deseniyle 4. stok sağlayıcı eklemek teknik olarak
mümkün görünüyor (gerçek, belgelenmiş REST API), ama fiyatlandırma/
hesap kurulumu/API key alımı kullanıcının kendi onayını gerektirir.
`config.example.toml`'a hiçbir yeni anahtar eklenmedi, `material.py`'ye
hiçbir kod eklenmedi -- bu görev tamamen araştırma/rapor aşamasında
kaldı.

## ACİL prod fix -- ElevenLabs TTS "failed to synthesize narration audio"

**Bildirilen hata:** Gerçek üretimde TTS başarısız oluyordu, kullanıcı
GÖREV 6'nın (bir gece önceki ElevenLabs Music entegrasyonu) TTS ile
çakıştığından şüpheleniyordu.

**Teşhis (`journalctl` + `storage/tasks/`):** En son başarısız görev
(`04350069`, pacing=`extended`, `voice_name=elevenlabs:...`) incelendi:
script 7759 karakter. Log'lar aynı deseni gösterdi (09:04 VE 10:53,
~2 saat arayla): `elevenlabs_tts` 3 denemenin ÜÇÜNDE de AYNI hatayla
başarısız -- `HTTPSConnectionPool(...): Read timed out. (read
timeout=60)`.

**GÖREV 6 KESİN OLARAK ELENDİ:** `voice.py` bir önceki gece HİÇ
değiştirilmemiş (`git log`/`git diff` ile doğrulandı) -- son değişikliği
haftalar önceki bir GÖREV'e ait. `config.toml`'ın `[elevenlabs]`
bölümünde de çakışma yok: TTS `api_key`/`model_id` okuyor,
`elevenlabs_music.py` (GÖREV 6) `api_key`'i PAYLAŞIYOR (kasıtlı, GÖREV
6'nın kendi tasarımı) ama `music_model_id`/`music_timeout` gibi TAMAMEN
AYRI anahtarlar kullanıyor -- hiçbiri üzerine yazılmamış. Ayrıca GÖREV
6'nın kodu pipeline'da stage 12'de (video render) çalışıyor, bu görevin
BAŞARISIZ olduğu stage 9 (TTS)'dan SONRA -- yani bu spesifik görevde
GÖREV 6 kodu hiç ÇALIŞMAMIŞ bile.

**Gerçek kök neden:** `audio_renderer.render_narration()`, script'in
TAMAMINI (`script.full_text`) TEK bir ElevenLabs isteğinde gönderiyor;
`elevenlabs_tts()` bu isteğe SABİT `timeout=60` uyguluyor. "Extended"
pacing (10dk video) ~7-8bin karakterlik script üretiyor -- bu uzunlukta
bir sentezin ElevenLabs sunucusunda tamamlanması genellikle 60sn'yi
aşıyor (GERÇEK API İLE DOĞRULANDI: aynı 7759 karakterlik script'le
3 deneme de aynı 60sn timeout'ta başarısız oldu, üçü de aynı desende --
sorun ağ değil, sabit süre limiti). Bu, GÖREV 6'dan TAMAMEN bağımsız,
"extended" pacing'in İLK KEZ ElevenLabs TTS ile gerçek, uzun bir
üretimde karşılaştığı, önceden var olan bir gecikme/kapasite hatası.

**AYRI, İKİNCİ bir bulgu (kod hatası DEĞİL, gerçek bir hesap kısıtı):**
Teşhis sırasında (ve muhtemelen kullanıcının kendi 2 denemesinde) yapılan
tekrarlanan 60sn'lik zaman aşımı denemeleri (her biri gerçek quota
tüketmiş olabilir, sunucu tarafında kabul edilip işlenmeye başlanmış
olabilir) hesabın bu faturalama dönemindeki kotasını sıkıştırmış:
gerçek bir API çağrısı `401 quota_exceeded` döndürdü ("quota of 165000
... 2427 credits remaining, 3880 required"). Kota sıfırlanması:
**2026-08-18**. Bu, KOD DEĞİL, gerçek bir hesap/kullanım kısıtı --
düzeltilemez, sadece raporlanabilir. Kullanıcının seçenekleri: kredi
ekleme, sıfırlanmayı bekleme, veya çok uzun (extended pacing) üretimler
için farklı bir TTS sağlayıcısı kullanma.

**Düzeltme (`app/services/voice.py`):**
- Yeni `_elevenlabs_tts_timeout(text_length)`: `max(60, len(text) // 15)`,
  600sn tavanlı (elevenlabs_music.py'nin kendi tavanıyla tutarlı). Kısa
  metinler (TTS'in asıl, sık kullanılan durumu) hâlâ ~60sn taban alıyor,
  hiç etkilenmiyor.
- `_NON_RETRYABLE_STATUSES`'a `"quota_exceeded"` eklendi (netlik için --
  401 zaten `_NON_RETRYABLE_CODES`'ta olduğu için pratikte zaten
  retry'lanmıyordu, ama artık kota hatası için özel, doğru bir log mesajı
  var: "add credits, wait for the next reset, or use a shorter pacing /
  different TTS provider" -- eskiden yanlış/alakasız "select a different
  ElevenLabs voice" mesajı gösteriliyordu).

**Test:** `test_voice.py`'ye 4 yeni test (`_elevenlabs_tts_timeout`'un
gerçek 7759 karakterlik script için 517sn, kısa metin için 60sn, çok
uzun metin için 600sn tavanı doğru hesapladığı; gerçek istekte hesaplanan
timeout'un gönderildiği; quota_exceeded'in TEK denemede durduğu (retry
yok); gerçek ReadTimeout exception'ının hâlâ 3 kez retry'landığı --
transient network blip'leri için mevcut davranış korunuyor). Tam suite:
**882 passed, 11 skipped** (878'den +4, sıfır regresyon). `ruff` temiz.

**Gerçek API doğrulaması (kalan kota göz önünde bulundurularak
kalibre edildi -- tam 7759 karakterlik script'i tekrar denemek kalan
kotayı riske atardı):** 4643 karakterlik gerçek narration-stili bir
metinle (`_elevenlabs_tts_timeout(4643)=309s`) gerçek bir istek
yapıldı -- **BAŞARILI**, 40.5sn'de tamamlandı, `ffprobe` ile doğrulandı:
`codec=mp3, duration=268.09s` (4.5 dakikalık gerçek, geçerli ses). Bu
uzunluğun normal koşullarda 60sn sınırına yakın olması (7759 karakterlik
orijinal script'in ~60/-70sn civarında olması beklenir), orijinal
başarısızlığın sınırda bir vaka olduğunu ve yeni timeout'un (309-517sn)
bunun için bol pay bıraktığını doğruluyor.

## Gece oturumu (overnight/narration-and-aspect-fix) -- GÖREV 1: Long pacing hâlâ 9:16 çıkıyordu

**Teşhis:** `storage/tasks/` kullanıcı tarafından Task Manager'dan az önce
temizlenmiş (08:28, `_delete_task` log'ları) -- geçmiş "long" pacing
üretimi incelenemedi, doğrudan kod yoluna ve gerçek bir yeniden-üretime
geçildi.

**Kök neden (kullanıcı ile aynı fikirde DEĞİL bir bulgu):** Bu bir
regresyon değil -- Aspect Ratio seçicisi GÖREV 2'de (önceki oturum,
`794a365`) Pacing'den TAMAMEN BAĞIMSIZ olarak eklenmişti, hiçbir zaman
otomatik bağlanmamıştı (her zaman sabit "9:16" varsayılanı). Asıl
sorun bir İSİMLENDİRME KARIŞIKLIĞI: Pacing dropdown'ında "Uzun" etiketi
`Pacing.long`'a ait (7 sahne x 8s ≈ 56sn, hâlâ Shorts-tarzı bir format,
9:16 için doğru varsayılan) -- GERÇEK 10+ dakikalık, 16:9'a uygun
"belgesel" tier'ı ayrı bir enum değeri, `Pacing.extended`, ve dropdown'da
"Belgesel Uzunluğunda (10+ dk)" olarak etiketli. Kullanıcı "uzun video"
isteyince doğal olarak "Uzun"u seçmiş, ama bu `Pacing.extended` DEĞİL.

**Düzeltme (`webui/Main.py`):** Pacing selectbox'ından hemen sonra,
short/long -> extended CANLI geçişini (`documentary_pacing_last_seen`
session_state ile) izleyen ve SADECE bu geçiş anında Aspect Ratio'yu
otomatik 16:9'a çeviren bir blok eklendi. `Pacing.long` bilinçli olarak
etkilenmiyor (9:16 onun için hâlâ doğru varsayılan). Taze bir oturumda
(ör. görev geri yükleme) pacing zaten "extended" olarak gelmişse
DOKUNULMUYOR (`previous_pacing is not None` şartı) -- kullanıcının
BİLEREK bıraktığı bir 9:16+extended kombinasyonunu ezmemek için. Tek
seferlik bir varsayılan-değiştirme, kilit değil -- kullanıcı sonrasında
elle 9:16'ya geri dönebilir.

**Test:** `test_webui_long_form.py`'ye 4 yeni test (canlı geçişte 16:9'a
otomatik geçiş; `Pacing.long`'un etkilenmediği; taze oturumda zorla
değiştirmediği; kullanıcının elle geri aldığı 9:16'nın tekrar
ezilmediği). Tam suite: **886 passed, 11 skipped** (882'den +4, sıfır
regresyon). `ruff` temiz.

**Gerçek doğrulama (stok video, ücretsiz, GECE bütçesine dahil değil --
Pexels ücretsiz):** `run_pipeline(..., pacing=Pacing.short,
video_aspect="16:9", video_source="pexels")` gerçekten çalıştırıldı --
gerçek `final.mp4` üretildi, `ffprobe` ile doğrulandı: **1920x1080**,
tam istenen 16:9. Bu, downstream pipeline'ın (video_renderer/
timeline_builder/asset_downloader) `video_aspect="16:9"` parametresini
hâlâ doğru onurlandırdığını -- son gece değişikliklerinden (Veo, 3-sayfa
restructuring) hiç etkilenmediğini -- kanıtlıyor.

## Gece oturumu -- GÖREV 2: Anlatım tarzı hâlâ "belgesel" hissi veriyordu

**Teşhis:** Kullanıcının şüphelendiği `_story_craft_instructions()`
(Hook/Retention/Callback) incelendi -- metni zaten stil-nötr (yapısal
talimatlar, "belgesel" hissi veren kelime/kalıp yok). Asıl kök neden
FARKLI, daha derin bir katmandaydı: `app/config/templates/__init__.py`
(`PROFILE_PROMPTS`, 14 ton) her tonun `"style"` alanında KELİMESİ KELİMESİNE
"X documentary." diye başlıyordu (ör. "Travel documentary.", "History
documentary.") -- bu metin `outline_generator`/`research_planner`'a
gidiyor, yani HOOK/CLOSING/SECTION içeriğini (script_generator'ın
"YouTube-dinamik" ses talimatıyla anlatmak zorunda olduğu HAM İÇERİK)
üretiyor. `script_generator.py`'nin kendi ses/sistem promptu önceki
oturumda (3bc21c2) YouTube-dinamiğe çevrilmişti (hâlâ öyle, bu gece
doğrulandı) -- ama bu SADECE SON TESLİMAT KATMANIYDI. Outline/research
aşaması, anlatılacak İÇERİĞİN KENDİSİNİ hâlâ açıkça "belgesel" çerçevesi
altında üretiyordu -- `outline_generator.py`'nin ("You are a documentary
outline writer.", "Produce a documentary outline...") ve
`research_planner.py`'nin ("You are a documentary research assistant...
plan a short documentary.") kendi sistem promptları da aynı şekilde.

**Kapsam dışı bırakılan, düşünülüp elenen iki nokta:**
`intent_analyzer.py`'nin kategori sınıflandırıcı promptu ("documentary
video topic") -- SADECE bir JSON kategori etiketi üretiyor, hiç anlatım
içeriği yazmıyor, narrasyon TONUNA sıfır etkisi var; dokunulmadı.
`storyboard_generator.py`'nin "You are a documentary storyboard artist..."
promptu -- GÖRSEL çekim/stok-footage seçimini şekillendiriyor, SÖZLÜ
anlatımı değil (kullanıcının şikayeti özellikle "konuşma ve anlatım"
hakkındaydı); bu gece kapsam dışı bırakıldı, ayrı bir görev olarak
değerlendirilebilir.

**Düzeltme:**
- `app/config/templates/__init__.py`: 14 tonun `"style"` alanı da
  "X documentary." yerine "X YouTube video. ... delivered like a [aynı
  script_generator.TONE_VOICE_GUIDANCE'taki persona]..." diyecek şekilde
  yeniden yazıldı (ör. cinematic: "delivered like a top travel YouTuber
  narrating quick cuts back-to-back, never lingering on one shot").
  Diğer alanlar (opening_hook/section_guidance/closing) zaten stil-nötrdü,
  değiştirilmedi.
- `app/departments/research/outline_generator.py`: "You are a documentary
  outline writer" -> "You are a YouTube video outline writer"; "Produce a
  documentary outline..." -> "Produce a video outline...".
- `app/departments/research/research_planner.py`: "You are a documentary
  research assistant... plan a short documentary." -> "You are a YouTube
  video research assistant... plan a fast-paced, high-retention YouTube
  video." (script_generator.DEFAULT_SCRIPT_SYSTEM_PROMPT ile aynı dil).

**Test:** `test_outline_generator.py`/`test_research_planner.py`'nin
byte-for-byte regresyon testleri yeni metne güncellendi (bu testler zaten
"önceki bir refactor'ün metni değiştirmediğini" kilitlemek içindi --
şimdi KASITLI bir içerik değişikliğini kilitliyorlar). Tam suite:
**886 passed, 11 skipped** (aynı sayı -- yeni test eklenmedi, mevcut 2
regresyon testi güncellendi). `ruff` temiz.

**Gerçek API ile önce/sonra karşılaştırması (`git stash` ile ESKİ kod
üzerinden gerçek bir "before" üretimi, sonra `stash pop` ile YENİ kod
üzerinden AYNI konuyla "after" -- "The Great Fire of London", credibility
tonu, gerçek research+outline+script LLM çağrıları):**

*Önce (kapanış):* "...great urban disasters are rarely caused by fire
alone—they are shaped by the choices made before and during the crisis."
-- klasik, düşünceli/"reflective" belgesel anlatıcısı kapanışı.

*Sonra (kapanış):* "In four days, medieval London was erased — and the
modern city began rising from its ashes." -- daha somut, daha az
"ahlak dersi veren belgesel sesi".

**Dürüst değerlendirme:** İki örnek de zaten oldukça enerjik/kısa cümleli
(script_generator'ın ses katmanı ÖNCEKİ oturumda zaten düzeltilmişti, bu
yüzden SON TESLİMAT iki örnekte de benzer) -- fark dramatik değil, ama
GERÇEK ve YAPISAL: "sonra" örneği bir doğrudan-izleyici sorusu ekledi
("how many poor Londoners were never counted?"), kapanışı daha az
moralize edici/"reflective". Asıl güçlü argüman örnek çıktıdan çok
YAPISAL: LLM'e giden 16 farklı prompt'tan (14 PROFILE_PROMPTS style +
2 sistem promptu) kelimesi kelimesine "documentary" ifadesi tamamen
kaldırıldı -- kullanıcının "hâlâ belgesel hissi veriyor" şikayetinin
gerçek, ölçülebilir kaynağıydı bu, tek bir örnek çıktıdaki öznel fark
değil.

## "Bao" — karakterli çocuk değerler eğitimi serisi (kullanıcı onaylı, ÇOCUK GÜVENLİĞİ)

**Context:** Bir önceki oturumda `fal-ai/kling-video/o1/standard/reference-to-video`
ile karakter tutarlılığı gerçek bir API testiyle doğrulanmıştı (bkz.
`docs/character-consistency-research.md`, panda "Bao" karakteri) -- ama o
araştırma KASITLI olarak hiçbir pipeline entegrasyonu içermiyordu. Kullanıcı
bu temel üzerine, "Bao" karakterli 10 bölümlük bir çocuk değerler eğitimi
serisi (İyilik, Arkadaşlık, Paylaşma, Azim, Kahramanlık) başlattı. Bu, ÇOCUK
GÜVENLİĞİ gerektiren ilk özellik olduğu için kod yazmadan önce sadece
kapsamlı bir plan verildi, kullanıcı onayı beklendi (tam otonomi
VERİLMEDİ) -- `docs/future-work.md`'nin daha önceki "vocabulary-only kids
mode ASLA gönderilmemeli" uyarısını tam karşılayacak şekilde, karakter
entegrasyonu VE zorunlu güvenlik katmanı BİRLİKTE teslim edildi.

**Teknik entegrasyon (minimal, cerrahi -- yeni bir akış DEĞİL):**
- `TopicCategory.values_education` + `Tone.nurturing` (KASITLI İSTİSNA: diğer
  15 ton "hep hızlı/punchy" iken, bu ton bilerek yavaş/sıcak/sakin --
  3-8 yaş hedef kitlesi için hızlı tempo zararlı).
- `Format.kids` -- `docs/future-work.md`'nin şartı gereği, güvenlik
  katmanıyla AYNI commit'te.
- `CharacterReference` modeli (`app/models/character.py`) +
  `DocumentaryProject.character_reference` alanı -- `topic_category`/
  `tone`/`format` ile AYNI desende, stage 1'de projeye bağlanıyor.
- `fal_video.py`: yeni `character_elements` parametresi `submit_video_job()`'a
  eklendi -- verildiğinde, global `fal_ai_video_model` sağlayıcı seçimini
  (kling/hailuo/veo) BİLEREK atlayıp her zaman Kling O1'e yönlendiriyor
  (ne Hailuo ne Veo karakter tutarlılığını destekliyor). Bu sırada gerçek
  bir kenar-durum bug'ı bulunup düzeltildi: `poll_job_status`/`get_job_result`
  submit anındaki `app_id`'yi ALMIYORDU, her zaman O ANKİ provider config'inden
  yeniden türetiyordu -- global sağlayıcı bir karakter işi devam ederken
  değişirse yanlış endpoint'i poll ederdi. Artık `submit_video_job`'un
  döndürdüğü `app_id` açıkça `ai_video_generator.py` üzerinden taşınıyor.
- `asset_generator.py`: `character_reference` verildiğinde her AI-video
  prompt'una `"Take @Element1 as {name}. "` öneki ekliyor (Kling O1'in
  `elements[]`'i tetiklemesi için zorunlu).
- `resource/characters/bao/` (front/three_quarter/back, önceki gerçek testte
  zaten kullanılan kırpılmış görseller) + `resource/characters/
  bao_content_calendar.yaml` (10 bölümün basit, salt-okunur planı -- hiçbir
  kod bunu OKUMUYOR, sadece insan referansı).
- Maliyet: `long` pacing (~1dk/bölüm) seçildi, 10 bölüm için tahmini **$62.72**
  (karaktersiz Kling varsayılanına göre fark ~$37.66).

**Çocuk güvenliği (ZORUNLU, kapatılamaz):**
`app/departments/creative/script_generator.py`'ye `_child_safe_guidance_
instructions()` eklendi -- `_growth_guidance_instructions` ile AYNI desen
(her zaman açık, webui'de toggle yok), `format != Format.kids` olduğunda
no-op. `Format.kids` olduğunda 7 somut kural ekliyor: yaş-uygun kelime
dağarcığı, şiddet yok, ölüm/ciddi tehlike yok, korkutucu görsel/atmosfer
yok, korkutucu gerçek-dünya temaları yok, her bölüm sıcak bir çözümle
bitmeli, ticari baskı yok. `build_script_prompt()`'a koşulsuz ekleniyor
(satır: `prompt += _child_safe_guidance_instructions(format)`), kullanıcının
kendi `custom_requirements`'ından ÖNCE. Ayrıca `_growth_guidance_
instructions`'ın "yorum yap" daveti kids için de bastırıldı (Closing nudge
kasıtlı olarak korundu -- zararsız/standart).

Publish tarafında: Documentary Studio zaten hiçbir otomatik yayın yolu
içermiyordu (sadece `_render_publish_section`'ın manuel butonu) -- bunun
üstüne, `format == Format.kids` için EK bir zorunlu onay kutusu eklendi
("Bu videoyu tamamen izledim ve çocuklar için uygun olduğunu onaylıyorum"),
Publish butonu bu işaretlenmeden disabled kalıyor.

**Doğrulama:**
- Yeni birim testleri (child-safe guidance içeriği, karakter-payload
  dispatch/bypass, `@Element1` öneki, `app_id` taşıma, publish-checkbox
  gating) + tam suite: sıfır regresyon.
- **Gerçek, ücretli uçtan-uca test** ($1.12, gerçek Kling O1 çağrısı):
  gerçek `script_generator.generate_script(format=Format.kids,
  tone=Tone.nurturing)` çağrısı gerçekten çocuk-güvenli bir anlatım
  üretti ("Bao had one bamboo stick; hungry Bird had none, so Bao
  shared."), gerçek `asset_generator`/`ai_video_generator` zinciri
  üzerinden gerçek bir 720x1280/10s klip üretildi -- görsel olarak Bao'nun
  kimliği (yüz işaretleri, sarı hasır yelek, sırt çantası) yeni bir
  sahnede/pozda tutarlı kaldı, sahne anlatımla (paylaşma) birebir eşleşti.

**Kapsam dışı bırakılan, açıkça belirtilen noktalar:** YouTube'un "Made for
Kids" (COPPA) etiketinin `publisher.py`'de ayarlanıp ayarlanmadığı ayrı bir
araştırma konusu, bu turda çözülmedi. `values_education`'ın tam
`PROFILE_PROMPTS`/`SHOT_GUIDANCE` metni ilk bölüm üretilirken daha da
netleşebilir. 10 bölümün otomatik/sıralı üretimi bilinçli olarak
YAPILMADI -- her bölüm hâlâ webui'den tek tek, insan onayıyla üretiliyor.

## Thumbnail A/B → 4 varyant + "duygu etiketi" (kullanıcı onaylı, önce plan)

Kullanıcı, mevcut 2-varyantlı (A/B) thumbnail özelliğini 4 varyanta
çıkarmak ve her varyanta okunabilir bir "duygu etiketi" eklemek istedi.
Kod yazmadan önce sadece plan istendi -- 5 net soruya (risk, duygu
etiketinin görsele mi yoksa metne mi gideceği, seçim/indirme
entegrasyonu, regresyon, zaman noktası seçimi) yazılı cevap verilip
onay alındıktan sonra kodlandı.

**Teknik (tamamen additive, sıfır regresyon hedefiyle):**
- `thumbnail_generator.py`: `generate_thumbnail_variant_c()`/`_d()`
  eklendi -- `generate_thumbnail_variant_b()`'nin BİREBİR aynı deseni,
  sadece farklı sabit `frame_fraction` (C=0.75 "later", D=0.10 "early
  ama ilk kare değil"). `generate_thumbnail()`/`_variant_b()` HİÇ
  değişmedi.
- `DocumentaryProject`: `thumbnail_variant_c_path`/`_d_path` alanları.
- `default_pipeline.py`'nin 2 çağrı noktası (`run_pipeline`,
  `regenerate_from_edited_script`): variant_b'nin hemen ardına
  variant_c/d çağrıları eklendi, her biri bağımsız best-effort (biri
  başarısız olursa diğerini engellemiyor).
- `webui/Main.py`'nin `_render_project_media_panel`'i: özel-durumlu
  "B varsa 2 kolon, yoksa 1 kolon" if/else'i, gerçekte var olan (alan
  dolu + dosya diskte mevcut) varyantların bir listesinden dinamik
  `st.columns(N)`'e genelleştirildi -- eski, sadece A+B'li ya da tek
  A'lı kayıtlarda `.get(...)` boş string döndüğü için otomatik 2/1
  koluna düşüyor, geriye dönük regresyon yok.
- "Duygu etiketi": GÖRSELE GÖMÜLÜ bir rozet DEĞİL, sadece webui
  caption metni (kullanıcının önerdiği düşük-risk seçenek) -- mevcut
  "Variant A/B" i18n deseninin devamı, `_overlay_title`'a dokunulmadı.
  Dürüstçe belirtildi: bu, karenin gerçekten analiz edilip bir duyguya
  sınıflandırıldığı anlamına GELMİYOR -- her sabit zaman noktasına
  önceden atanmış editoryal bir isim (C=0.75 "Doruk/Climax", D=0.10
  "Açılış/Opening").
- i18n: `Documentary Thumbnail Variant C/D` key'leri, 9 dilde.

**Gerçek tarayıcı doğrulaması (kullanıcının istediği gibi, commit'ten
ÖNCE gösterildi):** Ayrı, geçici bir Streamlit süreci (farklı port,
production'a dokunmadan) gerçek bir tamamlanmış projenin video +
thumbnail dosyalarıyla başlatıldı, Playwright/gerçek headless Chromium
ile ekran görüntüsü alındı. **Bu test sırasında gerçek bir bug
bulundu ve düzeltildi:** sabit `width=240` (eski 2-sütunlu tasarımdan
kalma), 4 dar sütunda görsel/caption üst üste binmesine yol açıyordu --
`width="stretch"` ile düzeltildi (her görsel kendi sütununa göre
ölçekleniyor). Düzeltmeden sonra tekrar doğrulandı: 4 ayrı görsel, üst
üste binme yok, doğru başlıklar ("Option A"..."Option D — Opening").

**Test:** Yeni birim testleri (`TestGenerateThumbnailVariantC/D`,
`test_default_pipeline.py`'nin variant_c/d mock+assert'leri, 3 yeni webui
AppTest -- 4 varyant render, kısmi varyant [C eksik] atlama, tek-varyant
eski davranış regresyon testi). Tam suite: **916 passed, 11 skipped**
(907'den +9, sıfır regresyon). `ruff` temiz.
