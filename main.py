"""
main.py
Entry point for the GitHub PR review report pipeline.
Runs the full flow: extract raw PR data from GitHub, then transform it
into the analysed report. Always re-fetches so the report reflects the
repository's current state.

Usage:
    python main.py
"""

import extract
import transform
import utils

REPO = "home-assistant/android"   # the single repo to analyse (change this one line to switch repos)
MAX_PRS = 30                      # how many recent merged PRs to fetch
FETCH_ALL = False                 # if True, ignore MAX_PRS and fetch every merged PR

RAW_FILE = "data/raw/pull_requests.json"
PROCESSED_FILE = "data/processed/pr_report.json"
CSV_OUTPUT_FILE = "data/processed/pr_report.csv"

OUTPUT_FORMAT = "csv"   # currently only "csv"; structured so other formats (e.g. parquet) can be added later
REPORT_COLUMNS = ["PR_number", "PR_title", "Author", "Merge_date", "CR_Passed", "CHECKS_PASSED"]
CSV_DELIMITER = ","   # field separator; some locales (e.g. ZA, DE) expect ";" - change here if needed

def main():
    print("=" * 60)
    print("GitHub PR Review Report - pipeline starting")
    print("=" * 60)

    # Step 1: extract raw PR data from GitHub (writes RAW_FILE)
    print("\n[1/3] Extracting raw PR data from GitHub ...")
    extract.extract(REPO, MAX_PRS, FETCH_ALL, RAW_FILE)

    # Step 2: transform raw data into the analysed report (writes PROCESSED_FILE)
    print("\n[2/3] Transforming raw data into the report ...")
    report = transform.transform(RAW_FILE, PROCESSED_FILE)

    print("\n[3/3] Writing the report file ...")
    if OUTPUT_FORMAT == "csv":
        utils.write_csv(report, CSV_OUTPUT_FILE, columns=REPORT_COLUMNS, delimiter=CSV_DELIMITER)
    else:
        raise ValueError(f"Unsupported OUTPUT_FORMAT: {OUTPUT_FORMAT}")

    print("\n" + "=" * 60)
    print(f"Pipeline complete. {len(report)} PRs processed.")
    print(f"Raw data:       {RAW_FILE}")
    print(f"Report (JSON):  {PROCESSED_FILE}")
    print(f"Report (CSV):   {CSV_OUTPUT_FILE}")
    print("=" * 60)


if __name__ == "__main__":
    main()