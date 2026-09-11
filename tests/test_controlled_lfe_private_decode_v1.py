#!/usr/bin/env python3
from __future__ import annotations

import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

import cv2
import numpy as np

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "src"))
os.environ["CUDA_VISIBLE_DEVICES"] = ""

import controlled_lfe_private_decode_protocol_v1 as protocol
import run_controlled_lfe_private_decode_v1 as runner


class PrivateDecodeTests(unittest.TestCase):
    def test_frozen_generation_builds_exact_collision_free_decode_plan(self):
        rows = protocol.build_plan()
        self.assertEqual(len(rows), 480)
        self.assertEqual(len({row["latent_path"] for row in rows}), 480)
        self.assertEqual(len({row["video_path"] for row in rows}), 480)
        self.assertEqual({int(row["seed_index"]) for row in rows}, {1, 2, 3, 4})
        self.assertEqual({row["condition"] for row in rows}, {"baseline", "target_projection_exchange", "orthogonal_sham"})

    def test_video_integrity_accepts_exact_native_contract_and_rejects_frame_loss(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            exact = root / "exact.mp4"
            short = root / "short.mp4"
            frame = np.zeros((protocol.HEIGHT, protocol.WIDTH, 3), dtype=np.uint8)
            for path, count in ((exact, protocol.FRAMES), (short, protocol.FRAMES - 1)):
                writer = cv2.VideoWriter(
                    str(path), cv2.VideoWriter_fourcc(*"mp4v"), protocol.FPS,
                    (protocol.WIDTH, protocol.HEIGHT),
                )
                self.assertTrue(writer.isOpened())
                for _ in range(count):
                    writer.write(frame)
                writer.release()
            self.assertEqual(protocol.inspect_video(exact)["frame_count"], protocol.FRAMES)
            with self.assertRaises(protocol.PrivateDecodeProtocolError):
                protocol.inspect_video(short)

    def test_heavy_libraries_are_lazily_imported_and_outputs_are_fail_closed(self):
        sources = {
            label: path.read_text(encoding="utf-8")
            for label, path in runner.CODE_PATHS.items()
        }
        for label in ("protocol", "runner", "verifier"):
            self.assertNotIn("\nimport torch", sources[label])
            self.assertNotIn("\nfrom diffusers", sources[label])
            self.assertNotIn("\nfrom safetensors", sources[label])
        self.assertIn("if scalar.exists() or staging.exists() or videos.exists()", sources["runtime"])
        self.assertIn("AutoencoderKLCogVideoX.from_pretrained", sources["runtime"])
        self.assertNotIn("ConsisIDPipeline.from_pretrained", sources["runtime"])

    def test_no_weight_dry_run_is_cuda_hidden_and_torch_free(self):
        self.assertFalse(runner.ACTIVE_AUTH.exists())
        with tempfile.TemporaryDirectory() as temporary:
            output = Path(temporary) / "dry_run"
            environment = {
                **os.environ,
                "CUDA_VISIBLE_DEVICES": "",
                "PYTHONDONTWRITEBYTECODE": "1",
            }
            completed = subprocess.run(
                [
                    sys.executable, str(runner.CODE_PATHS["runner"]),
                    "--mode", "dry-run", "--output-dir", str(output),
                ],
                check=True, env=environment, capture_output=True, text=True,
            )
            self.assertIn("PASS_PRIVATE_LATENT_DECODE_CPU_ONLY_NO_WEIGHT_DRY_RUN", completed.stdout)
            self.assertTrue((output / "private_decode_plan_v1.csv").is_file())
            self.assertTrue((output / "private_decode_no_weight_dry_run_v1.json").is_file())


if __name__ == "__main__":
    unittest.main()
