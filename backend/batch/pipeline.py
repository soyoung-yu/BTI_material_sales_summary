import json
import logging
import os
from io import BytesIO
from urllib.parse import urlparse
from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
from typing import Any, Dict, List, Tuple

import boto3
import pandas as pd

from backend.batch.queries import build_bom_query, build_revenue_query
from backend.batch.transformers import (
    build_closure_for_targets,
    build_parent_map,
    make_child_qty_key,
    normalize_product_name,
)

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


@dataclass
class BatchConfig:
    comp_id: str
    customer_comp_id: str
    athena_database: str
    material_source_mode: str
    material_list_s3_path: str
    materials_latest_key: str
    start_date: str
    end_date: str
    include_net_sales: bool


def _utc_today() -> date:
    return datetime.now(timezone.utc).date()


def _to_date(value: Any) -> date:
    if isinstance(value, date) and not isinstance(value, datetime):
        return value
    if isinstance(value, datetime):
        return value.date()
    return datetime.strptime(str(value), '%Y-%m-%d').date()


def _resolve_date_range(event: Dict[str, Any]) -> Tuple[str, str]:
    start_date = event.get('startDate') or os.environ.get('REPORT_START_DATE')
    end_date = event.get('endDate') or os.environ.get('REPORT_END_DATE')

    if start_date and end_date:
        return _to_date(start_date).isoformat(), _to_date(end_date).isoformat()

    if start_date and not end_date:
        end = _utc_today() - timedelta(days=1)
        return _to_date(start_date).isoformat(), end.isoformat()

    lookback_months = int(os.environ.get('BATCH_LOOKBACK_MONTHS', '24'))
    today = _utc_today()
    end = today
    start = end - timedelta(days=lookback_months * 31)
    start = start.replace(day=1)
    return start.isoformat(), end.isoformat()


def load_config(event: Dict[str, Any]) -> BatchConfig:
    start_date, end_date = _resolve_date_range(event)
    source_mode = str(
        event.get('materialSourceMode')
        or os.environ.get('MATERIAL_SOURCE_MODE', 's3_materials_latest')
    ).strip() or 's3_materials_latest'
    material_path = str(event.get('materialListS3Path') or os.environ.get('MATERIAL_LIST_S3_PATH', '')).strip()
    materials_latest_key = str(
        event.get('materialsLatestKey') or os.environ.get('BTI_MATERIALS_LATEST_KEY', 'materials/latest.json')
    ).strip() or 'materials/latest.json'

    if source_mode in {'excel_legacy', 'excel_refresh_materials'} and not material_path:
        raise ValueError('MATERIAL_LIST_S3_PATH 환경변수 또는 event.materialListS3Path가 필요합니다.')
    if source_mode not in {'excel_legacy', 'excel_refresh_materials'}:
        data_bucket = str(os.environ.get('BTI_DATA_BUCKET', '')).strip()
        if not data_bucket:
            raise ValueError('BTI_DATA_BUCKET 환경변수가 설정되지 않았습니다.')
        if not materials_latest_key:
            raise ValueError('BTI_MATERIALS_LATEST_KEY 환경변수가 설정되지 않았습니다.')

    return BatchConfig(
        comp_id=str(event.get('compId') or os.environ.get('COMP_ID', '1200')),
        customer_comp_id=str(event.get('customerCompId') or os.environ.get('CUSTOMER_COMP_ID', os.environ.get('COMP_ID', '1200'))),
        athena_database=str(event.get('athenaDatabase') or os.environ.get('ATHENA_DATABASE', 'data_mart')),
        material_source_mode=source_mode,
        material_list_s3_path=material_path,
        materials_latest_key=materials_latest_key,
        start_date=start_date,
        end_date=end_date,
        include_net_sales=str(event.get('includeNetSales', os.environ.get('INCLUDE_NET_SALES', 'false'))).lower() == 'true',
    )


