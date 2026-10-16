"""Validate ILO extracts, run SQL analysis, and build the site's data bundle.

Run `python analysis/build_data.py` after changing the cited inputs.
Run `python analysis/build_data.py --check` in review or CI.
"""

from __future__ import annotations

import argparse
import csv
import io
import json
import sqlite3
from collections import Counter
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
ANALYSIS = ROOT / "analysis"
EXPECTED_INDICATORS = {
    "world_gradients_1_3",
    "world_gradient_4",
    "low_income_any",
    "high_income_any",
    "world_female_gradient_4",
    "world_male_gradient_4",
    "high_income_female_gradient_4",
    "high_income_male_gradient_4",
    "task_count",
    "exposed_occupation_count",
}
GROUP_ORDER = (
    "gradient_4",
    "gradient_3",
    "gradient_2",
    "gradient_1",
    "minimal_exposure",
    "not_exposed",
)
GROUP_LABELS_VI = {
    "gradient_4": "Nhóm 4",
    "gradient_3": "Nhóm 3",
    "gradient_2": "Nhóm 2",
    "gradient_1": "Nhóm 1",
    "minimal_exposure": "Tiếp xúc rất ít",
    "not_exposed": "Chưa vào nhóm 1–4",
}


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8", newline="") as stream:
        return list(csv.DictReader(stream))


def validate_inputs(
    indicators: list[dict[str, str]],
    occupations: list[dict[str, str]],
    tasks: list[dict[str, str]],
    selection: list[dict[str, str]],
) -> dict[str, Decimal]:
    metric_ids = [row["metric_id"] for row in indicators]
    if len(metric_ids) != len(set(metric_ids)) or set(metric_ids) != EXPECTED_INDICATORS:
        raise ValueError("Indicator IDs must be unique and complete")
    values = {row["metric_id"]: Decimal(row["value"]) for row in indicators}
    for row in indicators:
        value = values[row["metric_id"]]
        if row["unit"].startswith("percent") and not 0 <= value <= 100:
            raise ValueError(f"Invalid percentage: {row['metric_id']}")
        if not row["source_doc"] or not row["source_page"]:
            raise ValueError(f"Missing source locator: {row['metric_id']}")
    for key in ("task_count", "exposed_occupation_count"):
        if values[key] != values[key].to_integral_value() or values[key] <= 0:
            raise ValueError(f"Invalid count: {key}")

    codes = [row["isco08_code"] for row in occupations]
    if len(codes) != 427 or len(codes) != len(set(codes)):
        raise ValueError("Expected 427 unique ISCO-08 codes from Table A1")
    groups = Counter(row["exposure_group"] for row in occupations)
    if set(groups) != set(GROUP_ORDER):
        raise ValueError(f"Unexpected exposure groups: {groups}")
    for row in occupations:
        mean, sd = Decimal(row["mean_score"]), Decimal(row["sd_score"])
        if not 0 <= mean <= 1 or not 0 <= sd <= 1:
            raise ValueError(f"Invalid score for ISCO {row['isco08_code']}")
        if not row["occupation_name_en"] or not row["source_page"]:
            raise ValueError(f"Incomplete occupation row: {row['isco08_code']}")

    occupation_groups = {row["isco08_code"]: row["exposure_group"] for row in occupations}
    if len(tasks) != 3265:
        raise ValueError("Expected 3,265 ISCO-08 task entries from the linked JSON")
    task_keys = set()
    for row in tasks:
        code = row["isco08_code"]
        key = (code, row["task_order"])
        if key in task_keys or occupation_groups.get(code) != row["exposure_group"]:
            raise ValueError(f"Duplicate task or mismatched occupation group: {key}")
        task_keys.add(key)
        if not 0 <= Decimal(row["task_score"]) <= 1:
            raise ValueError(f"Invalid task score: {key}")
        if row["task_risk"] not in {"very_low", "low", "medium", "high"}:
            raise ValueError(f"Invalid task risk: {key}")
        if not row["task_text_en"]:
            raise ValueError(f"Missing task description: {key}")
    if {code for code, _ in task_keys} != set(codes):
        raise ValueError("Task data does not cover every Annex A1 occupation")

    selected_codes = [row["isco08_code"] for row in selection]
    if len(selection) != 6 or len(set(selected_codes)) != 6:
        raise ValueError("The six editorial occupation examples must be unique")
    if not set(selected_codes) <= set(codes):
        raise ValueError("Editorial selection contains an ISCO code outside Table A1")
    if sorted(int(row["display_order"]) for row in selection) != list(range(1, 7)):
        raise ValueError("Editorial display order must be 1–6")
    return values


