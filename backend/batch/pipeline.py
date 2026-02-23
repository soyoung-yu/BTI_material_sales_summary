import json
import logging
import os
from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
from typing import Any, Dict, List, Tuple

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
    material_list_s3_path: str
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
        return str(start_date), str(end_date)

    lookback_months = int(os.environ.get('BATCH_LOOKBACK_MONTHS', '24'))
    today = _utc_today()
    end = today
    start = end - timedelta(days=lookback_months * 31)
    start = start.replace(day=1)
    return start.isoformat(), end.isoformat()


def load_config(event: Dict[str, Any]) -> BatchConfig:
    start_date, end_date = _resolve_date_range(event)
    material_path = event.get('materialListS3Path') or os.environ.get('MATERIAL_LIST_S3_PATH', '')
    if not material_path:
        raise ValueError('MATERIAL_LIST_S3_PATH 환경변수 또는 event.materialListS3Path가 필요합니다.')

    return BatchConfig(
        comp_id=str(event.get('compId') or os.environ.get('COMP_ID', '1200')),
        customer_comp_id=str(event.get('customerCompId') or os.environ.get('CUSTOMER_COMP_ID', os.environ.get('COMP_ID', '1200'))),
        athena_database=str(event.get('athenaDatabase') or os.environ.get('ATHENA_DATABASE', 'data_mart')),
        material_list_s3_path=material_path,
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
    df = pd.read_excel(s3_path, engine='openpyxl')
    if 'raw_cd' not in df.columns:
        # 운영 엑셀 컬럼명 대응 (원료코드/원료명 등)
        rename_map = {}
        for col in df.columns:
            key = str(col).strip().lower()
            if key in {'원료코드', 'raw_cd', 'raw code'} or key == '원료코드'.lower():
                rename_map[col] = 'raw_cd'
            elif key in {'원료명', 'raw_nm', 'raw name'} or key == '원료명'.lower():
                rename_map[col] = 'raw_nm'
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

    if 'raw_cd' not in df.columns:
        raise ValueError('소재 엑셀에 raw_cd(또는 원료코드) 컬럼이 필요합니다.')

    df['raw_cd'] = df['raw_cd'].astype(str).str.strip()
    if 'raw_nm' in df.columns:
        df['raw_nm'] = df['raw_nm'].astype(str).str.strip()
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

    cols = ['raw_cd', 'raw_nm', 'mmsta', 'researcher', 'created', 'approval_status']
    df = df[cols].copy()
    df = df.drop_duplicates(subset=['raw_cd']).sort_values(['raw_cd']).reset_index(drop=True)
    df['created'] = pd.to_datetime(df['created'], errors='coerce').dt.strftime('%Y-%m-%d').fillna(today)
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

    materials_src_df = read_materials_excel(cfg.material_list_s3_path)
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
            'materialListS3Path': cfg.material_list_s3_path,
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
