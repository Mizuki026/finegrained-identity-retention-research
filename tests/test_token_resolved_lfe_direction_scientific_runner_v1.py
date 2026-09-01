#!/usr/bin/env python3
import ast,sys,unittest
from collections import Counter,defaultdict
from pathlib import Path
REPO=Path(__file__).resolve().parents[1]; SRC=REPO/"src"; sys.path.insert(0,str(SRC))
import token_resolved_lfe_direction_protocol_v1 as protocol
import run_token_resolved_lfe_direction_scientific_v1 as runner
class ScientificRunnerTests(unittest.TestCase):
    def test_plan(self):
        _,formal=protocol.validate_formal_master(); plan=protocol.scientific_reference_plan(formal)
        self.assertEqual(len(plan),160); self.assertEqual(len({r["formal_unit_id"] for r in plan}),40)
        self.assertEqual(Counter(r["operation"] for r in plan),Counter({"direct_lfe":160}))
        seeds=defaultdict(set)
        for row in plan: seeds[row["formal_unit_id"]].add(row["seed"])
        self.assertTrue(all(value==set(protocol.FORMAL_SEEDS) for value in seeds.values()))
    def test_no_top_level_ml_imports(self): runner.assert_no_top_level_ml_imports()
    def test_runtime_no_serializer(self):
        tree=ast.parse((SRC/"token_resolved_lfe_direction_scientific_runtime_v1.py").read_text())
        attrs={n.func.attr for n in ast.walk(tree) if isinstance(n,ast.Call) and isinstance(n.func,ast.Attribute)}
        self.assertFalse({"save","numpy","tolist"}&attrs)
    def test_researcher_authority(self): self.assertIn("AUTHORIZED",runner.validate_researcher_authority()["status"])
if __name__=="__main__": unittest.main()
