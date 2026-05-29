import pandas as pd
import numpy as np
from unittest.mock import patch

from functions.get_wordfrequency import get_word_frequency, keyword_growth, trim_years

# =========================
# BASE DATAFRAME
# =========================

base_data = pd.DataFrame({
    "SR":  ["Smith J, 2024, J TEST", "Jones A, 2023, J TEST", "Brown B, 2022, J TEST"],
    "TI":  ["machine learning methods", "deep learning applications", "neural network models"],
    "AB":  ["This paper presents machine learning methods for data analysis.",
            "We propose deep learning applications in natural language processing.",
            "Neural network models are applied to image recognition tasks."],
    "DE":  [["machine learning", "data analysis"], ["deep learning", "NLP"], ["neural networks", "image recognition"]],
    "ID":  [["artificial intelligence", "neural networks"], ["deep learning", "NLP"], ["computer vision", "CNN"]],
    "PY":  [2024, 2023, 2022],
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
# trim_years
# ===========================================================================

try:
    w = pd.Series([1, 2, 3], index=[2020, 2021, 2022])
    result = trim_years(w, range(2020, 2023), cdf=False)
    check(
        "trim_years | base annual → correct values",
        list(result.values) == [1.0, 2.0, 3.0],
        list(result.values)
    )
except Exception as e:
    fail("trim_years | base annual → correct values", e)

try:
    w = pd.Series([1, 2, 3], index=[2020, 2021, 2022])
    result = trim_years(w, range(2020, 2023), cdf=True)
    check(
        "trim_years | cumulative → cumsum applied",
        list(result.values) == [1.0, 3.0, 6.0],
        list(result.values)
    )
except Exception as e:
    fail("trim_years | cumulative → cumsum applied", e)

try:
    w = pd.Series([5], index=[2021])
    result = trim_years(w, range(2020, 2023), cdf=False)
    check(
        "trim_years | gap years → filled with zeros",
        result[2020] == 0.0 and result[2021] == 5.0 and result[2022] == 0.0,
        list(result.values)
    )
except Exception as e:
    fail("trim_years | gap years → filled with zeros", e)

try:
    # PATCH 5: empty year_range → returns empty Series, no crash
    w = pd.Series([], dtype=float)
    result = trim_years(w, range(0, 0), cdf=True)
    check(
        "trim_years | PATCH 5 — empty year_range → empty Series no crash",
        len(result) == 0,
        result
    )
except Exception as e:
    fail("trim_years | PATCH 5 — empty year_range → empty Series no crash", e)


# ===========================================================================
# keyword_growth
# ===========================================================================

try:
    result = keyword_growth(base_data, tag="DE", sep=";", top=3, cdf=False)
    check(
        "keyword_growth | DE base → DataFrame with Year column",
        isinstance(result, pd.DataFrame) and "Year" in result.columns,
        result.columns.tolist()
    )
except Exception as e:
    fail("keyword_growth | DE base → DataFrame with Year column", e)

try:
    result = keyword_growth(base_data, tag="DE", sep=";", top=3, cdf=True)
    check(
        "keyword_growth | DE cumulative → values non-decreasing",
        all(
            result[col].is_monotonic_increasing
            for col in result.columns if col != "Year"
        ),
        result
    )
except Exception as e:
    fail("keyword_growth | DE cumulative → values non-decreasing", e)

try:
    result = keyword_growth(base_data, tag="DE", sep=";", top=2, cdf=False)
    non_year_cols = [c for c in result.columns if c != "Year"]
    check(
        "keyword_growth | top=2 → at most 2 term columns",
        len(non_year_cols) <= 2,
        non_year_cols
    )
except Exception as e:
    fail("keyword_growth | top=2 → at most 2 term columns", e)

try:
    # remove_terms filters out specified terms
    result_full = keyword_growth(base_data, tag="DE", top=10, cdf=False)
    result_filtered = keyword_growth(base_data, tag="DE", top=10, cdf=False,
                                     remove_terms=["MACHINE LEARNING"])
    check(
        "keyword_growth | remove_terms → term absent from columns",
        "MACHINE LEARNING" not in result_filtered.columns,
        result_filtered.columns.tolist()
    )
except Exception as e:
    fail("keyword_growth | remove_terms → term absent from columns", e)

try:
    # synonyms → term replaced by key
    synonyms = {"AI": ["DEEP LEARNING", "MACHINE LEARNING"]}
    result = keyword_growth(base_data, tag="DE", top=10, cdf=False, synonyms=synonyms)
    check(
        "keyword_growth | synonyms → replacement term in columns",
        "AI" in result.columns,
        result.columns.tolist()
    )
except Exception as e:
    fail("keyword_growth | synonyms → replacement term in columns", e)

try:
    # PATCH 3: all rows removed after filtering → empty DataFrame, no crash
    result = keyword_growth(
        base_data, tag="DE", top=10, cdf=False,
        remove_terms=["MACHINE LEARNING", "DATA ANALYSIS", "DEEP LEARNING",
                      "NLP", "NEURAL NETWORKS", "IMAGE RECOGNITION"]
    )
    check(
        "keyword_growth | PATCH 3 — all terms removed → empty DataFrame no crash",
        isinstance(result, pd.DataFrame),
        result
    )
except Exception as e:
    fail("keyword_growth | PATCH 3 — all terms removed → empty DataFrame no crash", e)

try:
    # PATCH 4: None elements in tag column → no crash
    data = make_data(DE=[None, ["deep learning", "NLP"], ["neural networks"]])
    result = keyword_growth(data, tag="DE", top=5, cdf=False)
    check(
        "keyword_growth | PATCH 4 — None in tag column → no crash",
        isinstance(result, pd.DataFrame),
        result.columns.tolist()
    )
except Exception as e:
    fail("keyword_growth | PATCH 4 — None in tag column → no crash", e)

try:
    # PATCH 4: mixed types (string, list, None) in tag column → no crash
    data = make_data(DE=["machine learning;data", ["deep learning"], None])
    result = keyword_growth(data, tag="DE", top=5, cdf=False)
    check(
        "keyword_growth | PATCH 4 — mixed types in tag column → no crash",
        isinstance(result, pd.DataFrame),
        result.columns.tolist()
    )
except Exception as e:
    fail("keyword_growth | PATCH 4 — mixed types in tag column → no crash", e)


# ===========================================================================
# get_word_frequency — output shape
# ===========================================================================

try:
    mock_freq = pd.DataFrame({
        "Year": [2022, 2023, 2024],
        "MACHINE LEARNING": [1, 2, 3],
        "DEEP LEARNING": [0, 1, 2],
        "NLP": [1, 1, 1],
    })
    with patch("functions.get_wordfrequency.keyword_growth", return_value=mock_freq):
        with patch("functions.get_wordfrequency.term_extraction", return_value=base_data):
            fig, word_freq = get_word_frequency(
                df=base_data,
                ngram=1,
                field_wf="DE",
                file_upload_terms_wf=None,
                file_upload_synonyms_wf=None,
                occurrences="per_year",
                top_words=[0, 3]
            )
    check(
        "get_word_frequency | returns fig and word_freq DataFrame",
        fig is not None and isinstance(word_freq, pd.DataFrame),
        f"fig={type(fig)}, word_freq shape={word_freq.shape}"
    )
except Exception as e:
    fail("get_word_frequency | returns fig and word_freq DataFrame", e)

try:
    mock_freq = pd.DataFrame({
        "Year": [2022, 2023, 2024],
        "MACHINE LEARNING": [1, 2, 3],
        "DEEP LEARNING": [0, 1, 2],
        "NLP": [1, 1, 1],
        "DATA": [2, 2, 2],
    })
    with patch("functions.get_wordfrequency.keyword_growth", return_value=mock_freq):
        with patch("functions.get_wordfrequency.term_extraction", return_value=base_data):
            fig, word_freq = get_word_frequency(
                df=base_data,
                ngram=1,
                field_wf="DE",
                file_upload_terms_wf=None,
                file_upload_synonyms_wf=None,
                occurrences="per_year",
                top_words=[0, 2]
            )
    non_year_cols = [c for c in word_freq.columns if c != "Year"]
    check(
        "get_word_frequency | top_words slice respected",
        len(non_year_cols) <= 3,
        non_year_cols
    )
except Exception as e:
    fail("get_word_frequency | top_words slice respected", e)

try:
    # PATCH 2: top_words[0] out of range → clamped, no crash
    mock_freq = pd.DataFrame({
        "Year": [2022, 2023],
        "MACHINE LEARNING": [1, 2],
    })
    with patch("functions.get_wordfrequency.keyword_growth", return_value=mock_freq):
        with patch("functions.get_wordfrequency.term_extraction", return_value=base_data):
            fig, word_freq = get_word_frequency(
                df=base_data,
                ngram=1,
                field_wf="DE",
                file_upload_terms_wf=None,
                file_upload_synonyms_wf=None,
                occurrences="per_year",
                top_words=[99, 100]  # both out of range
            )
    check(
        "get_word_frequency | PATCH 2 — top_words out of range → no crash",
        isinstance(word_freq, pd.DataFrame),
        word_freq.shape
    )
except Exception as e:
    fail("get_word_frequency | PATCH 2 — top_words out of range → no crash", e)

try:
    # cumulate mode → passed correctly to keyword_growth
    mock_freq = pd.DataFrame({
        "Year": [2022, 2023, 2024],
        "MACHINE LEARNING": [1, 3, 6],
    })
    with patch("functions.get_wordfrequency.keyword_growth", return_value=mock_freq) as mock_kg:
        with patch("functions.get_wordfrequency.term_extraction", return_value=base_data):
            get_word_frequency(
                df=base_data,
                ngram=1,
                field_wf="DE",
                file_upload_terms_wf=None,
                file_upload_synonyms_wf=None,
                occurrences="cumulate",
                top_words=[0, 1]
            )
    check(
        "get_word_frequency | occurrences=cumulate → cdf=True passed to keyword_growth",
        mock_kg.call_args[1].get("cdf") == True or mock_kg.call_args[0][3] == True,
        mock_kg.call_args
    )
except Exception as e:
    fail("get_word_frequency | occurrences=cumulate → cdf=True passed to keyword_growth", e)


# ===========================================================================
# SUMMARY
# ===========================================================================

total = passed + failed
print()
print("=" * 45)
print(f"  Total: {total}  |  ✅ {passed} passed  |  ❌ {failed} failed")
print("=" * 45)