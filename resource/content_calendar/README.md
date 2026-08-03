# İçerik Takvimleri

`*.yaml` dosyaları (ör. `zihin_davranis_calendar.yaml`), `scripts/
scheduled_generate.py` tarafından **gerçekten okunup yazılan** haftalık
üretim kuyruklarıdır (`resource/characters/bao_content_calendar.yaml`'ın
aksine -- o dosya sadece insan referansı, hiçbir kod okumuyor).

**Not:** `scheduled_generate.py` her başarılı üretimden sonra YAML
dosyasını `yaml.safe_dump()` ile yeniden yazar -- bu, dosyadaki `#`
yorumlarını SİLER (standart YAML kütüphanelerinin bir sınırlaması).
Kalıcı açıklama bu yüzden burada, README'de tutuluyor; YAML dosyasının
kendisi ilk otomatik çalıştırmadan sonra yorumsuz kalabilir, bu
beklenen bir davranış, veri kaybı değildir (sadece `status` alanları
ve varsa yeni eklediğiniz girdiler önemli).

## Şema

```yaml
niche: "<kanal nişinin adı>"
language: "tr"   # run_pipeline()'a geçirilen dil

long_form:   # haftada 1 (ör. Pazartesi), extended pacing (10dk)
  - week: 1
    topic: "<video başlığı/konusu>"
    topic_category: personal_development   # app/config/profile_dimensions.py TopicCategory
    tone: motivational                      # app/config/profile_dimensions.py Tone
    status: planned   # planned | generated | reviewed | published

shorts:      # haftada 4 (ör. Sal/Per/Cum/Paz), short pacing (35sn)
  - index: 1
    topic: "<video başlığı/konusu>"
    topic_category: psychology
    status: planned
```

`status: placeholder` özel bir değerdir -- script SADECE `status: planned`
girdileri işler, `placeholder` (ve `generated`/`reviewed`/`published`)
girdileri atlar. Şablon dosyada gelen örnek girdiler `placeholder`
olarak işaretli; gerçek başlıklarınızı eklerken her girdinin `status`'unu
`planned`'a çevirmeyi unutmayın.

## Akış

1. `scheduled_generate.py --kind long` (ya da `short`), ilgili listede
   `status: planned` olan İLK girdiyi bulur.
2. `run_pipeline()`'ı SADECE stok video (Pexels, ücretsiz) ile çalıştırır
   -- AI Video ve yayınlama (Publish) KESİNLİKLE devreye girmez.
3. Başarılı olursa girdinin `status`'u `generated`'a çevrilip dosya geri
   yazılır. Başarısız olursa dosya DEĞİŞMEZ -- bir sonraki zamanlanmış
   çalıştırma aynı konuyu tekrar dener.
4. `status: planned` girdi kalmazsa, script hiçbir şey üretmeden,
   hatasız çıkar ("takvim tükendi" logu) -- yeni haftalar eklemek için
   dosyaya elle yeni girdi eklemeniz yeterli.

## Manuel tetikleme (test için)

```bash
.venv/bin/python scripts/scheduled_generate.py --kind short
.venv/bin/python scripts/scheduled_generate.py --kind long
```

## Otomatik zamanlama

`deploy/systemd/documentary-scheduled-{long,short}.timer` -- kurulum
adımları için `deploy/systemd/README.md`'ye bakın.
