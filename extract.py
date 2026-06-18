"""
extract.py
Fetches raw merged-pull-request data from a GitHub repository.
Responsible only for retrieving data and saving it as JSON — no analysis.
"""

import os
import json
import time
from pathlib import Path

import requests
from dotenv import load_dotenv


# --- Configuration ---
load_dotenv()
TOKEN = os.environ["GITHUB_TOKEN"]

REPO = "home-assistant/android"   # the single repo to analyse (change this one line to switch repos)
MAX_PRS = 30                      # how many recent merged PRs to fetch
FETCH_ALL = False                 # if True, ignore MAX_PRS and fetch every merged PR (added later)

API_ROOT = "https://api.github.com"
HEADERS = {
    "Authorization": f"Bearer {TOKEN}",
    "Accept": "application/vnd.github+json",
    "X-GitHub-Api-Version": "2022-11-28",
    "User-Agent": "scytale-pr-report",
}

# Where raw output is saved
OUTPUT_DIR = Path("data/raw")
OUTPUT_FILE = OUTPUT_DIR / "pull_requests.json"


# --- Helpers ---
def github_get(url, params=None):
    """Make one authenticated GET request and return the parsed JSON.
    Raises a clear error if the request failed."""
    response = requests.get(url, headers=HEADERS, params=params)
    if response.status_code != 200:
        raise RuntimeError(
            f"GitHub API request failed ({response.status_code}) for {url}: {response.text[:200]}"
        )
    return response.json()


# --- Fetching steps ---
def fetch_merged_prs(repo, max_prs):
    """Fetch recent closed PRs and keep only those that were actually merged."""
    merged = []
    page = 1
    while len(merged) < max_prs:
        batch = github_get(
            f"{API_ROOT}/repos/{repo}/pulls",
            params={"state": "closed", "per_page": 100, "page": page,
                    "sort": "updated", "direction": "desc"},
        )
        if not batch:                       # no more PRs to read
            break
        for pr in batch:
            if pr.get("merged_at"):         # merged = closed AND has a merge date
                merged.append(pr)
                if len(merged) >= max_prs:
                    break
        page += 1
    return merged


def fetch_reviews(repo, pr_number):
    """Fetch the list of reviews for one PR."""
    # NOTE: deliberately not paginated - only the first page (~30 reviews) is fetched.
    # Acceptable because CR_Passed only needs to find at least one APPROVED review,
    # which is overwhelmingly likely to appear on the first page. Known limitation -
    # document this in the README.
    return github_get(f"{API_ROOT}/repos/{repo}/pulls/{pr_number}/reviews")


def fetch_checks(repo, sha):
    """Fetch BOTH check systems for a commit and return them together."""
    check_runs = github_get(f"{API_ROOT}/repos/{repo}/commits/{sha}/check-runs")
    statuses = github_get(f"{API_ROOT}/repos/{repo}/commits/{sha}/status")
    return {"check_runs": check_runs, "combined_status": statuses}


# --- Main extraction ---
def extract():
    effective_max = float("inf") if FETCH_ALL else MAX_PRS
    print(f"Fetching {'all' if FETCH_ALL else f'up to {MAX_PRS}'} merged PRs from {REPO} ...")
    prs = fetch_merged_prs(REPO, effective_max)
    print(f"Found {len(prs)} merged PRs. Fetching reviews and checks for each ...")

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    records = []
    for pr in prs:
        number = pr["number"]
        sha = pr["head"]["sha"]
        print(f"  PR #{number} ...")

        record = {
            "number": number,
            "title": pr["title"],
            "author": pr["user"]["login"] if pr.get("user") else None,
            "merged_at": pr["merged_at"],
            "head_sha": sha,
        }

        try:
            record["reviews"] = fetch_reviews(REPO, number)
            record["checks"] = fetch_checks(REPO, sha)
        except RuntimeError as e:
            record["error"] = str(e)
            print(f"    failed to fetch reviews/checks for PR #{number}: {e}")

        records.append(record)

        # Save after every PR so progress survives an interruption partway through.
        with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
            json.dump(records, f, indent=2)

        time.sleep(0.1)                     # small pause to be gentle on the API

    print(f"Saved {len(records)} records to {OUTPUT_FILE}")
    return records


if __name__ == "__main__":
    extract()