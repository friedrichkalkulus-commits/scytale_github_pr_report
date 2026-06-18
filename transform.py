"""
transform.py
Turns the raw PR data from extract.py into analysed report records.
Responsible for the JUDGEMENTS: CR_Passed and CHECKS_PASSED.

Definitions used (see README for rationale and limitations):
  CR_Passed     = at least one review has state "APPROVED" (any reviewer, including bots).
  CHECKS_PASSED = every check-run concluded "success", "neutral", or "skipped"
                  (non-blocking outcomes), AND every legacy combined-status entry
                  is "success", across BOTH GitHub check systems.
                  NOTE: this is "all checks that ran", not specifically "required"
                  checks. Distinguishing required checks needs branch-protection
                  data (a separate, more privileged API) - documented as a known
                  limitation.
"""

from pathlib import Path

import utils


# GitHub treats "neutral" and "skipped" check-runs as non-blocking outcomes -
# they don't represent a failure, just a check that opted not to run or doesn't
# pass/fail by design. Only these conclusions count as passing; anything else
# (failure, timed_out, action_required, cancelled, stale, etc.) does not.
PASSING_CONCLUSIONS = {"success", "neutral", "skipped"}


# --- File locations ---
INPUT_FILE = Path("data/raw/pull_requests.json")
OUTPUT_DIR = Path("data/processed")
OUTPUT_FILE = OUTPUT_DIR / "pr_report.json"


# --- The two judgements ---
def compute_cr_passed(reviews):
    """True if at least one review is an approval."""
    if not isinstance(reviews, list):
        return False
    return any(review.get("state") == "APPROVED" for review in reviews)


def compute_checks_passed(checks):
    """True if every check that ran (across both systems) succeeded.
    Returns False if no checks ran or the data is missing/malformed,
    since we cannot positively confirm a pass in that case."""
    if not isinstance(checks, dict):
        return False

    # System 1: modern check-runs. Each has a "conclusion" (success/failure/...).
    check_runs_block = checks.get("check_runs") or {}
    check_runs = check_runs_block.get("check_runs", []) if isinstance(check_runs_block, dict) else []

    # System 2: legacy combined status. Each entry has a "state".
    status_block = checks.get("combined_status") or {}
    statuses = status_block.get("statuses", []) if isinstance(status_block, dict) else []

    # If nothing ran at all, we can't confirm a pass.
    if not check_runs and not statuses:
        return False

    runs_ok = all(run.get("conclusion") in PASSING_CONCLUSIONS for run in check_runs)
    statuses_ok = all(status.get("state") == "success" for status in statuses)
    return runs_ok and statuses_ok


# --- Transform one record ---
def transform_record(record):
    """Turn one raw PR record into a clean report row."""
    # If extraction failed for this PR, we can't judge it - mark clearly.
    if "error" in record:
        return {
            "PR_number": record.get("number"),
            "PR_title": record.get("title"),
            "Author": record.get("author"),
            "Merge_date": record.get("merged_at"),
            "CR_Passed": False,
            "CHECKS_PASSED": False,
            "note": "extraction error - could not determine",
        }

    return {
        "PR_number": record.get("number"),
        "PR_title": record.get("title"),
        "Author": record.get("author"),
        "Merge_date": record.get("merged_at"),
        "CR_Passed": compute_cr_passed(record.get("reviews")),
        "CHECKS_PASSED": compute_checks_passed(record.get("checks")),
    }


# --- Main transform ---
def transform():
    print(f"Reading raw data from {INPUT_FILE} ...")
    raw_records = utils.load_json(INPUT_FILE)

    report = [transform_record(r) for r in raw_records]

    utils.save_json(OUTPUT_FILE, report)

    print(f"Transformed {len(report)} records -> {OUTPUT_FILE}")
    return report


if __name__ == "__main__":
    transform()