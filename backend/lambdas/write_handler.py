import base64
import hashlib
import hmac
import json
import os
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional, Tuple
from uuid import uuid4

import boto3
from botocore.exceptions import ClientError

s3 = boto3.client('s3')

DATA_BUCKET = os.environ.get('BTI_DATA_BUCKET', '')
MATERIALS_KEY = os.environ.get('BTI_MATERIALS_LATEST_KEY', 'materials/latest.json')
ACCOUNTS_KEY = os.environ.get('BTI_ACCOUNTS_KEY', 'auth/accounts.json')
MATERIAL_REQUESTS_KEY = os.environ.get('BTI_MATERIAL_REQUESTS_KEY', 'materials/requests_store.json')
ALLOWED_ORIGIN = os.environ.get('ALLOWED_ORIGIN', '*')
AUTH_SECRET = os.environ.get('BTI_AUTH_SECRET', 'dev-change-this-secret')
DEFAULT_RESET_PASSWORD = os.environ.get('BTI_DEFAULT_RESET_PASSWORD', 'firstpassword')
TOKEN_EXPIRES_HOURS = int(os.environ.get('BTI_AUTH_TOKEN_EXPIRES_HOURS', '12'))

ROLES = {'ADMIN', 'TEAM_ADMIN', 'TEAM_MEMBER'}

DEFAULT_ACCOUNTS = [
    {
        'account_id': 'acc-admin',
        'login_id': 'admin',
        'password': 'admin1234',
        'name': '관리자',
        'team_id': 'HQ',
        'team_name': '관리자',
        'role': 'ADMIN',
        'active': True,
    },
    {
        'account_id': 'acc-mb2-admin',
        'login_id': 'mb2_admin',
        'password': 'mb21234',
        'name': 'MB2팀장',
        'team_id': 'MB2',
        'team_name': 'MB2팀',
        'role': 'TEAM_ADMIN',
        'active': True,
    },
]


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _response(status: int, body: Dict[str, Any]) -> Dict[str, Any]:
    return {
        'statusCode': status,
        'headers': {
            'Content-Type': 'application/json',
            'Access-Control-Allow-Origin': ALLOWED_ORIGIN,
            'Access-Control-Allow-Methods': 'GET,POST,DELETE,OPTIONS',
            'Access-Control-Allow-Headers': 'Content-Type,Authorization'
        },
        'body': json.dumps(body, ensure_ascii=False, default=str)
    }


def _route(event: Dict[str, Any]) -> str:
    raw_path = event.get('rawPath') or event.get('path') or '/'
    stage = event.get('requestContext', {}).get('stage')
    if stage and raw_path.startswith(f'/{stage}/'):
        raw_path = raw_path[len(stage) + 1 :]
    return raw_path.rstrip('/') or '/'


def _parse_json_body(event: Dict[str, Any]) -> Dict[str, Any]:
    body = event.get('body')
    if not body:
        return {}
    if event.get('isBase64Encoded'):
        body = base64.b64decode(body).decode('utf-8')
    data = json.loads(body)
    return data if isinstance(data, dict) else {}


def _load_json_or_default(key: str, default_value: Any) -> Any:
    if not DATA_BUCKET:
        raise RuntimeError('BTI_DATA_BUCKET 환경변수가 설정되지 않았습니다.')
    try:
        obj = s3.get_object(Bucket=DATA_BUCKET, Key=key)
        return json.loads(obj['Body'].read())
    except ClientError as exc:
        code = exc.response.get('Error', {}).get('Code')
        if code in {'NoSuchKey', '404'}:
            return default_value
        raise


def _put_json(key: str, payload: Any) -> None:
    s3.put_object(
        Bucket=DATA_BUCKET,
        Key=key,
        Body=json.dumps(payload, ensure_ascii=False, default=str).encode('utf-8'),
        ContentType='application/json'
    )


def _hash_password(raw_password: str) -> str:
    text = str(raw_password or '')
    if text.startswith('sha256$'):
        return text
    digest = hashlib.sha256(text.encode('utf-8')).hexdigest()
    return f'sha256${digest}'


def _verify_password(stored: str, raw_password: str) -> bool:
    if str(stored).startswith('sha256$'):
        return hmac.compare_digest(str(stored), _hash_password(raw_password))
    return hmac.compare_digest(str(stored), str(raw_password))


