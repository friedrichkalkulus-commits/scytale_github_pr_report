# Project Context: GitHub PR Review Report

## Purpose

This project is a data integration that connects to GitHub, fetches the merged pull requests of a single repository, and produces a report stating, for each pull request, whether it was approved by a reviewer and whether its automated checks passed before merging.

In compliance terms, it collects evidence for a **code-review control**: the requirement that code changes are peer-reviewed and pass their required checks before being merged into the main codebase. This is the kind of control that governance and compliance frameworks expect an organisation to enforce and to be able to demonstrate. The report this project generates is, in effect, audit evidence showing whether that control was satisfied for each merged change.

The integration is built to be reusable: the source-specific logic (talking to GitHub) is separated from the general machinery (reading and writing data), so the same structure can be extended to other systems, for example, a ticketing system like JIRA, by reimplementing only the source-specific parts.

## What it produces

Running the pipeline produces three output files, written into two subfolders under `data/`:

- **`data/raw/pull_requests.json`** - the raw data fetched from GitHub: every merged pull request together with its full reviews and check results, exactly as returned by the GitHub API. This is the unprocessed evidence; it is large (several megabytes) because it preserves all the detail needed to make the judgements, and it can be inspected to audit how any result was reached.

- **`data/processed/pr_report.json`** - the analysed report in JSON form: one entry per pull request with the six report fields (see below). This is the raw data distilled down to the answers.

- **`data/processed/pr_report.csv`** - the same report as a CSV table, which is the primary deliverable. It is the report a person would open in a spreadsheet.

Each row of the report (in both the JSON and CSV) contains six fields:

| Field | Meaning |
|---|---|
| `PR_number` | The pull request's number. |
| `PR_title` | The pull request's title. |
| `Author` | The login of the user who opened it. |
| `Merge_date` | When it was merged (ISO 8601 timestamp). |
| `CR_Passed` | Whether it was approved by at least one reviewer. |
| `CHECKS_PASSED` | Whether all its checks passed before merging. |

The raw and processed outputs are kept separate by design: the raw file is the full evidence trail, while the processed files are the clean result. Keeping both means a result can always be traced back to the underlying data it came from.

(Pull requests whose data could not be fetched carry an extra `note` field in the JSON explaining why; this is described under Assumptions and Limitations below.)

## Architecture

The project is organised as a small pipeline of four Python modules, each with a single, clear responsibility:

- **`extract.py`** - retrieves the raw pull-request data from GitHub. It holds all the GitHub-specific details: authentication, the API endpoints, and the logic for fetching merged PRs, their reviews, and their checks. It does no analysis; it only fetches and hands back raw data.

- **`transform.py`** - performs the analysis. It takes the raw data and computes the two judgements, `CR_Passed` and `CHECKS_PASSED`, for each pull request. It  contains the GitHub-specific business rules (what counts as an approval, what counts as a passing check) but does no fetching.

- **`utils.py`** - holds general, source-agnostic helpers: reading and writing JSON, and writing the CSV report. Nothing here knows anything about GitHub, so these helpers could be reused unchanged by any other integration.

- **`main.py`** - the entry point and orchestrator. It owns all configuration (which repository, how many PRs, output format and file paths) and runs the steps in order: extract, then transform, then write the report. It contains no fetching or analysis logic of its own; it only wires the steps together and supplies them with their configuration.

The data flows in one direction: `extract` writes the raw JSON, `transform` reads that same file and writes the report, and `main` passes the shared file paths to both so they cannot disagree about where the data lives.

### The key design principle: shared vs. source-specific

The modules are split deliberately along one line: **what is specific to GitHub, versus what is general to any integration.**

- The *source-specific* parts, fetching from GitHub's API (`extract.py`) and judging GitHub's data (`transform.py`), are the things that would differ for a different source.
- The *general* parts, reading and writing data, formatting the CSV (`utils.py`), and the *orchestration* (`main.py`) are the things that would stay the same.

