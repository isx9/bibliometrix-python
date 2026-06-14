import pandas as pd
from .utils import *


def metaTagExtraction(df, Field="AU_CO", sep=";", aff_disamb=False):
    """
    Extract metadata tags from a DataFrame based on the specified field.
    Supports both pandas DataFrame and Shiny reactive.Value.
    """

    # PATCH: support both Shiny reactive.Value and pandas DataFrame
    if hasattr(df, "get") and callable(df.get) and not isinstance(df, pd.DataFrame):
        M = df.get().copy()
    else:
        M = df.copy()

    if Field == "SR":
        M = SR(M)

    if Field == "CR_AU":
        M = CR_AU(M)

    if Field == "CR_SO":
        M = CR_SO(M)

    if Field == "AU_CO":
        M = AU_CO(M)

    if Field == "AU1_CO":
        M = AU1_CO(M)

    if Field == "AU_UN":
        if aff_disamb:
            M = AU_UN(M, sep)
        else:
            M["AU_UN"] = M["C1"].apply(
                lambda x: ";".join(x) if isinstance(x, list) else str(x)
            ).str.replace(r"\[.*?\] ", "", regex=True)

            M["AU1_UN"] = M["RP"].astype(str).str.split(sep).apply(
                lambda l: l[0] if isinstance(l, list) else l
            )

            ind = M["AU1_UN"].str.find("),")
            a = ind[ind > -1].index
            M.loc[a, "AU1_UN"] = M.loc[a, "AU1_UN"].str[ind[a] + 2:]

    return M

def SR(M):
    listAU = M["AU"].apply(lambda l: [x.strip() for x in l])
    if M["DB"].iloc[0].lower() == "scopus":
        listAU = listAU.apply(
            lambda l: [x.replace(" ", ",").replace(",,", ",").replace(" ", "") for x in l]
        )
    FirstAuthors = listAU.apply(
        lambda l: l[0] if len(l) > 0 else "NA"
    ).str.replace(",", " ")

    no_art = M["JI"] == ""
    M.loc[no_art, "JI"] = M.loc[no_art, "SO"]
    J9 = M["JI"].str.replace(".", " ", regex=False).str.strip()
    SR = FirstAuthors + ", " + M["PY"].astype(str) + ", " + J9

    M["SR_FULL"] = SR.str.replace(r"\s+", " ", regex=True)
   
    M["SR"] = SR.str.replace(r"\s+", " ", regex=True)
    
    return M


def CR_AU(M):
    listCAU = M["CR"].apply(
        lambda x: x if isinstance(x, list) else []
    ).apply(lambda l: [x for x in l if len(x) > 10])
    FCAU = listCAU.apply(lambda l: [x.split(",")[0].strip() for x in l])
    M["CR_AU"] = FCAU.apply(lambda l: ";".join(l))

    return M


def CR_SO(M):
    listCAU = M["CR"].apply(lambda x: x if isinstance(x, list) else [])

    if M["DB"].iloc[0].upper() != "SCOPUS":
        FCAU = listCAU.apply(
            lambda l: [x.split(",")[2].strip() for x in l if len(x.split(",")) > 2]
        )
    else:
        FCAU = listCAU.apply(
            lambda l: [x.split(",")[0].strip() for x in l if len(x.split(",")) > 2]
        )

    # PATCH 2: originale usava None per righe vuote (lambda l: ";".join(l) if l else None).
    # None in una colonna stringa causa crash su operazioni .str.* downstream.
    # → sostituito con "" (stringa vuota) per sicurezza e coerenza col modulo.
    M["CR_SO"] = FCAU.apply(lambda l: ";".join(l) if l else "")

    return M


