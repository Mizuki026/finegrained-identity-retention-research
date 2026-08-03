import importlib.util
from pathlib import Path

MODULE = Path(__file__).parents[1] / "src" / "pilot_v1_1_attribute_evaluation_v1.py"
spec = importlib.util.spec_from_file_location("attribute_eval", MODULE)
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)

def test_synthetic_geometry_contract():
    mod.synthetic_tests()

def test_roi_is_inside_parser_grid():
    geometry = mod.hair_geometry((100, 100, 200, 200), 640, 480)
    assert geometry is not None
    _, _, _, _, x0, y0, x1, y1 = geometry
    assert 0 <= x0 < x1 <= 512
    assert 0 <= y0 < y1 <= 512

def test_eyeglasses_expected_label_mapping():
    assert mod.expected_match("eyeglasses", "present", "positive") == "True"
    assert mod.expected_match("eyeglasses", "absent", "negative") == "True"
    assert mod.expected_match("eyeglasses", "present", "negative") == "False"