This separation is what makes the project reusable across integrations. To add a new source (for example, a JIRA ticket integration), one would reimplement only the source-specific extraction and analysis, while reusing `utils.py` unchanged and following the same orchestration pattern in `main.py`. The shared machinery does not need to be touched. (A concrete prompt for building such a JIRA integration is provided alongside this document.)

## Key definitions and decisions

The two computed fields, `CR_Passed` and `CHECKS_PASSED`, each rest on a specific definition. These definitions are deliberate choices, explained below.

### Identifying merged pull requests

GitHub's API has no direct "merged" filter. A merged pull request is a *closed* pull request that also has a merge date. The pipeline therefore fetches closed pull requests and keeps only those whose `merged_at` field is set. This is the reliable signal, since it is based on structured data, not on the pull request's title or description, which can be misleading. (for example, a PR could have a misleading title beginning with "[NOT_MERGED_GIT_ISSUE]" but was in fact merged; filtering on `merged_at` rather than the title gets this right.)

### CR_Passed - "approved by at least one reviewer"

A pull request's reviews each have a state, such as `APPROVED`, `CHANGES_REQUESTED`, or `COMMENTED`. `CR_Passed` is `True` if at least one review has the state `APPROVED`. Any approving review counts, including those left by automated bot reviewers, the definition is simply "was there an approval," matching the requirement's wording.

### CHECKS_PASSED - "all required checks passed"

This is the more involved judgement, for two reasons.

First, GitHub reports check results through *two* separate systems: the modern "check-runs" (used by GitHub Actions) and an older "combined status" (used by some integrations). A given repository may use either or both, so the pipeline queries both and requires success across both.

Second, a check-run can conclude in several ways, not just "success" or "failure." It can also be `neutral` (an advisory check that deliberately neither passes nor fails), `skipped` (a check that intentionally did not run), or `cancelled` (a run stopped before finishing, often because a newer commit superseded it), among others. GitHub itself treats `neutral` and `skipped` as non-blocking. They do not prevent a merge. The pipeline follows this: a check-run counts as passing if its conclusion is `success`, `neutral`, or `skipped`, and as not passing otherwise (including `cancelled`, which cannot be confirmed as a success). For the older combined-status system, a check counts as passing only if its state is `success`.

`CHECKS_PASSED` is `True` only if every check that ran across both systems counts as passing. If no checks ran at all, it is `False`, since a pass cannot be positively confirmed from the absence of any checks.

