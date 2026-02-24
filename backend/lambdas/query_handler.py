import base64
import hashlib
import hmac
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
AUTH_SECRET = os.environ.get('BTI_AUTH_SECRET', 'dev-change-this-secret')
LEGACY_DEFAULT_TEAM_ID = os.environ.get('BTI_LEGACY_DEFAULT_TEAM_ID', 'MB2')
LEGACY_DEFAULT_TEAM_NAME = os.environ.get('BTI_LEGACY_DEFAULT_TEAM_NAME', 'MB2팀')


def _response(status: int, body: Dict[str, Any]) -> Dict[str, Any]:
    return {
        'statusCode': status,
        'headers': {
            'Content-Type': 'application/json',
            'Access-Control-Allow-Origin': ALLOWED_ORIGIN,
            'Access-Control-Allow-Methods': 'GET,OPTIONS',
            'Access-Control-Allow-Headers': 'Content-Type,Authorization'
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


def _normalize_materials_rows(rows: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    normalized: List[Dict[str, Any]] = []
    for row in rows or []:
        if not isinstance(row, dict):
            continue
        item = dict(row)
        team_id = str(item.get('team_id') or LEGACY_DEFAULT_TEAM_ID).strip() or LEGACY_DEFAULT_TEAM_ID
        default_team_name = LEGACY_DEFAULT_TEAM_NAME if team_id == LEGACY_DEFAULT_TEAM_ID else f'{team_id}팀'
        item['team_id'] = team_id
        item['team_name'] = str(item.get('team_name') or default_team_name).strip() or default_team_name
        normalized.append(item)
    return normalized


def _filter_rows_by_team(rows: List[Dict[str, Any]], claims: Dict[str, Any]) -> List[Dict[str, Any]]:
    if str(claims.get('role') or '') == 'ADMIN':
        return rows
    team_id = str(claims.get('team_id') or '').strip()
    if not team_id:
        return []
    return [r for r in rows if str(r.get('team_id') or LEGACY_DEFAULT_TEAM_ID).strip() == team_id]


def _build_raw_team_map(material_rows: List[Dict[str, Any]]) -> Dict[str, str]:
    team_map: Dict[str, str] = {}
    for row in _normalize_materials_rows(material_rows):
        raw_cd = str(row.get('raw_cd') or '').strip()
        if not raw_cd:
            continue
        team_map[raw_cd] = str(row.get('team_id') or LEGACY_DEFAULT_TEAM_ID).strip() or LEGACY_DEFAULT_TEAM_ID
    return team_map


def _filter_report_rows_by_team(rows: List[Dict[str, Any]], claims: Dict[str, Any], raw_team_map: Dict[str, str]) -> List[Dict[str, Any]]:
    if str(claims.get('role') or '') == 'ADMIN':
        return rows
    team_id = str(claims.get('team_id') or '').strip()
    if not team_id:
        return []
    result: List[Dict[str, Any]] = []
    for row in rows:
        raw_cd = str((row or {}).get('raw_cd') or '').strip()
        mapped_team = raw_team_map.get(raw_cd, LEGACY_DEFAULT_TEAM_ID)
        if mapped_team == team_id:
            result.append(row)
    return result


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


def _b64url_decode(text: str) -> bytes:
    padded = text + '=' * (-len(text) % 4)
    return base64.urlsafe_b64decode(padded.encode('ascii'))


def _verify_token(token: str) -> Dict[str, Any]:
    try:
        header_b64, payload_b64, sig_b64 = token.split('.', 2)
    except ValueError as exc:
        raise PermissionError('유효하지 않은 토큰 형식입니다.') from exc
    signing_input = f'{header_b64}.{payload_b64}'.encode('ascii')
    expected = hmac.new(AUTH_SECRET.encode('utf-8'), signing_input, hashlib.sha256).digest()
    actual = _b64url_decode(sig_b64)
    if not hmac.compare_digest(expected, actual):
        raise PermissionError('유효하지 않은 토큰입니다.')
    payload = json.loads(_b64url_decode(payload_b64))
    exp = int(payload.get('exp', 0) or 0)
    if exp and exp < int(datetime.utcnow().timestamp()):
        raise PermissionError('토큰이 만료되었습니다.')
    return payload


def _get_bearer_token(event: Dict[str, Any]) -> str:
    headers = event.get('headers') or {}
    auth = headers.get('Authorization') or headers.get('authorization') or ''
    if not str(auth).lower().startswith('bearer '):
        raise PermissionError('인증 토큰이 필요합니다.')
    token = str(auth)[7:].strip()
    if not token:
        raise PermissionError('인증 토큰이 필요합니다.')
    return token


def _require_auth(event: Dict[str, Any]) -> Dict[str, Any]:
    token = _get_bearer_token(event)
    return _verify_token(token)


def lambda_handler(event: Dict[str, Any], _context: Any) -> Dict[str, Any]:
    method = (event.get('requestContext', {}).get('http', {}) or {}).get('method') or event.get('httpMethod', 'GET')
    if method == 'OPTIONS':
        return _response(200, {'ok': True})

    try:
        claims = _require_auth(event)
        path = _route(event)
        query = event.get('queryStringParameters') or {}

        if path.endswith('/report-data') or path == '/report-data':
            payload = _load_json(REPORT_KEY)
            rows = _as_rows(payload)
            date_filtered_rows = _filter_by_date(rows, query.get('startDate', ''), query.get('endDate', ''))
            materials_payload = _load_json(MATERIALS_KEY)
            material_rows = _as_rows(materials_payload)
            raw_team_map = _build_raw_team_map(material_rows)
            filtered_rows = _filter_report_rows_by_team(date_filtered_rows, claims, raw_team_map)
            meta = payload.get('meta', {}) if isinstance(payload, dict) else {}
            meta = {
                **meta,
                'rowCount': len(filtered_rows),
                'scopeTeamId': 'ALL' if str(claims.get('role') or '') == 'ADMIN' else str(claims.get('team_id') or ''),
                'scopeTeamName': '전체팀' if str(claims.get('role') or '') == 'ADMIN' else str(claims.get('team_name') or ''),
                'servedAt': datetime.utcnow().isoformat(timespec='seconds') + 'Z'
            }
            return _response(200, {'rows': filtered_rows, 'meta': meta})

        if path.endswith('/materials') or path == '/materials':
            payload = _load_json(MATERIALS_KEY)
            rows = _normalize_materials_rows(_as_rows(payload))
            rows = _filter_rows_by_team(rows, claims)
            meta = payload.get('meta', {}) if isinstance(payload, dict) else {}
            meta = {
                **meta,
                'rowCount': len(rows),
                'scopeTeamId': 'ALL' if str(claims.get('role') or '') == 'ADMIN' else str(claims.get('team_id') or ''),
                'scopeTeamName': '전체팀' if str(claims.get('role') or '') == 'ADMIN' else str(claims.get('team_name') or ''),
                'servedAt': datetime.utcnow().isoformat(timespec='seconds') + 'Z'
            }
            return _response(200, {'rows': rows, 'meta': meta})

        if path.endswith('/data-status') or path == '/data-status':
            payload = _load_json(META_KEY)
            return _response(200, payload if isinstance(payload, dict) else {'status': 'unknown'})

        return _response(404, {'message': f'Unknown path: {path}'})
    except PermissionError as exc:
        return _response(403, {'message': str(exc)})
    except Exception as exc:
        return _response(500, {'message': str(exc)})
