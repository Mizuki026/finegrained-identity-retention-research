#!/usr/bin/env python3
import sys,unittest
from pathlib import Path
REPO=Path(__file__).resolve().parents[1];sys.path.insert(0,str(REPO/"src"))
import preprocessing_repeatability_protocol_v1 as protocol
import analyze_preprocessing_repeatability_v1 as analyzer
import verify_preprocessing_repeatability_v1 as verifier
import run_preprocessing_repeatability_diagnostic_v1 as runner

def synthetic(dim=8):
    import torch
    generator=torch.Generator().manual_seed(2026);tensors={};meta={}
    for attribute,prefix in (("eyeglasses","FEY"),("facial_hair","FFH")):
        for index in range(1,11):
            pair=f"{prefix}_{index:02d}"
            for role in protocol.ROLES:
                unit=f"{pair}_{role}";base=torch.randn(1,protocol.LFE_TOKENS,dim,generator=generator);tensors[unit]={"P1":{1:base.clone(),2:base.clone()},"P2":{1:base.clone(),2:base.clone()}};meta[unit]={"attribute":attribute,"formal_pair_id":pair,"role":role}
    pooled={unit:(value["P1"][1][0].mean(0)/torch.linalg.vector_norm(value["P1"][1][0].mean(0)).clamp_min(1e-12)) for unit,value in tensors.items()};frozen=[]
    for attribute,prefix in (("eyeglasses","FEY"),("facial_hair","FFH")):
        for held_i in range(1,11):
            held=f"{prefix}_{held_i:02d}";others=[f"{prefix}_{i:02d}" for i in range(1,11) if i!=held_i];direction=torch.stack([pooled[f"{p}_positive"]-pooled[f"{p}_control"] for p in others]).mean(0);margin=float(torch.dot(pooled[f"{held}_positive"],direction)-torch.dot(pooled[f"{held}_control"],direction));frozen.append({"attribute":attribute,"stage":"valid_face_emb_mean_token_l2_normalized","formal_pair_id":held,"margin":str(margin)})
    return tensors,meta,frozen
class RepeatabilityTests(unittest.TestCase):
    def test_design_and_complete_plan(self):
        self.assertIn("FROZEN",protocol.validate_design()["status"]);_,formal=protocol.formal_rows();self.assertEqual(len(protocol.unit_plan(formal)),40);plan=protocol.acquisition_plan(formal);self.assertEqual(len(plan),80);self.assertEqual({r["preprocessing_replicate"] for r in plan},{"P1","P2"})
    def test_no_top_level_ml_imports(self):runner.assert_no_top_level_ml_imports()
    def test_runtime_has_no_raw_tensor_serializer(self):
        text=(REPO/"src/preprocessing_repeatability_runtime_v1.py").read_text();self.assertNotIn("torch.save",text);self.assertNotIn("numpy.save",text);self.assertNotIn("pickle.dump",text)
    def test_complete_analyzer_and_independent_verifier(self):
        tensors,meta,frozen=synthetic();result=analyzer.analyze_transient(tensors,meta,frozen,dim=8);self.assertEqual([len(result[k]) for k in ("within","cross","margins","cross_pooled","run003")],[80,40,40,20,40]);self.assertTrue(all(r["bit_exact"] for r in result["within"]+result["cross"]));self.assertTrue(all(r["within_tolerance"] for r in result["run003"]));self.assertIn("PASS",verifier.verify_transient(tensors,meta,frozen,result,dim=8)["status"])
    def test_persisted_verifier_complete_crossings(self):
        import tempfile
        tensors,meta,frozen=synthetic();result=analyzer.analyze_transient(tensors,meta,frozen,dim=8)
        with tempfile.TemporaryDirectory() as raw:
            run=Path(raw);protocol.atomic_csv(run/"within_preprocessing_direct_repeat_v1.csv",analyzer.WITHIN_FIELDS,result["within"]);protocol.atomic_csv(run/"cross_preprocessing_lfe_equivalence_v1.csv",analyzer.CROSS_FIELDS,result["cross"]);protocol.atomic_csv(run/"preprocessing_replicate_pooled_margins_v1.csv",analyzer.MARGIN_FIELDS,result["margins"]);protocol.atomic_csv(run/"cross_replicate_pooled_comparison_v1.csv",analyzer.CROSS_POOL_FIELDS,result["cross_pooled"]);protocol.atomic_csv(run/"replicate_run_003_comparison_v1.csv",analyzer.RUN003_FIELDS,result["run003"])
            statuses=[]
            for unit in sorted(meta):
                for replicate in protocol.REPLICATES:statuses.append({"formal_unit_id":unit,"preprocessing_replicate":replicate,"status":"COMPLETE_TRANSIENT_ONLY"})
            protocol.atomic_csv(run/"preprocessing_repeatability_execution_status_v1.csv",("formal_unit_id","preprocessing_replicate","status"),statuses);protocol.atomic_json(run/"preprocessing_repeatability_in_memory_verification_v1.json",{"status":"PASS_INDEPENDENT_IN_MEMORY_PREPROCESSING_REPEATABILITY_RECOMPUTATION"})
            self.assertIn("PASS",verifier.verify_persisted(run)["status"])
    def test_within_control_failure_retained_and_gates_cross_interpretation(self):
        tensors,meta,frozen=synthetic();unit=sorted(tensors)[0];tensors[unit]["P1"][2]=tensors[unit]["P1"][2].clone();tensors[unit]["P1"][2][0,0,0]+=1.0;result=analyzer.analyze_transient(tensors,meta,frozen,dim=8);self.assertEqual(len(result["within"]),80);within=[r for r in result["within"] if r["formal_unit_id"]==unit and r["preprocessing_replicate"]=="P1"][0];cross=[r for r in result["cross"] if r["formal_unit_id"]==unit][0];self.assertFalse(within["within_frozen_tolerance"]);self.assertFalse(cross["within_input_controls_pass"]);self.assertIn("PASS",verifier.verify_transient(tensors,meta,frozen,result,dim=8)["status"])
if __name__=="__main__":unittest.main()