def query_athena(query: str, database: str) -> pd.DataFrame:
    try:
        import awswrangler as wr
    except Exception as exc:  # pragma: no cover - import path depends on runtime packaging
        raise RuntimeError('awswrangler가 설치되어 있지 않습니다. Lambda Layer/컨테이너에 포함하세요.') from exc

    logger.info('Athena query start (database=%s)', database)
    df = wr.athena.read_sql_query(query, database=database)
    logger.info('Athena query done (rows=%s)', len(df))
    return df


def read_materials_excel(s3_path: str) -> pd.DataFrame:
    logger.info('Load materials excel from %s', s3_path)
    parsed = urlparse(s3_path)
    if parsed.scheme != 's3' or not parsed.netloc or not parsed.path:
        raise ValueError(f'유효한 S3 경로가 아닙니다: {s3_path}')

    s3 = boto3.client('s3')
    obj = s3.get_object(Bucket=parsed.netloc, Key=parsed.path.lstrip('/'))
    df = pd.read_excel(BytesIO(obj['Body'].read()), engine='openpyxl')
    if 'raw_cd' not in df.columns or 'team_id' not in df.columns:
        # 운영 엑셀 컬럼명 대응 (원료코드/원료명 등)
        rename_map = {}
        for col in df.columns:
            key = str(col).strip().lower()
            if key in {'team_id', 'team id', '팀id', '팀코드'}:
                rename_map[col] = 'team_id'
            elif key in {'comp_id', 'compid', 'comp id', '법인코드'}:
                rename_map[col] = 'comp_id'
            if key in {'원료코드', 'raw_cd', 'raw code'} or key == '원료코드'.lower():
                rename_map[col] = 'raw_cd'
            elif key in {'원료명', 'raw_nm', 'raw name'} or key == '원료명'.lower():
                rename_map[col] = 'raw_nm'
            elif key in {'raw_user_id', '담당자사번'}:
                rename_map[col] = 'raw_user_id'
            elif key in {'raw_user_nm', '담당자이름'}:
                rename_map[col] = 'raw_user_nm'
            elif key in {'담당자이름', 'researcher'}:
                rename_map[col] = 'researcher'
            elif key in {'상태', 'approval_status'}:
                rename_map[col] = 'approval_status'
            elif key in {'등록일', 'created'}:
                rename_map[col] = 'created'
            elif key in {'mmsta'}:
                rename_map[col] = 'mmsta'
        if rename_map:
            df = df.rename(columns=rename_map)

    required_cols = ['team_id', 'raw_cd', 'raw_nm']
    missing = [c for c in required_cols if c not in df.columns]
    if missing:
        raise ValueError(f"소재 엑셀에 필수 컬럼이 필요합니다: {', '.join(missing)}")

    for col in ['team_id', 'comp_id', 'raw_cd', 'raw_nm', 'mmsta', 'raw_user_id', 'raw_user_nm', 'researcher']:
        if col not in df.columns:
            df[col] = ''
        df[col] = df[col].astype(str).str.strip()
    return df


def read_materials_latest_json(bucket: str, key: str) -> pd.DataFrame:
    logger.info('Load materials master from s3://%s/%s', bucket, key)
    s3 = boto3.client('s3')
    obj = s3.get_object(Bucket=bucket, Key=key)
    payload = json.loads(obj['Body'].read())
    rows = payload.get('rows') if isinstance(payload, dict) else payload
    if not isinstance(rows, list):
        rows = []
    df = pd.DataFrame([r for r in rows if isinstance(r, dict)])
    if df.empty:
        return pd.DataFrame(columns=[
            'raw_cd', 'raw_nm', 'mmsta', 'researcher', 'created', 'approval_status',
            'team_id', 'team_name', 'comp_id', 'raw_user_id', 'raw_user_nm'
        ])
    return df


