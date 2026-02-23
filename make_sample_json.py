import csv
import json
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parent
SRC = ROOT / "sample_df.csv"
OUT = ROOT / "out"


def to_float(value):
    try:
        return float(value)
    except Exception:
        return 0.0


def normalize_date(value):
    text = str(value or "").strip()
    if "T" in text:
        text = text.split("T", 1)[0]
    return text[:10]


def build_payloads():
    report_rows = []
    materials_map = {}

    with SRC.open("r", encoding="utf-8-sig", newline="") as file:
        reader = csv.DictReader(file)
        for row in reader:
            report_row = {
                "raw_cd": str(row.get("raw_cd", "")).strip(),
                "raw_nm": str(row.get("raw_nm", "")).strip(),
                "raw_ratio": to_float(row.get("raw_ratio")),
                "mitem_code": str(row.get("mitem_code", "")).strip(),
                "mitem_name": str(row.get("mitem_name", "")).strip(),
                "category": str(row.get("category", "")).strip(),
                "forml_code": str(row.get("forml_code", "")).strip(),
                "forml_name": str(row.get("forml_name", "")).strip(),
                "customer_code": str(row.get("customer_code", "")).strip(),
                "customer_name": str(row.get("customer_name", "")).strip(),
                "base_time": normalize_date(row.get("base_time", "")),
                "total_revenue": to_float(row.get("total_revenue")),
                "product_sales_revenue": to_float(row.get("product_sales_revenue")),
                "net_revenue": to_float(row.get("net_revenue")),
                "product_name": str(row.get("product_name", "")).strip(),
            }
            report_rows.append(report_row)

            raw_cd = report_row["raw_cd"]
            if raw_cd and raw_cd not in materials_map:
                materials_map[raw_cd] = {
                    "raw_cd": raw_cd,
                    "raw_nm": report_row["raw_nm"],
                    "mmsta": "",
                    "researcher": "",
                    "created": datetime.now(timezone.utc).date().isoformat(),
                    "approval_status": "완료",
                }

    generated_at = datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")
    batch_id = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")

    materials_rows = sorted(materials_map.values(), key=lambda item: item["raw_cd"])

    report_payload = {
        "rows": report_rows,
        "meta": {
            "batchId": batch_id,
            "generatedAt": generated_at,
            "status": "success",
            "rowCount": len(report_rows),
            "source": "sample_df.csv",
            "includeNetSales": False,
        },
    }

    materials_payload = {
        "rows": materials_rows,
        "meta": {
            "batchId": batch_id,
            "generatedAt": generated_at,
            "status": "success",
            "rowCount": len(materials_rows),
            "source": "sample_df.csv",
        },
    }

    meta_payload = {
        "status": "success",
        "batchId": batch_id,
        "lastSuccessAt": generated_at,
        "reportRowCount": len(report_rows),
        "materialsRowCount": len(materials_rows),
        "pipeline": {
            "source": {
                "sample": True,
                "file": "sample_df.csv",
                "includeNetSales": False,
            }
        },
    }

    return report_payload, materials_payload, meta_payload


def write_json(path: Path, payload):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def main():
    if not SRC.exists():
        raise FileNotFoundError(f"sample_df.csv not found: {SRC}")

    report_payload, materials_payload, meta_payload = build_payloads()

    report_path = OUT / "report" / "latest.json"
    materials_path = OUT / "materials" / "latest.json"
    meta_path = OUT / "meta" / "latest.json"

    write_json(report_path, report_payload)
    write_json(materials_path, materials_payload)
    write_json(meta_path, meta_payload)

    print("Created:")
    print(report_path)
    print(materials_path)
    print(meta_path)
    print("report rows:", report_payload["meta"]["rowCount"])
    print("materials rows:", materials_payload["meta"]["rowCount"])


if __name__ == "__main__":
    main()
