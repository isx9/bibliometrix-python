"d9k3qp"

from .utils import *
from .cocmatrix import *


def histNetwork(df, min_citations=0, sep=";", network=True):

    M = df.get()

    # SAFETY CHECK
    if M is None or M.empty:
        print("Input dataframe is empty")
        return None

    # SAFE DB HANDLING
    if 'DB' not in M.columns or M['DB'].empty:
        print("DB column missing")
        return None

    db = str(M['DB'].iloc[0])

    # ENSURE REQUIRED FIELDS
    if 'DI' not in M.columns:
        M['DI'] = ""

    M['DI'] = M['DI'].fillna("").astype(str)

    if 'CR' not in M.columns:
        print("\nYour collection does not contain Cited References metadata (Field CR is missing)\n")
        return None

    # ENSURE CR IS LIST
    M['CR'] = M['CR'].apply(
        lambda x: x if isinstance(x, list)
        else [i.strip() for i in str(x).split(sep)] if pd.notna(x)
        else []
    )

    # SAFE TC HANDLING
    if 'TC' not in M.columns:
        M['TC'] = 0

    M['TC'] = pd.to_numeric(M['TC'], errors='coerce').fillna(0)

    # SAFE PY HANDLING
    if 'PY' in M.columns:
        M['PY'] = pd.to_numeric(M['PY'], errors='coerce')

    # DATABASE ROUTING
    # PATCH: added OPENALEX and PUBMED to the wos() branch.
    # Both sources produce SR and DI fields in the format expected by wos(),
    # so the same matching logic applies. Citation accuracy may be lower for
    # OpenAlex because CR contains OpenAlex URLs instead of formatted strings,
    # but the function will not crash.
    if db in ("Web_of_Science", "OPENALEX", "PUBMED"):
        results = wos(
            M,
            min_citations=min_citations,
            sep=sep,
            network=network
        )

    elif db == "Scopus":
        results = scopus(
            M,
            min_citations=min_citations,
            sep=sep,
            network=network
        )

    else:
        print(f"\nDatabase '{db}' not recognized. Supported: Web_of_Science, OPENALEX, PUBMED, Scopus\n")
        return None

    return results