def sql_analysis(
    occupations: list[dict[str, str]],
    tasks: list[dict[str, str]],
    selection: list[dict[str, str]],
) -> tuple[list[dict[str, object]], list[dict[str, object]], list[dict[str, object]], int, int]:
    connection = sqlite3.connect(":memory:")
    connection.row_factory = sqlite3.Row
    connection.executescript(
        """
        CREATE TABLE occupations (
          isco08_code TEXT PRIMARY KEY,
          occupation_name_en TEXT NOT NULL,
          exposure_group TEXT NOT NULL,
          mean_score REAL NOT NULL,
          sd_score REAL NOT NULL,
          source_page INTEGER NOT NULL
        );
        CREATE TABLE selected_occupations (
          isco08_code TEXT PRIMARY KEY,
          display_order INTEGER UNIQUE NOT NULL,
          label_vi TEXT NOT NULL,
          color TEXT NOT NULL
        );
        CREATE TABLE tasks (
          isco08_code TEXT NOT NULL REFERENCES occupations(isco08_code),
          exposure_group TEXT NOT NULL,
          task_order INTEGER NOT NULL,
          task_score REAL NOT NULL,
          task_risk TEXT NOT NULL,
          task_text_en TEXT NOT NULL,
          PRIMARY KEY (isco08_code, task_order)
        );
        """
    )
    connection.executemany(
        "INSERT INTO occupations VALUES (:isco08_code, :occupation_name_en, :exposure_group, :mean_score, :sd_score, :source_page)",
        occupations,
    )
    connection.executemany(
        "INSERT INTO selected_occupations VALUES (:isco08_code, :display_order, :label_vi, :color)",
        selection,
    )
    connection.executemany(
        "INSERT INTO tasks VALUES (:isco08_code, :exposure_group, :task_order, :task_score, :task_risk, :task_text_en)",
        tasks,
    )
    connection.executescript((ANALYSIS / "queries.sql").read_text(encoding="utf-8"))
    exposed_codes, all_codes = connection.execute(
        "SELECT exposed_codes, all_codes FROM exposure_reconciliation"
    ).fetchone()
    profile = [
        dict(row)
        for row in connection.execute(
            "SELECT * FROM occupation_profile ORDER BY CASE exposure_group "
            + " ".join(f"WHEN '{group}' THEN {i}" for i, group in enumerate(GROUP_ORDER))
            + " END"
        )
    ]
    story_occupations = [
        dict(row)
        for row in connection.execute(
            "SELECT * FROM story_occupations ORDER BY display_order"
        )
    ]
    reconciliation = [
        dict(row)
        for row in connection.execute(
            "SELECT * FROM task_score_reconciliation ORDER BY absolute_gap DESC, isco08_code"
        )
    ]
    connection.close()
    return profile, story_occupations, reconciliation, exposed_codes, all_codes


