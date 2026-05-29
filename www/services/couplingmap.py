
# Normalizzazione del punteggio di citazione
def normalizeCitationScore(df, field="documents", impact_measure="local"):

    if field not in ["documents", "authors", "sources"]:
        print('\nfield argument is incorrect.\n\nPlease select one of the following choices: "documents", "authors", "sources"\n\n')
        return None

    # SAFETY CHECK
    if df is None:
        return None

    if isinstance(df, reactive.Value):
        df = df.get()

    if df is None or len(df) == 0:
        return None

    # REQUIRED COLUMNS
    required_cols = ['TC', 'PY']

    for col in required_cols:
        if col not in df.columns:
            df[col] = 0

    # LOCAL CITATIONS
    if impact_measure == "local":

        LC = localCitations(
            reactive.Value(df),
            fast_search=False,
            sep=";"
        )

        if LC is None:
            df['LCS'] = 0
        else:
            df = LC['M']

    else:
        df['LCS'] = 0

    # SAFE NUMERIC CONVERSION
    df['TC'] = pd.to_numeric(df['TC'], errors='coerce').fillna(0)
    df['PY'] = pd.to_numeric(df['PY'], errors='coerce')
    df['LCS'] = pd.to_numeric(df['LCS'], errors='coerce').fillna(0)

    # PREVENT DIVISION ERRORS
    df['LCS'] = df['LCS'].replace(0, 1)

    # SAFE NORMALIZATION
    df['NGCS'] = df.groupby('PY')['TC'].transform(
        lambda x: x / x.mean(skipna=True)
        if x.mean(skipna=True) not in [0, np.nan]
        else 0
    )

    df['NLCS'] = df.groupby('PY')['LCS'].transform(
        lambda x: x / x.mean(skipna=True)
        if x.mean(skipna=True) not in [0, np.nan]
        else 0
    )

    # DOCUMENTS
    if field == "documents":

        if 'SR' not in df.columns:
            df['SR'] = ""

        NCS = df[
            ['SR', 'PY', 'NGCS', 'NLCS', 'TC', 'LCS']
        ].rename(columns={
            'NGCS': 'MNGCS',
            'NLCS': 'MNLCS',
            'LCS': 'LC',
            'SR': 'documents'
        })

    # AUTHORS
    elif field == "authors":

        if 'AU' not in df.columns:
            df['AU'] = ""

        df['AU'] = df['AU'].fillna('').astype(str).str.split(';')

        exploded = (
            df.explode('AU')
            .assign(AU=lambda x: x['AU'].astype(str).str.strip())
        )

        NCS = (
            exploded.groupby('AU').agg(
                NP=('PY', 'count'),
                MNGCS=('NGCS', 'mean'),
                MNLCS=('NLCS', 'mean'),
                TC=('TC', 'mean'),
                LC=('LCS', 'mean')
            )
            .reset_index()
            .rename(columns={'AU': 'authors'})
        )

    # SOURCES
    elif field == "sources":

        if 'SO' not in df.columns:
            df['SO'] = ""

        NCS = (
            df.groupby('SO').agg(
                NP=('PY', 'count'),
                MNGCS=('NGCS', 'mean'),
                MNLCS=('NLCS', 'mean'),
                TC=('TC', 'mean'),
                LC=('LCS', 'mean')
            )
            .reset_index()
            .rename(columns={'SO': 'sources'})
        )

    # GLOBAL IMPACT
    if impact_measure == "global":

        NCS.drop(
            columns=['MNLCS', 'LC'],
            errors='ignore',
            inplace=True
        )

    else:

        if 'MNLCS' in NCS.columns:
            NCS['MNLCS'] = NCS['MNLCS'].fillna(0)

    return NCS


