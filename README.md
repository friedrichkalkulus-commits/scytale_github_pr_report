# GitHub PR Review Report

A small Python pipeline that checks whether a GitHub repository's merged pull requests were properly reviewed and passed their checks before being merged.

## Overview

This tool connects to GitHub, fetches the merged pull requests of a repository, and reports, for each one, whether it was approved by a reviewer and whether its automated checks passed before it was merged. It then writes the results to a CSV report.

The idea comes from compliance: organisations often need to show that code is only merged after it's been reviewed and has passed its checks. This tool gathers exactly that evidence, one pull request at a time. In other words, it produces an audit trail for a code-review control.

It was built as a take-home assignment, and a learning exercise. I'm comfortable with Python but was new to the surrounding tooling (Git, the GitHub API, working with tokens), so I used AI assistants mostly to help me navigate that side rather than to write the Python itself.

## What it produces

Running the pipeline creates three files under `data/`:

- `data/raw/pull_requests.json` - everything fetched from GitHub (all the PRs with their full reviews and checks). It's relatively large, because it keeps the complete detail behind every result.
- `data/processed/pr_report.json` - the analysed report as JSON.
- `data/processed/pr_report.csv` - the same report as a CSV. This is the main deliverable.

Each row of the report has six columns:

| Column | Meaning |
|---|---|
| `PR_number` | The pull request's number. |
| `PR_title` | Its title. |
| `Author` | Who opened it. |
| `Merge_date` | When it was merged. |
| `CR_Passed` | Whether at least one reviewer approved it. |
| `CHECKS_PASSED` | Whether its checks passed before merging. |

The raw and processed files are kept separate on purpose. The raw file is the full evidence, the processed files are the clean answers. That way any result can be traced back to the data it came from.

## Setup

You'll need Python 3 and a GitHub account.

1. **Clone the repo** and open it.

2. **Install the two dependencies:**

       pip install requests python-dotenv

   (Everything else the project uses is part of Python's standard library.)

3. **Create a GitHub personal access token.** A fine-grained token with read-only access to public repositories is enough. GitHub shows the token once when you create it. Copy it.

4. **Make a `.env` file** in the project root with a single line:

       GITHUB_TOKEN=your_token_here

   The `.env` file is git-ignored, so your token never gets committed. Each person running the project supplies their own token this way.

## Usage

Run the whole pipeline with:

    python main.py

That's it. It fetches, analyses, and writes the report in one go.

All the main settings live at the top of `main.py`, so to change what it does you only edit that one file:

| Setting | What it does |
|---|---|
| `REPO` | Which repository to analyse. |
| `MAX_PRS` | How many recent merged PRs to fetch. |
| `FETCH_ALL` | If `True`, fetch *every* merged PR (ignores `MAX_PRS`). |
| `CSV_DELIMITER` | The CSV separator: `,` by default, `;` for locales that use a comma as the decimal point. |
| `RAW_FILE`, `PROCESSED_FILE`, `CSV_OUTPUT_FILE` | Where the outputs go. |

The pipeline always re-fetches from GitHub, so each run reflects the repository's current state.

## How it works

It's a small pipeline of four modules, each with one job:

- `extract.py` - fetches the raw PR data from GitHub (the GitHub-specific part).
- `transform.py` - works out `CR_Passed` and `CHECKS_PASSED` from that data.
- `utils.py` - general helpers for reading/writing JSON and CSV (nothing GitHub-specific, so it could be reused by another integration).
- `main.py` - holds the configuration and runs the steps in order.

The split is deliberate. The GitHub-specific parts (fetching, judging) are separated from the general parts (reading, writing, orchestration). That's what would make it reasonable to add another integration (say JIRA) by rewriting only the source-specific pieces and reusing the rest. There's more detail on the architecture and design decisions in `ai_utils/project_context.md`.

## Key definitions

- **`CR_Passed`** is `True` if at least one review on the PR has the state `APPROVED` (any reviewer counts, including bots).
- **`CHECKS_PASSED`** is `True` only if every check that ran passed. GitHub reports checks through two systems (modern "check-runs" and older "combined status"), so the tool checks both. Some check outcomes, such as `neutral` and `skipped`, are treated as passing, since GitHub itself treats them as non-blocking. Outcomes like `failure` or `cancelled` are not.

One deliberate choice worth highlighting: a PR is only marked `True` if the control was actually satisfied. A PR merged with **no review**, or with **no checks recorded**, comes out `False`, not as a separate "unknown". From a compliance angle, the point is that a change merged without review or checks is exactly the kind of thing you'd want flagged for a closer look, not jus passed over.

## A note on what the reports showed

While testing, I ran this against a few `home-assistant` repositories, and the results were interesting:

- On **`core`** (the main, critical repo) almost every merged PR was reviewed and passed its checks.
- On **`android`** the picture was a bit looser, with many more PRs merged without an approved review, and somewhat more that didn't pass their checks.
- On **`plugin-audio`** (fetching its whole history) a large share of PRs came out `False`. They were mostly older PRs and dependency bumps that were merged with no review or no checks recorded against them.

It's tempting to read the `core` vs `android` difference as "the more critical repo is governed more strictly," which would make sense, but these are small, recent samples (30 PRs each), so that's a suggestive observation, not a real conclusion. The `plugin-audio` result is more clear-cut. It's the tool doing its job, surfacing merged changes that have no recorded oversight.

## Project structure

    .
    ├── extract.py            # fetch raw PR data from GitHub
    ├── transform.py          # compute CR_Passed and CHECKS_PASSED
    ├── utils.py              # shared JSON/CSV helpers
    ├── main.py               # configuration + entry point
    ├── ai_utils/
    │   ├── project_context.md        # full project context (for AI tools / developers)
    │   └── jira_integration_prompt.md # prompt to reproduce this for JIRA
    ├── data/
    │   ├── raw/              # raw fetched data
    |   |   └── pull_requests.json
    │   └── processed/        # the report (JSON + CSV)
    |   │   ├── pr_report.csv
    |   |   └── pr_report.json
    ├── .gitignore
    └── README.md

## Limitations

A few known limitations (the full list, with reasoning, is in `ai_utils/project_context.md`):

- **"Required" checks are approximated.** The tool checks whether *all* checks passed, not specifically the ones marked "required", since telling those apart needs
  branch-protection data from a separate API.
- **Checks are found via the PR's head commit.** If a repo squash-merges, or for old PRs predating the automated checking system that produces the checks we're reporting on, checks may not be recorded against that commit, so the PR shows `False` (consistent with the compliance choice above).
- **Reviews aren't paginated.** Only the first ~30 reviews per PR are read; since only one approval is needed, this has no practical effect.
- **A run is a snapshot.** It reports the current state and doesn't track history between runs.
