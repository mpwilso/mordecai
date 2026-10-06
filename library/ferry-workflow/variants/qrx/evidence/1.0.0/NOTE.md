# Where this evidence came from

`result.json` is the real `claude plugin eval` result for planted suite `1-convention`, run once and recorded in [docs/planted-results/1-convention.card.json](../../../../../../docs/planted-results/1-convention.card.json). The raw file named its absolute local paths (the suite's root, the plugin's path, and each run's trace file). Those paths were made relative to the repository root by removing the leading folder, and nothing else in the file changed.

- Original result hash: `sha256:06cf8a4738645aad259bd8029e0ae44aa5ef147105826d600ac7bfaba814a17c`, the hash in the recorded card.
- This file's hash: `sha256:3bb5d8ac7c8e782c48580164d16c8420e6218bed76e6546bb416d66513c1efb4`.

`card.json` was then made from this file with `mordecai identify`, run from the repository root with `--skill` set to the variant's skill folder. Its verdict, counts, cases hash and skill hash are the same as before the paths changed; only the result hash differs. Its skill hash covers only the skill folder, so it differs from the recorded card's, which covered the whole plugin.
