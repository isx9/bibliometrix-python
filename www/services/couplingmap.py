from .utils import *
from .cocmatrix import *
from .biblionetwork import *
from .termextraction import *
from .networkplot import *
from .histnetwork import *
from .metatagextraction import *
from .tabletag import *

def couplingMap(df, analysis="documents", field="CR", n=500, minfreq=5,
                ngrams=1, community_repulsion=0.1, impact_measure="local",
                stemming=False, size=0.5, label_term=None, n_labels=1, repel=True, clustering="walktrap"):
    
    if analysis not in ["documents", "authors", "sources"]:
        print('\nanalysis argument is incorrect.\n\nPlease select one of the following choices: "documents", "authors", "sources"\n\n')
        return None

    df = metaTagExtraction(df, "SR")
    M = df.get() if hasattr(df, 'get') and callable(df.get) and not isinstance(df, pd.DataFrame) else df

    ngrams = int(ngrams)
    minfreq = max(0, int(minfreq * len(M) // 1000))

    Net = network(df, analysis=analysis, field=field, stemming=stemming, n=n, community_repulsion=community_repulsion, cluster=clustering)

    # PATCH: network() returns None when the matrix is empty (e.g. OpenAlex URL-based references)
    if Net is None:
        print("Network is empty — cannot build coupling map.")
        return None

    net = Net['graph']
  
    NCS = normalizeCitationScore(df, field=analysis, impact_measure=impact_measure)

    # PATCH: normalizeCitationScore may return None if localCitations fails
    if NCS is None:
        print("NCS is None — cannot build coupling map.")
        return None

    if impact_measure == "global":
        NCS['MNLCS'] = NCS['MNGCS']
        NCS['LC'] = NCS['TC']

    NCS.iloc[:, 0] = NCS.iloc[:, 0].str.upper()

    label = pd.Series(net.vs['name'])

    L = pd.DataFrame({'id': label.str.upper()})
    L.columns = [analysis]

    NCS[analysis] = NCS[analysis].astype(str).str.upper()
    L[analysis] = L[analysis].astype(str).str.upper()

    D = L.merge(NCS, left_on=analysis, right_on=analysis, how='left', copy=True)

    label = pd.Series(net.vs['name'])
    
    L = pd.DataFrame({'id': label.str.upper()})
    L.columns = [analysis]
    D = L.merge(NCS, on=analysis, how='left', copy=True)
    
    L = pd.DataFrame({'id': label.str.lower()})
    L.columns = [analysis]
    Net['cluster_res'] = Net['cluster_res'].rename(columns={'vertex': analysis})
    C = L.merge(Net['cluster_res'], on=analysis, how='left', copy=True)
    
    group = Net['cluster_obj'].membership
    color = net.vs['color']
    
    color = [to_hex(c) if pd.notna(c) else "#D3D3D3" for c in color]

    D['group'] = group
    D['color'] = color

    DC = pd.concat([D, C.iloc[:, 1:]], axis=1)
    DC['name'] = DC.iloc[:, 0]
    
    DC = DC.reset_index(drop=True)
    
    df_lab = DC.groupby('group', as_index=False).apply(lambda x: x.assign(
        MNLCS2=x['MNLCS'].where(x['MNLCS'] >= 1),
        MNLCS=round(x['MNLCS'], 2),
        name=x['name'].str.lower(),
        freq=len(x)
    )).sort_values(by=['MNLCS'], ascending=False)

    df = df_lab.groupby('group').apply(lambda x: pd.Series({
        'freq': x['freq'].iloc[0],
        'centrality': x['pagerank_centrality'].mean() * 100,
        'impact': np.nan_to_num(x['MNLCS2'].mean(skipna=True)),
        'label_cluster': x['group'].iloc[0],
        'color': x['color'].iloc[0],
        'label': '\n'.join(x['name'].iloc[:min(n_labels, len(x))].tolist()),
        'words': '\n'.join((x['name'] + ' ' + x['MNLCS'].astype(str)).tolist())
    })).reset_index()

    df['rcentrality'] = df['centrality'].rank()
    df['rimpact'] = df['impact'].rank()

    meandens = df['rimpact'].mean()
    meancentr = df['rcentrality'].mean()
    df = df[df['freq'] >= minfreq]

    # PATCH: if df is empty after frequency filter, return None
    if df.empty:
        print("No clusters passed the frequency filter.")
        return None

    df_lab = df_lab[df_lab['group'].isin(df['group'])]
    df_lab = df_lab.iloc[:, [0, 6, 14, 7, 3]]
    df_lab.columns = [analysis, "Cluster", "ClusterFrequency", "ClusterColor", "NormalizedLocalCitationScore"]

    df_lab['ClusterName'] = df_lab['Cluster'].map(df.set_index('group')['label'])

    M = M.drop(columns=['SR']).reset_index()

    if label_term is None:
        label_term = "null"
    if label_term in ["DE", "ID", "TI", "AB"]:
        w = labeling(M, df_lab, term=label_term, n=n, n_labels=n_labels, analysis=analysis, ngrams=ngrams)
        df['label'] = w

    df['log_freq'] = np.log(df['freq'])
    df['adjusted_color'] = df['color'].apply(lambda x: adjust_color(x, alpha=0.5))

    x_max = df['rcentrality'].max()
    x_range = np.ptp(df['rcentrality'])
    y_min = df['rimpact'].min()
    y_range = np.ptp(df['rimpact'])

    x1 = x_max - 0.02 - (x_range * 0.125) + 0.5
    x2 = x_max - 0.02 + 0.5
    y1 = y_min
    y2 = y_min + (y_range * 0.125)

    def limit_to_first(text):
        if pd.isna(text):
            return ""
        lines = text.split('\n')
        if len(lines) > 10:
            lines = lines[:10]
            lines.append('...')
        return '\n'.join(lines)
    
    df['words'] = df['words'].apply(limit_to_first)
    df['words_daccapo'] = df['words'].str.replace('\n', '<br>')
    
    for i, row in df.iterrows():
        if pd.isna(row['words_daccapo']):
            df.at[i, 'words_daccapo'] = ""

    fig = px.scatter(
        df,
        x='rcentrality',
        y='rimpact',
        size=df['log_freq'] * 15,
        color_discrete_sequence=df['adjusted_color'],
        hover_name='words_daccapo',
        labels={'rcentrality': 'Centrality', 'rimpact': 'Impact'},
    )
    
    fig.update_layout(
        autosize=True,
        width=None,
        height=None,
        margin=dict(l=0, r=0, t=0, b=0)
    )

    fig.update_traces(
        hovertemplate='<b>%{hovertext}</b><extra></extra>',
        hovertext=[words.replace('\n', '<br>') for words in df['words']]
    )

    if 'words_daccapo' in df.columns:
        df = df.drop('words_daccapo', axis=1)

    fig.add_hline(y=meandens, line_dash="dash", line_color="rgba(0,0,0,0.7)")
    fig.add_vline(x=meancentr, line_dash="dash", line_color="rgba(0,0,0,0.7)")

    min_size = 10 * (1 + size)
    max_size = 30 * (1 + size)
    sizeref = 2.0 * max(df['log_freq']) / (max_size**2)
    
    fig.update_traces(
        marker=dict(
            color=df['adjusted_color'],
            symbol='circle',
            sizemode='area',
            sizemin=min_size,
            sizeref=sizeref,
            line=dict(width=10)
        )
    )

    if size > 0:
        labels = df['label'].where(df['freq'] > 1, '').str.lower().str.replace('\n', '<br>')
        text_size = 3 * (1 + size)
        
        if repel:
            fig.add_trace(go.Scatter(
                x=df['rcentrality'],
                y=df['rimpact'],
                text=labels,
                mode='text',
                textposition='top center',
                textfont=dict(size=text_size * 3),
                showlegend=False
            ))
        else:
            fig.add_trace(go.Scatter(
                x=df['rcentrality'],
                y=df['rimpact'],
                text=labels,
                mode='text',
                textposition='middle center',
                textfont=dict(size=text_size * 3),
                showlegend=False
            ))

    rangex = max(meancentr - df['rcentrality'].min(), df['rcentrality'].max() - meancentr)
    rangey = max(meandens - df['rimpact'].min(), df['rimpact'].max() - meandens)

    xlimits = [meancentr - rangex - 0.5, meancentr + rangex + 0.5]
    ylimits = [meandens - rangey - 0.5, meandens + rangey + 0.5]

    fig.update_layout(
        showlegend=False,
        plot_bgcolor='white',
        xaxis=dict(
            title="Centrality",
            showgrid=False,
            showticklabels=False,
            showline=True,
            linewidth=0.5,
            linecolor='black',
            zeroline=False,
            range=xlimits
        ),
        yaxis=dict(
            title="Impact",
            showgrid=False,
            showticklabels=False,
            showline=True,
            linewidth=0.5,
            linecolor='black',
            zeroline=False,
            range=ylimits
        ),
        autosize=True,
        width=None,
        height=None,
    )

    g = fig
    df = df.rename(columns={'words': 'items'})

    params = {
        'analysis': analysis,
        'field': field,
        'n': n,
        'minfreq': minfreq,
        'label_term': label_term,
        'ngrams': ngrams,
        'impact_measure': impact_measure,
        'stemming': stemming,
        'n_labels': n_labels,
        'size': size,
        'community_repulsion': community_repulsion,
        'repel': repel
    }
    params = pd.DataFrame(list(params.items()), columns=['params', 'values'])

    results = {
        'map': g,
        'clusters': df,
        'data': df_lab,
        'nclust': len(df),
        'NCS': D,
        'net': Net,
        'params': params
    }
    return results


def normalizeCitationScore(df, field="documents", impact_measure="local"):
    if field not in ["documents", "authors", "sources"]:
        print('\nfield argument is incorrect.\n\nPlease select one of the following choices: "documents", "authors", "sources"\n\n')
        return None

    if impact_measure == "local":
        lc = localCitations(df, fast_search=False, sep=";")
        # PATCH: localCitations may return None if histNetwork finds no citations
        if lc is None:
            return None
        df = lc['M']
    else:
        # PATCH: df may be reactive here
        df = df.get() if hasattr(df, 'get') and callable(df.get) and not isinstance(df, pd.DataFrame) else df
        df['LCS'] = 0

    df['TC'] = df['TC'].astype(float, errors='ignore')
    df['PY'] = df['PY'].astype(float, errors='ignore')

    df['LCS'] = df['LCS'].replace(0, 1)
    df['NGCS'] = df.groupby('PY')['TC'].transform(lambda x: x / x.mean(skipna=True))
    df['NLCS'] = df.groupby('PY')['LCS'].transform(lambda x: x / x.mean(skipna=True))

    if field == "documents":
        NCS = df[['SR', 'PY', 'NGCS', 'NLCS', 'TC', 'LCS']].rename(columns={
            'NGCS': 'MNGCS',
            'NLCS': 'MNLCS',
            'LCS': 'LC',
            'SR': 'documents'
        })

    elif field == "authors":
        df['AU'] = df['AU'].fillna('').str.split(';')
        exploded = df.explode('AU').assign(AU=lambda x: x['AU'].str.strip())

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

    elif field == "sources":
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

    if impact_measure == "global":
        NCS.drop(columns=['MNLCS', 'LC'], errors='ignore', inplace=True)
    else:
        NCS['MNLCS'] = NCS['MNLCS'].fillna(0)

    return NCS


def network(df, analysis, field, stemming, n, cluster, community_repulsion):
    NetMatrix = None

    # PATCH: extract plain DataFrame before passing to term_extraction or biblionetwork
    df_plain = df.get() if hasattr(df, 'get') and callable(df.get) and not isinstance(df, pd.DataFrame) else df
    
    if analysis == "documents":
        if field == "CR":
            NetMatrix = biblionetwork(df, analysis="coupling", network="references", short=True, shortlabel=False, sep=";")
        else:
            if field in ["TI", "AB"]:
                df_plain = term_extraction(df_plain, field=field, verbose=False, stemming=stemming)
                NetMatrix = biblionetwork(df_plain, analysis="coupling", network="references", short=True, shortlabel=False, sep=";")
    
    elif analysis == "authors":
        if field == "CR":
            NetMatrix = biblionetwork(df, analysis="coupling", network="authors", short=True)
        else:
            if field in ["TI", "AB"]:
                df_plain = term_extraction(df_plain, field=field, verbose=False, stemming=stemming)
    
    elif analysis == "sources":
        if field == "CR":
            NetMatrix = biblionetwork(df, analysis="coupling", network="sources", short=True)
        else:
            if field in ["TI", "AB"]:
                df_plain = term_extraction(df_plain, field=field, verbose=False, stemming=stemming)
    
    if NetMatrix is None:
        print("\n\nNetwork matrix is empty or analysis type is incorrect!\nThe analysis cannot be performed\n\n")
        return None
    
    if not isinstance(NetMatrix, pd.DataFrame):
        NetMatrix = pd.DataFrame(NetMatrix)
    
    NetMatrix = NetMatrix.loc[:, NetMatrix.columns.str.strip() != ""].loc[NetMatrix.index.str.strip() != ""]

    if NetMatrix.shape[0] > 0:
        Net = network_plot(NetMatrix, normalize="salton", n=n, 
                           Title=f"Coupling network of {analysis} using {field}", type="auto",
                           labelsize=2, halo=False, cluster=cluster, remove_isolates=True, 
                           community_repulsion=community_repulsion, remove_multiple=False, 
                           noloops=True, weighted=True, label_cex=True, edgesize=5, 
                           size=1, edges_min=1, label_n=n, verbose=False)
        return Net
    else:
        print("\n\nNetwork matrix is empty!\nThe analysis cannot be performed\n\n")
        return None


def labeling(df, df_lab, term, n, n_labels, analysis, ngrams):
    if term in ["TI", "AB"]:
        # PATCH: df is already a plain DataFrame here — no need to wrap in reactive
        df = term_extraction(df, field=term, ngrams=ngrams, verbose=False)
        term = f"{term}_TM"

    df_lab = df_lab.apply(lambda x: x.astype(str).str.upper().str.strip())
    df = df.apply(lambda x: x.astype(str).str.upper().str.strip())

    if analysis == "documents":
        df = df_lab.merge(df, left_on="documents", right_on="SR", how="left")

    elif analysis == "authors":
        WF = cocMatrix(df, Field=term, short=True)
        WA = cocMatrix(df, Field="AU", n=n, short=True)

        if WA.shape[1] != WF.shape[0]:
            raise ValueError("Dimensioni non allineate tra WA e WF")

        AF = WA.T @ WF

        A = {
            author: ';'.join(
                [name for name, count in zip(WF.columns, AF[i].toarray().flatten()) if count > 0]
            )
            for i, author in enumerate(WA.columns)
        }
        
        A = pd.DataFrame(list(A.items()), columns=["AU", term])
        df = df_lab.merge(A, left_on="authors", right_on="AU", how="left")

    elif analysis == "sources":
        df = df_lab.merge(df, left_on="sources", right_on="SO", how="inner")

    if 'SR' not in df.columns:
        df['SR'] = df.iloc[:, 0]

    df['SR'] = df.iloc[:, 0]
    tab_global = table_tag(df, term)
    tab_global = pd.DataFrame({
        'label': list(tab_global.keys()),
        'tot': list(tab_global.values()),
        'n': len(df)
    })

    df['w'] = df.groupby('Cluster').apply(lambda x: best_lab(x, tab_global, n_labels, term)).explode().reset_index(drop=True)

    return df['w']


def best_lab(df, tab_global, n_labels, term):
    tab = table_tag(df, term)
    tab = pd.DataFrame(list(tab.items()), columns=['label', 'value'])

    tab = tab.explode('label')

    tab = tab.merge(tab_global, on='label', how="left")

    if tab.empty:
        return ""

    tab['conf'] = round(tab['value'] / tab['tot'] * 100, 1).fillna(0)
    tab['supp'] = round(tab['tot'] / tab_global['n'].iloc[0] * 100, 1).fillna(0)
    tab['relevance'] = round(tab['conf'] * tab['supp'] / 100, 1)

    tab = tab.sort_values(by='relevance', ascending=False).head(n_labels)

    return '\n'.join(f"{label} - conf {conf}%" for label, conf in zip(tab['label'], tab['conf'])).lower()


def localCitations(df, fast_search=False, sep=";"):
    df = metaTagExtraction(df, "SR")
    M = df.get() if hasattr(df, 'get') and callable(df.get) and not isinstance(df, pd.DataFrame) else df

    # PATCH: safety check
    if M is None or M.empty:
        return None

    M['TC'] = M['TC'].fillna(0)
    if fast_search:
        loccit = M['TC'].quantile(0.75)
    else:
        loccit = 1
    
    H = histNetwork(df, min_citations=loccit, sep=sep, network=False)

    # PATCH: histNetwork may return None
    if H is None:
        return None

    LCS = H['histData']
    M = H['M']

    # PATCH: if all LCS are 0, return None to avoid empty result propagation
    if 'LCS' not in M.columns or M['LCS'].sum() == 0:
        return None
    
    AU = M['AU'].explode()
    n = AU.groupby(level=0).size()
    
    df_authors = pd.DataFrame({'AU': AU, 'LCS': M['LCS'].repeat(n).values})
    author_counts = df_authors.groupby('AU')['LCS'].sum().reset_index()
    author_counts.columns = ["Authors", "N. of Local Citations"]
    author_counts = author_counts.sort_values(by="N. of Local Citations", ascending=False)
    
    if 'SR' in M.columns:
        LCS = M[['SR', 'DI', 'PY', 'LCS', 'TC']].rename(columns={
            'SR': 'Paper',
            'DI': 'DOI',
            'PY': 'Year',
            'LCS': 'LCS',
            'TC': 'GCS'
        })
        LCS = LCS.sort_values(by='LCS', ascending=False)
    
    CR = {
        'Authors': author_counts,
        'Papers': LCS,
        'M': M
    }
    
    return CR


def adjust_color(color, alpha=0.5):
    """Adjust the color by changing its alpha value."""
    rgba = mcolors.to_rgba(color)
    adjusted_rgba = (rgba[0], rgba[1], rgba[2], alpha)
    return mcolors.to_hex(adjusted_rgba)


def avoid_net_overlaps(coords, labels, sizes, threshold=0.10):
    """Function to avoid label overlapping."""
    df = pd.DataFrame({
        'x': coords[:, 0],
        'y': coords[:, 1] / 2,
        'label': labels,
        'size': sizes
    })
    
    distances = squareform(pdist(df[['x', 'y']], metric='cityblock'))
    
    overlaps = []
    n = len(labels)
    for i in range(n):
        for j in range(i+1, n):
            if distances[i,j] < threshold:
                overlaps.append({
                    'from': labels[i],
                    'to': labels[j],
                    'dist': distances[i,j],
                    'w_from': sizes[i],
                    'w_to': sizes[j]
                })
    
    if not overlaps:
        return []
    
    overlaps_df = pd.DataFrame(overlaps)
    
    labels_to_remove = []
    i = 0
    
    while len(overlaps_df) > 0:
        row = overlaps_df.iloc[0]
        
        if row['w_from'] > row['w_to'] and row['dist'] < threshold:
            label = row['to']
        elif row['w_from'] <= row['w_to'] and row['dist'] < threshold:
            label = row['from']
        else:
            overlaps_df = overlaps_df.iloc[1:]
            continue
        
        overlaps_df = overlaps_df[
            (overlaps_df['from'] != label) & 
            (overlaps_df['to'] != label)
        ]
        labels_to_remove.append(label)
    
    return labels_to_remove