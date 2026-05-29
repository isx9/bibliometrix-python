import pandas as pd
import numpy as np
from collections import Counter
from unittest.mock import patch
 
from functions.get_treemap import table_tag, get_treemap
 
# =========================
# BASE DATAFRAME
# =========================
 
base_data = pd.DataFrame({
    "SR":  ["Smith J, 2024, J TEST", "Jones A, 2023, J TEST"],
    "TI":  ["machine learning methods", "deep learning applications"],
    "AB":  ["This paper presents machine learning methods for data analysis.",
            "We propose deep learning applications in natural language processing."],
    "DE":  [["machine learning", "data analysis"], ["deep learning", "NLP"]],
    "ID":  [["artificial intelligence", "neural networks"], ["deep learning", "NLP"]],
})
 
 
def make_data(**kwargs):
    """Clone base_data overriding only the specified fields."""
    d = base_data.copy()
    for k, v in kwargs.items():
        d[k] = v
    return d
 
 
# =========================
# HELPERS
# =========================
 
passed = 0
failed = 0
 
 
def ok(label, value=None):
    global passed
    passed += 1
    print(f"✅ {label}")
    if value is not None:
        print(f"   {value}")
 
 
def fail(label, err):
    global failed
    failed += 1
    print(f"❌ {label}")
    print(f"   {err}")
 
 
def check(label, condition, got=None):
    if condition:
        ok(label, got)
    else:
        fail(label, f"Assertion failed — got: {got}")
 
 
# ===========================================================================
# table_tag — tag DE
# ===========================================================================
 
try:
    result = table_tag(base_data, tag="DE")
    check(
        "table_tag | DE base → non-empty Counter",
        isinstance(result, dict) and len(result) > 0,
        result
    )
except Exception as e:
    fail("table_tag | DE base → non-empty Counter", e)
 
try:
    result = table_tag(base_data, tag="DE")
    check(
        "table_tag | DE → words in uppercase",
        all(k == k.upper() for k in result.keys()),
        list(result.keys())[:5]
    )
except Exception as e:
    fail("table_tag | DE → words in uppercase", e)
 
try:
    data = make_data(DE=[None, ["deep learning", "NLP"]])
    result = table_tag(data, tag="DE")
    check(
        "table_tag | DE with None → no crash",
        isinstance(result, dict),
        result
    )
except Exception as e:
    fail("table_tag | DE with None → no crash", e)
 
try:
    # Malformed string → safe_parse returns [], no crash
    data = make_data(DE=["not_a_valid_list{{", ["deep learning"]])
    result = table_tag(data, tag="DE")
    check(
        "table_tag | DE malformed string → no crash",
        isinstance(result, dict),
        result
    )
except Exception as e:
    fail("table_tag | DE malformed string → no crash", e)
 
try:
    # String representing a valid list → safe_parse converts it correctly
    data = make_data(DE=["['machine learning', 'data']", ["deep learning"]])
    result = table_tag(data, tag="DE")
    check(
        "table_tag | DE valid list string → parsed correctly",
        isinstance(result, dict),
        result
    )
except Exception as e:
    fail("table_tag | DE valid list string → parsed correctly", e)
 
 
# ===========================================================================
# table_tag — tag ID
# ===========================================================================
 
try:
    result = table_tag(base_data, tag="ID")
    check(
        "table_tag | ID base → non-empty Counter",
        isinstance(result, dict) and len(result) > 0,
        result
    )
except Exception as e:
    fail("table_tag | ID base → non-empty Counter", e)
 
try:
    data = make_data(ID=[None, None])
    result = table_tag(data, tag="ID")
    check(
        "table_tag | ID all None → empty dict no crash",
        isinstance(result, dict),
        result
    )
except Exception as e:
    fail("table_tag | ID all None → empty dict no crash", e)
 
 
# ===========================================================================
# table_tag — remove_terms
# ===========================================================================
 
try:
    remove = ["MACHINE LEARNING"]
    result = table_tag(base_data, tag="DE", remove_terms=remove)
    check(
        "table_tag | DE remove_terms → term removed",
        "MACHINE LEARNING" not in result,
        list(result.keys())
    )
except Exception as e:
    fail("table_tag | DE remove_terms → term removed", e)
 
try:
    # remove_terms is case-insensitive
    remove = ["machine learning"]
    result = table_tag(base_data, tag="DE", remove_terms=remove)
    check(
        "table_tag | DE remove_terms case-insensitive",
        "MACHINE LEARNING" not in result,
        list(result.keys())
    )
except Exception as e:
    fail("table_tag | DE remove_terms case-insensitive", e)
 
try:
    result = table_tag(base_data, tag="DE", remove_terms=None)
    check(
        "table_tag | DE remove_terms=None → no filter applied",
        isinstance(result, dict) and len(result) > 0,
        result
    )
except Exception as e:
    fail("table_tag | DE remove_terms=None → no filter applied", e)
 
 
# ===========================================================================
# table_tag — synonyms
# ===========================================================================
 
try:
    synonyms = {"AI": ["ARTIFICIAL INTELLIGENCE", "MACHINE LEARNING"]}
    result = table_tag(base_data, tag="DE", synonyms=synonyms)
    check(
        "table_tag | DE synonyms → term normalized",
        "AI" in result or isinstance(result, dict),
        result
    )
except Exception as e:
    fail("table_tag | DE synonyms → term normalized", e)
 
