import json
import os
from datetime import datetime
from typing import Any, Dict, List

import boto3

s3 = boto3.client('s3')

DATA_BUCKET = os.environ.get('BTI_DATA_BUCKET', '')
REPORT_KEY = os.environ.get('BTI_REPORT_LATEST_KEY', 'report/latest.json')
MATERIALS_KEY = os.environ.get('BTI_MATERIALS_LATEST_KEY', 'materials/latest.json')
META_KEY = os.environ.get('BTI_META_LATEST_KEY', 'meta/latest.json')
ALLOWED_ORIGIN = os.environ.get('ALLOWED_ORIGIN', '*')


def _response(status: int, body: Dict[str, Any]) -> Dict[str, Any]:
    return {
        'statusCode': status,
        'headers': {
            'Content-Type': 'application/json',
            'Access-Control-Allow-Origin': ALLOWED_ORIGIN,
            'Access-Control-Allow-Methods': 'GET,OPTIONS',
            'Access-Control-Allow-Headers': 'Content-Type'
        },
        'body': json.dumps(body, ensure_ascii=False, default=str)
    }


def _load_json(key: str) -> Any:
    if not DATA_BUCKET:
        raise RuntimeError('BTI_DATA_BUCKET 환경변수가 설정되지 않았습니다.')
    obj = s3.get_object(Bucket=DATA_BUCKET, Key=key)
    return json.loads(obj['Body'].read())


def _as_rows(payload: Any) -> List[Dict[str, Any]]:
    if isinstance(payload, dict) and isinstance(payload.get('rows'), list):
        return payload['rows']
    if isinstance(payload, list):
        return payload
    return []


def _normalize_date(value: str) -> str:
    if not value:
        return ''
    text = str(value).strip()
    if 'T' in text:
        text = text.split('T', 1)[0]
    return text[:10]


def _filter_by_date(rows: List[Dict[str, Any]], start_date: str, end_date: str) -> List[Dict[str, Any]]:
    if not start_date and not end_date:
        return rows

    start_norm = _normalize_date(start_date)
    end_norm = _normalize_date(end_date)
    filtered = []

    for row in rows:
        base_time = _normalize_date(row.get('base_time', ''))
        if not base_time:
            continue
        if start_norm and base_time < start_norm:
            continue
        if end_norm and base_time > end_norm:
            continue
        filtered.append(row)
    return filtered


def _route(event: Dict[str, Any]) -> str:
    raw_path = event.get('rawPath') or event.get('path') or '/'
    stage = event.get('requestContext', {}).get('stage')
    if stage and raw_path.startswith(f'/{stage}/'):
        raw_path = raw_path[len(stage) + 1 :]
    return raw_path.rstrip('/') or '/'


def lambda_handler(event: Dict[str, Any], _context: Any) -> Dict[str, Any]:
    method = (event.get('requestContext', {}).get('http', {}) or {}).get('method') or event.get('httpMethod', 'GET')
    if method == 'OPTIONS':
        return _response(200, {'ok': True})

    try:
        path = _route(event)
        query = event.get('queryStringParameters') or {}

        if path.endswith('/report-data') or path == '/report-data':
            payload = _load_json(REPORT_KEY)
            rows = _as_rows(payload)
            filtered_rows = _filter_by_date(rows, query.get('startDate', ''), query.get('endDate', ''))
            meta = payload.get('meta', {}) if isinstance(payload, dict) else {}
            meta = {
                **meta,
                'rowCount': len(filtered_rows),
                'servedAt': datetime.utcnow().isoformat(timespec='seconds') + 'Z'
            }
            return _response(200, {'rows': filtered_rows, 'meta': meta})

        if path.endswith('/materials') or path == '/materials':
            payload = _load_json(MATERIALS_KEY)
            rows = _as_rows(payload)
            meta = payload.get('meta', {}) if isinstance(payload, dict) else {}
            meta = {
                **meta,
                'rowCount': len(rows),
                'servedAt': datetime.utcnow().isoformat(timespec='seconds') + 'Z'
            }
            return _response(200, {'rows': rows, 'meta': meta})

        if path.endswith('/data-status') or path == '/data-status':
            payload = _load_json(META_KEY)
            return _response(200, payload if isinstance(payload, dict) else {'status': 'unknown'})

        return _response(404, {'message': f'Unknown path: {path}'})
    except Exception as exc:
        return _response(500, {'message': str(exc)})
