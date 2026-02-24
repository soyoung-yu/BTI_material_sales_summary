import json
import os
from datetime import datetime, timezone
from typing import Any, Dict

import boto3
from backend.batch.pipeline import run_batch_pipeline

s3 = boto3.client('s3')

DATA_BUCKET = os.environ.get('BTI_DATA_BUCKET', '')
REPORT_PREFIX = os.environ.get('BTI_REPORT_PREFIX', 'report')
MATERIALS_PREFIX = os.environ.get('BTI_MATERIALS_PREFIX', 'materials')
META_PREFIX = os.environ.get('BTI_META_PREFIX', 'meta')


def _put_json(key: str, payload: Dict[str, Any]) -> None:
    s3.put_object(
        Bucket=DATA_BUCKET,
        Key=key,
        Body=json.dumps(payload, ensure_ascii=False, default=str).encode('utf-8'),
        ContentType='application/json'
    )


def _batch_id() -> str:
    return datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')


def _extract_available_years(report_rows: Any) -> list[int]:
    years = set()
    for row in report_rows or []:
        if not isinstance(row, dict):
            continue
        base_time = str(row.get('base_time', '')).strip()
        if len(base_time) < 4:
            continue
        try:
            years.add(int(base_time[:4]))
        except ValueError:
            continue
    return sorted(years, reverse=True)


def lambda_handler(event: Dict[str, Any], _context: Any) -> Dict[str, Any]:
    if not DATA_BUCKET:
        raise RuntimeError('BTI_DATA_BUCKET 환경변수가 설정되지 않았습니다.')

    batch_id = _batch_id()
    started_at = datetime.now(timezone.utc).isoformat()

    try:
        report_rows, material_rows, pipeline_meta = run_batch_pipeline(event or {})

        report_payload = {
            'rows': report_rows,
            'meta': {
                'batchId': batch_id,
                'generatedAt': started_at,
                'status': 'success',
                'rowCount': len(report_rows)
            }
        }
        materials_payload = {
            'rows': material_rows,
            'meta': {
                'batchId': batch_id,
                'generatedAt': started_at,
                'status': 'success',
                'rowCount': len(material_rows)
            }
        }
        meta_payload = {
            'status': 'success',
            'batchId': batch_id,
            'lastSuccessAt': started_at,
            'reportRowCount': len(report_rows),
            'materialsRowCount': len(material_rows),
            'availableYears': _extract_available_years(report_rows),
            'pipeline': pipeline_meta,
        }

        _put_json(f'{REPORT_PREFIX}/versions/{batch_id}.json', report_payload)
        _put_json(f'{MATERIALS_PREFIX}/versions/{batch_id}.json', materials_payload)
        _put_json(f'{REPORT_PREFIX}/latest.json', report_payload)
        _put_json(f'{MATERIALS_PREFIX}/latest.json', materials_payload)
        _put_json(f'{META_PREFIX}/latest.json', meta_payload)

        return {
            'statusCode': 200,
            'body': json.dumps(meta_payload, ensure_ascii=False)
        }
    except Exception as exc:
        failure_meta = {
            'status': 'failed',
            'batchId': batch_id,
            'failedAt': started_at,
            'message': str(exc),
        }
        try:
            _put_json(f'{META_PREFIX}/latest.json', failure_meta)
        except Exception:
            pass
        return {
            'statusCode': 500,
            'body': json.dumps(failure_meta, ensure_ascii=False)
        }
