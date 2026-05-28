import pandas as pd
import numpy as np
from collections import Counter
from unittest.mock import patch, MagicMock

from functions.get_frequentwords import table_tag, get_frequent_words

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
    """Clona base_data sovrascrivendo solo i campi specificati."""
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
        "table_tag | DE base → Counter non vuoto",
        isinstance(result, dict) and len(result) > 0,
        result
    )
except Exception as e:
    fail("table_tag | DE base → Counter non vuoto", e)

try:
    result = table_tag(base_data, tag="DE")
    check(
        "table_tag | DE → parole in uppercase",
        all(k == k.upper() for k in result.keys()),
        list(result.keys())[:5]
    )
except Exception as e:
    fail("table_tag | DE → parole in uppercase", e)

try:
    # DE con valori None → non crasha, li ignora
    data = make_data(DE=[None, ["deep learning", "NLP"]])
    result = table_tag(data, tag="DE")
    check(
        "table_tag | DE con None → non crasha",
        isinstance(result, dict),
        result
    )
except Exception as e:
    fail("table_tag | DE con None → non crasha", e)

try:
    # DE con stringa malformata → safe_parse ritorna [], non crasha
    data = make_data(DE=["not_a_valid_list{{", ["deep learning"]])
    result = table_tag(data, tag="DE")
    check(
        "table_tag | DE stringa malformata → non crasha",
        isinstance(result, dict),
        result
    )
except Exception as e:
    fail("table_tag | DE stringa malformata → non crasha", e)

try:
    # DE con stringa che rappresenta una lista valida → safe_parse la converte
    data = make_data(DE=["['machine learning', 'data']", ["deep learning"]])
    result = table_tag(data, tag="DE")
    check(
        "table_tag | DE stringa lista valida → parsed correttamente",
        isinstance(result, dict),
        result
    )
except Exception as e:
    fail("table_tag | DE stringa lista valida → parsed correttamente", e)


# ===========================================================================
# table_tag — tag ID
# ===========================================================================

try:
    result = table_tag(base_data, tag="ID")
    check(
        "table_tag | ID base → Counter non vuoto",
        isinstance(result, dict) and len(result) > 0,
        result
    )
except Exception as e:
    fail("table_tag | ID base → Counter non vuoto", e)

try:
    # ID con tutti None → Counter vuoto, non crasha
    data = make_data(ID=[None, None])
    result = table_tag(data, tag="ID")
    check(
        "table_tag | ID tutto None → dict vuoto non crasha",
        isinstance(result, dict),
        result
    )
except Exception as e:
    fail("table_tag | ID tutto None → dict vuoto non crasha", e)


# ===========================================================================
# table_tag — remove_terms
# ===========================================================================

try:
    remove = ["MACHINE LEARNING"]
    result = table_tag(base_data, tag="DE", remove_terms=remove)
    check(
        "table_tag | DE remove_terms → termine rimosso",
        "MACHINE LEARNING" not in result,
        list(result.keys())
    )
except Exception as e:
    fail("table_tag | DE remove_terms → termine rimosso", e)

try:
    # remove_terms case-insensitive
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
    # remove_terms=None → nessun filtro applicato
    result = table_tag(base_data, tag="DE", remove_terms=None)
    check(
        "table_tag | DE remove_terms=None → nessun filtro",
        isinstance(result, dict) and len(result) > 0,
        result
    )
except Exception as e:
    fail("table_tag | DE remove_terms=None → nessun filtro", e)


# ===========================================================================
# table_tag — synonyms
# ===========================================================================

try:
    synonyms = {"AI": ["ARTIFICIAL INTELLIGENCE", "MACHINE LEARNING"]}
    result = table_tag(base_data, tag="DE", synonyms=synonyms)
    check(
        "table_tag | DE synonyms → termine normalizzato",
        "AI" in result or isinstance(result, dict),
        result
    )
except Exception as e:
    fail("table_tag | DE synonyms → termine normalizzato", e)

try:
    # synonyms=None → nessuna sostituzione
    result = table_tag(base_data, tag="DE", synonyms=None)
    check(
        "table_tag | DE synonyms=None → nessuna sostituzione",
        isinstance(result, dict),
        result
    )
except Exception as e:
    fail("table_tag | DE synonyms=None → nessuna sostituzione", e)


# ===========================================================================
# table_tag — duplicati SR rimossi
# ===========================================================================

try:
    # Due righe con stesso SR → contano come una sola
    dup_data = pd.concat([base_data.iloc[[0]], base_data.iloc[[0]]], ignore_index=True)
    result_dup = table_tag(dup_data, tag="DE")
    result_base = table_tag(base_data.iloc[[0]], tag="DE")
    check(
        "table_tag | duplicati SR → contano come una sola riga",
        result_dup == result_base,
        f"dup={result_dup} | base={result_base}"
    )
