from .utils import *
from .igraph2vis import *
from .termextraction import *
from .biblionetwork import *


def thematic_map(df, field="ID", n=250, minfreq=5, ngrams=1, stemming=False, size=0.5, n_labels=1, community_repulsion=0.1, repel=True, remove_terms=None, synonyms=None, cluster="walktrap", subgraphs=False):

    # PATCH: df may be a Shiny reactive Value or a plain DataFrame
    M = df
    m = df.get() if hasattr(df, 'get') and callable(df.get) and not isinstance(df, pd.DataFrame) else df
    m = m.copy()

    # Set ngrams based on field
    ngrams = int(ngrams) if field in ['TI', 'AB'] else 1
    stemming = True if stemming == "Yes" else False
    minfreq = max(0, int(minfreq * len(m) // 1000))

    # PATCH: extract plain DataFrame for term_extraction calls
    M_plain = df.get() if hasattr(df, 'get') and callable(df.get) and not isinstance(df, pd.DataFrame) else df

    # Preprocess field and create network matrix
    if field == "ID":
        NetMatrix = biblionetwork(M, analysis="co-occurrences", network="keywords", n=n, sep=";", remove_terms=remove_terms, synonyms=synonyms)
    elif field == "DE":
        NetMatrix = biblionetwork(M, analysis="co-occurrences", network="author_keywords", n=n, sep=";", remove_terms=remove_terms, synonyms=synonyms)
    elif field == "TI":
        # PATCH: run term_extraction on plain DataFrame to get TI_TM column
        M_extracted = term_extraction(M_plain, field="TI", ngrams=ngrams, verbose=False, stemming=stemming, remove_terms=remove_terms, synonyms=synonyms)
        # PATCH: wrap in reactive so biblionetwork/cocMatrix can call .get()
        NetMatrix = biblionetwork(reactive.Value(M_extracted), analysis="co-occurrences", network="titles", n=n, sep=";")
        # PATCH: update m with TI_TM so cluster_assignment can use it
        m["TI_TM"] = M_extracted["TI_TM"].values
        M = reactive.Value(M_extracted)
    elif field == "AB":
        # PATCH: same as TI
        M_extracted = term_extraction(M_plain, field="AB", ngrams=ngrams, verbose=False, stemming=stemming, remove_terms=remove_terms, synonyms=synonyms)
        NetMatrix = biblionetwork(reactive.Value(M_extracted), analysis="co-occurrences", network="abstracts", n=n, sep=";")
        # PATCH: update m with AB_TM so cluster_assignment can use it
        m["AB_TM"] = M_extracted["AB_TM"].values
        M = reactive.Value(M_extracted)
    else:
        raise ValueError("Invalid field specified.")

    # PATCH: biblionetwork may return None when the keyword matrix is empty
    # (e.g. PubMed DE is always empty from eSummary API).
    if NetMatrix is not None and not NetMatrix.empty:
        Net = network_plot(NetMatrix, normalize="association", Title="Keyword co-occurrences", type="auto",
                   labelsize=n_labels, halo=False, cluster=cluster, remove_isolates=True,
                   community_repulsion=community_repulsion, remove_multiple=False, noloops=True,
                   weighted=True, label_cex=True, edgesize=5, size=1, edges_min=1, verbose=False)
    else:
        print("\n\nNetwork matrix is empty!\nThe analysis cannot be performed\n\n")
        return None, None, pd.DataFrame(), pd.DataFrame(), pd.DataFrame()

    # PATCH: network_plot may return None on small/empty graphs
    if Net is None:
        return None, None, pd.DataFrame(), pd.DataFrame(), pd.DataFrame()

    S = Net['S']

    NetMatrix.index = NetMatrix.columns = NetMatrix.index.str.lower()

    net = Net['graph']
    net_groups = Net['cluster_obj']
    group = net_groups.membership

    word = net.vs['name']
    node_colors = net.vs['color']
    node_colors = ["#D3D3D3" if c is None else c for c in node_colors]

    W = list(NetMatrix.index.intersection(word))
    index = NetMatrix.index.isin(W)
    ii = [i for i, w in enumerate(word) if w in W]
    word = [word[i] for i in ii]
    group = [group[i] for i in ii]
    node_colors = [node_colors[i] for i in ii]

    C = np.diag(NetMatrix.values)
    S = NetMatrix.values
    sEij = pd.DataFrame(S[np.ix_(index, index)], index=NetMatrix.index[index], columns=NetMatrix.columns[index])
    sC = C[index]

    df_lab = pd.DataFrame({
        'sC': sC,
        'words': word,
        'groups': group,
        'color': node_colors,
        'cluster_label': 'NA'
    })

    df_lab = (df_lab[df_lab['sC'] >= minfreq]
            .groupby('groups')
            .apply(lambda x: pd.Series({
                'freq': x['sC'].sum(),
                'cluster_label': x.loc[x['sC'].idxmax(), 'words'],
                'sC': list(x['sC']),
                'words': ', '.join(x['words'].astype(str)),
                'color': x['color'].iloc[0]
            }))
            .reset_index())

    df_lab = df_lab.assign(
        words=df_lab['words'].str.split(', '),
        sC=df_lab['sC']
    ).explode(['words', 'sC']).reset_index(drop=True)

    index_names = sEij.index
    column_names = sEij.columns
    sEij = triu(sEij.values)

    df_lab_top = df_lab[['words', 'groups']].reset_index(drop=True)
    df_lab_top = df_lab_top.assign(words=df_lab_top['words'].str.split(', ')).explode('words').reset_index(drop=True)

    sEij_df = pd.DataFrame(sEij, index=index_names, columns=column_names)
    sEij_df = pd.DataFrame(sEij_df.values, index=sEij_df.index, columns=sEij_df.columns)
    sEij_df = sEij_df.reset_index(names=['words1'])
    sEij_df = pd.melt(sEij_df, id_vars=['words1'], var_name='words2', value_name='eij')
    sEij_df = sEij_df[sEij_df['eij'] > 0]

    sEij_df['words1'] = sEij_df['words1'].astype(str)
    df_lab_top['words'] = df_lab_top['words'].astype(str)
    df_lab['words'] = df_lab['words'].astype(str)

    sEij_df = sEij_df.merge(df_lab_top[['words', 'groups']],
                   left_on='words1', right_on='words', how='left')
    sEij_df = sEij_df.merge(df_lab_top[['words', 'groups']],
                   left_on='words2', right_on='words', how='left',
                   suffixes=('', '2'))
    sEij_df = sEij_df.drop(['words', 'words_y'], axis=1, errors='ignore')

    df_lab_top = (df_lab[['groups', 'cluster_label', 'color', 'freq']]
              .groupby('groups')
              .first()
              .reset_index())

    sEij_df = sEij_df.loc[:, ~sEij_df.columns.duplicated()]

    df_lab['words'] = df_lab['words'].str.split('\n').str[0]
    df_lab['words'] = df_lab['words'].str.replace(r'^\s*\d+\s*', '', regex=True).str.strip()

    df = sEij_df[
            sEij_df['words1'].isin(df_lab['words'].unique()) &
            sEij_df['words2'].isin(df_lab['words'].unique())
    ]

    if 'eij' not in sEij_df.columns:
        raise KeyError("Column 'eij' does not exist in sEij_df!")

    filtered_df = sEij_df[
        sEij_df['words1'].isin(df_lab['words'].unique()) &
        sEij_df['words2'].isin(df_lab['words'].unique())
    ]

    if filtered_df.empty:
        raise ValueError(
            "The filter removed all rows. "
            "Check the data in df_lab['words'] and sEij_df['words1', 'words2']."
        )

    df = (
        filtered_df
        .assign(ext=lambda x: (x['groups'] != x['groups2']).astype(int))
        .groupby('groups')
        .agg({
            'words1': lambda x: len(set(x)),
            'eij': lambda x: sum(x * x.index),
            'ext': lambda x: sum(x.index * (1 - x))
        })
        .rename(columns={
            'words1': 'n',
            'eij': 'CallonCentrality',
            'ext': 'CallonDensity'
        })
        .assign(
            CallonDensity=lambda x: x['CallonDensity'] / x['n'] * 100,
            RankCentrality=lambda x: x['CallonCentrality'].rank(),
            RankDensity=lambda x: x['CallonDensity'].rank()
        )
        .merge(df_lab_top, on='groups', how='left')
        .rename(columns={'cluster_label': 'Cluster', 'freq': 'ClusterFrequency'})
        .reset_index()
    )

    meandens = df['RankDensity'].mean()
    meancentr = df['RankCentrality'].mean()
    rangex = max(meancentr - df['RankCentrality'].min(), df['RankCentrality'].max() - meancentr)
    rangey = max(meandens - df['RankDensity'].min(), df['RankDensity'].max() - meandens)

    xlimits = [meancentr - (rangex * 1.2), meancentr + (rangex * 1.2)]
    ylimits = [meandens - (rangey * 1.2), meandens + (rangey * 1.2)]

    annotations = pd.DataFrame({
        'xpos': sorted(xlimits + xlimits),
        'ypos': ylimits + ylimits,
        'words': ['Emerging or\nDeclining Themes', 'Niche Themes', 'Basic Themes', 'Motor Themes'],
        'hjustvar': [0, 0, 1, 1],
        'vjustvar': [0, 1, 0, 1]
    })

    min_size = 5 * (1 + size)
    max_size = 30 * (1 + size)

    fig = px.scatter(
        df,
        x='RankCentrality',
        y='RankDensity',
        color=df.index.map(lambda x: f"rgba{tuple(int(c * 255) for c in node_colors[x][:3]) + (0.5,)}" if isinstance(node_colors[x], tuple) else node_colors[x]),
        labels={'RankCentrality': 'Relevance degree\n(Centrality)', 'RankDensity': 'Development degree\n(Density)'},
        opacity=0,
    )

    fig.update_traces(hoverinfo='skip', hovertemplate=None)
    fig.add_hline(y=meandens, line_dash="dash", line_color="rgba(0,0,0,0.7)")
    fig.add_vline(x=meancentr, line_dash="dash", line_color="rgba(0,0,0,0.7)")

    for _, row in annotations.iterrows():
        fig.add_annotation(
            x=row['xpos'], y=row['ypos'],
            text=row['words'], showarrow=False,
            xanchor='left' if row['hjustvar'] == 0 else 'right',
            yanchor='bottom' if row['vjustvar'] == 0 else 'top',
            font=dict(size=12 * (1 + size), color='rgba(32,32,32,0.5)')
        )

    if size > 0:
        text_size = 10 * (1 + size)

        if repel:
            for cluster_id, cluster_data in df.groupby('groups'):
                cluster_center_x = cluster_data['RankCentrality'].mean()
                cluster_center_y = cluster_data['RankDensity'].mean()
                cluster_size = cluster_data['ClusterFrequency'].sum()

                top_words = (df_lab[df_lab['groups'] == cluster_id]
                    .sort_values('sC', ascending=False)
                    .head(3)['words']
                    .str.lower()
                    .tolist())
                top_words_text = '\n'.join(top_words)

                hover_words = []
                df_sorted = df_lab[df_lab['groups'] == cluster_id].sort_values('sC', ascending=False)
                for idx, row in enumerate(df_sorted.head(10).itertuples()):
                    hover_words.append(f"{row.words}: {row.sC}")
                hover_text = '<br>'.join(hover_words)

                size_bubble = min_size + (max_size - min_size) * np.log1p(cluster_size) / np.log1p(df['n'].max()) * 3

                fig.add_trace(go.Scatter(
                    x=[cluster_center_x],
                    y=[cluster_center_y],
                    text=[top_words_text.replace('\n', '<br>')],
                    hovertext=[hover_text],
                    hoverinfo='text',
                    mode='markers+text',
                    textposition='middle center',
                    textfont=dict(size=text_size),
                    marker=dict(
                        size=size_bubble,
                        sizemin=100,
                        sizemode='diameter',
                        color=cluster_size,
                        colorscale='Viridis',
                        line=dict(width=1, color='DarkSlateGrey'),
                        opacity=0.5,
                    ),
                    showlegend=False
                ))

    fig.update_layout(
        height=800,
        showlegend=False,
        plot_bgcolor='white',
        xaxis=dict(
            title="Relevance degree\n(Centrality)",
            showgrid=False, showticklabels=False,
            showline=True, linewidth=0.5, linecolor='black',
            zeroline=False, range=xlimits
        ),
        yaxis=dict(
            title="Development degree\n(Density)",
            showgrid=False, showticklabels=False,
            showline=True, linewidth=0.5, linecolor='black',
            zeroline=False, range=ylimits
        )
    )
    fig = go.FigureWidget(fig)
    fig._config = fig._config | {'modeBarButtonsToRemove': ['pan', 'select', 'lasso2d', 'toImage'],
                                 'displaylogo': False}

    df_lab.columns = ['Cluster', 'Cluster_Frequency', 'Cluster_Label', 'Occurrences', 'Words', 'Color']
    df_lab = (df_lab
         .sort_values('Cluster')
         .dropna(subset=['Color'])
         .assign(Cluster=lambda x: pd.factorize(x['Cluster'])[0] + 1))

    cluster_res = Net['cluster_res']
    df_lab = df_lab.merge(cluster_res, left_on='Words', right_on='vertex', how='left')
    df_lab = df_lab[['Occurrences', 'Words', 'Cluster', 'Cluster_Label', 'btw_centrality', 'clos_centrality', 'pagerank_centrality']]
    df = df[['Cluster', 'CallonCentrality', 'CallonDensity', 'RankCentrality', 'RankDensity', 'ClusterFrequency']]

    document_to_clusters = cluster_assignment(M=m, words=df_lab, field=field, remove_terms=remove_terms, synonyms=synonyms, threshold=0.5)

    params = {
        'field': field, 'n': n, 'minfreq': minfreq, 'ngrams': ngrams,
        'stemming': stemming, 'size': size, 'n_labels': n_labels,
        'community_repulsion': community_repulsion, 'repel': repel,
        'remove_terms': remove_terms, 'synonyms': synonyms, 'cluster': cluster
    }

    flat_params = []
    for k, v in params.items():
        if isinstance(v, (list, dict)):
            for i, val in enumerate(v):
                flat_params.append((f"{k}{i+1}", val))
        else:
            flat_params.append((k, v))

    params_df = pd.DataFrame(flat_params, columns=['params', 'values'])

    if subgraphs:
        gcl = {}
        unique_colors = df['color'].unique()
        for cluster_color in unique_colors:
            node_indices = [i for i, v in enumerate(Net['graph'].vs)
                           if v['color'] == cluster_color]
            gcl[cluster_color] = Net['graph'].subgraph(node_indices)
    else:
        gcl = None

    node_opacity = 0.5
    net = Network(height="98vh", width="100%", notebook=True, cdn_resources="in_line")
    net.toggle_physics(False)

    unique_clusters = set(Net['cluster_obj'].membership)
    cluster_colors = {}
    cm_clusters = cluster_res

    for cluster_id in unique_clusters:
        r = np.random.randint(0, 255)
        g = np.random.randint(0, 255)
        b = np.random.randint(0, 255)
        cluster_colors[cluster_id] = f"rgba({r},{g},{b},{node_opacity})"

    layout = Net['graph']['layout']
    coords = np.array([[pos[0], pos[1]] for pos in layout])

    abs_max = np.abs(coords).max()
    if abs_max > 0:
        coords = coords / abs_max
    coords[:, 0] *= 1000
    coords[:, 1] *= 400

    node_labels = [v["name"] if "name" in v.attributes() else f"Node {v.index}" for v in Net['graph'].vs]
    node_sizes = []
    nodes = []

    degrees = Net['graph'].degree()
    min_deg = min(degrees) if degrees else 0
    max_deg = max(degrees) if degrees else 1

    for idx, vertex in enumerate(Net['graph'].vs):
        cluster_id = Net['cluster_obj'].membership[vertex.index]
        node_color = cluster_colors[cluster_id]

        node_size = 10 if max_deg == min_deg else (15 * (vertex.degree() - min_deg) / (max_deg - min_deg) + 10)
        node_size = max(10, min(130, node_size))
        font_size = node_size * 2
        node_sizes.append(node_size)

        min_font_size = 10
        max_font_size = 130
        font_opacity = np.sqrt((font_size - min_font_size) / (max_font_size - min_font_size)) * node_opacity + 0.3
        font_opacity = max(0.1, min(1, font_opacity))

        nodes.append({
            'id': vertex.index,
            'label': vertex["name"] if "name" in vertex.attributes() else f"Node {vertex.index}",
            'title': vertex["name"] if "name" in vertex.attributes() else f"Node {vertex.index}",
            'color': node_color,
            'size': node_size,
            'font': {'size': font_size, 'color': f'rgba(0,0,0,{font_opacity})'},
            'x': layout[idx][0] * 1000,
            'y': layout[idx][1] * 1000
        })

    noOverlap = True
    if noOverlap:
        threshold = 0.05
        ymax = np.ptp(coords[:, 1])
        xmax = np.ptp(coords[:, 0])
        threshold2 = threshold * np.mean([xmax, ymax])
        labels_to_remove = avoid_net_overlaps(coords, node_labels, node_sizes, threshold=threshold2)
    else:
        labels_to_remove = []

    unique_nodes = {node['id']: node for node in nodes}.values()
    for node in unique_nodes:
        if node['label'] in labels_to_remove:
            node['label'] = ''
        net.add_node(node['id'], **node)

    added_edges = set()
    edge_weights = [e.attributes().get('weight', 1) for e in Net['graph'].es]
    max_weight = max(edge_weights) if edge_weights else 1

    for edge in Net['graph'].es:
        source, target = edge.tuple
        cluster_source = Net['cluster_obj'].membership[source]
        cluster_target = Net['cluster_obj'].membership[target]

        if cluster_source == cluster_target:
            base_color = cluster_colors[cluster_source]
            rgba_values = [int(x) for x in base_color[5:-1].split(',')[:-1]]
            edge_color = f"rgba({rgba_values[0]},{rgba_values[1]},{rgba_values[2]},0.56)"
        else:
            edge_color = "rgba(105,105,105,0.38)"

        edge_weight = edge.attributes().get('weight', 1)
        normalized_weight = (edge_weight ** 2 / (max_weight ** 2)) * (10 + 2.5)

        edge_tuple = (source, target) if source < target else (target, source)

        if edge_tuple not in added_edges:
            net.add_edge(
                source, target,
                color=edge_color,
                width=normalized_weight,
                smooth={'type': 'horizontal'},
                dashes=False
            )
            added_edges.add(edge_tuple)

    node_shadow = False
    edit_nodes = False
    net.set_options(f"""
        var options = {{
            "nodes": {{
                "shadow": {"true" if node_shadow else "false"}
            }},
            "edges": {{
                "smooth": {{"type": "horizontal"}}
            }},
            "interaction": {{
                "dragNodes": true,
                "hideEdgesOnDrag": true,
                "navigationButtons": false,
                "zoomSpeed": 0.4
            }},
            "physics": {{
                "enabled": false
            }},
            "manipulation": {{
                "enabled": {"true" if edit_nodes else "false"}
            }}
        }}
    """)

    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".html")
    html_path = tmp.name
    with open(html_path, 'w', encoding="utf-8") as f:
        html = net.generate_html()
        new_css = "     .card {\n                 border: none;\n             }"
        updated_html = html.replace("</style>", new_css + "\n        </style>")
        updated_html = updated_html.replace("1px solid lightgray", "none")
        f.write(updated_html)

    results = {
        'map': fig,
        'clusters': df,
        'words': df_lab,
        'nclust': len(df),
        'net': Net,
        'subgraphs': gcl,
        'documentToClusters': document_to_clusters,
        'params': params_df
    }

    return results['map'], html_path.split(os.sep)[-1], results['words'], results['clusters'], results['documentToClusters']


def cluster_assignment(M, words, field, remove_terms=None, synonyms=None, threshold=0.5):

    if field in ["AB", "TI"]:
        field = f"{field}_TM"

    # PATCH: safety check if field doesn't exist in M
    if field not in M.columns:
        return pd.DataFrame()

    Fi = M[field]

    all_terms = []
    all_sr = []

    for i, terms_list in enumerate(Fi):
        if isinstance(terms_list, list):
            for term in terms_list:
                if term:
                    all_terms.append(term.strip())
                    all_sr.append(M['SR'].iloc[i])

    all_field = pd.DataFrame({'terms': all_terms, 'SR': all_sr})

    if remove_terms is not None:
        remove_terms = pd.DataFrame({'terms': [t.strip().upper() for t in remove_terms]})
        all_field = all_field.merge(remove_terms, on='terms', how='left', indicator=True)
        all_field = all_field[all_field['_merge'] == 'left_only'].drop('_merge', axis=1)

    if synonyms is not None:
        s = [syn.upper().split(";") for syn in synonyms]
        snew = [l[0] for l in s]
        sold = [l[1:] for l in s]
        syn = pd.DataFrame({
            'new': np.repeat(snew, [len(x) for x in sold]),
            'terms': [item.strip() for sublist in sold for item in sublist]
        })
        all_field = all_field.merge(syn, on='terms', how='left')
        all_field.loc[all_field['new'].notna(), 'terms'] = all_field.loc[all_field['new'].notna(), 'new']
        all_field = all_field[['SR', 'terms']]

    words = words.assign(
        p_w=1 / words['Occurrences'],
        p_c=words['pagerank_centrality']
    )

    words_for_merge = words.copy()
    words = words.groupby('Cluster')

    all_field['terms'] = all_field['terms'].astype(str)

    words_for_merge = words_for_merge.copy()
    words_for_merge['Words'] = words_for_merge['Words'].str.lower()

    terms = all_field.assign(terms=all_field['terms'].str.lower()).merge(
        words_for_merge, left_on='terms', right_on='Words', how='left'
    )

    terms = (terms.groupby('SR')
        .apply(lambda x: x.assign(pagerank=x['p_c'].sum()))
        .reset_index(drop=True)
        .groupby(['SR', 'Cluster_Label'])
        .agg({'p_w': 'sum', 'p_c': 'max'})
        .reset_index()
        .rename(columns={'p_c': 'pagerank'}))

    terms['p'] = terms['p_w'] / terms.groupby('SR')['p_w'].transform('sum')
    terms = terms.dropna(subset=['Cluster_Label']).drop('p_w', axis=1)

    terms_max = (terms[terms['p'] >= threshold]
        .sort_values('p', ascending=False)
        .groupby('SR')
        .agg({'Cluster_Label': lambda x: ';'.join(x)})
        .rename(columns={'Cluster_Label': 'Assigned_cluster'}))

    terms_pagerank = (terms.merge(terms_max, on='SR')
        .query('Cluster_Label == Assigned_cluster')[['SR', 'pagerank']])

    terms = (terms.drop('pagerank', axis=1)
        .pivot(index='SR', columns='Cluster_Label', values='p')
        .reset_index()
        .rename_axis(None, axis=1))

    terms = terms.merge(terms_max, on='SR').merge(terms_pagerank, on='SR')

    if 'DI' not in M.columns:
        M['DI'] = np.nan

    year = pd.Timestamp.now().year + 1
    M = M.reset_index(drop=True)

    tc_numeric = pd.to_numeric(M['TC'], errors='coerce').fillna(0)
    M = M.copy()
    M['TC'] = tc_numeric
    # PATCH: PY is stored as string in ETL output — convert to numeric
    # before arithmetic in TCpY calculation to avoid TypeError.
    M['PY'] = pd.to_numeric(M['PY'], errors='coerce')

    terms = (M.assign(
        TCpY=lambda x: x['TC'] / (year - x['PY']),
        NTC=lambda x: x.groupby('PY')['TC'].transform(
            lambda y: y / y.mean() if y.mean() != 0 else 0
        )
    )[['DI', 'AU', 'TI', 'SO', 'PY', 'TC', 'TCpY', 'NTC', 'SR']]
        .merge(terms, on='SR')
        .fillna(0)
        .groupby('Assigned_cluster')
        .apply(lambda x: x.sort_values('TC', ascending=False))
        .reset_index(drop=True))

    return terms