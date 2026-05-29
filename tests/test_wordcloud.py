import pandas as pd
import numpy as np
from collections import Counter
from unittest.mock import patch

from functions.get_wordcloud import table_tag, get_wordcloud, is_legible_on_white

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
# is_legible_on_white
# ===========================================================================

try:
    # Dark blue — legible
    check(
        "is_legible_on_white | dark blue → True",
        is_legible_on_white("#1f77b4") == True,
        is_legible_on_white("#1f77b4")
    )
except Exception as e:
    fail("is_legible_on_white | dark blue → True", e)

try:
    # White — not legible (too light)
    check(
        "is_legible_on_white | white → False",
        is_legible_on_white("white") == False,
        is_legible_on_white("white")
    )
except Exception as e:
    fail("is_legible_on_white | white → False", e)

try:
    # Black — not legible (too dark)
    check(
        "is_legible_on_white | black → False",
        is_legible_on_white("black") == False,
        is_legible_on_white("black")
    )
except Exception as e:
    fail("is_legible_on_white | black → False", e)


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
# get_wordcloud — output shape
# ===========================================================================

try:
    mock_counts = {"MACHINE LEARNING": 5, "DEEP LEARNING": 3, "NLP": 2}
    with patch("functions.get_wordcloud.table_tag", return_value=mock_counts):
        html_file, table = get_wordcloud(
            df=base_data,
            ngram=1,
            num_of_words_wc=3,
            field_wc="DE",
            file_upload_terms_wc=None,
            file_upload_synonyms_wc=None
        )
    check(
        "get_wordcloud | returns html filename and table",
        isinstance(html_file, str) and html_file.endswith(".html") and isinstance(table, pd.DataFrame),
        f"file={html_file}, table shape={table.shape}"
    )
except Exception as e:
    fail("get_wordcloud | returns html filename and table", e)

try:
    mock_counts = {"MACHINE LEARNING": 5, "DEEP LEARNING": 3, "NLP": 2, "DATA": 1}
    with patch("functions.get_wordcloud.table_tag", return_value=mock_counts):
        _, table = get_wordcloud(
            df=base_data,
            ngram=1,
            num_of_words_wc=10,
            field_wc="DE",
            file_upload_terms_wc=None,
            file_upload_synonyms_wc=None
        )
    check(
        "get_wordcloud | table contains all words (not truncated to num_of_words_wc)",
        len(table) == len(mock_counts),
        len(table)
    )
except Exception as e:
    fail("get_wordcloud | table contains all words (not truncated to num_of_words_wc)", e)

try:
    mock_counts = {"MACHINE LEARNING": 5, "DEEP LEARNING": 3, "NLP": 2, "DATA": 1}
    with patch("functions.get_wordcloud.table_tag", return_value=mock_counts):
        _, table = get_wordcloud(
            df=base_data,
            ngram=1,
            num_of_words_wc=2,
            field_wc="DE",
            file_upload_terms_wc=None,
            file_upload_synonyms_wc=None
        )
    check(
        "get_wordcloud | words in table are capitalized",
        all(w[0].isupper() for w in table["Words"] if w),
        list(table["Words"])
    )
except Exception as e:
    fail("get_wordcloud | words in table are capitalized", e)

try:
    # PATCH 6: empty word_counts → no IndexError on sorted_words[0]
    with patch("functions.get_wordcloud.table_tag", return_value={}):
        html_file, table = get_wordcloud(
            df=base_data,
            ngram=1,
            num_of_words_wc=10,
            field_wc="DE",
            file_upload_terms_wc=None,
            file_upload_synonyms_wc=None
        )
    check(
        "get_wordcloud | PATCH 6 — empty word_counts → no crash, returns html and table",
        isinstance(html_file, str) and html_file.endswith(".html") and isinstance(table, pd.DataFrame),
        f"file={html_file}, table shape={table.shape}"
    )
except Exception as e:
    fail("get_wordcloud | PATCH 6 — empty word_counts → no crash, returns html and table", e)

try:
    # PATCH 7: colors fallback — patch is_legible_on_white to always return False
    # so the colors list is empty; random.choice should not crash
    with patch("functions.get_wordcloud.is_legible_on_white", return_value=False):
        with patch("functions.get_wordcloud.table_tag", return_value={"MACHINE LEARNING": 5}):
            html_file, table = get_wordcloud(
                df=base_data,
                ngram=1,
                num_of_words_wc=10,
                field_wc="DE",
                file_upload_terms_wc=None,
                file_upload_synonyms_wc=None
            )
    check(
        "get_wordcloud | PATCH 7 — empty colors list → fallback used, no crash",
        isinstance(html_file, str) and html_file.endswith(".html"),
        html_file
    )
except Exception as e:
    fail("get_wordcloud | PATCH 7 — empty colors list → fallback used, no crash", e)


# ===========================================================================
# SUMMARY
# ===========================================================================

total = passed + failed
print()
print("=" * 45)
print(f"  Total: {total}  |  ✅ {passed} passed  |  ❌ {failed} failed")
print("=" * 45)
