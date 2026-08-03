"""

"Haftalık Otomatik Üretim" planı (kullanıcı onaylı, KRİTİK GÜVENLİK
SINIRI): scripts/scheduled_generate.py'nin gerçekten hiçbir yayınlama
kodu içermediğini, hiçbir zaman AI-video (paralı) kaynağına
geçmediğini kilitleyen testler. Gelecekte biri yanlışlıkla bir publish
çağrısı ya da video_source="ai_generated" eklerse bu dosya KIRILIR.

Tespit fonksiyonları BİLEREK AST tabanlı (statik `import` + dinamik
`importlib.import_module()`/`__import__()` çağrıları) -- dosyanın kendi
docstring'i/yorumları GÜVENLİK TASARIMINI AÇIKLARKEN "publisher"
kelimesini defalarca kullanıyor (bu İYİ, istenen bir şey) -- naif bir
düz-metin arama bunu YANLIŞ POZİTİF olarak işaretlerdi. AST, sadece
GERÇEK kod kullanımını (import ifadeleri) yakalıyor, doğal dil
açıklamasını değil.
"""

import ast
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

ROOT_DIR = Path(__file__).parent.parent.parent
SCRIPT_PATH = ROOT_DIR / "scripts" / "scheduled_generate.py"

_FORBIDDEN_IMPORT_SUBSTRINGS = ("publisher", "upload_post", "webui")


def _imported_module_names(script_path: Path) -> list[str]:
    """Hem `import a.b.c` (modül yolunun kendisi) hem de `from a.b import c`
    (HEM `a.b` HEM `a.b.c` -- `c` burada bir alt-modül/isim olabilir,
    "publisher" tam olarak böyle import ediliyor: `from app.departments.
    growth import publisher`, yani asıl "publisher" ismi `node.module`'da
    DEĞİL, `node.names`'te) biçimlerini yakalar.
    """
    tree = ast.parse(script_path.read_text(encoding="utf-8"))
    names: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            names.extend(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            names.append(node.module)
            names.extend(f"{node.module}.{alias.name}" for alias in node.names)
    return names


def _dynamic_import_string_args(script_path: Path) -> list[str]:
    """String literal argümanları `importlib.import_module(...)` ya da
    `__import__(...)` çağrılarından toplar -- statik `import` taramasını
    (yukarıdaki) dinamik bir importla atlatma girişimini yakalar."""
    tree = ast.parse(script_path.read_text(encoding="utf-8"))
    results: list[str] = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        func = node.func
        is_dynamic_import = (isinstance(func, ast.Name) and func.id == "__import__") or (
            isinstance(func, ast.Attribute) and func.attr == "import_module"
        )
        if not is_dynamic_import:
            continue
        for arg in node.args:
            if isinstance(arg, ast.Constant) and isinstance(arg.value, str):
                results.append(arg.value)
    return results


def _forbidden_imports(script_path: Path) -> list[str]:
    candidates = _imported_module_names(script_path) + _dynamic_import_string_args(script_path)
    return [
        name
        for name in candidates
        if any(bad in name.lower() for bad in _FORBIDDEN_IMPORT_SUBSTRINGS)
    ]


def _forced_video_source_literal(script_path: Path) -> str | None:
    """FORCED_VIDEO_SOURCE'a atanan GERÇEK string literal'i AST üzerinden
    bulur -- yorumların ne dediğiyle ilgilenmez, sadece gerçek kodu okur.
    """
    tree = ast.parse(script_path.read_text(encoding="utf-8"))
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name) and target.id == "FORCED_VIDEO_SOURCE":
                    if isinstance(node.value, ast.Constant) and isinstance(node.value.value, str):
                        return node.value.value
    return None


class TestScheduledGenerateNeverImportsPublisher(unittest.TestCase):
    def test_real_script_has_no_forbidden_static_or_dynamic_imports(self):
        found = _forbidden_imports(SCRIPT_PATH)
        self.assertEqual(found, [], f"forbidden imports found in {SCRIPT_PATH.name}: {found}")

    def test_real_script_only_imports_from_app_or_stdlib_or_third_party_deps(self):
        # Pozitif bir kontrol: sadece BEKLENEN üst düzey modüller import
        # ediliyor -- negatif "yasaklı kelime" testinin yakalayamayacağı
        # bir yeniden-adlandırma/takma-ad senaryosuna karşı ek güvence.
        allowed_top_level = {
            "argparse", "sys", "datetime", "pathlib", "uuid",  # stdlib
            "yaml", "loguru",  # third-party, requirements.txt'te zaten var
            "app",  # sadece app.config / app.pipeline alt modülleri
        }
        imported = _imported_module_names(SCRIPT_PATH)
        for name in imported:
            top_level = name.split(".")[0]
            self.assertIn(
                top_level, allowed_top_level, f"unexpected top-level import: {name}"
            )

    def test_forced_video_source_constant_is_pexels_via_real_import(self):
        # Gerçek import + değerlendirme -- AST'in "belki bir yerde runtime'da
        # değiştiriliyordur" riskini de kapatır (dosyayı gerçekten çalıştırıp
        # GERÇEK son değere bakıyor).
        from scripts import scheduled_generate

        self.assertEqual(scheduled_generate.FORCED_VIDEO_SOURCE, "pexels")

    def test_forced_video_source_literal_is_pexels_via_ast(self):
        self.assertEqual(_forced_video_source_literal(SCRIPT_PATH), "pexels")

    def test_run_pipeline_call_uses_the_forced_video_source_constant(self):
        # Kaynak metninde run_pipeline(...) çağrısının GERÇEKTEN
        # FORCED_VIDEO_SOURCE değişkenini kullandığını doğruluyor -- sabit
        # değeri doğru olsa bile çağrıda kullanılmıyorsa (ör. yanlışlıkla ham
        # bir string'e geri dönülmüşse) bu test yakalar.
        source = SCRIPT_PATH.read_text(encoding="utf-8")
        self.assertIn("video_source=FORCED_VIDEO_SOURCE", source)


