# Fletcher on Martian's code review benchmark

[Fletcher](https://github.com/shahparshva72/not-quite-my-tempo), an AI pull request reviewer, scored **50.6% F2 (50.6% precision, 50.6% recall)** on all 50 PRs of [Martian's offline code review benchmark](https://github.com/withmartian/code-review-benchmark), measured the way the [leaderboard](https://codereview.withmartian.com/?mode=offline&ob=2) measures it by default (Core categories, F2). Against the 21 tools the leaderboard shows, that places **12th of 22 under its default judge (Claude Opus 4.5)** and **7th under Claude Sonnet 4.5**.

Fletcher ran on `gemini-3.8-flash`, a flash-tier model. The full run cost **$4.25** for the reviews and **about $0.33** to judge them, all on Vertex AI. It ran on 17 October 2026 against Martian commit `e616e84`, and the leaderboard numbers come from Martian's own `analysis/benchmark_dashboard.py`.

![On the leaderboard's default view, Fletcher places 12th of 22](charts/ranking.svg)

## Results

Martian's leaderboard scores with **F2**, which counts recall as twice as important as precision, because a missed bug costs more than a false alarm. It also uses the **Core** profile by default, which leaves out golden comments about style and speculation.

| Profile | Precision | Recall | F1 | F2 |
| --- | --- | --- | --- | --- |
| **Core** (leaderboard default) | 50.6% (80 of 158) | 50.6% (80 of 158) | 50.6% | **50.6%** |
| All categories | 52.1% (85 of 163) | 49.1% (85 of 173) | 50.6% | 49.7% |

Where Fletcher's Core score would place among the 21 leaderboard tools, under each of Martian's judges:

| Judge | Rank on F2 | Rank on F1 |
| --- | --- | --- |
| Claude Opus 4.5 (leaderboard default) | 12th of 22 | 10th of 22 |
| Claude Sonnet 4.5 | 7th of 22 | 6th of 22 |
| GPT-5.2 | 6th of 22 | 5th of 22 |

Fletcher was judged by Gemini 3.8 Flash, which on this metric scored CodeRabbit about 2.5 points below Opus and Sonnet (48.5% vs 51.1% and 50.9%). If that holds for Fletcher too, these ranks understate it slightly.

| | Fletcher |
| --- | --- |
| PRs reviewed | 50 of 50 |
| Review cost | $4.25 (about $0.085 per PR) |
| Judge cost | about $0.33 |

Fletcher's precision and recall are equal. The top four tools beat it on both; most of the others above it on F2 find more issues at the cost of more noise. Its prompt asks for "a few high-signal findings over volume", which F1 rewards and F2 does not. On plain F1 over all categories and all 49 tools in Martian's data, hidden versions included, it would rank 4th ([chart](charts/ranking-f1-all-tools.svg)).

![Precision vs recall for the 21 leaderboard tools and Fletcher](charts/precision-recall.svg)

Per-PR numbers are in [`data/fletcher-per-pr.csv`](data/fletcher-per-pr.csv). Every review Fletcher wrote, with the golden comments and the judge's reasoning for each match, is in [`data/fletcher-reviews.json`](data/fletcher-reviews.json).

## Is the comparison fair?

Mostly, within about ±5 points. Martian's published scores were judged by Claude Opus 4.5, Claude Sonnet 4.5 and GPT-5.2. This run used Gemini 3.8 Flash as the judge, because the only budget available was Vertex AI credits. To check whether Gemini grades differently, two competitors' existing reviews were re-judged with it:

![Judges move F1 by about 5 points; Gemini lands within 1.5 of Sonnet](charts/judge-calibration.svg)

Gemini scored CodeRabbit 0.8 points and Greptile v5 1.5 points below Sonnet 4.5. Martian's own three judges disagree with each other by about 5 points on the same tool. So Fletcher's score carries a ±5-point error bar against the leaderboard. Under the identical Gemini judge, Fletcher (50.6%) beats CodeRabbit (42.7%) and Greptile v5 (39.3%) outright. All-category scores for every tool under all four judges are in [`data/scores-by-judge.json`](data/scores-by-judge.json), and the leaderboard's Core-profile numbers in [`data/leaderboard-core.json`](data/leaderboard-core.json).

## How it was run

Nothing was posted to GitHub, and no repositories were forked.

1. **Reviews.** [`harness/review.ts`](harness/review.ts) reads each benchmark PR from Martian's public copies through the GitHub API. It runs Fletcher's production review path (the same diff filter, repository context, prompt and comment formatting) against Vertex AI, then writes the review into Martian's `results/benchmark_data.json` as one more tool.
2. **Judging.** Martian's unmodified pipeline extracts the issues in each review, groups duplicates, and asks an LLM judge whether each issue matches a golden comment. It speaks the OpenAI API, so [`harness/judge-proxy.ts`](harness/judge-proxy.ts) serves that API on localhost and forwards every call to Gemini on Vertex AI.
3. **Scoring.** Martian's `analysis/benchmark_dashboard.py` computes the leaderboard numbers (Core profile, F2, hidden tools removed). [`analysis/build.py`](analysis/build.py) also pools true positives, false positives and misses across all 50 PRs for the all-category figures, exports `data/` and draws `charts/`.

The harness imports Fletcher's internals, so it only runs from inside the [not-quite-my-tempo](https://github.com/shahparshva72/not-quite-my-tempo) repository (`apps/api/scripts/martian-bench/`). The copy here is for reference; [`harness/HARNESS.md`](harness/HARNESS.md) has the full run guide.

To regenerate the data and charts from a Martian checkout that holds the run:

```sh
cd ~/path/to/code-review-benchmark/offline
uv run python analysis/benchmark_dashboard.py --output /tmp/dash.html
cd -
python3 analysis/build.py --martian ~/path/to/code-review-benchmark --dashboard /tmp/dash.json
```

## Caveats

- **Different judge.** See above: treat the score as ±5 points, which under the default Opus judge spans roughly 6th to 15th of 22.
- **Self-preference.** A Gemini judge scoring a Gemini-written review may favour it a little. The calibration check covers this only partly.
- **Incomplete golden set.** Some findings counted as false positives look like real bugs the human reviewers didn't list. That lowers precision for every tool alike.
- **Training leakage.** The PRs are public, so models may have seen them or their fixes.
- **One run.** Reviews and judging were each run once, so run-to-run variance is unknown.
- **Timeouts.** 3 of 50 reviews failed on the first pass. One PR (keycloak#38446) exceeded Fletcher's production 180-second timeout twice and was reviewed with a 360-second limit, so in production that PR would likely get no review.

## What Fletcher missed

In the 5-PR smoke test, half of Fletcher's 10 misses were concurrency bugs (3) or test gaps (2): races on shared caches, processes left running after a deadline, and a monkeypatched `sleep` that turns a test's wait into a no-op. These are the targets for the next prompt iteration.

## Credits and licence

The benchmark data, golden comments, judge pipeline and other tools' evaluations come from [withmartian/code-review-benchmark](https://github.com/withmartian/code-review-benchmark), MIT-licensed. Its licence is included in [`third_party/`](third_party/martian-code-review-benchmark-LICENSE).
