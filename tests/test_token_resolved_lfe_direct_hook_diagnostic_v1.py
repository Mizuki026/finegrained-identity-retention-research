#!/usr/bin/env python3
import sys,unittest
from pathlib import Path
REPO=Path(__file__).resolve().parents[1];sys.path.insert(0,str(REPO/"src"))
import token_resolved_lfe_direct_hook_diagnostic_protocol_v1 as protocol
import analyze_token_resolved_lfe_direct_hook_diagnostic_v1 as analyzer
import verify_token_resolved_lfe_direct_hook_diagnostic_v1 as verifier
import run_token_resolved_lfe_direct_hook_diagnostic_v1 as runner
class DiagnosticTests(unittest.TestCase):
    def test_design_and_plan(self):
        self.assertIn("FROZEN",protocol.validate_design()["status"]);_,formal=protocol.formal_rows();plan=protocol.diagnostic_plan(formal);self.assertEqual(len(plan),40);self.assertTrue(all(r["seed_index"]=="1" for r in plan))
    def test_no_top_level_ml_imports(self):runner.assert_no_top_level_ml_imports()
    def test_transient_analyzer_and_verifier(self):
        import torch
        g=torch.Generator().manual_seed(91);direct={};hook={};meta={}
        frozen=[]
        for attribute,prefix in protocol.ATTRIBUTES and (("eyeglasses","FEY"),("facial_hair","FFH")):
            for index in range(1,11):
                pair=f"{prefix}_{index:02d}"
                for role in protocol.ROLES:
                    unit=f"{pair}_{role}";value=torch.randn(1,protocol.LFE_TOKENS,8,generator=g);direct[unit]=value;hook[unit]=value.clone();meta[unit]={"attribute":attribute,"formal_pair_id":pair,"role":role}
        provisional=analyzer.analyze_transient(direct,hook,meta,[],dim=8) if False else None
        # Construct the frozen pooled target with the same independently specified LOPO formula.
        pooled={u:(v[0].mean(0)/torch.linalg.vector_norm(v[0].mean(0)).clamp_min(1e-12)) for u,v in hook.items()}
        for attribute,prefix in (("eyeglasses","FEY"),("facial_hair","FFH")):
            for held_i in range(1,11):
                held=f"{prefix}_{held_i:02d}";train=[f"{prefix}_{i:02d}" for i in range(1,11) if i!=held_i];direction=torch.stack([pooled[f"{p}_positive"]-pooled[f"{p}_control"] for p in train]).mean(0);margin=float(torch.dot(pooled[f"{held}_positive"],direction)-torch.dot(pooled[f"{held}_control"],direction));frozen.append({"attribute":attribute,"stage":"valid_face_emb_mean_token_l2_normalized","formal_pair_id":held,"margin":str(margin)})
        result=analyzer.analyze_transient(direct,hook,meta,frozen,dim=8);self.assertEqual(len(result["equivalence"]),40);self.assertTrue(all(r["bit_exact"] for r in result["equivalence"]));self.assertTrue(all(r["within_tolerance"] for r in result["hook_pooled"]));self.assertIn("PASS",verifier.verify_transient(direct,hook,meta,frozen,result,dim=8)["status"])
if __name__=="__main__":unittest.main()