def AU_CO(M, log=False):
    # NOTA: path hardcoded — da parametrizzare in futuro se il working directory
    # può variare tra ambienti (dev / prod / test).
    with open("www/static/countries.txt", "r") as file:
        countries = file.read().splitlines()

    M["AU_CO"] = None
    C1 = M["C1"]

    # PATCH 3: fillna può produrre numpy.float64 (NaN numerico) quando sia C1
    # che RP sono NaN — il loop sottostante tenta di iterare su quel float e crasha.
    # .infer_objects(copy=False) silenziona anche il FutureWarning pandas 3.x sul
    # downcast implicito di fillna.
    # Dopo fillna forziamo ogni cella non-lista a [] per garantire iterabilità.
    C1 = M["C1"].fillna(M["RP"]).infer_objects(copy=False)
    C1 = C1.apply(lambda x: x if isinstance(x, list) else ([] if pd.isna(x) else [x]))

    # NOTA: loop O(n) esplicito — accettabile per dataset tipici,
    # ma vectorizzabile con .apply per grandi volumi.
    for i in range(len(C1)):
        if isinstance(C1.iloc[i], list) and not C1.iloc[i]:
            if pd.notna(M["RP"].iloc[i]):
                C1.at[i] = [M["RP"].iloc[i]]
            else:
                C1.at[i] = []

    results = []
    for i in range(len(M)):
        countries_found = []
        for c1 in C1.iloc[i]:
            if pd.notna(c1):
                # PATCH 4: normalizza la stringa di input PRIMA della ricerca regex
                # in modo che "Russian Federation" venga mappato a "Russia" nel
                # dizionario countries.txt, dove è listato come "Russia".
                # Senza questa normalizzazione il replace post-match non scatta mai
                # perché il paese non viene trovato in primo luogo.
                last_part = (
                    c1.split(",")[-1].strip().upper()
                    .replace("RUSSIAN FEDERATION", "RUSSIA")
                    .replace("UNITED STATES", "USA")
                    .replace("ENGLAND", "UNITED KINGDOM")
                    .replace("SCOTLAND", "UNITED KINGDOM")
                    .replace("WALES", "UNITED KINGDOM")
                    .replace("NORTH IRELAND", "UNITED KINGDOM")
                )
                ind = [
                    c.upper() for c in countries
                    if re.search(
                        r'\b' + re.escape(c.upper()) + r'\b',
                        last_part
                    )
                ]
                countries_found.extend(ind)
        results.append(countries_found)

    M["AU_CO"] = results

    M["AU_CO"] = M["AU_CO"].apply(
        lambda countries: [
            country
            .replace("UNITED STATES", "USA")
            .replace("RUSSIAN FEDERATION", "RUSSIA")
            .replace("TAIWAN", "CHINA")
            .replace("ENGLAND", "UNITED KINGDOM")
            .replace("SCOTLAND", "UNITED KINGDOM")
            .replace("WALES", "UNITED KINGDOM")
            .replace("NORTH IRELAND", "UNITED KINGDOM")
            for country in countries
        ]
    )

    if log:
        with open("affiliations.txt", "w", encoding="utf-8") as file:
            for affiliation in M["AU_CO"]:
                file.write(f"{affiliation}\n")

    return M


def AU1_CO(M, log=False):
    # NOTA: stesso path hardcoded di AU_CO — stessa raccomandazione.
    with open("www/static/countries.txt", "r") as file:
        countries = file.read().splitlines()

    M["AU1_CO"] = None
    C1 = M["C1"]

    # PATCH 3 (AU1_CO): stesso fix di AU_CO — fillna può produrre float NaN
    # non iterabile quando sia C1 che RP sono NaN.
    # .infer_objects(copy=False) silenziona il FutureWarning pandas 3.x.
    C1 = M["C1"].fillna(M["RP"]).infer_objects(copy=False)
    C1 = C1.apply(lambda x: x if isinstance(x, list) else ([] if pd.isna(x) else [x]))

    # NOTA: loop O(n) esplicito — vedere commento in AU_CO.
    for i in range(len(C1)):
        if isinstance(C1.iloc[i], list) and not C1.iloc[i]:
            if pd.notna(M["RP"].iloc[i]):
                C1.at[i] = [M["RP"].iloc[i]]
            else:
                C1.at[i] = []

    results = []
    for i in range(len(M)):
        first_country = None
        for c1 in C1.iloc[i]:
            if pd.notna(c1):
                # PATCH 4 (AU1_CO): normalizza prima della ricerca — stesso
                # motivo di AU_CO (Russian Federation non presente in countries.txt).
                last_part = (
                    c1.split(",")[-1].strip().upper()
                    .replace("RUSSIAN FEDERATION", "RUSSIA")
                    .replace("UNITED STATES", "USA")
                    .replace("ENGLAND", "UNITED KINGDOM")
                    .replace("SCOTLAND", "UNITED KINGDOM")
                    .replace("WALES", "UNITED KINGDOM")
                    .replace("NORTH IRELAND", "UNITED KINGDOM")
                )
                for country in countries:
                    if re.search(r'\b' + re.escape(country.upper()) + r'\b', last_part):
                        first_country = country.upper()
                        break
            if first_country:
                break
        results.append(first_country)

    M["AU1_CO"] = results

    # PATCH 5: originale ritornava None per paese non trovato (else None).
    # Sostituito con "" per coerenza con il resto del modulo.
    # ATTENZIONE: i consumer di AU1_CO che usano `if country is None`
    # devono essere aggiornati a `if not country` per catturare anche "".
    M["AU1_CO"] = M["AU1_CO"].apply(
        lambda country: country
        .replace("UNITED STATES", "USA")
        .replace("RUSSIAN FEDERATION", "RUSSIA")
        .replace("TAIWAN", "CHINA")
        .replace("ENGLAND", "UNITED KINGDOM")
        .replace("SCOTLAND", "UNITED KINGDOM")
        .replace("WALES", "UNITED KINGDOM")
        .replace("NORTH IRELAND", "UNITED KINGDOM")
        if pd.notna(country) else ""
    )

    if log:
        with open("first_author_countries.txt", "w", encoding="utf-8") as file:
            for affiliation in M["AU1_CO"]:
                file.write(f"{affiliation}\n")

    return M


