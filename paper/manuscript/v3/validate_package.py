#!/usr/bin/env python3
"""Static validation for the manuscript package; performs no scientific analysis."""

from __future__ import annotations

import csv
import hashlib
import re
from collections import Counter
from pathlib import Path


HERE = Path(__file__).resolve().parent
TRACE = HERE.parents[1] / "traceability" / "v3"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def validate_tex(path: Path, bib_keys: set[str]) -> tuple[set[str], set[str]]:
    text = path.read_text(encoding="utf-8")
    if "/root/" in text:
        raise AssertionError(f"private absolute path in {path.name}")

    begins = Counter(re.findall(r"\\begin\{([^}]+)\}", text))
    ends = Counter(re.findall(r"\\end\{([^}]+)\}", text))
    if begins != ends:
        raise AssertionError(f"unbalanced environments in {path.name}: {begins - ends} {ends - begins}")

    citations: set[str] = set()
    for group in re.findall(r"\\cite\{([^}]+)\}", text):
        citations.update(key.strip() for key in group.split(","))
    missing_citations = citations - bib_keys
    if missing_citations:
        raise AssertionError(f"missing bibliography keys: {sorted(missing_citations)}")

    labels = set(re.findall(r"\\label\{([^}]+)\}", text))
    refs = set(re.findall(r"\\(?:ref|eqref)\{([^}]+)\}", text))
    missing_labels = refs - labels
    if missing_labels:
        raise AssertionError(f"missing labels in {path.name}: {sorted(missing_labels)}")
    return citations, labels


def validate_csv(path: Path) -> int:
    with path.open(newline="", encoding="utf-8") as handle:
        rows = list(csv.reader(handle))
    if not rows:
        raise AssertionError(f"empty CSV: {path}")
    width = len(rows[0])
    bad = [index + 1 for index, row in enumerate(rows) if len(row) != width]
    if bad:
        raise AssertionError(f"ragged CSV {path.name} at rows {bad}")
    return len(rows) - 1


def main() -> None:
    required = [
        HERE / "main.tex",
        HERE / "supplementary.tex",
        HERE / "preamble.tex",
        HERE / "references.bib",
        HERE / "cvpr.sty",
        HERE / "ieeenat_fullname.bst",
        HERE / "figures" / "audit_overview.pdf",
        HERE / "figures" / "pair_effects.pdf",
    ]
    for path in required:
        if not path.is_file() or path.stat().st_size == 0:
            raise AssertionError(f"missing or empty required file: {path}")

    bib_text = (HERE / "references.bib").read_text(encoding="utf-8")
    bib_keys = set(re.findall(r"@\w+\{([^,]+),", bib_text))
    main_citations, _ = validate_tex(HERE / "main.tex", bib_keys)
    validate_tex(HERE / "supplementary.tex", bib_keys)
    if main_citations != bib_keys:
        raise AssertionError(
            f"bibliography drift; unused={sorted(bib_keys - main_citations)}, "
            f"unresolved={sorted(main_citations - bib_keys)}"
        )

    supplement = (HERE / "supplementary.tex").read_text(encoding="utf-8")
    expected_pairs = {f"FEY_{i:02d}" for i in range(1, 11)} | {
        f"FFH_{i:02d}" for i in range(1, 11)
    }
    observed_pairs = set(re.findall(r"(?:FEY|FFH)\\_\d{2}", supplement))
    observed_pairs = {item.replace(r"\_", "_") for item in observed_pairs}
    if observed_pairs != expected_pairs:
        raise AssertionError(
            f"supplement pair family mismatch: missing={sorted(expected_pairs - observed_pairs)} "
            f"extra={sorted(observed_pairs - expected_pairs)}"
        )

    expected_figure_hashes = {
        "audit_overview.pdf": "c692f393275011908fa954fdee0c26a4b30c0f02af96478abd97e0bd40f1a352",
        "pair_effects.pdf": "ebf201493411f385ecaa48471e91d361d399bc301a78bf90cf9cefcbe7a53759",
    }
    for name, expected in expected_figure_hashes.items():
        actual = sha256(HERE / "figures" / name)
        if actual != expected:
            raise AssertionError(f"figure hash mismatch for {name}: {actual}")

    trace_counts = {}
    for path in sorted(TRACE.glob("*.csv")):
        trace_counts[path.name] = validate_csv(path)

    forbidden_suffixes = {".mp4", ".avi", ".mov", ".webm", ".pt", ".pth", ".safetensors"}
    forbidden = [path for path in HERE.rglob("*") if path.suffix.lower() in forbidden_suffixes]
    if forbidden:
        raise AssertionError(f"private media or weights in manuscript package: {forbidden}")

    print(f"PASS: {len(bib_keys)} bibliography entries and {len(main_citations)} cited keys")
    print("PASS: TeX environments, labels, references, and complete 20-pair supplement")
    print("PASS: figure hashes and no private media/model files")
    print("PASS: traceability CSV rows " + ", ".join(f"{key}={value}" for key, value in trace_counts.items()))


if __name__ == "__main__":
    main()
