import importlib.util
from pathlib import Path


MODULE = Path(__file__).parents[1] / "tools" / "audit_formal_candidate_pool_v1.py"
spec = importlib.util.spec_from_file_location("formal_pool_audit", MODULE)
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)


def row(item_id, identity, gender, glasses, facial, hair):
    return {
        "item_id": item_id,
        "identity": identity,
        "gender": gender,
        "eyeglasses_label": glasses,
        "facial_hair_ordinal": facial,
        "hair_color_label": hair,
    }


def test_counts_and_within_identity_pairs():
    rows = [
        row("i1", "alpha", "man", "present", "2", "dark"),
        row("i2", "alpha", "man", "absent", "2", "light"),
        row("i3", "beta", "woman", "absent", "0", "dark"),
        row("i4", "beta", "woman", "absent", "0", "light"),
    ]
    audit, matched = mod.audit_pool(rows)
    assert audit["candidate_images"] == 4
    assert audit["candidate_identities"] == 2
    assert audit["attributes"]["eyeglasses"]["within_identity_both_states"] == 1
    assert audit["attributes"]["facial_hair"]["within_identity_both_states"] == 0
    assert audit["attributes"]["hair_color"]["within_identity_both_states"] == 2
    assert [(entry["attribute"], entry["identity"]) for entry in matched] == [
        ("eyeglasses", "alpha"),
        ("hair_color", "alpha"),
        ("hair_color", "beta"),
    ]
    assert audit["design_diagnostics"]["six_cell_gender_balanced"] is False
    assert audit["design_diagnostics"]["all_attributes_have_within_identity_pair"] is False


def test_factorial_excludes_ambiguous_facial_hair_label():
    rows = [
        row("i1", "alpha", "man", "present", "1", "dark"),
        row("i2", "beta", "man", "absent", "2", "light"),
    ]
    audit, _ = mod.audit_pool(rows)
    combos = audit["factorial_combinations_excluding_facial_hair_ordinal_1"]
    assert len(combos) == 1
    assert combos[0]["facial_hair_ordinal"] == "2"
