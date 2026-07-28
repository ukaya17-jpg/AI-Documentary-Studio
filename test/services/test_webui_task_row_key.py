import ast
import hashlib
from pathlib import Path


ROOT_DIR = Path(__file__).parent.parent.parent
WEBUI_MAIN = ROOT_DIR / "webui" / "Main.py"


def _load_safe_task_row_key():
    """Main.py'den `_safe_task_row_key`'i Streamlit'i hiç import etmeden
    izole yükler -- aynı desen test_webui_task_history.py'de kullanılıyor."""
    tree = ast.parse(WEBUI_MAIN.read_text(encoding="utf-8"))
    function = next(
        node
        for node in tree.body
        if isinstance(node, ast.FunctionDef) and node.name == "_safe_task_row_key"
    )
    namespace = {"hashlib": hashlib}
    module = ast.fix_missing_locations(ast.Module(body=[function], type_ignores=[]))
    exec(compile(module, str(WEBUI_MAIN), "exec"), namespace)
    return namespace["_safe_task_row_key"]


safe_task_row_key = _load_safe_task_row_key()


def test_key_is_deterministic_for_the_same_task_id():
    assert safe_task_row_key("abc-123") == safe_task_row_key("abc-123")


def test_keys_differ_even_when_first_40_sanitized_characters_are_identical():
    # Gerçek production olayı (bkz. PROGRESS.md): iki farklı, uzun/tanımlayıcı
    # task_id ilk 40 karakterde aynıydı -- salt `[:40]` kesme, container
    # key'inde StreamlitDuplicateElementKey'e yol açtı. Ortak 40-karakter
    # önek + FARKLI kuyruklarla bunu burada yeniden üretiyoruz.
    common_prefix = "matrix_TopicCategory_healthy_living_Paci"[:40]
    task_id_a = common_prefix + "fic War"
    task_id_b = common_prefix + "fic Islands"

    assert len(task_id_a) > 40
    assert task_id_a[:40] == task_id_b[:40]
    assert safe_task_row_key(task_id_a) != safe_task_row_key(task_id_b)


def test_key_embeds_a_stable_hash_of_the_full_task_id():
    task_id = "some-long-descriptive-task-id-that-exceeds-forty-characters-total"
    expected_hash = hashlib.sha1(task_id.encode("utf-8")).hexdigest()[:10]

    assert safe_task_row_key(task_id).endswith(expected_hash)