def _load_accounts() -> List[Dict[str, Any]]:
    payload = _load_json_or_default(ACCOUNTS_KEY, {'rows': DEFAULT_ACCOUNTS})
    rows = payload.get('rows') if isinstance(payload, dict) else payload
    if not isinstance(rows, list) or len(rows) == 0:
        rows = DEFAULT_ACCOUNTS.copy()

    normalized = []
    changed = False
    for row in rows:
        if not isinstance(row, dict):
            continue
        item = dict(row)
        item.setdefault('account_id', f'acc-{uuid4().hex[:10]}')
        item.setdefault('active', True)
        if not str(item.get('password', '')).startswith('sha256$'):
            item['password'] = _hash_password(str(item.get('password', '')))
            changed = True
        normalized.append(item)

    if changed:
        _save_accounts(normalized)
    return normalized


def _save_accounts(rows: List[Dict[str, Any]]) -> None:
    _put_json(ACCOUNTS_KEY, {
        'rows': rows,
        'meta': {
            'updatedAt': _utcnow().isoformat(),
            'rowCount': len(rows)
        }
    })


def _public_account(a: Dict[str, Any]) -> Dict[str, Any]:
    return {
        'account_id': a.get('account_id'),
        'login_id': a.get('login_id'),
        'name': a.get('name'),
        'team_id': a.get('team_id'),
        'team_name': a.get('team_name'),
        'role': a.get('role'),
        'active': a.get('active', True),
    }


def _b64url(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b'=').decode('ascii')


def _b64url_decode(text: str) -> bytes:
    padded = text + '=' * (-len(text) % 4)
    return base64.urlsafe_b64decode(padded.encode('ascii'))


def _sign_token(payload: Dict[str, Any]) -> str:
    header = {'alg': 'HS256', 'typ': 'JWT'}
    header_b64 = _b64url(json.dumps(header, separators=(',', ':')).encode('utf-8'))
    payload_b64 = _b64url(json.dumps(payload, separators=(',', ':')).encode('utf-8'))
    signing_input = f'{header_b64}.{payload_b64}'.encode('ascii')
    sig = hmac.new(AUTH_SECRET.encode('utf-8'), signing_input, hashlib.sha256).digest()
    return f'{header_b64}.{payload_b64}.{_b64url(sig)}'


def _verify_token(token: str) -> Dict[str, Any]:
    try:
        header_b64, payload_b64, sig_b64 = token.split('.', 2)
    except ValueError:
        raise ValueError('유효하지 않은 토큰 형식입니다.')
    signing_input = f'{header_b64}.{payload_b64}'.encode('ascii')
    expected = hmac.new(AUTH_SECRET.encode('utf-8'), signing_input, hashlib.sha256).digest()
    actual = _b64url_decode(sig_b64)
    if not hmac.compare_digest(expected, actual):
        raise ValueError('유효하지 않은 토큰입니다.')
    payload = json.loads(_b64url_decode(payload_b64))
    exp = int(payload.get('exp', 0))
    if exp and exp < int(_utcnow().timestamp()):
        raise ValueError('토큰이 만료되었습니다.')
    return payload


def _get_bearer_token(event: Dict[str, Any]) -> Optional[str]:
    headers = event.get('headers') or {}
    auth = headers.get('Authorization') or headers.get('authorization')
    if not auth:
        return None
    if not str(auth).lower().startswith('bearer '):
        return None
    return str(auth)[7:].strip()


def _require_auth(event: Dict[str, Any]) -> Dict[str, Any]:
    token = _get_bearer_token(event)
    if not token:
        raise PermissionError('인증 토큰이 필요합니다.')
    claims = _verify_token(token)
    accounts = _load_accounts()
    account = next((a for a in accounts if a.get('account_id') == claims.get('sub') and a.get('active', True)), None)
    if not account:
        raise PermissionError('유효한 계정이 아닙니다.')
    return account


def _require_roles(account: Dict[str, Any], allowed_roles: set[str]) -> None:
    if account.get('role') not in allowed_roles:
        raise PermissionError('권한이 없습니다.')


def _load_material_requests() -> List[Dict[str, Any]]:
    payload = _load_json_or_default(MATERIAL_REQUESTS_KEY, {'rows': []})
    rows = payload.get('rows') if isinstance(payload, dict) else payload
    return rows if isinstance(rows, list) else []


def _save_material_requests(rows: List[Dict[str, Any]]) -> None:
    _put_json(MATERIAL_REQUESTS_KEY, {
        'rows': rows,
        'meta': {
            'updatedAt': _utcnow().isoformat(),
            'rowCount': len(rows)
        }
    })


def _load_materials_payload() -> Dict[str, Any]:
    payload = _load_json_or_default(MATERIALS_KEY, {'rows': [], 'meta': {}})
    if isinstance(payload, list):
        return {'rows': payload, 'meta': {}}
    if not isinstance(payload, dict):
        return {'rows': [], 'meta': {}}
    payload.setdefault('rows', [])
    payload.setdefault('meta', {})
    return payload


