# Fletcher on Martian's code review benchmark

[Fletcher](https://github.com/shahparshva72/not-quite-my-tempo), an AI pull request reviewer, scored **50.6% F1 (52.1% precision, 49.1% recall) on all 50 PRs** of [Martian's offline code review benchmark](https://github.com/withmartian/code-review-benchmark). Under the Sonnet 4.5 judge, which agrees most closely with the Gemini judge used here, that would rank **4th of 50 tools**. Allowing for differences between judges, it lands between 3rd and 14th.

Fletcher ran on `gemini-3.8-flash`, a flash-tier model. The full run cost **$4.25** for the reviews and **about $0.33** to judge them, all on Vertex AI. It ran on 17 October 2026 against Martian commit `e616e84`.

![Fletcher ranks 4th of 50 tools on F1](charts/ranking.svg)

## Results

| | Fletcher |
| --- | --- |
| F1 | 50.6% |
| Precision (findings that match a golden comment) | 52.1% (85 of 163) |
| Recall (golden comments found) | 49.1% (85 of 173) |
| PRs reviewed | 50 of 50 |
| Review cost | $4.25 (about $0.085 per PR) |
| Judge cost | about $0.33 |

Precision and recall are within 3 points of each other. Most tools trade one for the other: Copilot v2 finds more issues but adds more noise, and Devin is the reverse.

![Precision vs recall for 49 tools and Fletcher](charts/precision-recall.svg)

Per-PR numbers are in [`data/fletcher-per-pr.csv`](data/fletcher-per-pr.csv). Every review Fletcher wrote, with the golden comments and the judge's reasoning for each match, is in [`data/fletcher-reviews.json`](data/fletcher-reviews.json).

## Is the comparison fair?

Mostly, within about ±5 F1 points. Martian's published scores were judged by Claude Opus 4.5, Claude Sonnet 4.5 and GPT-5.2. This run used Gemini 3.8 Flash as the judge, because the only budget available was Vertex AI credits. To check whether Gemini grades differently, two competitors' existing reviews were re-judged with it:

![Judges move F1 by about 5 points; Gemini lands within 1.5 of Sonnet](charts/judge-calibration.svg)

Gemini scored CodeRabbit 0.8 points and Greptile v5 1.5 points below Sonnet 4.5. Martian's own three judges disagree with each other by about 5 points on the same tool. So Fletcher's score is shown against Sonnet-judged results with a ±5-point error bar. Under the identical Gemini judge, Fletcher (50.6%) beats CodeRabbit (42.7%) and Greptile v5 (39.3%) outright. Scores for every tool under all four judges are in [`data/scores-by-judge.json`](data/scores-by-judge.json).

## How it was run

Nothing was posted to GitHub, and no repositories were forked.

1. **Reviews.** [`harness/review.ts`](harness/review.ts) reads each benchmark PR from Martian's public copies through the GitHub API. It runs Fletcher's production review path (the same diff filter, repository context, prompt and comment formatting) against Vertex AI, then writes the review into Martian's `results/benchmark_data.json` as one more tool.
2. **Judging.** Martian's unmodified pipeline extracts the issues in each review, groups duplicates, and asks an LLM judge whether each issue matches a golden comment. It speaks the OpenAI API, so [`harness/judge-proxy.ts`](harness/judge-proxy.ts) serves that API on localhost and forwards every call to Gemini on Vertex AI.
3. **Scoring.** [`analysis/build.py`](analysis/build.py) pools true positives, false positives and misses across all 50 PRs (micro-averaged F1, every golden category counted), exports `data/` and draws `charts/`.

The harness imports Fletcher's internals, so it only runs from inside the [not-quite-my-tempo](https://github.com/shahparshva72/not-quite-my-tempo) repository (`apps/api/scripts/martian-bench/`). The copy here is for reference; [`harness/HARNESS.md`](harness/HARNESS.md) has the full run guide.

To regenerate the data and charts from a Martian checkout that holds the run:

```sh
python3 analysis/build.py --martian ~/path/to/code-review-benchmark
```

## Caveats

- **Different judge.** See above: treat the rank as ±5 F1 points.
- **Self-preference.** A Gemini judge scoring a Gemini-written review may favour it a little. The calibration check covers this only partly.
- **Scoring choices.** Every golden category counts and F1 weighs precision and recall equally. Martian's [leaderboard page](https://codereview.withmartian.com/?mode=offline&ob=2) may default to a different category set or F-beta, so its displayed numbers can differ from these.
- **Incomplete golden set.** Some findings counted as false positives look like real bugs the human reviewers didn't list. That lowers precision for every tool alike.
- **Training leakage.** The PRs are public, so models may have seen them or their fixes.
- **One run.** Reviews and judging were each run once, so run-to-run variance is unknown.
- **Timeouts.** 3 of 50 reviews failed on the first pass. One PR (keycloak#38446) exceeded Fletcher's production 180-second timeout twice and was reviewed with a 360-second limit, so in production that PR would likely get no review.

## What Fletcher missed

In the 5-PR smoke test, half of Fletcher's 10 misses were concurrency bugs (3) or test gaps (2): races on shared caches, processes left running after a deadline, and a monkeypatched `sleep` that turns a test's wait into a no-op. These are the targets for the next prompt iteration.

## Credits and licence

The benchmark data, golden comments, judge pipeline and other tools' evaluations come from [withmartian/code-review-benchmark](https://github.com/withmartian/code-review-benchmark), MIT-licensed. Its licence is included in [`third_party/`](third_party/martian-code-review-benchmark-LICENSE).
