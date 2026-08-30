#!/usr/bin/env python3
from __future__ import annotations

import csv
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch


REPO=Path(__file__).resolve().parents[1]
SRC=REPO/"src"
PLAN=REPO/"governance/mechanism_cosine_linkage_implementation_v1/approved_cosine_outcome_linkage_plan_v1.json"
sys.path.insert(0,str(SRC))

import analyze_cosine_outcome_linkage_v1 as analyzer  # noqa: E402
import audit_cosine_outcome_linkage_inputs_v1 as auditor  # noqa: E402
import verify_cosine_outcome_linkage_v1 as verifier  # noqa: E402


def write_json(path: Path,value: dict) -> None:
    path.write_text(json.dumps(value,indent=2)+"\n",encoding="utf-8")


def write_csv(path: Path,header: list[str],rows: list[dict]) -> None:
    with path.open("w",newline="",encoding="utf-8") as handle:
        writer=csv.DictWriter(handle,fieldnames=header,lineterminator="\n"); writer.writeheader(); writer.writerows(rows)


def synthetic_injection_rows():
    seeds={1:"2686238281",2:"280026145",3:"2169901996",4:"2046930553"}
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
                                value=pair_index/100+role_index/1000+seed_index/10000+step/100000+site/1000000+branch_index/10000000
                                yield {"trace_task_id":task,"formal_unit_id":unit,"formal_pair_id":pair,"attribute":attribute,"role":role,"seed_index":str(seed_index),"seed":seed,"step_index":str(step),"site_index":str(site),"cfg_branch":branch,"mean_tokenwise_cosine_h_r":str(value)}


class CosineOutcomeLinkageTests(unittest.TestCase):
    def setUp(self) -> None:
        self.cpu=patch.dict(os.environ,{"CUDA_VISIBLE_DEVICES":"","HF_HUB_OFFLINE":"1","TRANSFORMERS_OFFLINE":"1"}); self.cpu.start()

    def tearDown(self) -> None: self.cpu.stop()

    def test_approved_plan_is_complete_secondary_family(self) -> None:
        pairs=analyzer.validate_plan(json.loads(PLAN.read_text()))
        self.assertEqual({key:len(value) for key,value in pairs.items()},{"eyeglasses":10,"facial_hair":10})

    def test_average_ranks_and_spearman(self) -> None:
        self.assertEqual(analyzer.average_ranks([1,2,2,4]),[1.0,2.5,2.5,4.0])
        self.assertAlmostEqual(analyzer.spearman([1,2,3],[3,2,1]),-1.0)
        self.assertIsNone(analyzer.spearman([1,1,1],[1,2,3]))

    def test_dry_run_and_independent_verification(self) -> None:
        with tempfile.TemporaryDirectory(dir="/tmp") as temporary:
            root=Path(temporary); summary_path=root/"dry.json"
            summary=analyzer.no_weight_dry_run(PLAN,summary_path)
            self.assertFalse(summary["input_files_opened"]); self.assertEqual(summary["planned_associations"],36)
            result=verifier.verify_dry_run(summary_path)
            self.assertEqual(result["status"],"PASS_INDEPENDENT_COSINE_LINKAGE_NO_WEIGHT_DRY_RUN_VERIFICATION")

    def test_dry_run_requires_hidden_cuda(self) -> None:
        with patch.dict(os.environ,{"CUDA_VISIBLE_DEVICES":"0"}):
            with tempfile.TemporaryDirectory(dir="/tmp") as temporary:
                with self.assertRaises(analyzer.CosineLinkageError): analyzer.no_weight_dry_run(PLAN,Path(temporary)/"dry.json")

    def test_formal_execution_rejects_input_audit_authorization(self) -> None:
        auth=REPO/"governance/mechanism_cosine_linkage_implementation_v1/formal_input_audit_authorization_v1.json"
        with tempfile.TemporaryDirectory(dir="/tmp") as temporary:
            with self.assertRaises(analyzer.CosineLinkageError): analyzer.run_formal(auth,PLAN,Path(temporary)/"out")

    def test_unapproved_input_audit_fails_before_source_access(self) -> None:
        with tempfile.TemporaryDirectory(dir="/tmp") as temporary:
            root=Path(temporary); auth=root/"auth.json"; write_json(auth,{"status":"NOT_APPROVED","sources":{"eyeglasses_outcome":{"path":"/does/not/exist"}}})
            with self.assertRaises(auditor.AuditError): auditor.audit(auth,"eyeglasses_outcome",root/"out")
            self.assertFalse((root/"out").exists())

    def test_eyeglasses_single_source_rule(self) -> None:
        with tempfile.TemporaryDirectory(dir="/tmp") as temporary:
            path=Path(temporary)/"eye.csv"; rows=[]
            for pair_index in range(1,11):
                for seed in range(1,5):
                    row={column:"x" for column in auditor.EYE_HEADER}; row.update({"formal_pair_id":f"FEY_{pair_index:02d}","seed_index":str(seed),"human_positive_minus_control":str(pair_index+seed/10)}) ; rows.append(row)
            write_csv(path,auditor.EYE_HEADER,rows)
            _header,keys,counts=auditor.audit_eye(path)
            self.assertEqual(len(keys),40); self.assertEqual(counts["finite_values_checked"],40)

    def test_facial_hair_rule_requires_only_ten_target_values(self) -> None:
        with tempfile.TemporaryDirectory(dir="/tmp") as temporary:
            path=Path(temporary)/"hair.csv"; rows=[]
            for attribute,prefix in (("eyeglasses","FEY"),("facial_hair","FFH")):
                for pair_index in range(1,11):
                    row={column:"x" for column in auditor.HAIR_HEADER}; row.update({"formal_pair_id":f"{prefix}_{pair_index:02d}","attribute":attribute,"primary_positive_minus_control":"" if attribute=="eyeglasses" else str(pair_index/10)}) ; rows.append(row)
            write_csv(path,auditor.HAIR_HEADER,rows)
            _header,keys,counts=auditor.audit_hair(path)
            self.assertEqual(len(keys),20); self.assertEqual(counts["finite_values_checked"],10)

    def test_synthetic_complete_cosine_family(self) -> None:
        pairs=analyzer.validate_plan(json.loads(PLAN.read_text()))
        task_rows,pair_rows=analyzer.aggregate_cosine(synthetic_injection_rows(),pairs)
        self.assertEqual(len(task_rows),2880); self.assertEqual(len(pair_rows),360)
        outcomes={(attribute,pair):float(index) for attribute in analyzer.ATTRIBUTES for index,pair in enumerate(pairs[attribute],1)}
        joined,associations=analyzer.join_and_associate(pair_rows,outcomes)
        self.assertEqual(len(joined),360); self.assertEqual(len(associations),36)


if __name__=="__main__": unittest.main(verbosity=2)