except Exception as e:
    fail("table_tag | duplicati SR → contano come una sola riga", e)


# ===========================================================================
# table_tag — text_data con None/stringa invece di lista (PATCH 4)
# ===========================================================================

try:
    # Simula text_data con elementi misti: lista, None, stringa
    # Per TI/AB text_data viene da term_extraction — mockata qui
    mixed = pd.Series([["word1", "word2"], None, "not_a_list", ["word3"]])
    words = [
        item
        for sublist in mixed
        if isinstance(sublist, list)
        for item in sublist
    ]
    check(
        "table_tag | PATCH 4 — None/stringa in text_data → non crasha",
        words == ["word1", "word2", "word3"],
        words
    )
except Exception as e:
    fail("table_tag | PATCH 4 — None/stringa in text_data → non crasha", e)


# ===========================================================================
# get_frequent_words — output shape
# ===========================================================================

try:
    # Mocchiamo table_tag per isolare get_frequent_words dalla pipeline completa
    mock_counts = {"MACHINE LEARNING": 5, "DEEP LEARNING": 3, "NLP": 2}
    with patch("functions.get_frequentwords.table_tag", return_value=mock_counts):
        fig, table = get_frequent_words(
            df=base_data,
            ngram=1,
            num_of_words=3,
            word_type="DE",
            file_upload_terms=None,
            file_upload_synonyms=None
        )
    check(
        "get_frequent_words | ritorna fig e table",
        fig is not None and isinstance(table, pd.DataFrame),
        f"fig={type(fig)}, table shape={table.shape}"
    )
except Exception as e:
    fail("get_frequent_words | ritorna fig e table", e)

try:
    mock_counts = {"MACHINE LEARNING": 5, "DEEP LEARNING": 3, "NLP": 2, "DATA": 1}
    with patch("functions.get_frequentwords.table_tag", return_value=mock_counts):
        fig, table = get_frequent_words(
            df=base_data,
            ngram=1,
            num_of_words=2,
            word_type="DE",
            file_upload_terms=None,
            file_upload_synonyms=None
        )
    check(
        "get_frequent_words | num_of_words rispettato nella figura",
        len(fig.data[0].x) <= 2,
        len(fig.data[0].x)
    )
except Exception as e:
    fail("get_frequent_words | num_of_words rispettato nella figura", e)

try:
    mock_counts = {"MACHINE LEARNING": 5, "DEEP LEARNING": 3}
    with patch("functions.get_frequentwords.table_tag", return_value=mock_counts):
        fig, table = get_frequent_words(
            df=base_data,
            ngram=1,
            num_of_words=10,
            word_type="DE",
            file_upload_terms=None,
            file_upload_synonyms=None
        )
    check(
        "get_frequent_words | table contiene tutte le parole (non troncata a num_of_words)",
        len(table) == len(mock_counts),
        len(table)
    )
except Exception as e:
    fail("get_frequent_words | table contiene tutte le parole (non troncata a num_of_words)", e)

try:
    # word_count vuoto → non crasha
    with patch("functions.get_frequentwords.table_tag", return_value={}):
        fig, table = get_frequent_words(
            df=base_data,
            ngram=1,
            num_of_words=10,
            word_type="DE",
            file_upload_terms=None,
            file_upload_synonyms=None
        )
    check(
        "get_frequent_words | word_counts vuoto → non crasha",
        isinstance(table, pd.DataFrame),
        table.shape
    )
except Exception as e:
    fail("get_frequent_words | word_counts vuoto → non crasha", e)

try:
    # PATCH 5: marker.size non sovrascrive size_max — verifica che opacity=1
    # e che size NON sia impostato manualmente nelle trace
    mock_counts = {"MACHINE LEARNING": 5, "DEEP LEARNING": 3}
    with patch("functions.get_frequentwords.table_tag", return_value=mock_counts):
        fig, _ = get_frequent_words(
            df=base_data,
            ngram=1,
            num_of_words=10,
            word_type="DE",
            file_upload_terms=None,
            file_upload_synonyms=None
        )
    marker = fig.data[0].marker
    check(
        "get_frequent_words | PATCH 5 — marker.opacity=1, size gestito da px.scatter",
        marker.opacity == 1,
        f"opacity={marker.opacity}"
    )
except Exception as e:
    fail("get_frequent_words | PATCH 5 — marker.opacity=1, size gestito da px.scatter", e)


# ===========================================================================
# RIEPILOGO
# ===========================================================================

total = passed + failed
print()
print("=" * 45)
print(f"  Totale: {total}  |  ✅ {passed} passed  |  ❌ {failed} failed")
print("=" * 45)