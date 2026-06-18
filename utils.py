"""
utils.py
Source-agnostic helper functions shared across the pipeline.
Nothing here is GitHub-specific - these handle reading and writing data
in standard formats, so they could be reused by any integration.
"""

import csv
import json
from pathlib import Path


def save_json(path, data):
    """Write data to a JSON file (pretty-printed), creating parent folders if needed."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)


def load_json(path):
    """Read and return data from a JSON file."""
    with open(Path(path), encoding="utf-8") as f:
        return json.load(f)


def write_csv(records, path, columns=None, delimiter=","):
    """Write a list of dict records to a CSV file, creating parent folders if needed.

    records:   list of dicts (each dict is one row).
    columns:   optional list of column names controlling order and which fields to include.
               If omitted, uses the keys of the first record.
    delimiter: field separator. Defaults to "," (standard CSV). Some locales
               (e.g. South Africa, Germany) use "," as the decimal separator and
               expect ";"-delimited files, so this is configurable.
    """
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)

    if not records:
        open(path, "w", encoding="utf-8").close()
        return

    if columns is None:
        columns = list(records[0].keys())

    with open(path, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=columns, extrasaction="ignore", delimiter=delimiter)
        writer.writeheader()
        for record in records:
            writer.writerow(record)