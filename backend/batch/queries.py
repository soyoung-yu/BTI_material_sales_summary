from typing import Optional


def build_bom_query(comp_id: str) -> str:
    return f"""
SELECT DISTINCT
  CAST(spcomp AS varchar) AS child_code,
  CAST(mitem  AS varchar) AS parent_code,
  spqty
FROM cai.t_rd_bom
WHERE 1=1
  AND compid='{comp_id}'
  AND spcomp IS NOT NULL
  AND mitem  IS NOT NULL
""".strip()


def build_revenue_query(comp_id: str, start_date: str, end_date: str, customer_comp_id: Optional[str] = None) -> str:
    customer_comp_id = customer_comp_id or comp_id
    return f"""
SELECT
     a.mitem_code
    ,a.mitem_name
    ,b.customer_code
    ,b.customer_name
    ,a.sales_quantity
    ,a.total_revenue
    ,a.product_sales_revenue
    ,a.net_revenue
    ,a.currency
    ,a.category
    ,a.unit
    ,a.forml_code
    ,a.forml_name
    ,a.base_time
FROM data_mart.t_dmart_gcc_monthly_sales_revenue a
LEFT JOIN data_mart.t_dmart_master_customer b
       ON a.customer_code = b.customer_code
WHERE 1=1
  AND a.comp_id = '{comp_id}'
  AND a.base_time BETWEEN DATE '{start_date}' AND DATE '{end_date}'
  AND b.comp_id = '{customer_comp_id}'
  AND a.mitem_code LIKE '9%'
""".strip()
