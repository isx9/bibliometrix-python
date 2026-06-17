from .utils import *
from .cocmatrix import *


def biblionetwork(
    M,
    analysis="coupling",
    network="authors",
    n=None,
    sep=";",
    short=False,
    shortlabel=True,
    remove_terms=None,
    synonyms=None
):

    def crossprod(A, B):
        return A.T @ B

    NetMatrix = None

    # SAFETY CHECK
    if M is None:
        print("Input object is None")
        return None

    # ---------------- COUPLING ---------------- #

    if analysis == "coupling":
        # PATCH: CR-based coupling is not viable for OpenAlex or PubMed because
        # CR contains raw URLs (OpenAlex) or empty lists (PubMed) instead of
        # formatted WoS reference strings. Each URL is unique so cocMatrix builds
        # a massive sparse matrix that crashes with OOM. Skip early.
        db_name = ""
        if "DB" in M.columns and not M["DB"].empty:
            db_name = str(M["DB"].iloc[0]).lower()
    

        if network == "authors":

            WA = cocMatrix(M, Field="AU", type="sparse", n=n, sep=sep, short=short)
            WCR = cocMatrix(M, Field="CR", type="sparse", n=n, sep=sep, short=short)

            if WA is None or WCR is None:
                return None

            CRA = crossprod(WCR, WA)
            NetMatrix = crossprod(CRA, CRA)

        elif network == "references":

            WCR = cocMatrix(M, Field="CR", type="sparse", n=n, sep=sep, short=short)

            if WCR is None:
                return None

            WCR = WCR.T
            NetMatrix = crossprod(WCR, WCR)

        elif network == "sources":

            WSO = cocMatrix(M, Field="SO", type="sparse", n=n, sep=sep, short=short)
            WCR = cocMatrix(M, Field="CR", type="sparse", n=n, sep=sep, short=short)

            if WSO is None or WCR is None:
                return None

            CRSO = crossprod(WCR, WSO)
            NetMatrix = crossprod(CRSO, CRSO)

        elif network == "countries":

            WCO = cocMatrix(M, Field="AU_CO", type="sparse", n=n, sep=sep, short=short)
            WCR = cocMatrix(M, Field="CR", type="sparse", n=n, sep=sep, short=short)

            if WCO is None or WCR is None:
                return None

            CRCO = crossprod(WCR, WCO)
            NetMatrix = crossprod(CRCO, CRCO)

    # ---------------- CO-OCCURRENCES ---------------- #

    elif analysis == "co-occurrences":

        if network == "authors":

            WA = cocMatrix(M, Field="AU", type="sparse", n=n, sep=sep, short=short)

        elif network == "keywords":

            WA = cocMatrix(
                M,
                Field="ID",
                type="sparse",
                n=n,
                sep=sep,
                short=short,
                remove_terms=remove_terms,
                synonyms=synonyms
            )

        elif network == "author_keywords":

            WA = cocMatrix(
                M,
                Field="DE",
                type="sparse",
                n=n,
                sep=sep,
                short=short,
                remove_terms=remove_terms,
                synonyms=synonyms
            )

        elif network == "titles":

            WA = cocMatrix(
                M,
                Field="TI_TM",
                type="sparse",
                n=n,
                sep=sep,
                short=short,
                remove_terms=remove_terms,
                synonyms=synonyms
            )

        elif network == "abstracts":

            WA = cocMatrix(
                M,
                Field="AB_TM",
                type="sparse",
                n=n,
                sep=sep,
                short=short,
                remove_terms=remove_terms,
                synonyms=synonyms
            )

        elif network == "sources":

            WA = cocMatrix(M, Field="SO", type="sparse", n=n, sep=sep, short=short)

        else:
            print("Invalid co-occurrence network")
            return None

        if WA is None:
            return None

        NetMatrix = crossprod(WA, WA)

    # ---------------- CO-CITATION ---------------- #

    elif analysis == "co-citation":

        if network == "authors":

            WA = cocMatrix(M, Field="CR_AU", type="sparse", n=n, sep=sep, short=short)

        elif network == "references":

            WA = cocMatrix(M, Field="CR", type="sparse", n=n, sep=sep, short=short)

        elif network == "sources":

            WA = cocMatrix(M, Field="CR_SO", type="sparse", n=n, sep=sep, short=short)

        else:
            print("Invalid co-citation network")
            return None

        if WA is None:
            return None

        NetMatrix = crossprod(WA, WA)

    # ---------------- COLLABORATION ---------------- #

    elif analysis == "collaboration":

        if network == "authors":

            WA = cocMatrix(M, Field="AU", type="sparse", n=n, sep=sep, short=short)

        elif network == "universities":

            WA = cocMatrix(M, Field="AU_UN", type="sparse", n=n, sep=sep, short=short)

        elif network == "countries":

            WA = cocMatrix(M, Field="AU_CO", type="sparse", n=n, sep=sep, short=short)

        else:
            print("Invalid collaboration network")
            return None

        if WA is None:
            return None

        NetMatrix = crossprod(WA, WA)

    # ---------------- FINAL CLEANUP ---------------- #

    if NetMatrix is not None:

        NetMatrix = pd.DataFrame(NetMatrix)

        filtered_columns = [
            col for col in NetMatrix.columns
            if str(col).strip()
        ]

        filtered_index = [
            idx for idx in NetMatrix.index
            if str(idx).strip()
        ]

        NetMatrix = NetMatrix.loc[filtered_index, filtered_columns]

        # PATCH: M may already be a plain DataFrame after term_extraction
        M = M.get() if hasattr(M, 'get') and callable(M.get) and not isinstance(M, pd.DataFrame) else M

        # SAFETY CHECK
        if M is None or M.empty:
            return NetMatrix

        # SAFE DB HANDLING
        # PATCH: default changed from hardcoded "web_of_science" to "" so that
        # unknown sources don't silently get treated as WoS.
        db_name = ""

        if "DB" in M.columns and not M["DB"].empty:
            db_name = str(M["DB"].iloc[0]).lower()

        print(f"db_name: {db_name}")

        # PATCH: the Scopus-specific reference filter now checks for "scopus"
        # (lowercase) to match the normalized db_name above.
        if network == "references" and db_name == "scopus":

            ind = [
                i for i, col in enumerate(NetMatrix.columns)
                if str(col) and str(col)[0].isalpha()
            ]

            NetMatrix = NetMatrix.iloc[ind, ind]

        # PATCH: shortlabel now supported for openalex and pubmed.
        # Both use the same label format as WoS (author + year),
        # so they are routed to the same branch in label_short().
        if network == "references" and shortlabel:

            LABEL = label_short(NetMatrix, db=db_name)
            LABEL = remove_duplicated_labels(LABEL)

            NetMatrix.columns = LABEL
            NetMatrix.index = LABEL

    return NetMatrix


def label_short(NET, db=""):

    LABEL = pd.Series(NET.columns)

    YEAR = LABEL.str.extract(r'(\d{4})')[0].fillna("")

    # PATCH: added "openalex" and "pubmed" to the WoS branch since both
    # sources produce SR strings in the same "Author, Year, Journal" format.
    if db in ("web_of_science", "openalex", "pubmed"):

        AU = LABEL.str.split(" ").str[:2].str.join(" ")
        LABEL = AU + " " + YEAR

    elif db == "scopus":

        AU = LABEL.str.split(". ").str[0]
        LABEL = AU + ". " + YEAR

    # For unknown sources, return labels unchanged to avoid crashes.

    return LABEL.tolist()


def remove_duplicated_labels(LABEL):

    LABEL = pd.Series(LABEL)

    counts = LABEL.value_counts()

    duplicates = counts[counts > 1].index

    for dup in duplicates:

        dup_indices = LABEL[LABEL == dup].index

        LABEL.iloc[dup_indices] = [
            f"{dup}-{i+1}"
            for i in range(len(dup_indices))
        ]

    return LABEL.tolist()
