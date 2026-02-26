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
TEAM_REPORT_PREFIX = os.environ.get('BTI_TEAM_REPORT_PREFIX', f'{REPORT_PREFIX}/teams')
LEGACY_DEFAULT_TEAM_ID = os.environ.get('BTI_LEGACY_DEFAULT_TEAM_ID', 'MB2')


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


def _extract_team_id(item: Dict[str, Any]) -> str:
    return str(item.get('team_id') or LEGACY_DEFAULT_TEAM_ID).strip() or LEGACY_DEFAULT_TEAM_ID


def _build_raw_team_map(material_rows: Any) -> dict[str, str]:
    team_map: dict[str, str] = {}
    for row in material_rows or []:
        if not isinstance(row, dict):
            continue
        raw_cd = str(row.get('raw_cd') or '').strip()
        if not raw_cd:
            continue
        team_map[raw_cd] = _extract_team_id(row)
    return team_map


def _split_report_rows_by_team(report_rows: Any, material_rows: Any) -> dict[str, list[dict[str, Any]]]:
    raw_team_map = _build_raw_team_map(material_rows)
    grouped: dict[str, list[dict[str, Any]]] = {}
    for row in report_rows or []:
        if not isinstance(row, dict):
            continue
        raw_cd = str(row.get('raw_cd') or '').strip()
        team_id = raw_team_map.get(raw_cd, LEGACY_DEFAULT_TEAM_ID)
        grouped.setdefault(team_id, []).append(row)
    return grouped


def lambda_handler(event: Dict[str, Any], _context: Any) -> Dict[str, Any]:
    if not DATA_BUCKET:
        raise RuntimeError('BTI_DATA_BUCKET 환경변수가 설정되지 않았습니다.')

    batch_id = _batch_id()
    started_at = datetime.now(timezone.utc).isoformat()

    try:
        report_rows, material_rows, pipeline_meta = run_batch_pipeline(event or {})
        source_meta = (pipeline_meta or {}).get('source') or {}
        source_mode = str(source_meta.get('materialSourceModeEffective') or source_meta.get('materialSourceMode') or '')
        materials_refreshed_from_excel = bool(source_meta.get('materialsRefreshedFromExcel')) or source_mode == 'excel_refresh_materials'
        team_report_rows = _split_report_rows_by_team(report_rows, material_rows)
        team_report_row_counts = {team_id: len(rows) for team_id, rows in team_report_rows.items()}

        report_payload = {
            'rows': report_rows,
            'meta': {
                'batchId': batch_id,
                'generatedAt': started_at,
                'status': 'success',
                'rowCount': len(report_rows)
            }
        }
        meta_payload = {
            'status': 'success',
            'batchId': batch_id,
            'lastSuccessAt': started_at,
            'reportRowCount': len(report_rows),
            'materialsRowCount': len(material_rows),
            'availableYears': _extract_available_years(report_rows),
            'availableTeams': sorted(team_report_rows.keys()),
            'teamReportRowCounts': team_report_row_counts,
            'materialSource': source_mode or 'unknown',
            'materialsRefreshedFromExcel': materials_refreshed_from_excel,
            'materialsRefreshSourceKey': str(source_meta.get('materialListS3Path') or ''),
            'materialsRefreshRowCount': len(material_rows) if materials_refreshed_from_excel else 0,
            'pipeline': pipeline_meta,
        }

        if materials_refreshed_from_excel:
            materials_payload = {
                'rows': material_rows,
                'meta': {
                    'batchId': batch_id,
                    'generatedAt': started_at,
                    'status': 'success',
                    'rowCount': len(material_rows),
                    'refreshedFromExcel': True,
                    'sourceKey': str(source_meta.get('materialListS3Path') or ''),
                }
            }
            _put_json(f'{MATERIALS_PREFIX}/versions/{batch_id}.json', materials_payload)
            _put_json(f'{MATERIALS_PREFIX}/latest.json', materials_payload)

        _put_json(f'{REPORT_PREFIX}/versions/{batch_id}.json', report_payload)
        for team_id, rows in team_report_rows.items():
            team_payload = {
                'rows': rows,
                'meta': {
                    'batchId': batch_id,
                    'generatedAt': started_at,
                    'status': 'success',
                    'rowCount': len(rows),
                    'scopeTeamId': team_id,
                    'teamScopedPrecomputed': True,
                }
            }
            _put_json(f'{TEAM_REPORT_PREFIX}/{team_id}/versions/{batch_id}.json', team_payload)
        _put_json(f'{REPORT_PREFIX}/latest.json', report_payload)
        for team_id, rows in team_report_rows.items():
            team_payload = {
                'rows': rows,
                'meta': {
                    'batchId': batch_id,
                    'generatedAt': started_at,
                    'status': 'success',
                    'rowCount': len(rows),
                    'scopeTeamId': team_id,
                    'teamScopedPrecomputed': True,
                }
            }
            _put_json(f'{TEAM_REPORT_PREFIX}/{team_id}/latest.json', team_payload)
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
