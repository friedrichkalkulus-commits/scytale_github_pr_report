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


def main():
    print("=" * 60)
    print("GitHub PR Review Report - pipeline starting")
    print("=" * 60)

    # Step 1: extract raw PR data from GitHub (writes data/raw/pull_requests.json)
    print("\n[1/2] Extracting raw PR data from GitHub ...")
    extract.extract()

    # Step 2: transform raw data into the analysed report (writes data/processed/pr_report.json)
    print("\n[2/2] Transforming raw data into the report ...")
    report = transform.transform()

    print("\n" + "=" * 60)
    print(f"Pipeline complete. {len(report)} PRs processed.")
    print("Raw data:       data/raw/pull_requests.json")
    print("Report (JSON):  data/processed/pr_report.json")
    print("=" * 60)


if __name__ == "__main__":
    main()