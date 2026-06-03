"""
Data-quality scoring, PII masking and JSON-safe serialization helpers.

Everything here operates on real pandas DataFrames so the numbers shown in
the UI (quality score, nulls, duplicates, masked fields) are computed from
the actual data, never mocked.
"""
import hashlib
import math
import re

import numpy as np
import pandas as pd


# ─────────────────────────────── SERIALIZATION ───────────────────────────────

def _clean_scalar(v):
    """Make a single pandas/numpy value JSON-serializable."""
    if v is None:
        return None
    if isinstance(v, float) and (math.isnan(v) or math.isinf(v)):
        return None
    if isinstance(v, (np.integer,)):
        return int(v)
    if isinstance(v, (np.floating,)):
        f = float(v)
        return None if (math.isnan(f) or math.isinf(f)) else f
    if isinstance(v, (np.bool_,)):
        return bool(v)
    if isinstance(v, (pd.Timestamp,)):
        return v.isoformat()
    if v is pd.NaT:
        return None
    if isinstance(v, (np.ndarray,)):
        return [_clean_scalar(x) for x in v.tolist()]
    return v


def df_to_records(df, limit=None):
    """Convert a DataFrame to a list of JSON-safe dicts."""
    if df is None:
        return []
    sub = df.head(limit) if limit is not None else df
    records = sub.to_dict(orient='records')
    return [{k: _clean_scalar(v) for k, v in row.items()} for row in records]


def df_columns(df):
    if df is None:
        return []
    return [str(c) for c in df.columns]


# ─────────────────────────────── QUALITY SCORE ───────────────────────────────

def compute_quality(df):
    """
    Compute a real data-quality report for a DataFrame.

    Score (0-100) penalises null cells and duplicate rows. The breakdown is
    surfaced in the UI to make the pipeline's effect visible step by step.
    """
    if df is None or len(df) == 0:
        return {
            'rows': 0,
            'columns': 0 if df is None else len(df.columns),
            'null_cells': 0,
            'null_ratio': 0.0,
            'duplicate_rows': 0,
            'score': 100.0,
            'columns_detail': [],
        }

    rows = len(df)
    cols = len(df.columns)
    total_cells = rows * cols if cols else 1

    null_cells = int(df.isna().sum().sum())
    null_ratio = null_cells / total_cells if total_cells else 0.0
    duplicate_rows = int(df.duplicated().sum())
    dup_ratio = duplicate_rows / rows if rows else 0.0

    # Weighted penalty: nulls hurt more than duplicates.
    score = 100.0 * (1 - 0.6 * null_ratio - 0.4 * dup_ratio)
    score = max(0.0, min(100.0, round(score, 1)))

    columns_detail = []
    for col in df.columns:
        series = df[col]
        n_null = int(series.isna().sum())
        columns_detail.append({
            'name': str(col),
            'dtype': str(series.dtype),
            'null_count': n_null,
            'unique_count': int(series.nunique(dropna=True)),
        })

    return {
        'rows': rows,
        'columns': cols,
        'null_cells': null_cells,
        'null_ratio': round(null_ratio, 4),
        'duplicate_rows': duplicate_rows,
        'score': score,
        'columns_detail': columns_detail,
    }


# ─────────────────────────────── PII MASKING ─────────────────────────────────

def _mask_name(value):
    """TCHOYI ABRAHAM WILSON -> T*** A*** W***"""
    parts = str(value).split()
    return ' '.join((p[0] + '***') if p else p for p in parts)


def _mask_tail(value, keep=4):
    """10092345001 -> *******5001"""
    s = re.sub(r'\s+', '', str(value))
    if len(s) <= keep:
        return '*' * len(s)
    return '*' * (len(s) - keep) + s[-keep:]


def _mask_phone(value):
    """699123456 -> 699***456"""
    s = re.sub(r'\s+', '', str(value))
    if len(s) <= 6:
        return '*' * len(s)
    return s[:3] + '*' * (len(s) - 6) + s[-3:]


def _mask_email(value):
    s = str(value)
    if '@' not in s:
        return _mask_tail(s, keep=2)
    local, _, domain = s.partition('@')
    head = local[0] if local else ''
    return f"{head}***@{domain}"


def _mask_hash(value):
    return 'sha256:' + hashlib.sha256(str(value).encode('utf-8')).hexdigest()[:12]


MASK_STRATEGIES = {
    'name_initials': _mask_name,
    'account_tail': _mask_tail,
    'phone_middle': _mask_phone,
    'email': _mask_email,
    'hash': _mask_hash,
}


def mask_series(series, strategy):
    fn = MASK_STRATEGIES.get(strategy, _mask_hash)
    return series.apply(lambda v: v if pd.isna(v) else fn(v))


# Heuristics for auto-detecting sensitive columns (banking context).
SENSITIVE_PATTERNS = {
    'name_initials': re.compile(r'(nom|name|client|beneficiaire|titulaire)', re.I),
    'account_tail': re.compile(r'(compte|account|iban|rib|carte|card)', re.I),
    'phone_middle': re.compile(r'(tel|phone|mobile|gsm|numero)', re.I),
    'email': re.compile(r'(email|mail|courriel)', re.I),
}


def detect_sensitive_columns(df):
    """Return [{column, strategy}] for columns that look like PII."""
    found = []
    for col in df.columns:
        for strategy, pattern in SENSITIVE_PATTERNS.items():
            if pattern.search(str(col)):
                found.append({'column': str(col), 'strategy': strategy})
                break
    return found