def wos(M, min_citations, sep, network):

    print("\nWOS DB:\nSearching local citations (LCS) by reference items (SR) and DOIs...\n")

    # SAFETY CHECK
    required_cols = ['PY', 'CR']

    for col in required_cols:
        if col not in M.columns:
            print(f"Missing required column: {col}")
            return None

    # SORT DATA
    M = M.sort_values(by="PY").reset_index(drop=True)

    # UNIQUE LABELS
    M['Paper'] = np.arange(0, len(M))
    M['nLABEL'] = np.arange(0, len(M))

    # PROCESS REFERENCES
    CR = []

    for i, refs in enumerate(M['CR']):

        if not isinstance(refs, list):
            continue

        for ref in refs:

            if not isinstance(ref, str):
                continue

            # DOI EXTRACTION
            doi = ""

            if 'DOI' in ref:
                parts = ref.split('DOI', 1)
                doi = parts[1].strip() if len(parts) > 1 else ""

            # REF PARTS
            ref_parts = ref.split(',')

            au = ref_parts[0].replace('.', ' ').strip() if len(ref_parts) > 0 else ""
            py = ref_parts[1].strip() if len(ref_parts) > 1 else ""
            so = ref_parts[2].strip() if len(ref_parts) > 2 else ""

            sr = f"{au}, {py}, {so}"

            CR.append({
                'ref': ref,
                'Paper': i,
                'DI': doi,
                'AU': au,
                'PY': py,
                'SO': so,
                'SR': sr
            })

    print(f"\nAnalyzing {len(CR)} reference items...\n")

    CR_df = pd.DataFrame(CR)

    # SAFE SR_FULL
    if 'SR_FULL' not in M.columns:
        M['SR_FULL'] = ""

    M['LABEL'] = (
        M['SR_FULL'].fillna('').astype(str).str.upper()
        + " DOI "
        + M['DI'].fillna('').astype(str).str.upper()
    )

    M['LABEL'] = M['LABEL'].str.strip()

    CR_df['LABEL'] = (
        CR_df['SR'].fillna('').astype(str).str.upper()
        + " DOI "
        + CR_df['DI'].fillna('').astype(str).str.upper()
    )

    CR_df['LABEL'] = CR_df['LABEL'].str.strip()

    # MATCH REFERENCES
    L = pd.merge(
        M,
        CR_df,
        on='LABEL',
        how='left',
        suffixes=('_M', '_CR')
    )

    L = L[L['Paper_CR'].notnull()]

    if len(L) > 0:

        L['CITING'] = M.loc[L['Paper_CR'], 'LABEL'].values
        L['nCITING'] = M.loc[L['Paper_CR'], 'nLABEL'].values
        L['CIT_PY'] = M.loc[L['Paper_CR'], 'PY'].values

    # COMPUTE LCS
    LCS = L.groupby('nLABEL').size().reset_index(name='LCS')

    M['LCS'] = (
        M['nLABEL']
        .map(LCS.set_index('nLABEL')['LCS'])
        .fillna(0)
        .astype(int)
    )

    # SAFE OPTIONAL COLUMNS
    optional_cols = ['TI', 'DE', 'ID']

    for col in optional_cols:
        if col not in M.columns:
            M[col] = ""

    histData = M[
        M['TC'] >= min_citations
    ][['LABEL', 'TI', 'DE', 'ID', 'DI', 'PY', 'LCS', 'TC']]

    histData.columns = [
        'Paper',
        'Title',
        'Author_Keywords',
        'KeywordsPlus',
        'DOI',
        'Year',
        'LCS',
        'GCS'
    ]

    WLCR = None

    # NETWORK BUILDING
    if network and len(L) > 0:

        CITING = L.groupby('CITING').agg(
            LCR=('LABEL', lambda x: ';'.join(x.dropna())),
            PY=('CIT_PY', 'first'),
            Paper=('Paper_CR', 'first')
        ).reset_index().sort_values(by='PY')

        M['LCR'] = ""

        for idx, row in CITING.iterrows():

            paper_idx = int(row['Paper'])

            if 0 <= paper_idx < len(M):
                M.at[paper_idx, 'LCR'] = row['LCR']

        # DUPLICATE LABEL HANDLING
        st = False
        i = 0

        while not st:

            ind = M['LABEL'].duplicated(keep=False)

            if ind.any():

                i += 1

                M.loc[ind, 'LABEL'] = (
                    M.loc[ind, 'LABEL']
                    + f"-{chr(96 + i)}"
                )

            else:
                st = True

        M.index = M['LABEL'].str.strip()

        M['LCR'] = M['LCR'].fillna('')

        WLCR = cocMatrix(
            reactive.Value(M),
            Field="LCR",
            sep=sep
        )

        if WLCR is not None:

            missing_LABEL = set(M.index) - set(WLCR.columns)

            if missing_LABEL:

                missing_df = pd.DataFrame(
                    0,
                    index=WLCR.index,
                    columns=list(missing_LABEL)
                )

                WLCR = pd.concat([WLCR, missing_df], axis=1)

        print(
            f"\nFound {len(M[M['LCS'] > 0])} documents with non-empty Local Citations (LCS)\n"
        )

    results = {
        'NetMatrix': WLCR,
        'histData': histData,
        'M': M,
        'LCS': M['LCS'].tolist()
    }

    return results


