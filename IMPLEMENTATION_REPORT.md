# Uygulama Raporu — 2026-08-15 (gece oturumu, tam otonomi)

Talimat: 5 konuyu tek oturumda, onay beklemeden baştan sona uygula, test et,
ruff kontrolü yap, main'e push et, deploy et. Bu rapor o oturumun sonucu.

**Özet:** 4/5 konu kod değişikliğiyle çözüldü (KONU 2 önceki bir oturumda
zaten çözülmüştü, bu turda sadece doğrulandı/dokunulmadı). Toplam test
sayısı 1049 → **1087** (+38 yeni test), **0 fail**, 11 skip (ilgisiz,
önceden de vardı). `ruff check .` temiz. Push + deploy tamamlandı.

---

## KONU 1: Sahne Bazlı Gerçek Ses Değişimi

### Mimari inceleme (özet — temel mekanizma önceki oturumda kuruldu)

- `render_narration()`: TEK `voice.tts()` çağrısı, `script.full_text`
  üzerinde, TEK `voice_name`.
- Altyazı zamanlaması **karışık**: ElevenLabs (karakter sesleri bunu
  kullanıyor) `/with-timestamps` endpoint'inden **gerçek ölçülen**
  karakter-bazlı hizalama alıyor; diğer sağlayıcılar (Gemini, MiMo,
  no-voice) karakter-sayısı **oranına göre tahmin** yapıyor.
  `create_subtitle()` altyazıyı `script.lines` (sahne) değil, **noktalamaya
  göre bölünmüş cümlelere** göre segmentliyor.