(Note: this judges *all* checks that ran, which is a close approximation of, but not identical to, the requirement's "required status checks." The distinction is explained under Assumptions and Limitations below.)

## Dependencies

The project uses Python 3 and two external packages:

- **`requests`** - for making HTTP calls to the GitHub API.
- **`python-dotenv`** - for loading the token from the `.env` file.

Everything else it uses (`json`, `csv`, `os`, `time`, `pathlib`) is part of the Python standard library and needs no installation. The two external packages can be installed with `pip install requests python-dotenv` (or from the project's `requirements.txt`).

## Running

With a valid `.env` in place and the dependencies installed, the whole pipeline runs with a single command:

    python main.py

This runs the three steps in order (extract, transform, write report) and writes the three output files described above. The pipeline always re-fetches from GitHub, so each run reflects the repository's current state. Running it repeatedly overwrites the output files in place rather than accumulating copies.

## Assumptions and limitations

The following are deliberate choices and known boundaries of the current implementation. They are documented openly because each reflects a conscious decision about scope, and knowing them is part of using the report correctly.

**"Required" checks are approximated.** The requirement asks whether *required* status checks passed. Distinguishing which checks are *required* (as opposed to merely informational) depends on a repository's branch-protection settings, which are exposed through a separate and more privileged part of the GitHub API. This implementation instead judges whether *all* checks that ran passed. For a repository where the meaningful checks are effectively required, this is a close and reasonable approximation, but it is not a literal reading of "required."

**Checks are located via the pull request's head commit, and absence is treated as not-passing.** The pipeline looks for checks recorded against the pull request's head commit. In some cases none are found, for two main reasons: the repository may squash-merge (which rewrites the merge into a new commit, so checks recorded against the original commit are not associated with the one queried), or the pull request may predate the repository's automated checking setup. When no checks are found, `CHECKS_PASSED` is `False`. This is deliberate: from a compliance standpoint, a change merged with no recorded checks has not demonstrably satisfied the control and is worth flagging, rather than being treated as a neutral "unknown." The same reasoning applies to `CR_Passed` when a pull request has no reviews at all. (This behaviour was observed clearly on an older repository, where many historical pull requests were merged with no checks recorded against the queried commit.)

**Any approval counts, including from bots.** `CR_Passed` treats any `APPROVED` review as an approval, including approvals from automated bot reviewers. This matches the plain wording of the requirement ("approved by at least one reviewer"). It does not attempt to judge whether the approver was a human or whether they were a "qualified" reviewer.

**Approvals are not re-checked for withdrawal.** A reviewer can approve a pull request and later request changes, which would make the earlier approval stale. This implementation counts any `APPROVED` review without checking whether it was later superseded. This is expected to be rare and did not affect the results, so the simpler rule gives the same answer as the stricter one would; it is noted as a boundary rather than an observed problem.

**Reviews are read from the first page only.** The list of reviews for a pull request is not paginated; only the first page (around thirty reviews) is fetched. Because `CR_Passed` only needs to find one approval, and an approval is overwhelmingly likely to appear within the first page, this has no practical effect, but a pull request with an unusually large number of reviews could in principle have an approval beyond the first page that is not seen.

**Failed extractions are marked, not silently dropped.** If the data for a particular pull request cannot be fetched, that pull request is still included in the report with both `CR_Passed` and `CHECKS_PASSED` set to `False`, and the processed JSON carries an extra `note` field explaining that extraction failed. This `note` field is intentionally omitted from the CSV, which keeps the CSV to its six columns. A consequence is that, in the CSV alone, an extraction failure is indistinguishable from a genuine "not approved / checks failed"; the JSON should be consulted to tell them apart. In the sample data no extractions failed.

**The report is comma-separated by default.** The CSV uses a comma delimiter, which is the universal default. Some locales use a comma as the decimal separator and expect a semicolon-delimited file instead; this is configurable via the `CSV_DELIMITER` setting, but the shipped default is a comma.

**A run reflects a single moment.** The pipeline always re-fetches and reports the repository's state at the time it runs. It does not track history or detect changes between runs. For already-merged pull requests this is stable (their reviews and checks are settled once merged), so re-running over a quiet period produces identical output.

## Extending to other integrations

This project analyses GitHub, but its structure is meant to generalise to other sources. The reusable part, reading and writing data, formatting the CSV report (`utils.py`), and the orchestration pattern in `main.py`, is not specific to GitHub. Only the source-specific parts, fetching and judging, would change for a different source.

To add a new integration (for example, a JIRA ticket integration that reports on tickets rather than pull requests), one would:

1. Write a new extraction step that fetches the raw data from the new source's API, in place of `extract.py`.
2. Write a new transformation step that computes the equivalent judgements for that source's data, in place of `transform.py`.
3. Reuse `utils.py` unchanged for reading, writing, and CSV output.
4. Follow the same orchestration pattern in `main.py`, holding the new source's configuration and running the steps in order.

The shared machinery does not need to be modified, only the source-specific extraction and analysis are rewritten. A concrete, ready-to-use prompt for building a JIRA integration along these lines is provided in this folder as `jira_integration_prompt.md`.

(For a project supporting many integrations at once, an object-oriented design, a shared base class with one subclass per source, would be a natural way to formalise this shared-versus-specific split. The current module-based structure achieves the same separation in a simpler form suited to this project's scope.)