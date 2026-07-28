import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

ROOT_DIR = Path(__file__).parent.parent.parent
WEBUI_MAIN = ROOT_DIR / "webui" / "Main.py"

# GÖREV 1 (TAM OTONOMİ): "Klasik Mod" kullanıcıdan gizlendi (visibility=
# "hidden"), silinmedi -- _render_legacy_page() hâlâ st.navigation'da
# kayıtlı, sadece kenar çubuğunda görünmüyor. Streamlit's AppTest,
# st.navigation()'ın kendi sidebar render'ını sorgulanabilir widget'lar
# olarak açığa çıkarmıyor (app.sidebar her zaman boş bir SpecialBlock
# dönüyor) -- bu yüzden burada gerçek görünürlük davranışını değil, kaynak
# koddaki niyeti kilitliyoruz: bir sonraki kişi visibility="hidden"'ı
# yanlışlıkla silerse bu test kırmızı çıkar. Gerçek görünürlük, canlı
# tarayıcı ile ayrıca doğrulandı (bkz. PROGRESS.md).


def _page_blocks() -> dict[str, str]:
    """st.navigation([...]) çağrısı içindeki her st.Page(...) bloğunu,
    render fonksiyonunun adına göre anahtarlanmış bir dict olarak döner.
    """
    source = WEBUI_MAIN.read_text(encoding="utf-8")
    nav_start = source.index("pg = st.navigation(")
    nav_end = source.index("pg.run()", nav_start)
    nav_block = source[nav_start:nav_end]

    blocks = {}
    for match in re.finditer(r"st\.Page\(\s*\n?\s*(_render_\w+)", nav_block):
        render_fn = match.group(1)
        start = match.start()
        # st.Page(...) çok satırlı -- bir sonraki "st.Page(" ya da bloğun
        # sonuna kadar olan metni bu sayfanın bloğu olarak al.
        next_page = re.search(r"st\.Page\(", nav_block[start + 1 :])
        end = start + 1 + next_page.start() if next_page else len(nav_block)
        blocks[render_fn] = nav_block[start:end]
    return blocks


def test_classic_mode_page_is_still_registered():
    # Silinmedi -- 4 test dosyasındaki (~39 test) _LEGACY_PAGE_HASH tabanlı
    # doğrudan erişim hâlâ çalışmalı.
    blocks = _page_blocks()
    assert "_render_legacy_page" in blocks
    assert 'url_path="classic"' in blocks["_render_legacy_page"]


def test_classic_mode_page_is_hidden_from_the_sidebar():
    blocks = _page_blocks()
    assert 'visibility="hidden"' in blocks["_render_legacy_page"]


def test_stock_quality_and_history_pages_remain_visible():
    # 3-sayfa restructuring (kullanıcı onaylı, TAM OTONOMİ): eski birleşik
    # "Oluştur" sayfası (_render_documentary_studio_page), Video Kaynağı
    # seçimine göre ikiye bölündü -- "Stok Üretimler" (varsayılan) ve
    # "Belgesel Niteliği" (url_path="quality").
    blocks = _page_blocks()
    assert "_render_stock_productions_page" in blocks
    assert "_render_documentary_quality_page" in blocks
    assert "_render_history_page" in blocks
    assert 'visibility="hidden"' not in blocks["_render_stock_productions_page"]
    assert 'visibility="hidden"' not in blocks["_render_documentary_quality_page"]
    assert 'visibility="hidden"' not in blocks["_render_history_page"]


def test_stock_productions_page_is_the_default():
    # Eski birleşik sayfadaki video-kaynağı selectbox'ının varsayılanı da
    # "stock" (index=0) idi -- bölünmeden sonra varsayılan-sayfa davranışı
    # değişmesin diye "Stok Üretimler" varsayılan kalıyor.
    blocks = _page_blocks()
    assert "default=True" in blocks["_render_stock_productions_page"]
    assert "default=True" not in blocks["_render_documentary_quality_page"]


def test_documentary_quality_page_has_its_own_url_path():
    blocks = _page_blocks()
    assert 'url_path="quality"' in blocks["_render_documentary_quality_page"]
