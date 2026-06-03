from www.services import *


def get_co_occurence_network(df, field_cn, ngram, network_layout, clustering_algorithm_cn, normalization_cn, color_by_year, num_of_nodes,
                            repulsion_force, remove_isolated, min_edges, node_opacity, num_of_labels, node_shape, label_size_ls,
                            edge_size, node_shadow, edit_nodes, label_cex, file_upload_terms, file_upload_synonyms):

    M = df

    # Load stopwords and synonyms
    remove_terms = None
    if file_upload_terms:
        with open(file_upload_terms[0]['datapath'], 'r', encoding='utf-8') as file:
            remove_terms = [line.strip() for line in file]

    synonyms = None
    if file_upload_synonyms:
        with open(file_upload_synonyms[0]['datapath'], 'r', encoding='utf-8') as file:
            syn_dict = {}
            for line in file:
                terms = [term.strip() for term in line.split(';')]
                if terms:
                    key = terms[0]
                    syn_dict[key] = terms[1:]
            synonyms = syn_dict if syn_dict else None

    ngrams = int(ngram) if field_cn in ['TI', 'AB'] else 1

    if num_of_labels > num_of_nodes:
        num_of_labels = num_of_nodes

    network_data = None
    title = ""

    # PATCH: extract plain DataFrame once for use with term_extraction
    M_plain = M.get() if hasattr(M, 'get') and callable(M.get) and not isinstance(M, pd.DataFrame) else M

    if field_cn == 'ID':
        network_data = biblionetwork(M, "co-occurrences", "keywords", num_of_nodes,
                                    sep=";", remove_terms=remove_terms, synonyms=synonyms)
        title = "Keywords Plus Network"
    elif field_cn == 'DE':
        network_data = biblionetwork(M, "co-occurrences", "author_keywords", num_of_nodes,
                                    sep=";", remove_terms=remove_terms, synonyms=synonyms)
        title = "Authors' Keywords network"
    elif field_cn == 'TI':
        # PATCH: pass plain DataFrame to term_extraction — it does not accept reactives
        M = term_extraction(M_plain, "TI", ngrams=ngrams,
                          remove_terms=remove_terms, synonyms=synonyms)
        network_data = biblionetwork(M, "co-occurrences", "titles", num_of_nodes, sep=";")
        title = "Title Words network"
    elif field_cn == 'AB':
        # PATCH: pass plain DataFrame to term_extraction — it does not accept reactives
        M = term_extraction(M_plain, "AB", ngrams=ngrams,
                          remove_terms=remove_terms, synonyms=synonyms)
        network_data = biblionetwork(M, "co-occurrences", "abstracts", num_of_nodes, sep=";")
        title = "Abstract Words network"
    elif field_cn == 'WC':
        wsc = cocMatrix(M, "WC", binary=False)
        network_data = np.matmul(wsc.T, wsc)
        title = "Subject Categories network"

    # PATCH: return early if network_data is None or empty
    if network_data is None:
        return None, None, None, None

    if isinstance(network_data, pd.DataFrame) and network_data.empty:
        return None, None, None, None

    if normalization_cn == "none":
        normalize = None
    else:
        normalize = normalization_cn

    cocnet = network_plot(
        NetMatrix=network_data,
        normalize=normalize,
        Title=title,
        type=network_layout,
        size_cex=True,
        size=5,
        remove_multiple=False,
        edgesize=edge_size,
        labelsize=label_size_ls,
        label_cex=label_cex,
        label_n=num_of_labels,
        edges_min=min_edges,
        label_color=False,
        curved=True,
        alpha=node_opacity,
        cluster=clustering_algorithm_cn,
        remove_isolates=remove_isolated,
        community_repulsion=repulsion_force / 2,
        verbose=False
    )

    # PATCH: cocnet may be None if network_plot fails on small/empty graphs
    if cocnet is None:
        return None, None, None, None

    if color_by_year:
        Y = field_by_year(M, field_cn)
        g = cocnet['graph']
        labels = [v['name'] for v in g.vs]
        Y_df = Y['df']

        mask = Y_df['item'].str.lower().isin(labels)
        df_year = Y_df[mask].copy()

        year_range = df_year['year_med'].max() - df_year['year_med'].min() + 1 if not df_year.empty else 1
        colors = plt.cm.Blues(np.linspace(0, 1, int(year_range * 10)))

        median_year = df_year['year_med'].median() if not df_year.empty else 0
        max_year = df_year['year_med'].max() if not df_year.empty else 0

        def safe_year_lookup(label):
            matches = df_year[df_year['item'].str.lower() == label.lower()]['year_med']
            return matches.iloc[0] if not matches.empty else median_year

        vertex_colors = []
        for label in labels:
            year = safe_year_lookup(label)
            color_idx = max(0, min(int((max_year - year + 1) * 10 - 1), len(colors) - 1))
            vertex_colors.append(colors[color_idx])

        g.vs['color'] = vertex_colors
        g.vs['year_med'] = [safe_year_lookup(label) for label in labels]
        cocnet['graph'] = g

    net = Network(height="98vh", width="100%", notebook=True, cdn_resources="in_line")
    net.toggle_physics(False)

    unique_clusters = set(cocnet['cluster_obj'].membership)
    cluster_colors = {}
    cm_clusters = cocnet['cluster_res']

    for cluster_id in unique_clusters:
        r = np.random.randint(0, 255)
        g = np.random.randint(0, 255)
        b = np.random.randint(0, 255)
        cluster_colors[cluster_id] = f"rgba({r},{g},{b},{node_opacity})"

    layout = cocnet['graph']['layout']
    coords = np.array([[pos[0], pos[1]] for pos in layout])

    abs_max = np.abs(coords).max()
    if abs_max > 0:
        coords = coords / abs_max

    coords[:, 0] *= 1000
    coords[:, 1] *= 400

    node_labels = [v["name"] if "name" in v.attributes() else f"Node {v.index}" for v in cocnet['graph'].vs]
    node_sizes = []
    nodes = []

    for idx, vertex in enumerate(cocnet['graph'].vs):
        cluster_id = cocnet['cluster_obj'].membership[vertex.index]
        node_color = cluster_colors[cluster_id]

        degrees = cocnet['graph'].degree()
        if not degrees:
            node_size = 10
        else:
            min_deg, max_deg = min(degrees), max(degrees)
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
            'font': {
                'size': font_size,
                'color': f'rgba(0,0,0,{font_opacity})',
                'vadjust': -0.7 * font_size if node_shape.lower() in ['dot', 'square'] else 0
            },
            'shadow': node_shadow,
            'shape': node_shape,
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
    edge_weights = [e.attributes().get('weight', 1) for e in cocnet['graph'].es]
    max_weight = max(edge_weights) if edge_weights else 1

    for edge in cocnet['graph'].es:
        source, target = edge.tuple
        cluster_source = cocnet['cluster_obj'].membership[source]
        cluster_target = cocnet['cluster_obj'].membership[target]

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

    nodes_df_orig = pd.DataFrame(nodes)
    nodes_df_orig['y'] = nodes_df_orig['y'] * -1

    font_sizes = nodes_df_orig['font'].apply(lambda x: x.get('size', 75))
    min_font = font_sizes.min()
    max_font = font_sizes.max()

    font_range = max_font - min_font
    if font_range > 0:
        nodes_df_orig['font_size'] = ((font_sizes - min_font) / font_range * 20) + 10
    else:
        nodes_df_orig['font_size'] = 20.0

    nodes_df = nodes_df_orig.copy()
    nodes_df['log'] = np.ceil(np.log(nodes_df['size']))
    nodes_df = nodes_df.loc[nodes_df.index.repeat(nodes_df['log'].astype(int))]

    reds_colors = [
        [0.0, 'rgb(255,255,255)'],
        [0.05, 'rgb(238,238,238)'],
        [0.125, 'rgb(254,224,210)'],
        [0.25, 'rgb(252,187,161)'],
        [0.375, 'rgb(252,146,114)'],
        [0.5, 'rgb(251,106,74)'],
        [0.625, 'rgb(239,59,44)'],
        [0.75, 'rgb(203,24,29)'],
        [0.875, 'rgb(165,15,21)'],
        [1.0, 'rgb(103,0,13)']
    ]

    fig = go.Figure()
    fig.add_trace(go.Histogram2d(
        x=nodes_df['x'],
        y=nodes_df['y'],
        histnorm='density',
        colorscale=reds_colors,
        showscale=False,
        zsmooth='best'
    ))

    for _, row in nodes_df.iterrows():
        fig.add_annotation(
            xref='x1', yref='y',
            x=row['x'], y=row['y'],
            text=row['label'],
            showarrow=False,
            font=dict(family='Arial', size=row['font_size'], color='black')
        )

    fig.update_layout(
        xaxis=dict(
            title="", showgrid=False, zeroline=False, showline=False,
            showticklabels=False, domain=[0, 1], gridcolor='#FFFFFF', tickvals=[]
        ),
        yaxis=dict(
            title="", showgrid=False, zeroline=False, showline=False,
            showticklabels=False, domain=[0, 1], gridcolor='#FFFFFF', tickvals=[]
        ),
        plot_bgcolor='rgba(0, 0, 0, 0)',
        paper_bgcolor='rgba(0, 0, 0, 0)',
        showlegend=False,
        hovermode=False,
        margin=dict(l=0, r=0, t=0, b=0),
        height=600,
    )

    fig.update_traces(hoverinfo='none')
    fig = go.FigureWidget(fig)
    fig._config = fig._config | {'modeBarButtonsToRemove': ['pan', 'select', 'lasso2d', 'toImage'],
                                 'displaylogo': False}

    cluster_data = pd.DataFrame({
        'Node': [v['name'] if 'name' in v.attributes() else f'Node {v.index}' for v in cocnet['graph'].vs],
        'Cluster': cocnet['cluster_obj'].membership,
        'Betweenness': cocnet['graph'].betweenness(),
        'Closeness': cocnet['graph'].closeness(),
        'PageRank': cocnet['graph'].pagerank()
    })

    numeric_cols = ['Betweenness', 'Closeness', 'PageRank']
    cluster_data[numeric_cols] = cluster_data[numeric_cols].round(3)
    cocnet['cluster_res'] = cluster_data

    node_degrees = pd.DataFrame({
        'node': [v['name'] if 'name' in v.attributes() else f'Node {v.index}' for v in cocnet['graph'].vs],
        'degree': cocnet['graph'].degree()
    })

    node_degrees = node_degrees.sort_values('degree', ascending=False)
    node_degrees['x'] = range(1, len(node_degrees) + 1)
    max_degree = node_degrees['degree'].max()
    node_degrees['degree'] = node_degrees['degree'] / max_degree if max_degree > 0 else 0

    degree_plot = go.Figure()
    degree_plot.add_trace(go.Scatter(
        x=node_degrees['x'],
        y=node_degrees['degree'],
        mode='lines+markers',
        line=dict(color='#5567BB', width=1),
        marker=dict(size=6),
        hovertemplate='%{text}<extra></extra>',
        text=[f"{node} - Degree {degree:.3f}" for node, degree in zip(node_degrees['node'], node_degrees['degree'])]
    ))

    degree_plot.update_layout(
        xaxis_title='Node',
        yaxis_title='Cumulative Degree',
        plot_bgcolor='white',
        paper_bgcolor='white',
        font=dict(color='#444444'),
        title_font_size=24,
        xaxis=dict(
            showgrid=True, gridcolor='#EFEFEF',
            title_font=dict(size=14, color='#555555'),
            showline=True, linewidth=0.5, linecolor='black'
        ),
        yaxis=dict(
            showgrid=True, gridcolor='#EFEFEF',
            title_font=dict(size=14, color='#555555'),
            title_standoff=25,
            showline=True, linewidth=0.5, linecolor='black'
        ),
        height=600,
        hoverlabel=dict(
            bgcolor="white", font_size=13,
            font_family="Segoe UI, Arial", bordercolor="#5567BB"
        ),
    )
    degree_plot = go.FigureWidget(degree_plot)
    degree_plot._config = degree_plot._config | {'modeBarButtonsToRemove': ['pan', 'select', 'lasso2d', 'toImage'],
                                                 'displaylogo': False}

    return html_path.split(os.sep)[-1], fig, cocnet['cluster_res'], degree_plot


