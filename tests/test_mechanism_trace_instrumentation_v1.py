#!/usr/bin/env python3
from __future__ import annotations

import subprocess
import sys
import unittest
from pathlib import Path


REPO = Path(__file__).resolve().parents[1]
SRC = REPO / "src"
sys.path.insert(0, str(SRC))

import torch  # noqa: E402

import mechanism_trace_instrumentation_v1 as trace  # noqa: E402


class Collector:
    def __init__(self) -> None:
        self.rows = []

    def write(self, row) -> None:
        self.rows.append(row)


def task(
    unit: str = "FEY_01_positive",
    role: str = "positive",
    seed_index: int = 1,
    phase: str = "scientific",
) -> dict[str, str]:
    pair = unit.rsplit("_", 1)[0]
    return {
        "trace_task_id": f"synthetic__{unit}__s{seed_index}",
        "phase": phase,
        "formal_unit_id": unit,
        "formal_pair_id": pair,
        "attribute": "eyeglasses" if unit.startswith("FEY") else "facial_hair",
        "role": role,
        "seed_index": str(seed_index),
        "seed": trace.FORMAL_SEED_STRINGS[seed_index - 1],
        "condition": "baseline",
        "repetition": "1",
    }


def reference_vectors(
    sign: float = 1.0,
    image_latent: torch.Tensor | None = None,
) -> dict[str, torch.Tensor]:
    base = torch.tensor([sign, 0.0, 0.0, 0.0], dtype=torch.float32)
    result = {stage: base.clone() for stage in trace.REFERENCE_VECTOR_STAGES}
    result[trace.IMAGE_LATENT_VECTOR_STAGE] = (
        image_latent.detach().float().clone() if image_latent is not None else base.clone()
    )
    return result


