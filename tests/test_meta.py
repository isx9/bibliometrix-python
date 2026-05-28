import pandas as pd
import numpy as np

from www.services.metatagextraction import metaTagExtraction

# =========================
# BASE DATAFRAME
# =========================

base_data = pd.DataFrame({
    "AU": [["Smith J", "Doe A"]],
    "SO": ["JOURNAL OF TEST"],
    "JI": ["J TEST"],
    "PY": [2024],
    "DB": ["OPENALEX"],
    "C1": [["University of Naples, Italy"]],
    "RP": ["University of Naples, Italy"],
    "CR": [["Smith, 2020, SCIENCE"]],
    "C3": [None],
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
# SR
# ===========================================================================

try:
    result = metaTagExtraction(base_data, Field="SR")
    check("SR | base", "SR" in result.columns, result[["SR"]].head())
except Exception as e:
    fail("SR | base", e)

try:
    # Duplicati: due righe identiche devono produrre SR distinti
    dup = pd.concat([base_data, base_data], ignore_index=True)
    result = metaTagExtraction(dup, Field="SR")
    check("SR | duplicati → SR univoci", result["SR"].nunique() == 2, result[["SR"]].head())
except Exception as e:
    fail("SR | duplicati → SR univoci", e)

try:
    # Autore mancante → "NA" come fallback
    result = metaTagExtraction(make_data(AU=[[]]), Field="SR")
    check("SR | autore vuoto → NA", "NA" in result["SR"].iloc[0], result["SR"].iloc[0])
except Exception as e:
    fail("SR | autore vuoto → NA", e)

try:
    # JI vuoto → fallback su SO
    result = metaTagExtraction(make_data(JI=[""]), Field="SR")
    check("SR | JI vuoto → usa SO", "JOURNAL OF TEST" in result["SR"].iloc[0], result["SR"].iloc[0])
except Exception as e:
    fail("SR | JI vuoto → usa SO", e)

try:
    # DB scopus → autore riformattato
    result = metaTagExtraction(make_data(DB=["scopus"]), Field="SR")
    check("SR | DB=scopus → non crasha", "SR" in result.columns, result["SR"].iloc[0])
except Exception as e:
    fail("SR | DB=scopus → non crasha", e)

try:
    # SR_FULL deve essere presente
    result = metaTagExtraction(base_data, Field="SR")
    check("SR | SR_FULL presente", "SR_FULL" in result.columns, result["SR_FULL"].iloc[0])
except Exception as e:
    fail("SR | SR_FULL presente", e)


# ===========================================================================
# AU_CO
# ===========================================================================

try:
    result = metaTagExtraction(base_data, Field="AU_CO")
    check("AU_CO | base → ITALY trovata", "ITALY" in result["AU_CO"].iloc[0], result[["AU_CO"]].head())
except Exception as e:
    fail("AU_CO | base → ITALY trovata", e)

try:
    # C1=None, RP valido → fallback su RP, non crash
    result = metaTagExtraction(make_data(C1=[None], RP=["Univ London, London, United Kingdom"]), Field="AU_CO")
    check("AU_CO | C1=None → non crasha", isinstance(result["AU_CO"].iloc[0], list), result["AU_CO"].iloc[0])
except Exception as e:
    fail("AU_CO | C1=None → non crasha", e)

try:
    # C1=lista vuota → non crash
    result = metaTagExtraction(make_data(C1=[[]]), Field="AU_CO")
    check("AU_CO | C1=[] → non crasha", isinstance(result["AU_CO"].iloc[0], list), result["AU_CO"].iloc[0])
except Exception as e:
    fail("AU_CO | C1=[] → non crasha", e)

try:
    # C1 e RP entrambi NaN → lista vuota
    result = metaTagExtraction(make_data(C1=[np.nan], RP=[np.nan]), Field="AU_CO")
    check("AU_CO | C1=NaN, RP=NaN → lista vuota", result["AU_CO"].iloc[0] == [], result["AU_CO"].iloc[0])
except Exception as e:
    fail("AU_CO | C1=NaN, RP=NaN → lista vuota", e)

try:
    # Paese non riconosciuto → lista vuota, non crash
    result = metaTagExtraction(make_data(C1=[["Univ Narnia, Narnia, Neverland"]]), Field="AU_CO")
    check("AU_CO | paese sconosciuto → lista vuota", isinstance(result["AU_CO"].iloc[0], list), result["AU_CO"].iloc[0])
except Exception as e:
    fail("AU_CO | paese sconosciuto → lista vuota", e)

try:
    # ENGLAND → UNITED KINGDOM
    result = metaTagExtraction(make_data(C1=[["Univ Oxford, Oxford, England"]]), Field="AU_CO")
    check("AU_CO | ENGLAND → UNITED KINGDOM",
          "UNITED KINGDOM" in result["AU_CO"].iloc[0] and "ENGLAND" not in result["AU_CO"].iloc[0],
          result["AU_CO"].iloc[0])
except Exception as e:
    fail("AU_CO | ENGLAND → UNITED KINGDOM", e)

try:
    # SCOTLAND → UNITED KINGDOM
    result = metaTagExtraction(make_data(C1=[["Univ Edinburgh, Edinburgh, Scotland"]]), Field="AU_CO")
    check("AU_CO | SCOTLAND → UNITED KINGDOM", "UNITED KINGDOM" in result["AU_CO"].iloc[0], result["AU_CO"].iloc[0])
except Exception as e:
    fail("AU_CO | SCOTLAND → UNITED KINGDOM", e)

try:
    # WALES → UNITED KINGDOM
    result = metaTagExtraction(make_data(C1=[["Univ Cardiff, Cardiff, Wales"]]), Field="AU_CO")
    check("AU_CO | WALES → UNITED KINGDOM", "UNITED KINGDOM" in result["AU_CO"].iloc[0], result["AU_CO"].iloc[0])
except Exception as e:
    fail("AU_CO | WALES → UNITED KINGDOM", e)

try:
    # UNITED STATES → USA
    result = metaTagExtraction(make_data(C1=[["MIT, Cambridge, United States"]]), Field="AU_CO")
    check("AU_CO | UNITED STATES → USA",
          "USA" in result["AU_CO"].iloc[0] and "UNITED STATES" not in result["AU_CO"].iloc[0],
          result["AU_CO"].iloc[0])
except Exception as e:
    fail("AU_CO | UNITED STATES → USA", e)

try:
    # RUSSIAN FEDERATION → RUSSIA
    result = metaTagExtraction(make_data(C1=[["Univ Moscow, Moscow, Russian Federation"]]), Field="AU_CO")
    check("AU_CO | RUSSIAN FEDERATION → RUSSIA", "RUSSIA" in result["AU_CO"].iloc[0], result["AU_CO"].iloc[0])
except Exception as e:
    fail("AU_CO | RUSSIAN FEDERATION → RUSSIA", e)

try:
    # Più affiliazioni → più paesi
    result = metaTagExtraction(
        make_data(C1=[["Univ Roma, Rome, Italy", "MIT, Cambridge, United States"]]),
        Field="AU_CO"
    )
    countries = result["AU_CO"].iloc[0]
    check("AU_CO | affiliazioni multiple → più paesi",
          "ITALY" in countries and "USA" in countries, countries)
except Exception as e:
    fail("AU_CO | affiliazioni multiple → più paesi", e)


# ===========================================================================
# AU1_CO
# ===========================================================================

try:
    result = metaTagExtraction(base_data, Field="AU1_CO")
    check("AU1_CO | base → ITALY", result["AU1_CO"].iloc[0] == "ITALY", result[["AU1_CO"]].head())
except Exception as e:
    fail("AU1_CO | base → ITALY", e)

try:
    result = metaTagExtraction(make_data(C1=[[]], RP=[np.nan]), Field="AU1_CO")
    check("AU1_CO | C1=[], RP=NaN → stringa vuota", result["AU1_CO"].iloc[0] == "", result["AU1_CO"].iloc[0])
except Exception as e:
    fail("AU1_CO | C1=[], RP=NaN → stringa vuota", e)

try:
    result = metaTagExtraction(make_data(C1=[None], RP=[np.nan]), Field="AU1_CO")
    check("AU1_CO | C1=None, RP=NaN → stringa vuota", result["AU1_CO"].iloc[0] == "", result["AU1_CO"].iloc[0])
except Exception as e:
    fail("AU1_CO | C1=None, RP=NaN → stringa vuota", e)

try:
    result = metaTagExtraction(make_data(C1=[["Univ Narnia, Narnia, Neverland"]]), Field="AU1_CO")
    check("AU1_CO | paese sconosciuto → stringa vuota", result["AU1_CO"].iloc[0] == "", result["AU1_CO"].iloc[0])
except Exception as e:
    fail("AU1_CO | paese sconosciuto → stringa vuota", e)

try:
    result = metaTagExtraction(make_data(C1=[["Univ Oxford, Oxford, England"]]), Field="AU1_CO")
    check("AU1_CO | ENGLAND → UNITED KINGDOM", result["AU1_CO"].iloc[0] == "UNITED KINGDOM", result["AU1_CO"].iloc[0])
except Exception as e:
    fail("AU1_CO | ENGLAND → UNITED KINGDOM", e)

try:
    # Con più affiliazioni → solo il primo paese
    result = metaTagExtraction(
        make_data(C1=[["Univ Roma, Rome, Italy", "MIT, Cambridge, United States"]]),
        Field="AU1_CO"
    )
    check("AU1_CO | affiliazioni multiple → solo primo paese",
          result["AU1_CO"].iloc[0] == "ITALY", result["AU1_CO"].iloc[0])
except Exception as e:
    fail("AU1_CO | affiliazioni multiple → solo primo paese", e)


# ===========================================================================
# CR_AU
# ===========================================================================

try:
    result = metaTagExtraction(
        make_data(CR=[["Smith J, 2020, SCIENCE, DOI: 10.1000/xyz"]]),
        Field="CR_AU"
    )
    check("CR_AU | base → autore estratto", "Smith J" in result["CR_AU"].iloc[0], result[["CR_AU"]].head())
except Exception as e:
    fail("CR_AU | base → autore estratto", e)

try:
    result = metaTagExtraction(make_data(CR=[[]]), Field="CR_AU")
    check("CR_AU | lista vuota → stringa vuota", result["CR_AU"].iloc[0] == "", result["CR_AU"].iloc[0])
except Exception as e:
    fail("CR_AU | lista vuota → stringa vuota", e)

try:
    result = metaTagExtraction(make_data(CR=[None]), Field="CR_AU")
    check("CR_AU | CR=None → stringa vuota", result["CR_AU"].iloc[0] == "", result["CR_AU"].iloc[0])
except Exception as e:
    fail("CR_AU | CR=None → stringa vuota", e)

try:
    # Stringhe troppo corte (<10 char) → filtrate
    result = metaTagExtraction(make_data(CR=[["Short"]]), Field="CR_AU")
    check("CR_AU | stringa corta → filtrata", result["CR_AU"].iloc[0] == "", result["CR_AU"].iloc[0])
except Exception as e:
    fail("CR_AU | stringa corta → filtrata", e)

try:
    result = metaTagExtraction(
        make_data(CR=[["Smith J, 2020, SCIENCE, DOI", "Jones A, 2021, NATURE, DOI"]]),
        Field="CR_AU"
    )
    check("CR_AU | referenze multiple → separate da ;", ";" in result["CR_AU"].iloc[0], result["CR_AU"].iloc[0])
except Exception as e:
    fail("CR_AU | referenze multiple → separate da ;", e)

try:
    # Stringa malformata senza virgola → non crasha
    result = metaTagExtraction(make_data(CR=[["SmithJ2020JTESTnocommaXXXXX"]]), Field="CR_AU")
    check("CR_AU | stringa malformata → non crasha", isinstance(result["CR_AU"].iloc[0], str), result["CR_AU"].iloc[0])
except Exception as e:
    fail("CR_AU | stringa malformata → non crasha", e)


# ===========================================================================
# CR_SO
# ===========================================================================

try:
    result = metaTagExtraction(
        make_data(CR=[["Smith J, 2020, SCIENCE, vol1"]], DB=["ISI"]),
        Field="CR_SO"
    )
    check("CR_SO | base ISI → source estratta", "SCIENCE" in result["CR_SO"].iloc[0], result[["CR_SO"]].head())
except Exception as e:
    fail("CR_SO | base ISI → source estratta", e)

try:
    result = metaTagExtraction(
        make_data(CR=[["NATURE, 2020, Smith J, vol1"]], DB=["SCOPUS"]),
        Field="CR_SO"
    )
    check("CR_SO | base SCOPUS → source estratta", "NATURE" in result["CR_SO"].iloc[0], result["CR_SO"].iloc[0])
except Exception as e:
    fail("CR_SO | base SCOPUS → source estratta", e)

try:
    result = metaTagExtraction(make_data(CR=[[]]), Field="CR_SO")
    check("CR_SO | lista vuota → stringa vuota (non None)", result["CR_SO"].iloc[0] == "", result["CR_SO"].iloc[0])
except Exception as e:
    fail("CR_SO | lista vuota → stringa vuota (non None)", e)

try:
    result = metaTagExtraction(make_data(CR=[None]), Field="CR_SO")
    check("CR_SO | CR=None → stringa vuota", result["CR_SO"].iloc[0] == "", result["CR_SO"].iloc[0])
except Exception as e:
    fail("CR_SO | CR=None → stringa vuota", e)

try:
    # Poche virgole → filtrata, non crash
    result = metaTagExtraction(make_data(CR=[["Smith J, 2020"]], DB=["ISI"]), Field="CR_SO")
    check("CR_SO | poche virgole → filtrata", result["CR_SO"].iloc[0] == "", result["CR_SO"].iloc[0])
except Exception as e:
    fail("CR_SO | poche virgole → filtrata", e)

try:
    result = metaTagExtraction(
        make_data(CR=[["Smith J, 2020, SCIENCE, v1", "Jones A, 2021, NATURE, v2"]], DB=["ISI"]),
        Field="CR_SO"
    )
    check("CR_SO | sorgenti multiple → separate da ;", ";" in result["CR_SO"].iloc[0], result["CR_SO"].iloc[0])
except Exception as e:
    fail("CR_SO | sorgenti multiple → separate da ;", e)


# ===========================================================================
# metaTagExtraction (generale)
# ===========================================================================

try:
    original_cols = set(base_data.columns)
    _ = metaTagExtraction(base_data, Field="AU_CO")
    check("metaTagExtraction | df originale non mutato",
          set(base_data.columns) == original_cols and "AU_CO" not in base_data.columns,
          list(base_data.columns))
except Exception as e:
    fail("metaTagExtraction | df originale non mutato", e)

try:
    result = metaTagExtraction(base_data, Field="AU_CO")
    check("metaTagExtraction | ritorna DataFrame", isinstance(result, pd.DataFrame), type(result))
except Exception as e:
    fail("metaTagExtraction | ritorna DataFrame", e)

try:
    result = metaTagExtraction(base_data, Field="UNKNOWN_FIELD")
    check("metaTagExtraction | Field sconosciuto → non crasha", isinstance(result, pd.DataFrame), type(result))
except Exception as e:
    fail("metaTagExtraction | Field sconosciuto → non crasha", e)


# ===========================================================================
# RIEPILOGO
# ===========================================================================

total = passed + failed
print()
print("=" * 45)
print(f"  Totale: {total}  |  ✅ {passed} passed  |  ❌ {failed} failed")
print("=" * 45)