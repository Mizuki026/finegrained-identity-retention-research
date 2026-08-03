# Research State and Claim Ledger v1

- Ledger ID: `consisid_finegrained_claim_ledger_v1`
- Status: frozen governance baseline
- Effective date: 2026-08-03 UTC
- Pilot: `/root/autodl-tmp/finegrained/experiments/pilot_v1_1`
- Evidence cutoff: before any Pilot v1.1 video decoding or pixel inspection

## Evidence vocabulary

| Class | Meaning | Permitted wording |
|---|---|---|
| Fact | Directly supported by a frozen artifact, hash, or reproducible observation | “The artifact records…” / “The file exists…” |
| Diagnostic | Engineering or measurement evidence about a possible failure mode | “The diagnostic flags…” |
| Inference | Interpretation that goes beyond direct observation | “This is consistent with…” |
| Hypothesis | Prospective proposition awaiting a valid test | “We hypothesize…” |
| Research decision | Human-authorized design or scope choice | “The protocol freezes…” |

## Authoritative current state

| ID | Class | Statement | Evidence | Boundary |
|---|---|---|---|---|
| F001 | Fact | Pilot v1.1 has 12 manifest rows: four each for eyeglasses, facial hair, and hair color. | `manifest.csv`, SHA256 `dcf66f0222986403493a7c9a09d3106299099d4aef590634348b41ce12544f79d` | Does not establish successful generation or evaluation. |
| F002 | Fact | The generation summary and terminal log record 12/12 successful generations, and twelve non-empty MP4 paths exist. | `generation_summary_v1.csv`, `formal_generation_v1.log`, byte-level path inventory | Does not establish full decode, correct media metadata, visual integrity, identity retention, or attribute retention. |
| F003 | Fact | The canonical config SHA256 is `40014634ef08f17eae3bf41b4d551796efe3855fc7f25c8d3f9b66d9f0e7ef47`. | Disk SHA256 plus generation script, events, metadata, and frozen video protocol | The 65-character handoff value is a transcription error; frozen artifacts must not be changed to match it. |
| F004 | Fact | The eyeglasses reference audit passed on its four frozen references. | `eyeglasses_metric_spec_v2.json` and its reference audit | This is reference-set usability only, not a general eyeglasses detector validation. |
| F005 | Fact | Facial-hair CLIP was rejected and the frozen primary procedure is `facial_hair_manual_ordinal_v2`; the v1.1 reference audit passed after the authorized replacement. | Manual protocol and facial-hair reference audit | This is not video-level facial-hair retention evidence. |
| F006 | Fact | Hair color is frozen as BiSeNet class 17, anatomical upper-head ROI, eroded core, and continuous CIELAB median L*. | `hair_color_metric_spec_v1.json` | Reference ordering is descriptive and does not validate a universal light/dark threshold. |
| F007 | Fact | The frozen video evaluation protocol separates valid-observable, unobservable, pipeline failure, and video technical failure. | `video_evaluation_protocol_v1.json` | No frame has yet been assigned one of these statuses. |
| F008 | Fact | Output-level integrity auditing and attribute/identity evaluation have not started. | Absence of the planned post-generation audit artifacts at governance freeze time | No H1–H4 result may be claimed. |
| F009 | Fact | The workspace root is not a Git repository; the clean upstream baseline repository is `code/ConsisID` at commit `60429e4b0d24d36ce8df7fb58f7ab42b86e2b70e`. | Read-only Git inspection | The clean upstream status does not version experiment artifacts outside that repository. |

## Hypothesis ledger

| ID | Hypothesis | Current status | Minimum evidence needed before promotion | Current claim permission |
|---|---|---|---|---|
| H1 | Identity-related attributes are not uniformly preserved across generated video. | Untested | Audited output-level measurements with sample-level summaries, observability accounting, and replication beyond a single confounded Pilot | Hypothesis only |
| H2 | Retention is associated with attribute properties such as area, locality, frequency content, spatial precision, and sensitivity to pose/occlusion. | Untested and operationalization incomplete | Predefined property measures, controlled/matched sampling, adequate identities/seeds, and a frozen statistical model | Hypothesis only |
| H3 | Different attributes lose decodable or causally effective information at different locations or timesteps in ConsisID. | Untested; no representation evidence | Output-level effect first, then frozen probes, followed by intervention evidence that reproducibly changes output attributes | Hypothesis only; output metrics alone cannot support it |
| H4 | Coarse hair-color retention/stability exceeds that of local fine-grained eyeglasses or facial hair. | Untested and confounded | Valid per-video measurements plus a larger matched design separating attribute granularity from identity/domain effects | Hypothesis only |

## Prohibited claims at the current evidence cutoff

Do not claim that:

- any of the three attributes is preserved or lost;
- one attribute is more fragile than another;
- coarse attributes outperform fine-grained attributes;
- high identity similarity implies attribute retention;
- a temporal module, transformer layer, reference encoder, or denoising timestep is responsible;
- ConsisID has a localized causal bottleneck or requires a new correction method;
- Pilot frame counts constitute independent sample size;
- results from ConsisID generalize to all reference-conditioned video diffusion models.

## Known design risks retained in the ledger

- Identity is confounded with attribute label in the Pilot.
- Turing sample 4 is a historical black-and-white image and introduces photographic-domain, age, and era confounding.
- Public-figure identities may be represented in pretraining data.
- Pose, occlusion, blur, lighting, crop, and small region size affect observability and must not be coded as absence.
- Reference-audited metrics can fail under generated-video domain shift.
- Forty-nine correlated frames do not create forty-nine independent experimental units.
- A three-attribute aggregate score could hide distinct failure modes and is not authorized.

## Stage gates

1. Freeze governance and the video-integrity protocol before pixel access.
2. With separate approval, run only the CPU-only integrity audit on the twelve frozen MP4 files.
3. Stop if the integrity gate fails; preserve all failures and request a research decision rather than excluding or regenerating samples.
4. Only after integrity review may a separate authorization start frame-level observability, identity, or attribute evaluation.
5. Pilot go/no-go must precede formal experiments, probing, intervention, and method development.