class MechanismTraceInstrumentationTests(unittest.TestCase):
    def test_module_import_is_lazy_in_fresh_process(self) -> None:
        code = (
            "import sys; import mechanism_trace_instrumentation_v1; "
            "assert 'torch' not in sys.modules"
        )
        result = subprocess.run(
            [sys.executable, "-c", code],
            cwd=REPO,
            env={"PYTHONPATH": str(SRC)},
            text=True,
            capture_output=True,
            check=False,
        )
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_reference_pooling_shapes_and_unit_norms(self) -> None:
        id_cond = torch.arange(1280, dtype=torch.float32).reshape(1, 1280) + 1
        hidden = [torch.ones((1, 577, 1024), dtype=torch.float32) * (i + 1) for i in range(5)]
        vectors = trace.pooled_reference_vectors(id_cond, hidden)
        self.assertEqual(
            set(vectors),
            {"insightface_l2_normalized", "eva_head_l2_normalized", "eva_hidden_0_patch_mean_l2_normalized", "eva_hidden_1_patch_mean_l2_normalized", "eva_hidden_2_patch_mean_l2_normalized", "eva_hidden_3_patch_mean_l2_normalized", "eva_hidden_4_patch_mean_l2_normalized"},
        )
        self.assertEqual(tuple(vectors["insightface_l2_normalized"].shape), (512,))
        self.assertEqual(tuple(vectors["eva_head_l2_normalized"].shape), (768,))
        for vector in vectors.values():
            self.assertTrue(torch.isclose(torch.linalg.vector_norm(vector), torch.tensor(1.0)))

    def test_cross_attention_summary_formula_and_shape(self) -> None:
        collector = Collector()
        recorder = trace.TraceRecorder(task(), collector)
        recorder.step_index = 0
        recorder.site_index = 0
        recorder.scheduler_timestep = 999
        hidden = torch.ones((2, 26, 3072), dtype=torch.float32)
        residual = torch.ones_like(hidden) * 2
        recorder._cross_attention_hook(0)(None, (torch.zeros((1, 32, 2048)), hidden), residual)
        self.assertEqual(len(collector.rows), 2)
        self.assertEqual(recorder.site_index, 1)
        self.assertEqual({row["cfg_branch"] for row in collector.rows}, {"unconditional", "text"})
        for row in collector.rows:
            self.assertAlmostEqual(row["rms_h"], 1.0)
            self.assertAlmostEqual(row["rms_r"], 2.0)
            self.assertAlmostEqual(row["local_face_scale"], 1.0)
            self.assertAlmostEqual(row["rms_post"], 3.0)
            self.assertAlmostEqual(row["relative_residual_rms"], 2.0)
            self.assertAlmostEqual(row["mean_tokenwise_cosine_h_r"], 1.0, places=5)
            self.assertEqual(len([key for key in row if key.startswith("frame_rms_r_")]), 13)

    def test_deterministic_stage_drift_across_seeds_is_blocked(self) -> None:
        readout = trace.ReferenceReadout()
        readout.add(task(seed_index=1), reference_vectors())
        changed = reference_vectors()
        changed["insightface_l2_normalized"] = torch.tensor(
            [0.0, 1.0, 0.0, 0.0], dtype=torch.float32
        )
        with self.assertRaisesRegex(
            trace.ProtocolError, "deterministic reference vector changed across seeds"
        ):
            readout.add(task(seed_index=2), changed)

    def test_duplicate_scientific_seed_is_blocked(self) -> None:
        readout = trace.ReferenceReadout()
        readout.add(task(seed_index=1), reference_vectors())
        with self.assertRaisesRegex(
            trace.ProtocolError, "duplicate scientific representation seed"
        ):
            readout.add(task(seed_index=1), reference_vectors())

    def test_missing_scientific_seeds_are_blocked(self) -> None:
        readout = trace.ReferenceReadout()
        readout.add(task(seed_index=1), reference_vectors())
        with self.assertRaisesRegex(trace.ProtocolError, "representation seeds incomplete"):
            readout._unit_mean_vectors()

    def test_image_latent_uses_exact_four_seed_mean_without_renormalization(self) -> None:
        readout = trace.ReferenceReadout()
        image_vectors = (
            torch.tensor([1.0, 0.0, 0.0, 0.0]),
            torch.tensor([1.0, 0.0, 0.0, 0.0]),
            torch.tensor([0.0, 1.0, 0.0, 0.0]),
            torch.tensor([0.0, 1.0, 0.0, 0.0]),
        )
        for seed_index, image_vector in enumerate(image_vectors, start=1):
            readout.add(
                task(seed_index=seed_index),
                reference_vectors(image_latent=image_vector),
            )
        mean = readout._unit_mean_vectors()["FEY_01_positive"][
            trace.IMAGE_LATENT_VECTOR_STAGE
        ]
        self.assertTrue(
            torch.equal(mean, torch.tensor([0.5, 0.5, 0.0, 0.0], dtype=torch.float32))
        )
        self.assertFalse(torch.isclose(torch.linalg.vector_norm(mean), torch.tensor(1.0)))

    def test_engineering_same_seed_repeats_remain_supported(self) -> None:
        readout = trace.ReferenceReadout()
        metadata = task(seed_index=1, phase="engineering")
        readout.add(metadata, reference_vectors())
        readout.add(metadata, reference_vectors())
        self.assertEqual(set(readout.vectors["FEY_01_positive"]), {"2686238281"})

    def test_directional_ranking_emits_all_fixed_panel_margins(self) -> None:
        readout = trace.ReferenceReadout()
        for attribute, prefix in (("eyeglasses", "FEY"), ("facial_hair", "FFH")):
            for pair_index in range(1, 11):
                pair = f"{prefix}_{pair_index:02d}"
                for role, sign in (("positive", 1.0), ("control", -1.0)):
                    unit = f"{pair}_{role}"
                    for seed_index in range(1, 5):
                        metadata = task(unit, role, seed_index)
                        metadata["attribute"] = attribute
                        image = torch.tensor(
                            [sign, seed_index / 100.0, 0.0, 0.0],
                            dtype=torch.float32,
                        )
                        image = image / torch.linalg.vector_norm(image)
                        readout.add(
                            metadata,
                            reference_vectors(sign=sign, image_latent=image),
                        )
        rows = readout.margins()
        self.assertEqual(len(rows), 180)
        self.assertEqual(
            {row["stage"] for row in rows},
            set(trace.REFERENCE_VECTOR_STAGES),
        )
        self.assertEqual({row["direction"] for row in rows}, {"correct"})
        self.assertTrue(all(row["margin"] > 0 for row in rows))


if __name__ == "__main__":
    unittest.main(verbosity=2)