def _save_materials_payload(payload: Dict[str, Any]) -> None:
    payload = dict(payload)
    payload['meta'] = {
        **(payload.get('meta') or {}),
        'updatedAt': _utcnow().isoformat(),
        'rowCount': len(payload.get('rows') or [])
    }
    _put_json(MATERIALS_KEY, payload)


def _normalize_request_type(value: str) -> str:
    text = str(value or '').strip().upper()
    if text in {'CREATE', 'UPDATE', 'DELETE'}:
        return text
    raise ValueError('request_type은 CREATE/UPDATE/DELETE 중 하나여야 합니다.')


def _handle_login(event: Dict[str, Any]) -> Dict[str, Any]:
    body = _parse_json_body(event)
    login_id = str(body.get('login_id') or body.get('loginId') or '').strip()
    password = str(body.get('password') or '')
    if not login_id or not password:
        return _response(400, {'message': 'login_id와 password가 필요합니다.'})

    accounts = _load_accounts()
    account = next((a for a in accounts if a.get('login_id') == login_id and a.get('active', True)), None)
    if not account or not _verify_password(str(account.get('password', '')), password):
        return _response(401, {'message': '아이디 또는 비밀번호가 올바르지 않습니다.'})

    now = _utcnow()
    claims = {
        'sub': account['account_id'],
        'login_id': account['login_id'],
        'role': account['role'],
        'team_id': account.get('team_id'),
        'team_name': account.get('team_name'),
        'name': account.get('name'),
        'iat': int(now.timestamp()),
        'exp': int((now + timedelta(hours=TOKEN_EXPIRES_HOURS)).timestamp())
    }
    token = _sign_token(claims)
    return _response(200, {'token': token, 'user': _public_account(account)})


def _handle_change_password(event: Dict[str, Any]) -> Dict[str, Any]:
    user = _require_auth(event)
    body = _parse_json_body(event)
    current_pw = str(body.get('current_password') or body.get('currentPassword') or '')
    new_pw = str(body.get('new_password') or body.get('newPassword') or '')
    if not current_pw or not new_pw:
        return _response(400, {'message': 'current_password와 new_password가 필요합니다.'})
    if len(new_pw) < 4:
        return _response(400, {'message': '새 비밀번호는 4자 이상이어야 합니다.'})

    accounts = _load_accounts()
    idx = next((i for i, a in enumerate(accounts) if a.get('account_id') == user.get('account_id')), -1)
    if idx < 0:
        return _response(404, {'message': '계정을 찾을 수 없습니다.'})
    if not _verify_password(str(accounts[idx].get('password', '')), current_pw):
        return _response(401, {'message': '현재 비밀번호가 올바르지 않습니다.'})
    accounts[idx] = {**accounts[idx], 'password': _hash_password(new_pw)}
    _save_accounts(accounts)
    return _response(200, {'ok': True})


def _handle_admin_create_account(event: Dict[str, Any]) -> Dict[str, Any]:
    user = _require_auth(event)
    _require_roles(user, {'ADMIN'})
    body = _parse_json_body(event)
    login_id = str(body.get('login_id') or body.get('loginId') or '').strip()
    password = str(body.get('password') or '')
    name = str(body.get('name') or '').strip()
    team_id = str(body.get('team_id') or body.get('teamId') or '').strip()
    team_name = str(body.get('team_name') or body.get('teamName') or team_id).strip()
    role = str(body.get('role') or '').strip().upper()
    if role not in {'TEAM_ADMIN', 'TEAM_MEMBER'}:
        return _response(400, {'message': 'role은 TEAM_ADMIN 또는 TEAM_MEMBER만 가능합니다.'})
    if not all([login_id, password, name, team_id]):
        return _response(400, {'message': 'login_id, password, name, team_id는 필수입니다.'})

    accounts = _load_accounts()
    if any(a.get('login_id') == login_id for a in accounts):
        return _response(409, {'message': '이미 존재하는 로그인 ID입니다.'})

    new_account = {
        'account_id': f'acc-{uuid4().hex[:10]}',
        'login_id': login_id,
        'password': _hash_password(password),
        'name': name,
        'team_id': team_id,
        'team_name': team_name,
        'role': role,
        'active': True,
        'created_at': _utcnow().isoformat(),
    }
    accounts.append(new_account)
    _save_accounts(accounts)
    return _response(201, {'account': _public_account(new_account)})


