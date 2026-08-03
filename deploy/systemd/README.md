# Zamanlanmış Üretim -- systemd unit'leri

`ai-documentary-studio-webui.service`'ten (production Streamlit servisi)
TAMAMEN AYRI, `scripts/scheduled_generate.py`'yi haftalık tetikleyen 2
`Type=oneshot` servis + 2 timer. **Yayınlama (Publish) İÇERMEZ** -- bkz.
`scripts/scheduled_generate.py`'nin dosya başı docstring'i +
`test/services/test_scheduled_generate_safety.py`.

## Zamanlama

- `documentary-scheduled-long.timer` -- Pazartesi 09:00 UTC, `--kind long`
  (extended pacing, 10dk, 16:9).
- `documentary-scheduled-short.timer` -- Salı/Perşembe/Cuma/Pazar 09:00
  UTC, `--kind short` (short pacing, 35sn, 9:16).

Her ikisi de `Persistent=true` -- sunucu o an kapalıysa, açılınca
gecikmeli çalıştırılır (kaçırılan bir hafta kaybolmaz).

## Kurulum

```bash
sudo cp deploy/systemd/documentary-scheduled-*.service deploy/systemd/documentary-scheduled-*.timer /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now documentary-scheduled-long.timer
sudo systemctl enable --now documentary-scheduled-short.timer
```

## Doğrulama

```bash
systemctl list-timers documentary-scheduled-*   # bir sonraki tetiklenme zamanını gösterir
journalctl -u documentary-scheduled-long.service -n 50   # son çalıştırmanın logu
journalctl -u documentary-scheduled-short.service -n 50
```

## Manuel/anlık tetikleme (haftalarca beklemeden test için)

Timer'lardan bağımsız, doğrudan script'i çalıştırın:

```bash
.venv/bin/python scripts/scheduled_generate.py --kind short
.venv/bin/python scripts/scheduled_generate.py --kind long
```

## Kaldırma

```bash
sudo systemctl disable --now documentary-scheduled-long.timer documentary-scheduled-short.timer
sudo rm /etc/systemd/system/documentary-scheduled-*.service /etc/systemd/system/documentary-scheduled-*.timer
sudo systemctl daemon-reload
```
