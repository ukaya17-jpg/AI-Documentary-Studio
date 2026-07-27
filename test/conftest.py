"""Global test safety nets.

See PROGRESS.md ("Provider Sistemi -- ADIM 1/2/3" section) for the full
incident writeup this fixture exists because of: a webui test patched
config.app with a fake value but forgot to also mock config.save_config().
Documentary Studio calls config.save_config() unconditionally on every
page render (see _render_documentary_advanced_settings() in webui/Main.py),
so that one missing mock was enough to overwrite the REAL, live production
config.toml's pexels_api_keys with a test placeholder.

Fixing the three offending tests was not considered sufficient -- any
future test that patches config.app/config.ui/config.azure/etc. and
renders a Documentary Studio page (or otherwise triggers a real
config.save_config() call) could reintroduce the exact same class of bug.
This autouse fixture makes that structurally impossible for the whole
test suite: config.save_config()'s file target is unconditionally
redirected to a throwaway per-test temp path, so even a fully-forgotten
mock can, at worst, write to a file nobody reads. Tests that need to
verify save_config()'s own real write behavior (see
test_config.py::test_save_config_uses_parseable_atomic_output) still can
-- they layer their own patch.object(config, "config_file", ...) on top,
which simply overrides this fixture's redirect for their own scope.
"""

import pytest

from app.config import config


@pytest.fixture(autouse=True)
def _never_write_the_real_config_toml(monkeypatch, tmp_path):
    monkeypatch.setattr(config, "config_file", str(tmp_path / "config.toml"))
    monkeypatch.setattr(config, "root_dir", str(tmp_path))