def _handle_admin_list_accounts(event: Dict[str, Any]) -> Dict[str, Any]:
    user = _require_auth(event)
    _require_roles(user, {'ADMIN'})
    accounts = _load_accounts()
    return _response(200, {'rows': [_public_account(a) for a in accounts], 'meta': {'rowCount': len(accounts)}})


def _handle_admin_delete_account(event: Dict[str, Any]) -> Dict[str, Any]:
    user = _require_auth(event)
    _require_roles(user, {'ADMIN'})
    path_params = event.get('pathParameters') or {}
    account_id = str(path_params.get('accountId') or '').strip()
    if not account_id:
        return _response(400, {'message': 'accountId path parameter가 필요합니다.'})
    accounts = _load_accounts()
    idx = next((i for i, a in enumerate(accounts) if a.get('account_id') == account_id), -1)
    if idx < 0:
        return _response(404, {'message': '계정을 찾을 수 없습니다.'})
    if accounts[idx].get('role') == 'ADMIN':
        return _response(400, {'message': '관리자 계정은 삭제할 수 없습니다.'})
    deleted = accounts.pop(idx)
    _save_accounts(accounts)
    return _response(200, {'deleted': _public_account(deleted)})


def _handle_admin_reset_password(event: Dict[str, Any]) -> Dict[str, Any]:
    user = _require_auth(event)
    _require_roles(user, {'ADMIN'})
    path_params = event.get('pathParameters') or {}
    account_id = str(path_params.get('accountId') or '').strip()
    if not account_id:
        return _response(400, {'message': 'accountId path parameter가 필요합니다.'})
    accounts = _load_accounts()
    idx = next((i for i, a in enumerate(accounts) if a.get('account_id') == account_id), -1)
    if idx < 0:
        return _response(404, {'message': '계정을 찾을 수 없습니다.'})
    if accounts[idx].get('role') == 'ADMIN':
        return _response(400, {'message': '관리자 계정 비밀번호 초기화는 지원하지 않습니다.'})
    accounts[idx] = {**accounts[idx], 'password': _hash_password(DEFAULT_RESET_PASSWORD)}
    _save_accounts(accounts)
    return _response(200, {'ok': True, 'resetPassword': DEFAULT_RESET_PASSWORD})


def _normalize_material_request_payload(body: Dict[str, Any]) -> Dict[str, Any]:
    request_type = _normalize_request_type(body.get('request_type') or body.get('requestType'))
    payload = body.get('payload')
    if not isinstance(payload, dict):
        payload = {
            'raw_cd': body.get('raw_cd') or body.get('rawCd'),
            'raw_nm': body.get('raw_nm') or body.get('rawNm'),
            'mmsta': body.get('mmsta', ''),
            'researcher': body.get('researcher', ''),
            'created': body.get('created', ''),
            'approval_status': body.get('approval_status', ''),
        }
    return {'request_type': request_type, 'payload': payload}


def _handle_material_requests_create(event: Dict[str, Any]) -> Dict[str, Any]:
    user = _require_auth(event)
    body = _parse_json_body(event)
    normalized = _normalize_material_request_payload(body)

    req = {
        'request_id': f'req-{uuid4().hex[:12]}',
        'request_type': normalized['request_type'],
        'request_status': 'PENDING',
        'team_id': user.get('team_id'),
        'requested_by_account_id': user.get('account_id'),
        'requested_by_name': user.get('name'),
        'payload': normalized['payload'],
        'approved_by_account_id': None,
        'approved_by_name': None,
        'approved_at': None,
        'created_at': _utcnow().isoformat(),
    }
    rows = _load_material_requests()
    rows.insert(0, req)
    _save_material_requests(rows)
    return _response(201, {'request': req})


def _handle_material_requests_list(event: Dict[str, Any]) -> Dict[str, Any]:
    user = _require_auth(event)
    _require_roles(user, {'TEAM_ADMIN', 'ADMIN'})
    rows = _load_material_requests()
    if user.get('role') == 'TEAM_ADMIN':
        rows = [r for r in rows if str(r.get('team_id')) == str(user.get('team_id'))]
    return _response(200, {'rows': rows, 'meta': {'rowCount': len(rows)}})


