import ast
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

ROOT_DIR = Path(__file__).parent.parent.parent
WEBUI_MAIN = ROOT_DIR / "webui" / "Main.py"
DEFAULT_PIPELINE = ROOT_DIR / "app" / "pipeline" / "default_pipeline.py"
I18N_DIR = ROOT_DIR / "webui" / "i18n"

ALL_LOCALES = ("de", "en", "es", "id", "pt", "ru", "tr", "vi", "zh")

_STAGE_MESSAGE_KEYS = (
    "Documentary Stage Intent",
    "Documentary Stage Research",
    "Documentary Stage Outline",
    "Documentary Stage Scene",
    "Documentary Stage Script",
    "Documentary Stage Storyboard",
    "Documentary Stage Asset",
    "Documentary Stage Asset Download",
    "Documentary Stage Audio",
    "Documentary Stage Timeline",
    "Documentary Stage SEO",
    "Documentary Stage Video Render",
)


def _translation(locale):
    data = json.loads((I18N_DIR / f"{locale}.json").read_text(encoding="utf-8"))
    return data["Translation"]


def test_stage_message_keys_present_and_non_empty_in_every_locale():
    for locale in ALL_LOCALES:
        translation = _translation(locale)
        for key in _STAGE_MESSAGE_KEYS:
            assert key in translation, f"{key!r} missing from {locale}.json"
            assert translation[key].strip(), f"{key!r} is empty in {locale}.json"


def _extract_dict_literal(source_path: Path, var_name: str) -> dict:
    """Bir modülü hiç import etmeden (Streamlit'siz/pipeline importsuz),
    sadece AST üzerinden belirli bir modül-seviyesi dict literal'ini
    okur -- test_webui_task_history.py'deki AST-çıkarma deseniyle aynı.
    """
    tree = ast.parse(source_path.read_text(encoding="utf-8"))
    for node in tree.body:
        if isinstance(node, ast.Assign) and any(
            isinstance(target, ast.Name) and target.id == var_name
            for target in node.targets
        ):
            return ast.literal_eval(node.value)
    raise AssertionError(f"{var_name!r} not found in {source_path}")


def _extract_stage_call_names(source_path: Path) -> list[str]:
    """default_pipeline.py'deki `stage(n, "name")` çağrılarının literal
    isim argümanlarını, dosyadaki sırayla döndürür.
    """
    tree = ast.parse(source_path.read_text(encoding="utf-8"))
    names = []

    class _StageCallVisitor(ast.NodeVisitor):
        def visit_Call(self, node):
            if (
                isinstance(node.func, ast.Name)
                and node.func.id == "stage"
                and len(node.args) == 2
                and isinstance(node.args[1], ast.Constant)
                and isinstance(node.args[1].value, str)
            ):
                names.append(node.args[1].value)
            self.generic_visit(node)

    _StageCallVisitor().visit(tree)
    return names


def test_stage_key_mapping_matches_default_pipeline_stage_names_exactly():
    """Regresyon: webui/Main.py'nin _DOCUMENTARY_STAGE_KEYS'i,
    default_pipeline.py'nin gerçek stage() çağrılarında kullandığı ham
    isimlerin AYNISINI (fazlasız eksiksiz) kapsamalı -- pipeline'a yeni bir
    aşama eklenip burası unutulursa bu test kırılır (status mesajı sessizce
    güncellenmemek yerine, en azından bu görülür).
    """
    stage_keys = _extract_dict_literal(WEBUI_MAIN, "_DOCUMENTARY_STAGE_KEYS")
    pipeline_stage_names = _extract_stage_call_names(DEFAULT_PIPELINE)

    assert len(pipeline_stage_names) == 12
    assert set(stage_keys) == set(pipeline_stage_names)


def test_stage_key_mapping_values_are_all_known_i18n_keys():
    stage_keys = _extract_dict_literal(WEBUI_MAIN, "_DOCUMENTARY_STAGE_KEYS")
    assert set(stage_keys.values()) == set(_STAGE_MESSAGE_KEYS)