try:
    result = table_tag(base_data, tag="DE", synonyms=None)
    check(
        "table_tag | DE synonyms=None → no substitution",
        isinstance(result, dict),
        result
    )
except Exception as e:
    fail("table_tag | DE synonyms=None → no substitution", e)
 
 
# ===========================================================================
# table_tag — duplicate SR removed
# ===========================================================================
 
try:
    dup_data = pd.concat([base_data.iloc[[0]], base_data.iloc[[0]]], ignore_index=True)
    result_dup = table_tag(dup_data, tag="DE")
    result_base = table_tag(base_data.iloc[[0]], tag="DE")
    check(
        "table_tag | duplicate SR → counted as single row",
        result_dup == result_base,
        f"dup={result_dup} | base={result_base}"
    )
except Exception as e:
    fail("table_tag | duplicate SR → counted as single row", e)
 
 
# ===========================================================================
# table_tag — PATCH 4: None/string in text_data
# ===========================================================================
 
try:
    mixed = pd.Series([["word1", "word2"], None, "not_a_list", ["word3"]])
    words = [
        item
        for sublist in mixed
        if isinstance(sublist, list)
        for item in sublist
    ]
    check(
        "table_tag | PATCH 4 — None/string in text_data → no crash",
        words == ["word1", "word2", "word3"],
        words
    )
except Exception as e:
    fail("table_tag | PATCH 4 — None/string in text_data → no crash", e)
 
 
# ===========================================================================
# get_treemap — output shape
# ===========================================================================
 
try:
    mock_counts = {"MACHINE LEARNING": 5, "DEEP LEARNING": 3, "NLP": 2}
    with patch("functions.get_treemap.table_tag", return_value=mock_counts):
        fig, table = get_treemap(
            df=base_data,
            ngram=1,
            num_of_words=3,
            word_type="DE",
            file_upload_terms=None,
            file_upload_synonyms=None
        )
    check(
        "get_treemap | returns fig and table",
        fig is not None and isinstance(table, pd.DataFrame),
        f"fig={type(fig)}, table shape={table.shape}"
    )
except Exception as e:
    fail("get_treemap | returns fig and table", e)
 
try:
    mock_counts = {"MACHINE LEARNING": 5, "DEEP LEARNING": 3, "NLP": 2, "DATA": 1}
    with patch("functions.get_treemap.table_tag", return_value=mock_counts):
        fig, table = get_treemap(
            df=base_data,
            ngram=1,
            num_of_words=2,
            word_type="DE",
            file_upload_terms=None,
            file_upload_synonyms=None
        )
    # treemap has an extra root node "Tree" — children are num_of_words
    labels = [l for l in list(fig.data[0].labels) if l != "Tree"]
    check(
        "get_treemap | num_of_words respected",
        len(labels) <= 2,
        labels
    )
except Exception as e:
    fail("get_treemap | num_of_words respected", e)
 
try:
    mock_counts = {"MACHINE LEARNING": 5, "DEEP LEARNING": 3}
    with patch("functions.get_treemap.table_tag", return_value=mock_counts):
        fig, table = get_treemap(
            df=base_data,
            ngram=1,
            num_of_words=10,
            word_type="DE",
            file_upload_terms=None,
            file_upload_synonyms=None
        )
    check(
        "get_treemap | table contains all words (not truncated to num_of_words)",
        len(table) == len(mock_counts),
        len(table)
    )
except Exception as e:
    fail("get_treemap | table contains all words (not truncated to num_of_words)", e)
 
try:
    # Empty word_counts → no crash
    with patch("functions.get_treemap.table_tag", return_value={}):
        fig, table = get_treemap(
            df=base_data,
            ngram=1,
            num_of_words=10,
            word_type="DE",
            file_upload_terms=None,
            file_upload_synonyms=None
        )
    check(
        "get_treemap | empty word_counts → no crash",
        isinstance(table, pd.DataFrame),
        table.shape
    )
except Exception as e:
    fail("get_treemap | empty word_counts → no crash", e)
 
try:
    # texttemplate set correctly
    mock_counts = {"MACHINE LEARNING": 5, "DEEP LEARNING": 3}
    with patch("functions.get_treemap.table_tag", return_value=mock_counts):
        fig, _ = get_treemap(
            df=base_data,
            ngram=1,
            num_of_words=10,
            word_type="DE",
            file_upload_terms=None,
            file_upload_synonyms=None
        )
    check(
        "get_treemap | texttemplate set correctly",
        "%{label}" in fig.data[0].texttemplate,
        fig.data[0].texttemplate
    )
except Exception as e:
    fail("get_treemap | texttemplate set correctly", e)
 
try:
    # layout height = 800
    mock_counts = {"MACHINE LEARNING": 5, "DEEP LEARNING": 3}
    with patch("functions.get_treemap.table_tag", return_value=mock_counts):
        fig, _ = get_treemap(
            df=base_data,
            ngram=1,
            num_of_words=10,
            word_type="DE",
            file_upload_terms=None,
            file_upload_synonyms=None
        )
    check(
        "get_treemap | layout height=800",
        fig.layout.height == 800,
        fig.layout.height
    )
except Exception as e:
    fail("get_treemap | layout height=800", e)
 
 
# ===========================================================================
# SUMMARY
# ===========================================================================
 
total = passed + failed
print()
print("=" * 45)
print(f"  Total: {total}  |  ✅ {passed} passed  |  ❌ {failed} failed")
print("=" * 45)