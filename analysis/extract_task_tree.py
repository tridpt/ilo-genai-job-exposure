"""Flatten the task-level JSON linked from ILO Working Paper 140.

The public visualization contains 3,265 task entries under 427 ISCO-08 codes.
Scores and task labels are preserved; the hierarchy and score-in-name format
are converted into a tabular CSV for analysis.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
import re
from pathlib import Path
from urllib.request import urlopen


ROOT = Path(__file__).resolve().parents[1]
SOURCE_URL = "https://pgmyrek.github.io/2025_GenAI_scores_ISCO08/output_data.json"
SOURCE_SHA256 = "c73052a0fb47d2df5d40c5c886c264cc20984e3fbad0631a0f1f9bde1cd3d98b"
OUTPUT = ROOT / "data" / "ilo_tasks.csv"
FIELDS = (
    "isco08_code",
    "exposure_group",
    "task_order",
    "task_score",
    "task_risk",
    "task_text_en",
)
RISK_LABELS = {"Very Low", "Low", "Medium", "High"}
GROUPS = {
    "Exposed: Gradient 1": "gradient_1",
    "Exposed: Gradient 2": "gradient_2",
    "Exposed: Gradient 3": "gradient_3",
    "Exposed: Gradient 4": "gradient_4",
    "Minimal Exposure": "minimal_exposure",
    "Not Exposed": "not_exposed",
}
TASK_PATTERN = re.compile(r"^\(\s*([0-9]+(?:\.[0-9]+)?)\s*\)\s*-\s*(.+)$")


def source_bytes(json_path: Path | None) -> bytes:
    if json_path is None:
        with urlopen(SOURCE_URL, timeout=45) as response:
            content = response.read()
    else:
        content = json_path.read_bytes()
    digest = hashlib.sha256(content).hexdigest()
    if digest != SOURCE_SHA256:
        raise ValueError(f"Task JSON SHA-256 changed: {digest}. Review the new version first.")
    return content


def extract(content: bytes) -> tuple[list[dict[str, str]], dict[str, str]]:
    tree = json.loads(content)
    if tree.get("name") != "ISCO-08":
        raise ValueError("Unexpected task-tree root")
    level = [tree]
    for depth in range(1, 5):
        level = [child for node in level for child in node.get("children", [])]
        if not level:
            raise ValueError(f"Missing ISCO hierarchy level {depth}")
    occupation_nodes = level

    records: list[dict[str, str]] = []
    group_by_code: dict[str, str] = {}
    for occupation in occupation_nodes:
        match = re.match(r"^(\d{4})\s+-\s+", occupation["name"])
        if not match:
            raise ValueError(f"Malformed occupation name: {occupation['name']!r}")
        code = match.group(1)
        if code in group_by_code:
            raise ValueError(f"Duplicate occupation in task tree: {code}")
        if occupation.get("risk") not in GROUPS:
            raise ValueError(f"Unknown occupation exposure group for {code}")
        group_by_code[code] = GROUPS[occupation["risk"]]
        for order, task in enumerate(occupation.get("children", []), start=1):
            task_match = TASK_PATTERN.match(" ".join(task["name"].split()))
            if not task_match or task.get("risk") not in RISK_LABELS:
                raise ValueError(f"Malformed task under ISCO {code}")
            score = float(task_match.group(1))
            if not 0 <= score <= 1:
                raise ValueError(f"Task score outside 0–1 range under ISCO {code}")
            records.append(
                {
                    "isco08_code": code,
                    "exposure_group": group_by_code[code],
                    "task_order": str(order),
                    "task_score": f"{score:.4f}",
                    "task_risk": task["risk"].lower().replace(" ", "_"),
                    "task_text_en": " ".join(task_match.group(2).split()),
                }
            )

    if len(group_by_code) != 427 or len(records) != 3265:
        raise ValueError(f"Expected 427 occupations and 3,265 tasks; got {len(group_by_code)}, {len(records)}")
    return records, group_by_code


def csv_text(records: list[dict[str, str]]) -> str:
    output = io.StringIO(newline="")
    writer = csv.DictWriter(output, fieldnames=FIELDS, lineterminator="\n")
    writer.writeheader()
    writer.writerows(records)
    return output.getvalue()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json", type=Path, help="Use a local copy of the pinned JSON")
    parser.add_argument("--check", action="store_true", help="Compare extraction with the committed CSV")
    args = parser.parse_args()
    records, groups = extract(source_bytes(args.json))
    result = csv_text(records)
    if args.check:
        if not OUTPUT.exists() or OUTPUT.read_text(encoding="utf-8") != result:
            raise SystemExit("The task extract differs from data/ilo_tasks.csv")
        print(f"Verified {len(records)} tasks under {len(groups)} ISCO-08 codes")
    else:
        OUTPUT.parent.mkdir(exist_ok=True)
        OUTPUT.write_text(result, encoding="utf-8", newline="")
        print(f"Wrote {len(records)} tasks to {OUTPUT.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