def _apply_request_to_materials(materials_rows: List[Dict[str, Any]], request_row: Dict[str, Any]) -> List[Dict[str, Any]]:
    payload = request_row.get('payload') or {}
    req_type = request_row.get('request_type')
    raw_cd = str(payload.get('raw_cd') or '').strip()
    rows = [dict(r) for r in materials_rows]

    if req_type == 'CREATE':
        new_row = {
            'raw_cd': raw_cd,
            'raw_nm': payload.get('raw_nm', ''),
            'mmsta': payload.get('mmsta', ''),
            'researcher': payload.get('researcher', request_row.get('requested_by_name', '')),
            'created': payload.get('created') or _utcnow().date().isoformat(),
            'approval_status': '완료',
        }
        rows = [r for r in rows if str(r.get('raw_cd', '')).strip() != raw_cd]
        rows.insert(0, new_row)
        return rows

    idx = next((i for i, r in enumerate(rows) if str(r.get('raw_cd', '')).strip() == raw_cd), -1)
    if idx < 0:
        if req_type == 'DELETE':
            return rows
        rows.insert(0, {
            'raw_cd': raw_cd,
            'raw_nm': payload.get('raw_nm', ''),
            'mmsta': payload.get('mmsta', ''),
            'researcher': payload.get('researcher', request_row.get('requested_by_name', '')),
            'created': payload.get('created') or _utcnow().date().isoformat(),
            'approval_status': '완료',
        })
        return rows

    if req_type == 'DELETE':
        rows.pop(idx)
        return rows

    if req_type == 'UPDATE':
        rows[idx] = {
            **rows[idx],
            **{k: v for k, v in payload.items() if v is not None},
            'approval_status': '완료'
        }
        return rows

    return rows


def _handle_material_requests_approve(event: Dict[str, Any]) -> Dict[str, Any]:
    user = _require_auth(event)
    _require_roles(user, {'TEAM_ADMIN', 'ADMIN'})
    path_params = event.get('pathParameters') or {}
    request_id = str(path_params.get('requestId') or '').strip()
    if not request_id:
        return _response(400, {'message': 'requestId path parameter가 필요합니다.'})

    req_rows = _load_material_requests()
    idx = next((i for i, r in enumerate(req_rows) if r.get('request_id') == request_id), -1)
    if idx < 0:
        return _response(404, {'message': '요청을 찾을 수 없습니다.'})
    req = req_rows[idx]
    if req.get('request_status') != 'PENDING':
        return _response(400, {'message': '이미 처리된 요청입니다.'})
    if user.get('role') == 'TEAM_ADMIN' and str(req.get('team_id')) != str(user.get('team_id')):
        return _response(403, {'message': '본인 팀 요청만 승인할 수 있습니다.'})

    materials_payload = _load_materials_payload()
    updated_rows = _apply_request_to_materials(materials_payload.get('rows') or [], req)
    materials_payload['rows'] = updated_rows
    _save_materials_payload(materials_payload)

    req_rows[idx] = {
        **req_rows[idx],
        'request_status': 'APPROVED',
        'approved_by_account_id': user.get('account_id'),
        'approved_by_name': user.get('name'),
        'approved_at': _utcnow().isoformat()
    }
    _save_material_requests(req_rows)
    return _response(200, {'request': req_rows[idx]})


def lambda_handler(event: Dict[str, Any], _context: Any) -> Dict[str, Any]:
    method = (event.get('requestContext', {}).get('http', {}) or {}).get('method') or event.get('httpMethod', 'GET')
    if method == 'OPTIONS':
        return _response(200, {'ok': True})

    try:
        path = _route(event)

        if (path.endswith('/auth/login') or path == '/auth/login') and method == 'POST':
            return _handle_login(event)

        if (path.endswith('/auth/change-password') or path == '/auth/change-password') and method == 'POST':
            return _handle_change_password(event)

        if (path.endswith('/admin/accounts') or path == '/admin/accounts') and method == 'GET':
            return _handle_admin_list_accounts(event)

        if (path.endswith('/admin/accounts') or path == '/admin/accounts') and method == 'POST':
            return _handle_admin_create_account(event)

        if '/admin/accounts/' in path and path.endswith('/reset-password') and method == 'POST':
            return _handle_admin_reset_password(event)

        if '/admin/accounts/' in path and method == 'DELETE':
            return _handle_admin_delete_account(event)

        if (path.endswith('/materials/requests') or path == '/materials/requests') and method == 'GET':
            return _handle_material_requests_list(event)

        if (path.endswith('/materials/requests') or path == '/materials/requests') and method == 'POST':
            return _handle_material_requests_create(event)

        if '/materials/requests/' in path and path.endswith('/approve') and method == 'POST':
            return _handle_material_requests_approve(event)

        return _response(404, {'message': f'Unknown path/method: {method} {path}'})
    except PermissionError as exc:
        return _response(403, {'message': str(exc)})
    except ValueError as exc:
        return _response(400, {'message': str(exc)})
    except Exception as exc:
        return _response(500, {'message': str(exc)})