# Network
def network(df, analysis, field, stemming, n, cluster, community_repulsion):

    NetMatrix = None

    # SAFETY CHECK
    if df is None:
        return None

    # DOCUMENTS
    if analysis == "documents":

        if field == "CR":

            NetMatrix = biblionetwork(
                df,
                analysis="coupling",
                network="references",
                short=True,
                shortlabel=False,
                sep=";"
            )

        else:

            if field in ["TI", "AB"]:

                df = term_extraction(
                    df,
                    field=field,
                    verbose=False,
                    stemming=stemming
                )

                NetMatrix = biblionetwork(
                    df,
                    analysis="coupling",
                    network="references",
                    short=True,
                    shortlabel=False,
                    sep=";"
                )

    # AUTHORS
    elif analysis == "authors":

        if field == "CR":

            NetMatrix = biblionetwork(
                df,
                analysis="coupling",
                network="authors",
                short=True
            )

    # SOURCES
    elif analysis == "sources":

        if field == "CR":

            NetMatrix = biblionetwork(
                df,
                analysis="coupling",
                network="sources",
                short=True
            )

    # EMPTY CHECK
    if NetMatrix is None:

        print(
            "\n\nNetwork matrix is empty or analysis type is incorrect!\nThe analysis cannot be performed\n\n"
        )

        return None

    # SAFE DATAFRAME
    if not isinstance(NetMatrix, pd.DataFrame):
        NetMatrix = pd.DataFrame(NetMatrix)

    if NetMatrix.empty:
        return None

    # REMOVE EMPTY LABELS
    NetMatrix = NetMatrix.loc[
        NetMatrix.index.astype(str).str.strip() != ""
    ]

    NetMatrix = NetMatrix.loc[
        :,
        NetMatrix.columns.astype(str).str.strip() != ""
    ]

    if NetMatrix.shape[0] > 0:

        Net = network_plot(
            NetMatrix,
            normalize="salton",
            n=n,
            Title=f"Coupling network of {analysis} using {field}",
            type="auto",
            labelsize=2,
            halo=False,
            cluster=cluster,
            remove_isolates=True,
            community_repulsion=community_repulsion,
            remove_multiple=False,
            noloops=True,
            weighted=True,
            label_cex=True,
            edgesize=5,
            size=1,
            edges_min=1,
            label_n=n,
            verbose=False
        )

        return Net

    else:

        print(
            "\n\nNetwork matrix is empty!\nThe analysis cannot be performed\n\n"
        )

        return None


def localCitations(df, fast_search=False, sep=";"):

    # SAFETY CHECK
    if df is None:
        return None

    df = metaTagExtraction(df, "SR")

    M = df.get()

    if M is None or M.empty:
        return None

    # REQUIRED COLUMNS
    required_cols = ['TC', 'AU']

    for col in required_cols:
        if col not in M.columns:
            if col == 'AU':
                M[col] = [[] for _ in range(len(M))]
            else:
                M[col] = 0

    M['TC'] = pd.to_numeric(
        M['TC'],
        errors='coerce'
    ).fillna(0)

    # FAST SEARCH
    if fast_search:
        loccit = M['TC'].quantile(0.75)
    else:
        loccit = 1

    H = histNetwork(
        df,
        min_citations=loccit,
        sep=sep,
        network=False
    )

    if H is None:
        return None

    LCS = H['histData']
    M = H['M']

    # SAFE AUTHORS
    M['AU'] = M['AU'].apply(
        lambda x: x if isinstance(x, list)
        else [i.strip() for i in str(x).split(sep)] if pd.notna(x)
        else []
    )

    AU = M['AU'].explode()

    n = AU.groupby(level=0).size()

    df_authors = pd.DataFrame({
        'AU': AU,
        'LCS': M['LCS'].repeat(n).values
    })

    author_counts = (
        df_authors.groupby('AU')['LCS']
        .sum()
        .reset_index()
    )

    author_counts.columns = [
        "Authors",
        "N. of Local Citations"
    ]

    author_counts = author_counts.sort_values(
        by="N. of Local Citations",
        ascending=False
    )

    # SAFE PAPER TABLE
    if 'SR' not in M.columns:
        M['SR'] = ""

    for col in ['DI', 'PY', 'LCS', 'TC']:
        if col not in M.columns:
            M[col] = 0 if col in ['LCS', 'TC'] else ""

    LCS = M[
        ['SR', 'DI', 'PY', 'LCS', 'TC']
    ].rename(columns={
        'SR': 'Paper',
        'DI': 'DOI',
        'PY': 'Year',
        'LCS': 'LCS',
        'TC': 'GCS'
    })

    LCS = LCS.sort_values(
        by='LCS',
        ascending=False
    )

    CR = {
        'Authors': author_counts,
        'Papers': LCS,
        'M': M
    }

    return CR