def field_by_year(df, field_cn, timespan=None, min_freq=2, n_items=5, remove_terms=None, synonyms=None):
    """
    Analyzes field frequency by year.
    """
    # PATCH: df may be a Shiny reactive Value or a plain DataFrame
    M = df.get() if hasattr(df, 'get') and callable(df.get) and not isinstance(df, pd.DataFrame) else df
    M = M.copy()

    A = cocMatrix(df, field_cn, binary=False, remove_terms=remove_terms, synonyms=synonyms)

    # PATCH: cocMatrix may return None if field is empty
    if A is None or A.empty:
        empty = pd.DataFrame()
        return {'df': empty, 'df_graph': empty}

    n = np.sum(A, axis=0)

    years = M['PY'].values

    trend_med = []
    for col_idx in range(A.shape[1]):
        term_years = np.repeat(years, A.iloc[:, col_idx].astype(int))
        if len(term_years) > 0:
            q1, med, q3 = np.percentile(term_years, [25, 50, 75])
            trend_med.append({
                'item': A.columns[col_idx],
                'freq': n[col_idx],
                'year_q1': q1,
                'year_med': med,
                'year_q3': q3
            })

    trend_med = pd.DataFrame(trend_med)

    if trend_med.empty:
        return {'df': trend_med, 'df_graph': trend_med}

    if timespan is None:
        timespan = [trend_med['year_med'].min(), trend_med['year_med'].max()]

    df_result = (trend_med
          .assign(item=lambda x: x['item'].str.lower())
          .sort_values(['year_med', 'freq', 'item'], ascending=[False, False, True])
          .groupby('year_med')
          .head(n_items)
          .query('freq >= @min_freq')
          .query('@timespan[0] <= year_med <= @timespan[1]')
          .copy())

    df_result['item'] = pd.Categorical(
        df_result['item'],
        categories=df_result.sort_values('freq', ascending=True)['item'].unique(),
        ordered=True
    )

    results = {
        'df': trend_med,
        'df_graph': df_result
    }

    return results