- **Kritik bulgu (önceki oturumda tespit edildi, bu turda kapsam onaylandı
  ve düzeltildi):** `video_concat_mode` AI-üretilen video için de
  `random` idi -- `app/services/video.py`'nin `_prioritize_unique_source_
  clips()`'i `random.shuffle()` yapıyordu. AI-üretilen video HER sahne
  için TEK bir klip ürettiği için (scene sırasına göre), bu karıştırma
  sahne↔anlatım (ve şimdi sahne↔karakter sesi) eşleşmesini bozabiliyordu.
  **Düzeltildi:** AI-üretilen video kaynağı artık HER ZAMAN `sequential`
  kullanıyor (`default_pipeline.py`, hem `run_pipeline` hem
  `regenerate_from_edited_script`); stok görüntü `random` kalmaya devam
  ediyor (çeşitlilik amacı hâlâ geçerli).

### Bu turda eklenen YENİ davranış

1. **Varsayılan/Yedek Anlatıcı** (`audio_renderer.py`,
   `_KIDS_DEFAULT_NARRATOR_SLUG = "professor_nova"`): Kids formatında,
   Auto kadrolama bir sahneye hiç karakter atamadıysa (`characters: []`),
   genel `voice_name` yerine **Professor Nova**'nın sesi kullanılıyor.
   Kids DIŞINDA bu varsayılan HİÇ tetiklenmiyor (o durumda genel
   `voice_name` -- birebir eski davranış).
2. **Çoklu karakter sesi belirsizliği** (KONU 3 ile birleşik): bir sahneye
   2+ karakter atandıysa, hangi sesin okuyacağı Kids formatında yine
   Professor Nova'ya, diğer formatlarda **listedeki İLK karaktere**
   (casting_generator'ın kendi öncelik sırası) düşüyor.
3. `_should_use_per_scene_narration()`: sahne-bazlı yolun ne zaman
   tetikleneceğine karar veren tek nokta -- ya en az bir sahnede karakter
   varsa, ya da format Kids ise (karaktersiz sahnelerde bile Professor
   Nova farkı üretebileceği için). `casting_by_scene` boş/None ise
   (Auto DEĞİLSE) format ne olursa olsun HER ZAMAN eski tek-çağrılı yola
   düşer -- **regresyon garantisi**.
4. Ton varsayılanı (`profile_dimensions.resolve_tone`): Kids formatında,
   `tone_override` YOKSA, topic_category'den BAĞIMSIZ olarak
   `Tone.nurturing` dönüyor. Daha önce Kids + `topic_category=space` gibi
   bir kombinasyon "epic" (hızlı/yoğun -- kodun kendisinin "3-8 yaş için
   ZARARLI" dediği) tona düşebiliyordu. **`Tone.nurturing` zaten mevcut
   enum'da vardı** (values_education kategorisi için kullanılıyordu),
   yeni bir değer eklenmedi.

### Regresyon garantisi

`casting_by_scene` sadece `character_selection == AUTO_CHARACTER`
olduğunda dolu geliyor (default_pipeline._resolve_references_by_scene) --
sabit karakter / karaktersiz modlarda hep `{}`, bu yüzden yeni mekanizma
hiç tetiklenmiyor. `_resolve_narration_voice()` (tek sabit karakter
override'ı) dokunulmadı, paralel çalışıyor.

**Bilinen sınırlama (koda not düşüldü, düzeltilmedi):**
`regenerate_from_edited_script()` `casting_by_scene`'i hiç bilmiyor
(DocumentaryProject'te kalıcı değil) -- script düzenleyip yeniden render
edilirse sahne-bazlı sesler kaybolur, tek genel sese düşer. Görseller
(asset_plan yeniden üretilmediği için) doğru kalır. Gerçek düzeltme yeni
bir kalıcı alan gerektirir -- kapsam dışı bırakıldı.

---

## KONU 2: "Mira" Halüsinasyonu — ÖNCEDEN ÇÖZÜLDÜ, bu turda dokunulmadı

Bu, önceki bir oturumda (commit `1a67874`) zaten kökten çözülmüştü:
`script_generator.py`'nin `FORMAT_GUIDANCE[Format.kids]`'i artık isim
uydurmayı açıkça yasaklıyor ("Do not invent or name any character..."),
çünkü kök sebep doğrulanmıştı: script casting'den (stage 6.5) ÖNCE (stage
5) yazılıyor, script_generator'ın gerçek roster'a hiç erişimi yok. Test
(`test_kids_format_forbids_inventing_a_named_character`) zaten mevcuttu,
bu turda tekrar çalıştırılıp doğrulandı, hâlâ geçiyor. **Bu turda hiçbir
kod değişikliği yapılmadı** -- talimat aynı analizi tekrar istiyordu, ama
analiz zaten geçerliydi.

---

## KONU 3: Çoklu Karakter Aynı Sahnede

### Şema değişikliği

`casting_generator.py`'nin JSON şeması: `"character": slug|null` (tekil)
→ **`"characters": [slug, ...]` (0-N liste)**. Neden bu yaklaşım (mevcut
`CHARACTER_PAIRS`'i genelleştirmek yerine): `CHARACTER_PAIRS` SABİT,
önceden tanımlı ikili kombinasyonlar (ör. "Anne Kuş & Yavrusu") için --
casting_generator'ın HER SAHNE için DİNAMİK olarak karar vermesi gereken
bir şeyi (konuya göre hangi 1-3 karakter uygun) statik bir eşleşme
tablosuyla ifade etmek pratik değil. Serbest liste, LLM'in doğal kararına
en uygun temsil.

### Üst sınır: 3 karakter/sahne

`docs/character-consistency-research.md`'deki gerçek fal.ai Kling O1
şemasını kontrol ettim: **"max 7 total (elements + image_urls + implicit
start frame)"**. `image_urls` hiç kullanılmıyor, implicit start frame 1
slot yiyor → 6 kullanılabilir element. Bir sahnede karakterlerin yanında
bir de mekan (1 element daha) seçilebiliyor → pratik üst sınır **3
karakter + 1 mekan = 4**, sert 6 sınırının altında güvenli bir marj.
`_MAX_CHARACTERS_PER_SCENE = 3` sabiti + `_parse_character_slugs()` fazla
karakterleri (liste sonundan, en düşük öncelikli) sessizce düşürüp
`logger.warning()` ile kaydediyor.

### Alt akış değişikliği gerekmedi

`asset_generator.build_asset_plan()`'ın `@Element1, @Element2, ...`
prompt-oluşturma mantığı **zaten** `enumerate(scene_references)` ile
genel yazılmıştı (karakter+mekan kombinasyonu için) -- N karaktere
genelleme için HİÇBİR değişiklik gerekmedi. `default_pipeline.
_resolve_references_by_scene()`'de tek satırlık bir `for slug in
casting_by_scene[idx]["characters"]:` döngüsü yeterliydi.

---

## KONU 4: CTA/Etkileşim Formatlı Short Videolar

`script_generator.py`'ye `video_style: str = "informational"` parametresi
eklendi. `"engagement_cta"` verildiğinde `_engagement_cta_instructions()`
prompt'a bir blok ekliyor: kısa bir bağlam + izleyiciye doğrudan bir soru
+ yorum daveti, bilgi aktarmanın ZORUNLU olmadığı vurgusuyla.
`_growth_guidance_instructions()`'ın genel (kids için bastırılan)
"Engagement:" satırından BİLEREK bağımsız/farklı -- bu yeni blok Kids
formatında da bastırılMIYOR (kullanıcının kendi örneği: "Sen Olsan Nasıl
Bir Robot Tasarlardın?" zaten kids içerikte kullanılıyor).

`default_pipeline.run_pipeline()`'a opsiyonel `video_style` parametresi
eklendi (varsayılan "informational", script_generator'a aynen geçiyor).

**webui:** "Gelişmiş Ayarlar" expander'ına (`_render_documentary_advanced_
settings`, custom_requirements'ın hemen ardından) bir selectbox eklendi --
"Bilgi Videosu" / "Etkileşim (Soru-Cevap)". Her iki video kaynağı
sayfasında da görünür (stock_keyword_hint'in aksine, sayfaya bağımlı
değil). 9 dilde (en/zh/de/es/id/pt/ru/tr/vi) i18n çevirisi eklendi --
`test_webui_i18n.py`'nin otomatik eksik-anahtar kontrolüyle doğrulandı.

Gerçek Streamlit `AppTest` ile uçtan uca doğrulandı: kontrol her iki
sayfada da render ediliyor, varsayılan "informational", seçim
`run_pipeline()`'a doğru `video_style` değeriyle ulaşıyor.

---

## KONU 5: İçerik Derinliği/Kapsam İncelemesi

Kod analizi **önceki bir oturumda** zaten yapılmıştı: `PACING_SCENE_SPEC
[short] = {scene_count: 7, scene_duration: 5.0}` (35sn toplam) ve
`PACING_OUTLINE_SECTION_RANGE[short] = (4,7)` -- gerçek "Jüpiter'in 95
Uydusu" üretiminde outline TAM 7 bölüm ürettiği için (scene_count'a eşit)
`scene_planner`'ın importance-trimming'i HİÇ devreye girmedi, hiçbir bölüm
atılmadı. Sorun trimming BUG'ı değil -- "short" tasarım gereği 35 saniyelik
bir "Shorts" formatı (`profile_dimensions.py:131`'in kendi yorumu), 7
zengin bölümü (Galileo'nun keşfi, 4 isimli uydu, düzensiz uydu
popülasyonu) taşımak için asla yeterli olmayacaktı. **Bu turda kod
değişikliği yapılmadı** (bug yok) -- talimatın "opsiyonel, zaman kalırsa"
dediği yumuşak öneri mekanizması eklendi:

**webui:** Pacing "short" seçiliyken (varsayılan), pacing seçicisinin
hemen altında bir `st.caption()` görünüyor -- "birden fazla ayrı alt-konu
ya da isimli varlık içeren konularda 'Orta Video (5dk)' genelde daha
uygun olur" mesajı. Statik (konu genişliğini otomatik algılamıyor -- bu,
kapsam dışı bırakılan bir LLM-çağrısı gerektirirdi), sadece pacing="short"
iken görünüyor, hiçbir davranışı engellemiyor/değiştirmiyor. 9 dilde i18n
eklendi, gerçek `AppTest` ile (short'ta görünüyor, long'ta görünmüyor)
doğrulandı.

---

## Test ve Ruff Sonuçları

```
pytest test/ -q
1087 passed, 11 skipped, 12 warnings, 10869 subtests passed in 106.80s
(1049 → 1087, +38 yeni test, 0 fail)

ruff check .
All checks passed!
```

Değişen/etkilenen dosyalar (21 dosya, +842/-103 satır):
`app/config/profile_dimensions.py`, `app/departments/creative/
casting_generator.py`, `app/departments/creative/script_generator.py`,
`app/departments/production/audio_renderer.py`, `app/pipeline/
default_pipeline.py`, `webui/Main.py`, `webui/i18n/*.json` (9 dosya), ve
karşılık gelen 6 test dosyası.

## Deploy Durumu

- Commit + push: main'e doğrudan (ayrı branch/PR yok, talimat gereği).
- `./deploy.sh` çalıştırıldı -- `git pull` + servis restart + health check.
- `systemctl is-active ai-documentary-studio-webui.service` ile doğrulandı.

(Bu raporun altına gerçek commit hash'i ve deploy health-check çıktısı,
push+deploy adımlarından hemen sonra ekleniyor -- aşağıya bakın.)