class TestForbiddenImportDetectorReallyWorks(unittest.TestCase):
    """Kullanıcının istediği kanıt: detector fonksiyonlarının GERÇEKTEN
    çalıştığını, bilinçli olarak sabote edilmiş bir KOPYA üzerinde
    göstermek -- gerçek scripts/scheduled_generate.py dosyasına hiç
    dokunulmuyor.
    """

    def setUp(self):
        self.tmp_dir = Path(tempfile.mkdtemp())
        self.addCleanup(lambda: shutil.rmtree(self.tmp_dir, ignore_errors=True))

    def test_detector_catches_a_sabotaged_copy_with_a_static_publisher_import(self):
        sabotaged = self.tmp_dir / "sabotaged_static_import.py"
        shutil.copy(SCRIPT_PATH, sabotaged)
        with open(sabotaged, "a", encoding="utf-8") as f:
            f.write("\n\nfrom app.departments.growth import publisher  # SABOTAGE\n")

        found = _forbidden_imports(sabotaged)
        self.assertTrue(
            any("publisher" in name.lower() for name in found),
            f"sabotaged static import was not detected: {found}",
        )

    def test_detector_catches_a_sabotaged_copy_with_a_dynamic_publisher_import(self):
        sabotaged = self.tmp_dir / "sabotaged_dynamic_import.py"
        shutil.copy(SCRIPT_PATH, sabotaged)
        with open(sabotaged, "a", encoding="utf-8") as f:
            f.write(
                "\n\nimport importlib\n"
                "publisher = importlib.import_module('app.departments.growth.publisher')"
                "  # SABOTAGE\n"
            )

        found = _forbidden_imports(sabotaged)
        self.assertTrue(
            any("publisher" in name.lower() for name in found),
            f"sabotaged dynamic import was not detected: {found}",
        )

    def test_detector_catches_a_sabotaged_copy_with_an_upload_post_import(self):
        sabotaged = self.tmp_dir / "sabotaged_upload_post_import.py"
        shutil.copy(SCRIPT_PATH, sabotaged)
        with open(sabotaged, "a", encoding="utf-8") as f:
            f.write("\n\nfrom app.services import upload_post  # SABOTAGE\n")

        found = _forbidden_imports(sabotaged)
        self.assertTrue(
            any("upload_post" in name.lower() for name in found),
            f"sabotaged upload_post import was not detected: {found}",
        )

    def test_detector_catches_a_sabotaged_copy_that_switches_to_ai_generated(self):
        sabotaged = self.tmp_dir / "sabotaged_ai_video.py"
        shutil.copy(SCRIPT_PATH, sabotaged)
        content = sabotaged.read_text(encoding="utf-8")
        content = content.replace(
            'FORCED_VIDEO_SOURCE = "pexels"',
            'FORCED_VIDEO_SOURCE = "ai_generated"  # SABOTAGE',
        )
        sabotaged.write_text(content, encoding="utf-8")

        self.assertEqual(_forced_video_source_literal(sabotaged), "ai_generated")
        self.assertNotEqual(_forced_video_source_literal(sabotaged), "pexels")

    def test_detector_finds_nothing_wrong_in_an_unmodified_copy(self):
        # Regresyon: detector aşırı hassas değil -- gerçek, sabote
        # EDİLMEMİŞ script'te hiçbir yasaklı import bulmamalı, bu, dosyanın
        # kendi docstring'i/yorumları "publisher" kelimesini AÇIKÇA
        # kullanmasına RAĞMEN geçerli (AST sadece gerçek importlara bakıyor).
        clean_copy = self.tmp_dir / "clean_copy.py"
        shutil.copy(SCRIPT_PATH, clean_copy)
        self.assertEqual(_forbidden_imports(clean_copy), [])
        self.assertEqual(_forced_video_source_literal(clean_copy), "pexels")


if __name__ == "__main__":
    unittest.main()