def make_bundle(
    values: dict[str, Decimal],
    profile: list[dict[str, object]],
    occupations: list[dict[str, object]],
    reconciliation: list[dict[str, object]],
    exposed_codes: int,
    all_codes: int,
) -> dict[str, object]:
    if exposed_codes != int(values["exposed_occupation_count"]):
        raise ValueError("Table A1 exposed-code count disagrees with the ILO brief")
    exposed = values["world_gradients_1_3"] + values["world_gradient_4"]
    outside = Decimal(100) - exposed
    grid_medium = int(values["world_gradients_1_3"].quantize(0, rounding=ROUND_HALF_UP))
    grid_high = int(values["world_gradient_4"].quantize(0, rounding=ROUND_HALF_UP))
    grid_outside = 100 - grid_medium - grid_high
    if grid_outside != int(outside.quantize(0, rounding=ROUND_HALF_UP)):
        raise ValueError("The 100-cell illustration does not reconcile")
    if len(reconciliation) != all_codes or any(row["task_rows"] == 0 for row in reconciliation):
        raise ValueError("Task-to-occupation reconciliation is incomplete")
    within_point_01 = sum(row["absolute_gap"] <= 0.01 for row in reconciliation)
    largest_gap = reconciliation[0]
    if largest_gap["absolute_gap"] > 0.03:
        raise ValueError("Unexpected task/annex score gap above 0.03")

    return {
        "global": {
            "gradients_1_3_pct": float(values["world_gradients_1_3"]),
            "gradient_4_pct": float(values["world_gradient_4"]),
            "total_exposed_pct": float(exposed),
            "outside_pct": float(outside),
            "grid": {
                "outside": grid_outside,
                "gradients_1_3": grid_medium,
                "gradient_4": grid_high,
            },
        },
        "income": {
            "low_pct": float(values["low_income_any"]),
            "high_pct": float(values["high_income_any"]),
            "gap_pp": float(values["high_income_any"] - values["low_income_any"]),
        },
        "gender": {
            "world": {
                "female": float(values["world_female_gradient_4"]),
                "male": float(values["world_male_gradient_4"]),
            },
            "rich": {
                "female": float(values["high_income_female_gradient_4"]),
                "male": float(values["high_income_male_gradient_4"]),
            },
        },
        "method": {
            "task_count": int(values["task_count"]),
            "isco_task_entries": 3265,
            "exposed_occupation_count": exposed_codes,
            "annex_occupation_count": all_codes,
        },
        "quality_check": {
            "means_within_0_01": within_point_01,
            "occupation_count": all_codes,
            "largest_gap": {
                "isco08_code": largest_gap["isco08_code"],
                "annex_mean_score": largest_gap["annex_mean_score"],
                "task_mean_score": largest_gap["task_mean_score"],
                "absolute_gap": largest_gap["absolute_gap"],
            },
        },
        "occupation_profile": [
            {
                "group": row["exposure_group"],
                "label_vi": GROUP_LABELS_VI[row["exposure_group"]],
                "count": row["occupation_count"],
                "unweighted_mean_score": row["unweighted_mean_score"],
                "min_score": row["min_score"],
                "max_score": row["max_score"],
            }
            for row in profile
        ],
        "occupations": [
            {
                "isco08_code": row["isco08_code"],
                "label_vi": row["label_vi"],
                "name_en": row["occupation_name_en"],
                "group": row["exposure_group"],
                "group_label_vi": GROUP_LABELS_VI[row["exposure_group"]],
                "mean_score": row["mean_score"],
                "sd_score": row["sd_score"],
                "source_page": row["source_page"],
                "color": row["color"],
            }
            for row in occupations
        ],
    }


def profile_csv(profile: list[dict[str, object]]) -> str:
    output = io.StringIO(newline="")
    writer = csv.DictWriter(
        output,
        fieldnames=(
            "exposure_group",
            "occupation_count",
            "unweighted_mean_score",
            "min_score",
            "max_score",
        ),
        lineterminator="\n",
    )
    writer.writeheader()
    writer.writerows(profile)
    return output.getvalue()


def reconciliation_csv(rows: list[dict[str, object]]) -> str:
    output = io.StringIO(newline="")
    writer = csv.DictWriter(
        output,
        fieldnames=(
            "isco08_code",
            "occupation_name_en",
            "exposure_group",
            "task_rows",
            "annex_mean_score",
            "task_mean_score",
            "absolute_gap",
        ),
        lineterminator="\n",
    )
    writer.writeheader()
    writer.writerows(rows)
    return output.getvalue()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="Verify generated files are current")
    args = parser.parse_args()
    indicators = read_csv(DATA / "ilo_indicators.csv")
    occupations = read_csv(DATA / "ilo_occupations.csv")
    tasks = read_csv(DATA / "ilo_tasks.csv")
    selection = read_csv(ANALYSIS / "selected_occupations.csv")
    values = validate_inputs(indicators, occupations, tasks, selection)
    profile, story_occupations, reconciliation, exposed_codes, all_codes = sql_analysis(
        occupations, tasks, selection
    )
    if len(story_occupations) != len(selection):
        raise ValueError("SQL join lost an editorial occupation")
    bundle = make_bundle(
        values, profile, story_occupations, reconciliation, exposed_codes, all_codes
    )
    serialized = json.dumps(bundle, ensure_ascii=False, indent=2) + "\n"
    outputs = {
        DATA / "occupation_profile.csv": profile_csv(profile),
        DATA / "occupation_reconciliation.csv": reconciliation_csv(reconciliation),
        DATA / "story-data.json": serialized,
        DATA / "story-data.js": "window.STORY_DATA = " + serialized.rstrip() + ";\n",
    }
    for path, content in outputs.items():
        if args.check:
            if not path.exists() or path.read_text(encoding="utf-8") != content:
                raise SystemExit(f"Generated file is stale: {path.relative_to(ROOT)}")
        else:
            path.write_text(content, encoding="utf-8", newline="")
    action = "Verified" if args.check else "Built"
    print(
        f"{action} 3,265 tasks, 427 occupation codes, {exposed_codes} exposed codes, "
        f"{bundle['quality_check']['means_within_0_01']}/427 means within 0.01, "
        f"and {len(outputs)} generated files"
    )


if __name__ == "__main__":
    main()
