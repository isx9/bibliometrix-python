"""
io_utils.py
-----------
Shared CSV read/write helpers for the standardized WoS-schema DataFrame.

These functions are the single source of truth for how multi-value
columns (AU, AF, C1, AU_CO, DE, ID, CR) are serialized to and
deserialized from CSV. Both the ETL demo notebook and the dashboard's
"Load Bibliometrix file(s)" (CSV) import path must use these functions
instead of re-implementing the logic separately, to avoid the two
copies drifting out of sync.

Per spec Section 4.2 ("Delimiter Standard"), multi-value fields are
joined/split using ";" as the internal delimiter — NOT the raw Python
list repr (e.g. "['a', 'b']"), which is fragile, harder to read, and
was the source of a bug where the dashboard's CSV import silently
produced empty lists for every multi-value column.

IMPORTANT — delimiter collision with PubMed-style "CR" content:
Individual reference strings (CR) commonly contain a literal ";" as
natural punctuation, e.g. "J Acoust Soc Am. 2025 Dec 1;158(6):4243-4267.
doi: 10.1121/10.0041768.". If that ";" were left unescaped, splitting
on ";" would incorrectly cut a single reference into two, inflating
counts like "References" in the dashboard. To prevent this, any ";"
that occurs *inside* an individual list item is escaped to a private-use
sentinel character before joining, and restored after splitting. The
on-disk delimiter remains ";" (spec-compliant and human-readable); only
the round-trip through save/load needs to be aware of the escaping.
"""
import pandas as pd

LIST_COLUMNS = ["AU", "AF", "C1", "CR", "DE", "ID", "AU_CO"]
STR_COLUMNS = [
    "DB", "UT", "DI", "PMID", "TI", "SO", "JI", "PY", "DT", "LA",
    "RP", "AB", "VL", "IS", "BP", "EP", "SR", "SR_FULL",
]

# Private-use sentinel standing in for a literal ";" that belongs to the
# *content* of a list item, as opposed to the ";" used as the separator
# between items. U+E000 is in the Unicode Private Use Area, so it will
# never collide with real bibliographic text.
_ESCAPED_SEMICOLON = "\uE000"


def _escape_item(item: str) -> str:
    """Protect any literal ';' inside a single list item before joining."""
    return item.replace(";", _ESCAPED_SEMICOLON)


def _unescape_item(item: str) -> str:
    """Restore literal ';' inside a single list item after splitting."""
    return item.replace(_ESCAPED_SEMICOLON, ";")


def save_standardized_csv(df: pd.DataFrame, path: str) -> None:
    """
    Save a standardized DataFrame to CSV, joining list columns with the
    ";" delimiter required by the spec, instead of letting pandas write
    the raw Python representation of the lists.

    Any ";" that is part of an individual item's own text (e.g. PubMed
    citation punctuation in CR) is escaped first, so it survives the
    round trip without being mistaken for the separator.
    """
    out = df.copy()
    for col in LIST_COLUMNS:
        if col in out.columns:
            out[col] = out[col].apply(
                lambda l: ";".join(_escape_item(str(v)) for v in l) if isinstance(l, list) else ""
            )
    out.to_csv(path, index=False)


def load_standardized_csv(path) -> pd.DataFrame:
    """
    Reload a CSV written by save_standardized_csv() (or any CSV using the
    ";"-delimited multi-value convention) and restore the original Python
    types: list[str] for multi-value fields (split on ";", with escaped
    internal ";" restored), non-null str for scalar fields, and int for TC.

    `path` can be a file path or a file-like/datapath object accepted by
    pandas.read_csv.
    """
    df = pd.read_csv(path, keep_default_na=False, na_values=[])

    for col in LIST_COLUMNS:
        if col in df.columns:
            df[col] = df[col].apply(
                lambda x: [_unescape_item(v.strip()) for v in x.split(";") if v.strip()]
                if isinstance(x, str) else (x if isinstance(x, list) else [])
            )

    for col in STR_COLUMNS:
        if col in df.columns:
            df[col] = df[col].apply(lambda x: "" if pd.isna(x) else str(x))

    if "TC" in df.columns:
        df["TC"] = pd.to_numeric(df["TC"], errors="coerce").fillna(0).astype(int)

    return df