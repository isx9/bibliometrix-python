from .utils import *


def cocMatrix(
    df,
    Field="AU",
    type="sparse",
    n=None,
    sep=";",
    binary=True,
    short=False,
    remove_terms=None,
    synonyms=None
):
    """
    Computes occurrences between elements of a Tag Field from a bibliographic data frame.
    """

    # PATCH: df may be a Shiny reactive Value or a plain DataFrame
    M = df.get() if hasattr(df, 'get') and callable(df.get) and not isinstance(df, pd.DataFrame) else df

    # SAFETY CHECK
    if M is None or M.empty:
        print("Input dataframe is empty")
        return None

    # SAFETY CHECK FOR SR
    if "LABEL" not in M.columns:
        if "SR" not in M.columns:
            print("SR column missing")
            return None

        M.index = M["SR"]
        print("Processing field: " + Field + "\n")

    RowNames = M.index

    # REMOVE TERMS AND MERGE SYNONYMS
    if Field in ["ID", "DE", "TI", "TI_TM", "AB", "AB_TM"]:

        if Field not in M.columns:
            print(f"{Field} column missing")
            return None

        Fi = M[Field].fillna("").apply(
            lambda x: x if isinstance(x, list)
            else [i.strip() for i in str(x).split(sep)]
        )

        TERMS = pd.DataFrame({
            "item": [
                item.upper()
                for sublist in Fi
                for item in sublist
            ],
            "SR": M.index.repeat(Fi.str.len())
        })

        # Merge synonyms
        if synonyms:
            synonyms_dict = {
                syn.split(";")[0].strip().upper():
                [s.strip().upper() for s in syn.split(";")[1:]]
                for syn in synonyms
            }

            for key, values in synonyms_dict.items():
                TERMS["item"] = TERMS["item"].replace(values, key)

        # Remove terms
        if remove_terms:
            TERMS = TERMS[
                ~TERMS["item"].str.upper().isin(
                    [term.strip().upper() for term in remove_terms]
                )
            ]

        TERMS = TERMS.groupby("SR")["item"].apply(
            lambda x: ";".join(x)
        ).reset_index()

        M = (
            M.drop(columns=[Field, "SR"], errors="ignore")
            .merge(TERMS, on="SR", how="left")
            .rename(columns={"item": Field})
        )

        M.index = RowNames

    # SAFETY CHECK FOR CR
    if Field == "CR":

        if "CR" not in M.columns:
            print("CR column missing")
            return None

        M["CR"] = M["CR"].apply(
            lambda x: [
                ref.replace("DOI;", "DOI ")
                for ref in x
            ] if isinstance(x, list) else x
        )

    # FIELD EXISTENCE CHECK
    if Field in M.columns:

        Fi = M[Field].fillna("").apply(
            lambda x: x if isinstance(x, list)
            else [i.strip() for i in str(x).split(sep)]
        )

    else:
        print(f"Field {Field} is not a column name of input data frame")
        return None

    Fi = Fi.apply(lambda x: [i.strip() for i in x])

    # DELETE INVALID REFERENCES
    if Field == "CR":
        Fi = Fi.apply(
            lambda x: [i for i in x if len(i) > 10]
        )

    allField = [
        item
        for sublist in Fi
        for item in sublist
        if item
    ]

    # REDUCE REFERENCES
    if Field == "CR":
        allField = reduceRefs(allField)
        Fi = Fi.apply(reduceRefs)

    tabField = pd.Series(allField).value_counts()
    uniqueField = tabField.index.tolist()

    if n:
        uniqueField = uniqueField[:n]

    elif short:
        uniqueField = tabField[tabField > 1].index.tolist()

    if not uniqueField:
        print("Matrix is empty!!")
        return None

    # MATRIX CREATION
    if type == "matrix" or not binary:
        WF = np.zeros((M.shape[0], len(uniqueField)))

    elif type == "sparse":
        WF = lil_matrix((M.shape[0], len(uniqueField)))

    else:
        print("Error in type argument")
        return None

    col_idx = {
        term: idx
        for idx, term in enumerate(uniqueField)
    }

    row_idx = {
        sr: idx
        for idx, sr in enumerate(M.index)
    }

    # BUILD MATRIX
    for i, terms in Fi.items():

        if terms:

            if binary:

                indices = [
                    col_idx[term]
                    for term in set(terms)
                    if term in col_idx
                ]

                WF[row_idx[i], indices] = 1

            else:

                term_counts = pd.Series(terms).value_counts()

                for term, count in term_counts.items():

                    if term in col_idx:
                        WF[row_idx[i], col_idx[term]] = count

    if type == "sparse" and not binary:
        WF = lil_matrix(WF)

    # CONVERT TO DATAFRAME
    WF_df = pd.DataFrame(
        WF.toarray(),
        index=M.index,
        columns=uniqueField
    )

    if binary:
        WF_df = WF_df.astype(int)

    return WF_df


def reduceRefs(refs):
    """
    Remove everything after "V" followed by a digit and "DOI " from references.
    """

    reduced_refs = []

    for ref in refs:

        if not isinstance(ref, str):
            continue

        # Remove everything after V followed by digit
        v_match = re.search(r"V\d", ref)

        if v_match:
            ref = ref[:v_match.start()]

        # Remove everything after DOI
        doi_match = re.search(r"DOI ", ref)

        if doi_match:
            ref = ref[:doi_match.start()]

        reduced_refs.append(ref.strip())

    return reduced_refs
