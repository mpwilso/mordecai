# Where this evidence came from

`result.json` is the real `claude plugin eval` result for planted suite `h1-must-fire`, run once and recorded in [docs/planted-results/h1-must-fire.card.json](../../../../../../docs/planted-results/h1-must-fire.card.json). The raw file named its absolute local paths (the suite's root, the plugin's path, and each run's trace file). Those paths were made relative to the repository root by removing the leading folder, and nothing else in the file changed.

- Original result hash: `sha256:bfc1c25c3440b7770c161798fbd5c8bd17528d757d5e84d54e38a5b06fd4718b`, the hash in the recorded card.
- This file's hash: `sha256:5fe8ff35bb6083bac8ddeaa99227d3c165be91e6af2a42b7ae5906c707009b03`.

`card.json` was then made from this file with `mordecai identify`, run from the repository root with `--skill` set to the variant's skill folder. Its verdict, counts, cases hash and skill hash are the same as before the paths changed; only the result hash differs. Its skill hash covers only the skill folder, so it differs from the recorded card's, which covered the whole plugin.
