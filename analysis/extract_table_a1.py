"""Extract the complete ISCO-08 occupation table from ILO Working Paper 140.

The PDF is the source. The CSV is a checked-in, reproducible snapshot so the
website and analysis can be built without relying on a live ILO connection.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import io
import re
from pathlib import Path
from urllib.request import Request, urlopen

import pdfplumber


ROOT = Path(__file__).resolve().parents[1]
SOURCE_URL = "https://www.ilo.org/sites/default/files/2025-05/WP140_web.pdf"
SOURCE_SHA256 = "9077761c72aabaa3c7ee70999ec5aa46a6afcf943b5fb01baa971f601d363ee9"
OUTPUT = ROOT / "data" / "ilo_occupations.csv"
FIELDS = (
    "isco08_code",
    "occupation_name_en",
    "exposure_group",
    "mean_score",
    "sd_score",
    "source_page",
)
GROUPS = {
    "Gradient 1": "gradient_1",
    "Gradient 2": "gradient_2",
    "Gradient 3": "gradient_3",
    "Gradient 4": "gradient_4",
    "Minimal Exposure": "minimal_exposure",
    "Not Exposed": "not_exposed",
}
EXPECTED_COUNTS = {
    "gradient_1": 17,
    "gradient_2": 44,
    "gradient_3": 38,
    "gradient_4": 13,
    "minimal_exposure": 84,
    "not_exposed": 231,
}


def source_bytes(pdf_path: Path | None) -> bytes:
    if pdf_path is None:
        request = Request(SOURCE_URL, headers={"User-Agent": "Mozilla/5.0"})
        with urlopen(request, timeout=45) as response:
            content = response.read()
    else:
        content = pdf_path.read_bytes()
    if not content.startswith(b"%PDF"):
        raise ValueError("The source response is not a PDF")
    digest = hashlib.sha256(content).hexdigest()
    if digest != SOURCE_SHA256:
        raise ValueError(f"ILO PDF SHA-256 changed: {digest}. Review the new version first.")
    return content


def extract(content: bytes) -> list[dict[str, str]]:
    records: list[dict[str, str]] = []
    in_annex = False
    with pdfplumber.open(io.BytesIO(content)) as pdf:
        for pdf_page, page in enumerate(pdf.pages, start=1):
            page_text = page.extract_text() or ""
            if (
                "Table A1. ISCO-08 occupations by exposure gradient" in page_text
                and "Exposure 4-digit code Occupation Name Mean SD" in page_text
            ):
                in_annex = True
            if in_annex and "3. Survey Questionnaire" in page_text:
                break
            if not in_annex:
                continue

            match = re.match(r"(\d+)\s+ILO Working Paper 140", page_text)
            if not match:
                raise ValueError(f"Printed page number not found on PDF page {pdf_page}")
            printed_page = match.group(1)
            tables = page.extract_tables()
            if len(tables) != 1:
                raise ValueError(f"Expected one annex table on PDF page {pdf_page}")
            table = tables[0]
            if table[0] != ["Exposure", "4-digit code", "Occupation Name", "Mean", "SD"]:
                raise ValueError(f"Unexpected table header on PDF page {pdf_page}")

            for source_group, code, name, mean, sd in table[1:]:
                group = GROUPS.get(" ".join(source_group.split()))
                clean_name = " ".join(name.split())
                if not group or not re.fullmatch(r"\d{4}", code) or not clean_name:
                    raise ValueError(f"Malformed row on printed page {printed_page}: {code!r}")
                mean_value, sd_value = float(mean), float(sd)
                if not (0 <= mean_value <= 1 and 0 <= sd_value <= 1):
                    raise ValueError(f"Score outside 0–1 range for {code}")
                records.append(
                    {
                        "isco08_code": code,
                        "occupation_name_en": clean_name,
                        "exposure_group": group,
                        "mean_score": f"{mean_value:.2f}",
                        "sd_score": f"{sd_value:.2f}",
                        "source_page": printed_page,
                    }
                )

    counts = {group: sum(row["exposure_group"] == group for row in records) for group in GROUPS.values()}
    if counts != EXPECTED_COUNTS:
        raise ValueError(f"Annex count check failed: {counts}")
    codes = [row["isco08_code"] for row in records]
    if len(codes) != len(set(codes)):
        raise ValueError("Duplicate ISCO-08 occupation code")
    return records


def csv_text(records: list[dict[str, str]]) -> str:
    output = io.StringIO(newline="")
    writer = csv.DictWriter(output, fieldnames=FIELDS, lineterminator="\n")
    writer.writeheader()
    writer.writerows(records)
    return output.getvalue()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pdf", type=Path, help="Use a local copy of the pinned ILO PDF")
    parser.add_argument("--check", action="store_true", help="Compare extraction with the committed CSV")
    args = parser.parse_args()
    records = extract(source_bytes(args.pdf))
    result = csv_text(records)
    if args.check:
        if not OUTPUT.exists() or OUTPUT.read_text(encoding="utf-8") != result:
            raise SystemExit("The extracted annex differs from data/ilo_occupations.csv")
        print(f"Verified {len(records)} rows against the ILO PDF and CSV snapshot")
    else:
        OUTPUT.parent.mkdir(exist_ok=True)
        OUTPUT.write_text(result, encoding="utf-8", newline="")
        print(f"Wrote {len(records)} occupation rows to {OUTPUT.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