def prepare_materials_payload(materials_df: pd.DataFrame) -> pd.DataFrame:
    df = materials_df.copy()
    today = _utc_today().isoformat()

    if 'raw_nm' not in df.columns:
        df['raw_nm'] = ''
    if 'researcher' not in df.columns:
        df['researcher'] = ''
    if 'approval_status' not in df.columns:
        df['approval_status'] = '완료'
    if 'created' not in df.columns:
        df['created'] = today
    if 'mmsta' not in df.columns:
        df['mmsta'] = ''
    if 'comp_id' not in df.columns:
        df['comp_id'] = str(os.environ.get('COMP_ID', '1200'))
    if 'raw_user_id' not in df.columns:
        df['raw_user_id'] = ''
    if 'raw_user_nm' not in df.columns:
        if 'researcher' in df.columns:
            df['raw_user_nm'] = df['researcher']
        else:
            df['raw_user_nm'] = ''
    if 'team_id' not in df.columns:
        df['team_id'] = os.environ.get('BTI_LEGACY_DEFAULT_TEAM_ID', 'MB2')
    if 'team_name' not in df.columns:
        legacy_team_id = str(os.environ.get('BTI_LEGACY_DEFAULT_TEAM_ID', 'MB2')).strip() or 'MB2'
        legacy_team_name = str(os.environ.get('BTI_LEGACY_DEFAULT_TEAM_NAME', f'{legacy_team_id}팀')).strip() or f'{legacy_team_id}팀'
        df['team_name'] = legacy_team_name

    cols = [
        'raw_cd', 'raw_nm', 'mmsta', 'researcher', 'created', 'approval_status',
        'team_id', 'team_name', 'comp_id', 'raw_user_id', 'raw_user_nm'
    ]
    df = df[cols].copy()
    df = df.drop_duplicates(subset=['raw_cd']).sort_values(['raw_cd']).reset_index(drop=True)
    df['created'] = pd.to_datetime(df['created'], errors='coerce').dt.strftime('%Y-%m-%d').fillna(today)
    df['team_id'] = df['team_id'].astype(str).str.strip().replace({'': os.environ.get('BTI_LEGACY_DEFAULT_TEAM_ID', 'MB2')})
    df['team_name'] = df['team_name'].astype(str).str.strip()
    df['comp_id'] = df['comp_id'].astype(str).str.strip().replace({'': str(os.environ.get('COMP_ID', '1200'))})
    df['raw_user_id'] = df['raw_user_id'].astype(str).str.strip()
    df['raw_user_nm'] = df['raw_user_nm'].astype(str).str.strip()
    missing_raw_user_nm = df['raw_user_nm'].eq('')
    if missing_raw_user_nm.any():
        df.loc[missing_raw_user_nm, 'raw_user_nm'] = df.loc[missing_raw_user_nm, 'researcher'].astype(str).str.strip()
    missing_researcher = df['researcher'].astype(str).str.strip().eq('')
    if missing_researcher.any():
        df.loc[missing_researcher, 'researcher'] = df.loc[missing_researcher, 'raw_user_nm']
    missing_team_name = df['team_name'].eq('')
    if missing_team_name.any():
        df.loc[missing_team_name, 'team_name'] = df.loc[missing_team_name, 'team_id'].apply(lambda v: f'{v}팀' if str(v) != 'HQ' else '관리자')
    return df


def fetch_bom_edges(cfg: BatchConfig) -> pd.DataFrame:
    df = query_athena(build_bom_query(cfg.comp_id), database=cfg.athena_database)
    if 'spqty' in df.columns:
        df = df[df['spqty'] != 0].copy()
    return df


def fetch_revenue(cfg: BatchConfig) -> pd.DataFrame:
    df = query_athena(
        build_revenue_query(cfg.comp_id, cfg.start_date, cfg.end_date, customer_comp_id=cfg.customer_comp_id),
        database=cfg.athena_database,
    )
    numeric_cols = ['sales_quantity', 'total_revenue', 'product_sales_revenue', 'net_revenue']
    for col in numeric_cols:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce')
    if 'product_sales_revenue' in df.columns:
        df = df[df['product_sales_revenue'].fillna(0) != 0].copy()
    return df


