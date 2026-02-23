import re
from collections import defaultdict, deque
from typing import Dict, Iterable, List, Tuple

import pandas as pd


ALL_CLOSED_BRACKETS_ANYWHERE = re.compile(
    r"[\(\[\{（【［<][^)\]\}）】］>]*[\)\]\}）】］>]"
)
PATTERNS = [
    ALL_CLOSED_BRACKETS_ANYWHERE,
    re.compile(r"\s*#.+$"),
    re.compile(r"\s*\d+(?:\.\d+)?\s*(?:ml|l|g|mg)\b", re.I),
    re.compile(r"\s*\d+\s*\+\s*\d+\s*"),
    re.compile(r"(기획세트|기획|세트|더블|트리플|\d+\s*개입|\d+\s*개|\d+\s*매|\d+\s*입)$"),
]
SPACE_RE = re.compile(r"\s+")


def normalize_product_name(name: str):
    if pd.isna(name):
        return name

    s = str(name).strip()
    prev = None
    while prev != s:
        prev = s
        for pat in PATTERNS:
            s = pat.sub(" ", s).strip()
        s = SPACE_RE.sub(" ", s).strip()
    return re.sub(r"\s+", "", s)


def build_parent_map(bom_edges_df: pd.DataFrame) -> Dict[str, List[Tuple[str, float]]]:
    parent_map: Dict[str, List[Tuple[str, float]]] = defaultdict(list)
    for child, parent, qty in zip(
        bom_edges_df['child_code'].astype(str),
        bom_edges_df['parent_code'].astype(str),
        bom_edges_df['spqty'],
    ):
        parent_map[child].append((parent, qty))
    return parent_map


def build_closure_for_targets(target_codes: Iterable[str], parent_map, max_depth: int = 50) -> pd.DataFrame:
    rows = []
    for child in map(str, target_codes):
        queue = deque([(child, 0, None)])
        visited = {child}

        while queue:
            node, depth, spqty = queue.popleft()
            for parent, parent_spqty in parent_map.get(node, []):
                if parent in visited:
                    continue
                visited.add(parent)
                next_depth = depth + 1
                child_spqty = parent_spqty if depth == 0 else spqty
                rows.append((child, parent, next_depth, child_spqty))
                if next_depth < max_depth:
                    queue.append((parent, next_depth, child_spqty))

    return pd.DataFrame(rows, columns=['child_code', 'ancestor_code', 'depth', 'child_spqty'])


def make_child_qty_key(child_list, qty_list, ndigits: int = 10):
    if not (isinstance(child_list, list) and isinstance(qty_list, list)):
        return tuple()
    if len(child_list) != len(qty_list):
        return tuple()

    pairs = []
    for child, qty in zip(child_list, qty_list):
        child = str(child).strip()
        qty = pd.to_numeric(qty, errors='coerce')
        qty = 0 if pd.isna(qty) else round(float(qty), ndigits)
        pairs.append((child, qty))
    return tuple(sorted(pairs))
