# CVPR-style mechanism-audit manuscript

This directory contains the formal paper source for the completed fixed-panel
study. The paper is intentionally framed as a preregistered mechanism audit and
a rigorous mixed/negative result. It does not claim that LFE information is
absent, that the local route is irrelevant, or that the accepted working models
have been mechanistically verified.

## Files

- `main.tex`: main CVPR 2027 review manuscript.
- `supplementary.tex`: complete 20-pair family, coverage, lineage, and claim boundaries.
- `references.bib`: primary-source bibliography.
- `preamble.tex`: shared packages and macros.
- `cvpr.sty`, `ieeenat_fullname.bst`: official CVPR 2027 author-kit style files.
- `figures/`: presentation-only figures derived from the frozen aggregate pair-effect CSV.
- `make_figures.py`: deterministic figure builder; it does not open references, videos, frames, mappings, or annotation submissions.

The evidence and number provenance package is in `../../traceability/v3/`.

To regenerate the figures, pass the frozen aggregate pair-effect CSV explicitly:

```bash
python make_figures.py --pair-effects /path/to/frozen/pair_effects_v1.csv
```

The required input SHA256 is recorded in the v3 traceability package. The
script deliberately has no environment-specific default path.

## Build

From this directory, with a standard LaTeX distribution and `latexmk` installed:

```bash
latexmk -pdf -interaction=nonstopmode -halt-on-error main.tex
latexmk -pdf -interaction=nonstopmode -halt-on-error supplementary.tex
```

The present machine did not contain a TeX compiler when the manuscript was
created, so the repository records static validation rather than a compiled
PDF. Before submission, compile with the official venue environment, inspect
the page count and overfull boxes, replace the anonymous author block as
appropriate, and keep the mandatory LLM Usage Statement.

## Frozen scientific boundary

No new experiment, cross-model validation, prospective discriminating
intervention, metric, threshold, frame family, exclusion, imputation, pair
selection, token selection, regeneration, or public identity-linked media was
introduced for this manuscript. All numerical scientific claims come from
previously frozen artifacts.
