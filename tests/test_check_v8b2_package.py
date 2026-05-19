import importlib.util
import sys
from pathlib import Path


SCRIPT_PATH = Path("scripts/check_v8b2_package.py")


def load_module():
    spec = importlib.util.spec_from_file_location("check_v8b2_package", SCRIPT_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_run_checks_passes_for_current_package():
    module = load_module()
    status, results = module.run_checks()
    assert status == "PASS"
    assert results
    assert all(result.level == "PASS" for result in results)


def test_required_paths_function_is_testable():
    module = load_module()
    manifest = module.load_manifest()
    results = module.check_required_paths(manifest)
    assert results
    assert not [result for result in results if result.level == "FAIL"]
