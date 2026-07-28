from pathlib import Path

ROOT_DIR = Path(__file__).parent.parent.parent
WEBUI_MAIN = ROOT_DIR / "webui" / "Main.py"
STYLES_CSS = ROOT_DIR / "webui" / "styles.css"

# Kullanıcı talebi: sidebar navigasyonu HİÇBİR ZAMAN otomatik gizlenmemeli/
# katlanmamalı.
#
# İlk düzeltme (initial_sidebar_state="auto" -> "expanded") YETERSİZ
# çıktı: gerçek Playwright testiyle bulundu, Streamlit sidebar her
# katlandığında (kullanıcı tıklaması VEYA "auto" iken dar viewport'ta
# OTOMATİK) bunu localStorage["stSidebarCollapsed-"]="true" olarak
# KALICI kaydediyor ve bu, sonraki HER yüklemede initial_sidebar_state'i
# geçersiz kılıyor -- yani "auto" döneminde bir kez dar pencerede açan
# her kullanıcı, sunucu tarafı fix'ten SONRA bile sidebar'ı asla geri
# görmüyordu. Asıl düzeltme styles.css'te: sidebar'ı Streamlit'in dahili
# collapsed state'inden (localStorage dahil) tamamen bağımsız olarak
# görsel olarak her zaman açık tutan bir CSS kuralı (collapsed'ken
# Streamlit'in uyguladığı transform: translateX(-300px)'i geçersiz
# kılıyor). Gerçek Playwright testiyle doğrulandı: localStorage'a stale
# "true" önceden yazılıp reload edildiğinde bile sidebar açık kalıyor.
#
# AppTest bu framework-seviyesi CSS/JS davranışını sorgulanabilir
# widget'lar olarak açığa çıkarmıyor (test_webui_navigation.py'deki
# intent-lock deseniyle tutarlı) -- bu yüzden kaynak koddaki niyet burada
# kilitleniyor, gerçek davranış PROGRESS.md'de belgelenen canlı tarayıcı
# testiyle (stale localStorage senaryosu dahil) ayrıca doğrulandı.


def test_sidebar_initial_state_is_expanded():
    source = WEBUI_MAIN.read_text(encoding="utf-8")
    config_start = source.index("st.set_page_config(")
    # Basit source.index(")", ...) yanlış eşleşir (açıklama yorumundaki
    # parantezli metinler yüzünden) -- çağrı kendi satırında tek başına
    # duran bir ")" ile kapanıyor.
    config_end = source.index("\n)", config_start)
    config_block = source[config_start:config_end]
    assert 'initial_sidebar_state="expanded"' in config_block


def test_sidebar_css_forces_visibility_regardless_of_stale_collapsed_state():
    css = STYLES_CSS.read_text(encoding="utf-8")
    assert 'div[data-testid="stSidebar"]' in css
    assert "transform: none !important;" in css
