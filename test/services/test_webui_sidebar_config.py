from pathlib import Path

ROOT_DIR = Path(__file__).parent.parent.parent
WEBUI_MAIN = ROOT_DIR / "webui" / "Main.py"

# Kullanıcı talebi: sidebar navigasyonu HİÇBİR ZAMAN otomatik gizlenmemeli/
# katlanmamalı. Gerçek Playwright testiyle doğrulandı: initial_sidebar_
# state="auto" (eski değer) Streamlit'in kendi dahili responsive kırılma
# noktasında (~700px ve altı viewport genişliği) sidebar'ı otomatik
# katlıyordu (aria-expanded=false, bounding box x=-300/width=0).
# initial_sidebar_state="expanded" ile AYNI testte 1400/700/375px
# genişliklerin ÜÇÜNDE de sidebar açık kaldı (aria-expanded=true,
# width=300) -- kullanıcı yine de manuel olarak katlayabilir, sadece
# OTOMATİK/viewport-tetiklemeli katlanma engelleniyor. AppTest bu
# framework-seviyesi ayarı sorgulanabilir bir widget olarak açığa
# çıkarmıyor (test_webui_navigation.py'deki intent-lock deseniyle
# tutarlı, bkz. o dosyanın üstteki notu) -- bu yüzden kaynak koddaki
# niyet burada kilitleniyor, gerçek davranış PROGRESS.md'de belgelenen
# canlı tarayıcı testiyle ayrıca doğrulandı.


def test_sidebar_never_auto_collapses_on_narrow_viewports():
    source = WEBUI_MAIN.read_text(encoding="utf-8")
    config_start = source.index("st.set_page_config(")
    # Basit source.index(")", ...) yanlış eşleşir (aşağıdaki açıklama
    # yorumundaki "(eski değer)" gibi parantezli metinler yüzünden) --
    # bu dosyanın kod stiliyle tutarlı olarak çağrı, kendi satırında tek
    # başına duran bir ")" ile kapanıyor.
    config_end = source.index("\n)", config_start)
    config_block = source[config_start:config_end]
    assert 'initial_sidebar_state="expanded"' in config_block
