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

Henüz başlanmadı. Sıradaki adım: `app/models/`, `app/services/`, `app/pipeline/`,
`app/config/profile_dimensions.py`, `app/config/templates/` dosyalarının sıfırdan
kurulması.

## FAZ 2 — Content OS genişletmesi

Başlanmadı. FAZ 1 sağlam bir şekilde bitmeden başlanmayacak. Faz 2 planı burada
kullanıcı onayı beklenerek yazılacak.

## Karar bekleyen noktalar

Şu an yok.
