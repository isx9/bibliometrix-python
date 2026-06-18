from www.services import *


def get_clustering_coupling(df, unit_of_analysis, coupling_measured, stemmer, impact_measure, 
                            cluster_labeling, ngram, num_of_units, min_cluster_freq, 
                            label_per_cluster, label_size, community_repulsion, 
                            clustering_algorithm, node_shape='dot'):
    
    # Generate coupling map
    coupling_map = couplingMap(
        df,
        analysis=unit_of_analysis,
        field=coupling_measured,
        n=num_of_units,
        minfreq=min_cluster_freq,
        ngrams=ngram,
        community_repulsion=community_repulsion,
        impact_measure=impact_measure,
        stemming=stemmer,
        size=label_size,
        label_term=cluster_labeling,
        n_labels=label_per_cluster,
        repel=False,
        clustering=clustering_algorithm  
    )

    # PATCH: couplingMap returns None when network is empty
    # (e.g. OpenAlex URL-based references produce no valid coupling matrix)
    if coupling_map is None:
        empty_fig = go.FigureWidget(go.Figure())
        return empty_fig, "", pd.DataFrame(), pd.DataFrame()

    ### Plotting the coupling map
    fig = coupling_map['map']
    fig.update_layout(
        height=750,
        autosize=True,
        width=None,
        showlegend=True,
        margin=dict(t=20)
    )
    fig = go.FigureWidget(fig)
    fig._config = fig._config | {'modeBarButtonsToRemove': ['pan', 'select', 'lasso2d', 'toImage'],
                                 'displaylogo': False}

    cm_data = coupling_map['data']
    cm_clusters = coupling_map['clusters']

    # Get graph and verify it's an igraph object
    graph = coupling_map['net']['graph']
    if not isinstance(graph, ig.Graph):
        raise TypeError("Expected an igraph.Graph object in 'couplingMap['net']['graph'].")
    
    net = Network(height="98vh", width="100%", notebook=True, cdn_resources="in_line")
    net.toggle_physics(False)

    unique_clusters = set(coupling_map['net']['cluster_obj'].membership)
    cluster_colors = {}
    
    for i, cluster_id in enumerate(unique_clusters):
        if i < len(cm_clusters):
            hex_color = cm_clusters['adjusted_color'].iloc[i]
            hex_color = hex_color.lstrip('#')
            rgb = tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))
            cluster_colors[cluster_id] = f"rgba({rgb[0]},{rgb[1]},{rgb[2]},0.3)"
        else:
            cluster_colors[cluster_id] = f"rgba(128,128,128,0.3)"

    layout = graph.layout_fruchterman_reingold()
    coords = np.array([[pos[0], pos[1]] for pos in layout])
    
    coords = coords / np.abs(coords).max()
    coords[:, 0] *= 1000
    coords[:, 1] *= 400

    node_labels = [v["name"] if "name" in v.attributes() else f"Node {v.index}" for v in graph.vs]
    node_sizes = []
    nodes = []
    
    for idx, vertex in enumerate(graph.vs):
        cluster_id = coupling_map['net']['cluster_obj'].membership[vertex.index]
        node_color = cluster_colors[cluster_id]

        min_deg, max_deg = min(graph.degree()), max(graph.degree())
        node_size = 30 if max_deg == min_deg else (35 * (vertex.degree() - min_deg) / (max_deg - min_deg) + 30)
        node_size = max(30, min(150, node_size))
        font_size = node_size * 2.5
        node_sizes.append(node_size)
        
        if font_size < 90:
            font_opacity = 0.4
        elif 90 <= font_size < 100:
            font_opacity = 0.6
        elif 100 <= font_size < 120:
            font_opacity = 0.8
        else:  
            font_opacity = 1.0
        
        nodes.append({
            'id': vertex.index,
            'label': vertex["name"] if "name" in vertex.attributes() else f"Node {vertex.index}",
            'title': vertex["name"] if "name" in vertex.attributes() else f"Node {vertex.index}",
            'color': node_color,
            'size': node_size,
            'font': {
                'size': font_size, 
                'color': f'rgba(0,0,0,{font_opacity})', 
                'vadjust': -0.7*font_size if node_shape.lower() in ['dot', 'square'] else 0
            },
            'shadow': True,
            'shape': 'dot',
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
    edge_weights = [e.attributes().get('weight', 1) for e in graph.es]
    max_weight = max(edge_weights) if edge_weights else 1
    
    for edge in graph.es:
        source, target = edge.tuple
        cluster_source = coupling_map['net']['cluster_obj'].membership[source]
        cluster_target = coupling_map['net']['cluster_obj'].membership[target]
        
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
                source, 
                target, 
                color=edge_color,
                width=normalized_weight,
                smooth={'type': 'horizontal'},
                dashes=False
            )
            added_edges.add(edge_tuple)

    net.set_options("""
        var options = {
            "nodes": {
                "shadow": true
            },
            "edges": {
                "smooth": {"type": "horizontal"}
            },
            "interaction": {
                "dragNodes": true,
                "hideEdgesOnDrag": true,
                "navigationButtons": false,
                "zoomSpeed": 0.4
            },
            "physics": {
                "enabled": false
            },
            "manipulation": {
                "enabled": false
            }
        }
    """)

    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".html")
    html_path = tmp.name
    with open(html_path, 'w', encoding="utf-8") as f:
        html = net.generate_html()
        new_css = "     .card {\n                 border: none;\n             }"
        updated_html = html.replace("</style>", new_css + "\n        </style>")
        updated_html = updated_html.replace("1px solid lightgray", "none")
        f.write(updated_html)

    return fig, html_path.split(os.sep)[-1], cm_data, cm_clusters