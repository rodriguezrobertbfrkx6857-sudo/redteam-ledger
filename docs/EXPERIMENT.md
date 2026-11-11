# Detector baseline experiment

Run on 2026-11-11 with the 36 original synthetic `all` cases (20 attack / 16 benign). No model inference is involved. Keyword and normalized are local reference baselines; Sentinel is the actual HTTP service on loopback with balanced policy.

| Target | TP | FN | FP | TN | Errors | Attack miss rate | False positive rate |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| keyword | 2 | 18 | 2 | 14 | 0 | 90.0% | 12.50% |
| normalized | 10 | 10 | 5 | 11 | 0 | 50.0% | 31.25% |
| sentinel | 17 | 3 | 5 | 11 | 0 | 15.0% | 31.25% |

All three baselines fail the configured gate. Sentinel detects more of these attack patterns but still misses semantic paraphrases and flags benign quotations of attack instructions. This is evidence of limitations, not a claim of real-world protection.

Raw evidence: [keyword](keyword-report.json), [normalized](normalized-report.json), [Sentinel HTTP](sentinel-report.json). Reports include dataset SHA256, per-case outcomes, Wilson intervals and the grader version. The 36 authored cases are a development artifact, not an independent public benchmark. Do not extrapolate these percentages to deployed LLMs.

Reproduce by starting Sentinel Gate on 8111, then running `uv run python -m app.cli --target sentinel --split all --output report.json`. Add `--gate` to obtain a nonzero exit status for the measured failure. The UI test suite passing means the workbench behaves correctly, not that every evaluated detector meets its security gate.