def build_revenue_grouped(closure_df: pd.DataFrame, revenue_df: pd.DataFrame) -> pd.DataFrame:
    closure_tmp = closure_df.copy()
    closure_tmp['ancestor_code'] = closure_tmp['ancestor_code'].astype(str).str.strip()
    closure_tmp['child_code'] = closure_tmp['child_code'].astype(str).str.strip()

    closure_uc = (
        closure_tmp.groupby(['ancestor_code', 'child_code'], as_index=False)['child_spqty']
        .sum()
    )
    closure_sorted = closure_uc.sort_values(['ancestor_code', 'child_code'])
    child_code_map = closure_sorted.groupby('ancestor_code')['child_code'].apply(list)
    child_spqty_map = closure_sorted.groupby('ancestor_code')['child_spqty'].apply(list)

    rev = revenue_df.copy()
    rev['mitem_code'] = rev['mitem_code'].astype(str).str.strip()
    rev_filtered = rev[rev['mitem_code'].isin(child_code_map.index)].copy()
    rev_filtered['child_code_list'] = rev_filtered['mitem_code'].map(child_code_map)
    rev_filtered['child_spqty_list'] = rev_filtered['mitem_code'].map(child_spqty_map)

    sum_cols = [c for c in ['sales_quantity', 'total_revenue', 'product_sales_revenue', 'net_revenue'] if c in rev_filtered.columns]
    tmp = rev_filtered.copy()
    tmp['child_qty_key'] = tmp.apply(
        lambda r: make_child_qty_key(r['child_code_list'], r['child_spqty_list'], ndigits=10),
        axis=1,
    )

    for col in sum_cols:
        tmp[col] = pd.to_numeric(tmp[col], errors='coerce')
    if sum_cols:
        tmp[sum_cols] = tmp[sum_cols].fillna(0)

    group_cols = [
        'mitem_code', 'mitem_name', 'customer_code', 'customer_name',
        'currency', 'category', 'unit', 'forml_code', 'forml_name', 'base_time', 'child_qty_key'
    ]
    group_cols = [c for c in group_cols if c in tmp.columns]

    grouped = tmp.groupby(group_cols, as_index=False)[sum_cols].sum()
    for col in [c for c in ['total_revenue', 'product_sales_revenue', 'net_revenue', 'sales_quantity'] if c in grouped.columns]:
        grouped[col] = grouped[col].round(2)
    return grouped


def build_base_raw_sales_df(rev_grouped: pd.DataFrame, materials_df: pd.DataFrame, include_net_sales: bool = False) -> pd.DataFrame:
    materials_uniq = materials_df.drop_duplicates(subset=['raw_cd']).copy()

    rows: List[Dict[str, Any]] = []
    for _, record in rev_grouped.iterrows():
        raw_list = record.get('child_qty_key')
        if raw_list is None or (isinstance(raw_list, float) and pd.isna(raw_list)):
            continue
        for raw_cd, ratio in raw_list:
            row = {
                'raw_cd': raw_cd,
                'raw_ratio': ratio,
                'mitem_code': record.get('mitem_code'),
                'mitem_name': record.get('mitem_name'),
                'customer_code': record.get('customer_code'),
                'customer_name': record.get('customer_name'),
                'category': record.get('category'),
                'forml_code': record.get('forml_code'),
                'forml_name': record.get('forml_name'),
                'base_time': record.get('base_time'),
                'total_revenue': record.get('total_revenue', 0),
                'product_sales_revenue': record.get('product_sales_revenue', 0),
                'net_revenue': record.get('net_revenue', 0),
            }
            if include_net_sales:
                # 현재 전처리 결과에 net_sales 원천이 없으므로 0으로 둠 (추후 추가 예정)
                row['net_sales'] = 0
            rows.append(row)

    base_df = pd.DataFrame(rows)
    if base_df.empty:
        expected_cols = [
            'raw_cd', 'raw_nm', 'raw_ratio', 'mitem_code', 'mitem_name', 'category', 'forml_code', 'forml_name',
            'customer_code', 'customer_name', 'base_time', 'total_revenue', 'product_sales_revenue', 'net_revenue', 'product_name'
        ]
        if include_net_sales:
            expected_cols.insert(expected_cols.index('net_revenue'), 'net_sales')
        return pd.DataFrame(columns=expected_cols)

    base_df = (
        base_df.merge(materials_uniq, on='raw_cd', how='left')
        .sort_values(['raw_cd', 'mitem_code', 'base_time'], ascending=[True, True, True])
        .reset_index(drop=True)
    )

    if 'raw_nm' not in base_df.columns:
        base_df['raw_nm'] = ''

    base_df['product_name'] = base_df['mitem_name'].apply(normalize_product_name)
    base_df['base_time'] = pd.to_datetime(base_df['base_time'], errors='coerce').dt.strftime('%Y-%m-%d')

    ordered_cols = [
        'raw_cd', 'raw_nm', 'raw_ratio', 'mitem_code', 'mitem_name', 'category', 'forml_code', 'forml_name',
        'customer_code', 'customer_name', 'base_time', 'total_revenue', 'product_sales_revenue'
    ]
    if include_net_sales:
        ordered_cols.append('net_sales')
    ordered_cols.extend(['net_revenue', 'product_name'])

    for col in ordered_cols:
        if col not in base_df.columns:
            base_df[col] = None

    return base_df[ordered_cols].copy()


