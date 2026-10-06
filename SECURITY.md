# Security

## Reporting a vulnerability

Please report it privately through GitHub: on this repository's **Security** tab, choose **Report a vulnerability**. Don't open a public issue. Mordecai is a portfolio project maintained by one person, so there is no bounty.

## In scope

Mordecai reads eval results, cards and plugin directories that someone else may have written, so these count:

- A result, card or plugin that makes `mordecai identify`, `check` or `lint` read, hash or follow a path outside the current directory or a directory you passed with `--skill` or `--cases-root`.
- Text from a result or card that reaches the terminal as control characters or escape sequences, or reaches `--markdown` output as HTML, a link, an image or a mention.
- A malformed input that gives a wrong verdict instead of an error, or that crashes, hangs or exhausts memory.
- Anything in `.github/workflows/` that could expose a token or run untrusted code with write access.

## Out of scope

- What `claude plugin eval` does when it runs a plugin. It runs the plugin's code on your machine; that's Claude Code's to answer, and only evaluate plugins you trust.
- Whether a verdict is statistically right. That's a design question; open an issue.
- The sibling projects named in the README. Each has its own repository.