def scopus(M, min_citations=0, sep=";", network=True):

    print("\nScopus DB:\nProcessing citations...\n")

    required_cols = ['CR', 'SR']

    for col in required_cols:
        if col not in M.columns:
            print(f"Missing required column: {col}")
            return None

    # ENSURE CR LISTS
    M['CR'] = M['CR'].apply(
        lambda x: x if isinstance(x, list)
        else [i.strip() for i in str(x).split(sep)] if pd.notna(x)
        else []
    )

    CR = M['CR']

    CR = pd.DataFrame({
        'SR_citing': np.repeat(M['SR'], CR.str.len()),
        'ref': [item for sublist in CR for item in sublist]
    })

    CR['PY'] = pd.to_numeric(
        CR['ref'].str.extract(r'.*\((\d{4})\).*')[0],
        errors='coerce'
    )

    CR['AU'] = (
        CR['ref']
        .str.extract(r'^(.*?),')[0]
        .str.replace('.', '', regex=False)
        .str.strip()
    )

    CR['PP'] = CR['ref'].str.extract(r'PP\. (\d+-\d+)')[0]

    CR = CR.dropna(subset=['PY'])

    print(f"\nFiltered {len(CR)} valid citations...\n")

    # SAFE OPTIONAL COLUMNS
    optional_cols = ['AU', 'BP', 'EP']

    for col in optional_cols:
        if col not in M.columns:
            M[col] = ""

    M_merge = M[['AU', 'PY', 'BP', 'EP', 'SR']].copy()

    M_merge['AU'] = (
        M_merge['SR']
        .str.extract(r'^(.*?),')[0]
        .str.replace('.', '', regex=False)
        .str.strip()
    )

    M_merge['BP'] = pd.to_numeric(M_merge['BP'], errors='coerce')
    M_merge['EP'] = pd.to_numeric(M_merge['EP'], errors='coerce')

    M_merge['PP'] = M_merge.apply(
        lambda row: f"{row['BP']}-{row['EP']}"
        if pd.notna(row['BP'])
        else np.nan,
        axis=1
    )

    M_merge['Included'] = True

    M_merge.rename(columns={'SR': 'SR_cited'}, inplace=True)

    CR = CR.merge(M_merge, on=['PY', 'AU'], how='left')

    CR = CR[CR['Included'].notna()]

    print(f"\nFound {len(CR)} matching citations...\n")

    LCS = CR.groupby('SR_cited').size().reset_index(name='LCS')

    M = M.merge(
        LCS,
        left_on='SR',
        right_on='SR_cited',
        how='left'
    ).fillna({'LCS': 0})

    print(f"\nCalculated Local Citation Scores (LCS) for {len(M)} papers...\n")

    # SAFE OPTIONAL FIELDS
    output_cols = ['SR_FULL', 'TI', 'DE', 'ID', 'DI']

    for col in output_cols:
        if col not in M.columns:
            M[col] = ""

    histData = M[
        ['SR_FULL', 'TI', 'DE', 'ID', 'DI', 'PY', 'LCS', 'TC']
    ].copy()

    histData.columns = [
        'Paper',
        'Title',
        'Author_Keywords',
        'KeywordsPlus',
        'DOI',
        'Year',
        'LCS',
        'GCS'
    ]

    histData = histData.sort_values(by='Year').reset_index(drop=True)

    WLCR = None

    if network:

        print("\nBuilding co-citation matrix...\n")

        CRadd = pd.DataFrame({
            'SR_citing': M['SR'].unique(),
            'SR_cited': M['SR'].unique(),
            'value': 1
        })

        WLCR = CR[['SR_citing', 'SR_cited']].copy()

        WLCR['value'] = 1

        WLCR = pd.concat([WLCR, CRadd]).drop_duplicates()

        WLCR = WLCR.pivot_table(
            index='SR_citing',
            columns='SR_cited',
            values='value',
            fill_value=0
        )

        WLCR = WLCR.loc[
            WLCR.index.isin(CRadd['SR_cited'])
        ]

        print(
            f"\nCo-citation matrix built with {WLCR.shape[0]} rows and {WLCR.shape[1]} columns...\n"
        )

    results = {
        'NetMatrix': WLCR,
        'histData': histData,
        'M': M,
        'LCS': M['LCS'].tolist()
    }

    return results