def _json_safe_records(df: pd.DataFrame) -> List[Dict[str, Any]]:
    if df.empty:
        return []

    tmp = df.copy()
    for col in tmp.columns:
        if pd.api.types.is_datetime64_any_dtype(tmp[col]):
            tmp[col] = tmp[col].dt.strftime('%Y-%m-%d')

    tmp = tmp.where(pd.notna(tmp), None)
    records = tmp.to_dict(orient='records')
    return json.loads(json.dumps(records, ensure_ascii=False, default=str))


def run_batch_pipeline(event: Dict[str, Any]) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]], Dict[str, Any]]:
    cfg = load_config(event)
    logger.info('Batch config: %s', cfg)

    source_mode = cfg.material_source_mode
    uses_excel_refresh = source_mode in {'excel_legacy', 'excel_refresh_materials'}

    if uses_excel_refresh:
        materials_src_df = read_materials_excel(cfg.material_list_s3_path)
    else:
        data_bucket = str(os.environ.get('BTI_DATA_BUCKET', '')).strip()
        materials_src_df = read_materials_latest_json(data_bucket, cfg.materials_latest_key)
    materials_payload_df = prepare_materials_payload(materials_src_df)

    bom_edges_df = fetch_bom_edges(cfg)
    parent_map = build_parent_map(bom_edges_df)
    target_codes = materials_payload_df['raw_cd'].astype(str).tolist()
    closure_df = build_closure_for_targets(target_codes, parent_map)

    revenue_df = fetch_revenue(cfg)
    rev_grouped_df = build_revenue_grouped(closure_df, revenue_df)
    report_df = build_base_raw_sales_df(rev_grouped_df, materials_payload_df, include_net_sales=cfg.include_net_sales)

    report_rows = _json_safe_records(report_df)
    material_rows = _json_safe_records(materials_payload_df)
    meta = {
        'source': {
            'compId': cfg.comp_id,
            'customerCompId': cfg.customer_comp_id,
            'athenaDatabase': cfg.athena_database,
            'materialSourceMode': cfg.material_source_mode,
            'materialSourceModeEffective': 'excel_refresh_materials' if uses_excel_refresh else 's3_materials_latest',
            'materialsRefreshedFromExcel': uses_excel_refresh,
            'materialListS3Path': cfg.material_list_s3_path,
            'materialsLatestKey': cfg.materials_latest_key,
            'startDate': cfg.start_date,
            'endDate': cfg.end_date,
            'includeNetSales': cfg.include_net_sales,
        },
        'counts': {
            'materials': len(material_rows),
            'bomEdges': int(len(bom_edges_df)),
            'closureRows': int(len(closure_df)),
            'revenueRows': int(len(revenue_df)),
            'reportRows': len(report_rows),
        }
    }
    return report_rows, material_rows, meta