def AU_UN(M, sep):
    C1 = M["C1"].fillna(M["RP"])
    AFF = C1.str.replace(r"\[.*?\] ", "", regex=True)
    indna = AFF.isna()
    AFF[indna] = M["RP"][indna]
    AFF = AFF.str.strip()
    listAFF = AFF.str.split(sep)

    uTags = [
        "UNIV", "COLL", "SCH", "INST", "ACAD", "ECOLE", "CTR", "SCI",
        "CENTRE", "CENTER", "CENTRO", "HOSP", "ASSOC", "COUNCIL",
        "FONDAZ", "FOUNDAT", "ISTIT", "LAB", "TECH", "RES", "CNR",
        "ARCH", "SCUOLA", "PATENT OFF", "CENT LIB", "HEALTH", "NATL",
        "LIBRAR", "CLIN", "FDN", "OECD", "FAC", "WORLD BANK", "POLITECN",
        "INT MONETARY FUND", "CLIMA", "METEOR", "OFFICE", "ENVIR",
        "CONSORTIUM", "OBSERVAT", "AGRI", "MIT ", "INFN", "SUNY "
    ]

    def extract_affiliations(l):
        index = []
        for item in l:
            item = item.replace("(REPRINT AUTHOR)", "")
            affL = item.split(",")
            indd = [i for i, aff in enumerate(affL) if any(tag in aff for tag in uTags)]
            if not indd:
                index.append("NOTREPORTED")
            elif any(char.isdigit() for char in affL[indd[0]]):
                index.append("NOTDECLARED")
            else:
                index.append(affL[indd[0]])
        return ";".join(index)

    M["AU_UN"] = listAFF.apply(extract_affiliations)

    if M["DB"].iloc[0] in ["ISI", "OPENALEX"] and "C3" in M.columns:
        # PATCH 6: originale usava M["AU_UN"].loc[...] = ... su una Series.
        # Sintassi deprecata che causa SettingWithCopyWarning e può non
        # modificare il DataFrame sottostante in alcune versioni di pandas.
        # → corretto con M.loc[condition, "AU_UN"] = ... (forma raccomandata).
        M.loc[M["C3"].notna() & (M["C3"] != ""), "AU_UN"] = M["C3"]
        M["AU_UN"] = M["AU_UN"].str.split(sep).apply(
            lambda l: sep.join([x.strip() for x in l])
        )

    M["AU_UN"] = M["AU_UN"].str.replace(r"\\&", "AND", regex=True).str.replace("&", "AND", regex=False)

    RP = M["RP"].fillna(M["C1"])
    AFF = RP.str.replace(r"\[.*?\] ", "", regex=True)
    indna = AFF.isna()
    AFF[indna] = M["RP"][indna]
    AFF = AFF.str.strip()
    listAFF = AFF.str.split(sep)

    M["AU1_UN"] = listAFF.apply(extract_affiliations)
    M["AU1_UN"] = M["AU1_UN"].str.replace(r"\\&", "AND", regex=True).str.replace("&", "AND", regex=False)

    M["AU_UN_NR"] = None
    listAFF2 = M["AU_UN"].str.split(sep)
    cont = listAFF2.apply(lambda l: [i for i, x in enumerate(l) if x == "NR"])

    for i, indices in enumerate(cont):
        if indices:
            M.at[i, "AU_UN_NR"] = ";".join([listAFF.iloc[i][j] for j in indices])

    # PATCH 7: originale usava None come valore di replace
    # (replace({"NOTDECLARED": None, "NOTREPORTED": None})).
    # None in una colonna stringa causa crash su operazioni .str.* successive.
    # → sostituito con "" (stringa vuota) per sicurezza e coerenza col modulo.
    M["AU_UN"] = M["AU_UN"].replace({"NOTDECLARED": "", "NOTREPORTED": ""})
    M["AU_UN"] = M["AU_UN"].str.replace("NOTREPORTED;", "", regex=False).str.replace(";NOTREPORTED", "", regex=False)
    M["AU_UN"] = M["AU_UN"].str.replace("NOTDECLARED;", "", regex=False).str.replace("NOTDECLARED", "", regex=False)

    return M