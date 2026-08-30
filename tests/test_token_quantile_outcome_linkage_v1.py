#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch


REPO=Path(__file__).resolve().parents[1]; SRC=REPO/"src"; PLAN=REPO/"governance/mechanism_token_quantile_linkage_execution_v1/approved_token_quantile_outcome_linkage_plan_v1.json"
sys.path.insert(0,str(SRC))
import analyze_token_quantile_outcome_linkage_v1 as analyzer  # noqa: E402
import audit_token_quantile_outcome_linkage_inputs_v1 as auditor  # noqa: E402
import verify_token_quantile_outcome_linkage_v1 as verifier  # noqa: E402


def write_json(path: Path,value: dict) -> None: path.write_text(json.dumps(value)+"\n",encoding="utf-8")


def synthetic_rows(nonmonotone_first: bool=False):
    seeds={1:"2686238281",2:"280026145",3:"2169901996",4:"2046930553"}; first=True
    for attribute,prefix in (("eyeglasses","FEY"),("facial_hair","FFH")):
        for pair_index in range(1,11):
            pair=f"{prefix}_{pair_index:02d}"
            for role_index,role in enumerate(("positive","control")):
                unit=f"{pair}_{role}"
                for seed_index,seed in seeds.items():
                    task=f"S__{unit}__s{seed_index}__baseline__r1"
                    for step in range(50):
                        for site in range(21):
                            for branch_index,branch in enumerate(analyzer.BRANCHES):
                                center=pair_index/100+role_index/1000+seed_index/10000+step/100000+site/1000000+branch_index/10000000
                                values=(center,center+0.01,center+0.02)
                                if first and nonmonotone_first: values=(center+0.02,center+0.01,center)
                                first=False
                                yield {"trace_task_id":task,"formal_unit_id":unit,"formal_pair_id":pair,"attribute":attribute,"role":role,"seed_index":str(seed_index),"seed":seed,"step_index":str(step),"site_index":str(site),"cfg_branch":branch,"token_rms_r_q10":str(values[0]),"token_rms_r_q50":str(values[1]),"token_rms_r_q90":str(values[2])}


class TokenQuantileLinkageTests(unittest.TestCase):
    def setUp(self) -> None:
        self.cpu=patch.dict(os.environ,{"CUDA_VISIBLE_DEVICES":"","HF_HUB_OFFLINE":"1","TRANSFORMERS_OFFLINE":"1"}); self.cpu.start()

    def tearDown(self) -> None: self.cpu.stop()

    def test_plan_fixes_three_metrics_and_108_associations(self) -> None:
        pairs=analyzer.validate_plan(json.loads(PLAN.read_text()))
        self.assertEqual(tuple(json.loads(PLAN.read_text())["metrics"]),analyzer.METRICS); self.assertEqual(sum(len(value) for value in pairs.values()),20)

    def test_no_weight_dry_run_and_independent_verification(self) -> None:
        with tempfile.TemporaryDirectory(dir="/tmp") as temporary:
            path=Path(temporary)/"dry.json"; summary=analyzer.no_weight_dry_run(PLAN,path)
            self.assertFalse(summary["input_files_opened"]); self.assertEqual(summary["planned_associations"],108)
            self.assertEqual(verifier.verify_dry_run(path)["status"],"PASS_INDEPENDENT_TOKEN_QUANTILE_NO_WEIGHT_DRY_RUN_VERIFICATION")

    def test_dry_run_requires_hidden_cuda(self) -> None:
        with patch.dict(os.environ,{"CUDA_VISIBLE_DEVICES":"0"}):
            with tempfile.TemporaryDirectory(dir="/tmp") as temporary:
                with self.assertRaises(analyzer.QuantileLinkageError): analyzer.no_weight_dry_run(PLAN,Path(temporary)/"dry.json")

    def test_formal_mode_rejects_unapproved_authorization(self) -> None:
        with tempfile.TemporaryDirectory(dir="/tmp") as temporary:
            root=Path(temporary); auth=root/"auth.json"; write_json(auth,{"status":"IMPLEMENTATION_ONLY"})
            with self.assertRaises(analyzer.QuantileLinkageError): analyzer.run_formal(auth,PLAN,root/"out")

    def test_input_audit_rejects_unapproved_before_source_access(self) -> None:
        with tempfile.TemporaryDirectory(dir="/tmp") as temporary:
            root=Path(temporary); auth=root/"auth.json"; write_json(auth,{"status":"NO"})
            with self.assertRaises(auditor.AuditError): auditor.audit(auth,"injection_summaries",root/"out")

    def test_nonmonotone_quantile_triple_fails_closed(self) -> None:
        pairs=analyzer.validate_plan(json.loads(PLAN.read_text()))
        with self.assertRaises(analyzer.QuantileLinkageError): analyzer.aggregate_quantiles(synthetic_rows(True),pairs)

    def test_synthetic_complete_108_family(self) -> None:
        pairs=analyzer.validate_plan(json.loads(PLAN.read_text())); task_rows,pair_rows=analyzer.aggregate_quantiles(synthetic_rows(),pairs)
        self.assertEqual(len(task_rows),8640); self.assertEqual(len(pair_rows),1080)
        outcomes={(attribute,pair):float(index) for attribute in analyzer.ATTRIBUTES for index,pair in enumerate(pairs[attribute],1)}
        joined,associations=analyzer.join_and_associate(pair_rows,outcomes); self.assertEqual(len(joined),1080); self.assertEqual(len(associations),108)

    def test_no_derived_metric_in_plan(self) -> None:
        plan=json.loads(PLAN.read_text()); self.assertNotIn("q90_minus_q10",plan["metrics"]); self.assertIn("q90_minus_q10",plan["forbidden_derived_metrics"])

    def test_metric_role_remains_secondary(self) -> None:
        self.assertEqual(json.loads(PLAN.read_text())["metric_role"],"secondary_complete_family")


if __name__=="__main__": unittest.main(verbosity=2)
