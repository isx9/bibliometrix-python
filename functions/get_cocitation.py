from www.services import *


def get_co_citation(
    df, field, sep, cocit_network_layout, cocit_clustering_algorithm, cocit_repulsion,
    cocit_shape, cocit_shadow, cocit_curved, citlabelsize, citedgesize, citlabel_cex,
    citNodes, cit_isolates, citedges_min
):

    """
    Generate a co-citation network safely.
    """

    M = df
    M = M.get() if hasattr(M, 'get') and callable(M.get) and not isinstance(M, pd.DataFrame) else M
    print("M type:", type(M))

    # Validate field
    valid_fields = ["CR", "CR_AU", "CR_SO"]

    if field not in valid_fields:
        print("Invalid co-citation field")
        return None, go.FigureWidget(go.Figure()), pd.DataFrame(), go.FigureWidget(go.Figure())

    # Ensure citNodes is valid
    citNodes = max(1, int(citNodes))

    # Prepare network safely
    NetRefs = None
    Title = ""

    try:

        if field == "CR":

            NetRefs = biblionetwork(
                M,
                analysis="co-citation",
                network="references",
                n=citNodes,
                sep=sep
            )
            print("NetRefs result:", NetRefs)

            Title = "Cited References network"

        elif field == "CR_AU":

            if "CR_AU" not in M.columns:
                M = metaTagExtraction(M, Field="CR_AU", sep=sep)

            NetRefs = biblionetwork(
                M,
                analysis="co-citation",
                network="authors",
                n=citNodes,
                sep=sep
            )

            Title = "Cited Authors network"

        elif field == "CR_SO":

            if "CR_SO" not in M.columns:
                M = metaTagExtraction(M, Field="CR_SO", sep=sep)

            NetRefs = biblionetwork(
                M,
                analysis="co-citation",
                network="sources",
                n=citNodes,
                sep=sep
            )

            Title = "Cited Sources network"

    except Exception as e:

        print(f"Network generation failed: {e}")

        return (
            None,
            go.FigureWidget(go.Figure()),
            pd.DataFrame(),
            go.FigureWidget(go.Figure())
        )

    # Validate matrix
    if NetRefs is None:

        print("Co-citation matrix is empty")

        return (
            None,
            go.FigureWidget(go.Figure()),
            pd.DataFrame(),
            go.FigureWidget(go.Figure())
        )

    if isinstance(NetRefs, pd.DataFrame):

        if NetRefs.empty:

            print("Co-citation network is empty")

            return (
                None,
                go.FigureWidget(go.Figure()),
                pd.DataFrame(),
                go.FigureWidget(go.Figure())
            )
        if NetRefs.shape[0] < 2:
            print("Co-citation network too small to build (less than 2 nodes)")
            return (None, 
                    go.FigureWidget(go.Figure()),
                    pd.DataFrame(),
                    go.FigureWidget(go.Figure())
                   )

    # Safe label calculation
    label_n = min(citNodes, citlabelsize)

    try:

        cocitnet = network_plot(
            NetMatrix=NetRefs,
            normalize=None,
            Title=Title,
            type=cocit_network_layout,
            size_cex=True,
            size=5,
            remove_multiple=False,
            edgesize=max(0.1, citedgesize * 3),
            labelsize=max(1, citlabelsize),
            label_cex=citlabel_cex,
            curved=cocit_curved,
            label_n=label_n,
            edges_min=max(0, citedges_min),
            label_color=False,
            remove_isolates=cit_isolates,
            alpha=0.7,
            cluster=cocit_clustering_algorithm,
            community_repulsion=max(0.01, cocit_repulsion / 2),
            verbose=False
        )

    except Exception as e:

        print(f"network_plot failed: {e}")

        return (
            None,
            go.FigureWidget(go.Figure()),
            pd.DataFrame(),
            go.FigureWidget(go.Figure())
        )

    # PATCH: network_plot() can return None directly (not just raise) for
    # small/degenerate networks, e.g. when remove_isolates strips out most
    # nodes. The try/except above only catches exceptions, not a clean None
    # return, so cocitnet could reach here as None and crash on the dict-like
    # check below. Guard against that explicitly.
    if cocitnet is None:

        print("network_plot returned None (degenerate network)")

        return (
            None,
            go.FigureWidget(go.Figure()),
            pd.DataFrame(),
            go.FigureWidget(go.Figure())
        )

    # Validate graph object
    if "graph" not in cocitnet:

        print("Graph object missing")

        return (
            None,
            go.FigureWidget(go.Figure()),
            pd.DataFrame(),
            go.FigureWidget(go.Figure())
        )

    if cocitnet["graph"].vcount() == 0:

        print("Graph contains no nodes")

        return (
            None,
            go.FigureWidget(go.Figure()),
            pd.DataFrame(),
            go.FigureWidget(go.Figure())
        )

    net = Network(
        height="98vh",
        width="100%",
        notebook=True,
        cdn_resources="in_line"
    )

    net.toggle_physics(False)

    # Cluster colors
    unique_clusters = set(cocitnet['cluster_obj'].membership)

    cluster_colors = {}

    for cluster_id in unique_clusters:

        r = np.random.randint(0, 255)
        g = np.random.randint(0, 255)
        b = np.random.randint(0, 255)

        cluster_colors[cluster_id] = f"rgba({r},{g},{b},0.7)"

    # Layout safety
    layout = cocitnet['graph']['layout']

    coords = np.array([[pos[0], pos[1]] for pos in layout])

    if coords.size == 0:

        coords = np.array([[0, 0]])

    max_abs = np.abs(coords).max()

    if max_abs == 0:
        max_abs = 1

    coords = coords / max_abs

    coords[:, 0] *= 1000
    coords[:, 1] *= 400

    # Node safety
    degrees = cocitnet['graph'].degree()

    min_deg = min(degrees) if degrees else 0
    max_deg = max(degrees) if degrees else 1

    node_labels = []

    node_sizes = []

    nodes = []

    for idx, vertex in enumerate(cocitnet['graph'].vs):

        label = (
            vertex["name"]
            if "name" in vertex.attributes()
            else f"Node {vertex.index}"
        )

        node_labels.append(label)

        cluster_id = cocitnet['cluster_obj'].membership[vertex.index]

        node_color = cluster_colors[cluster_id]

        if max_deg == min_deg:
            node_size = 10
        else:
            node_size = (
                15 * (vertex.degree() - min_deg)
                / (max_deg - min_deg)
            ) + 10

        node_size = max(10, min(130, node_size))

        node_sizes.append(node_size)

        font_size = node_size * 2

        min_font_size = 10
        max_font_size = 130

        denom = max_font_size - min_font_size

        if denom == 0:
            denom = 1

        font_opacity = (
            np.sqrt((font_size - min_font_size) / denom)
            * 0.7
        ) + 0.3

        font_opacity = max(0.1, min(1, font_opacity))

        nodes.append({
            'id': vertex.index,
            'label': label,
            'title': label,
            'color': node_color,
            'size': node_size,
            'font': {
                'size': font_size,
                'color': f'rgba(0,0,0,{font_opacity})',
                'vadjust': -0.7 * font_size
                if cocit_shape.lower() in ['dot', 'square']
                else 0
            },
            'shadow': cocit_shadow,
            'shape': cocit_shape,
            'x': layout[idx][0] * 1000,
            'y': layout[idx][1] * 1000
        })

    # Overlap protection
    try:

        labels_to_remove = avoid_net_overlaps(
            coords,
            node_labels,
            node_sizes,
            threshold=0.05
        )

    except Exception:

        labels_to_remove = []

    # Add nodes
    unique_nodes = {node['id']: node for node in nodes}.values()

    for node in unique_nodes:

        if node['label'] in labels_to_remove:
            node['label'] = ''

        net.add_node(node['id'], **node)

    # Safe edge handling
    added_edges = set()

    edge_weights = [
        e.attributes().get('weight', 1)
        for e in cocitnet['graph'].es
    ]

    max_weight = max(edge_weights) if edge_weights else 1

    if max_weight == 0:
        max_weight = 1

    for edge in cocitnet['graph'].es:

        source, target = edge.tuple

        cluster_source = cocitnet['cluster_obj'].membership[source]
        cluster_target = cocitnet['cluster_obj'].membership[target]

        if cluster_source == cluster_target:

            base_color = cluster_colors[cluster_source]

            rgba_values = [
                int(x)
                for x in base_color[5:-1].split(',')[:-1]
            ]

            edge_color = (
                f"rgba({rgba_values[0]},"
                f"{rgba_values[1]},"
                f"{rgba_values[2]},0.56)"
            )

        else:

            edge_color = "rgba(105,105,105,0.38)"

        edge_weight = edge.attributes().get('weight', 1)

        normalized_weight = (
            (edge_weight ** 2)
            / (max_weight ** 2)
        ) * 12.5

        edge_tuple = (
            (source, target)
            if source < target
            else (target, source)
        )

        if edge_tuple not in added_edges:

            net.add_edge(
                source,
                target,
                color=edge_color,
                width=max(0.1, normalized_weight),
                smooth={'type': 'horizontal'}
                if cocit_curved else False,
                dashes=False
            )

            added_edges.add(edge_tuple)

    # Save HTML safely
    tmp = tempfile.NamedTemporaryFile(
        delete=False,
        suffix=".html"
    )

    html_path = tmp.name

    with open(html_path, 'w', encoding="utf-8") as f:

        html = net.generate_html()

        f.write(html)

    # Minimal safe outputs
    fig_density = go.FigureWidget(go.Figure())

    degree_plot = go.FigureWidget(go.Figure())

    cluster_data = pd.DataFrame({
        'Node': [
            v['name']
            if 'name' in v.attributes()
            else f'Node {v.index}'
            for v in cocitnet['graph'].vs
        ],
        'Cluster': cocitnet['cluster_obj'].membership,
        'Betweenness': cocitnet['graph'].betweenness(),
        'Closeness': cocitnet['graph'].closeness(),
        'PageRank': cocitnet['graph'].pagerank()
    })

    numeric_cols = [
        'Betweenness',
        'Closeness',
        'PageRank'
    ]

    cluster_data[numeric_cols] = (
        cluster_data[numeric_cols]
        .fillna(0)
        .round(3)
    )

    cocitnet['cluster_res'] = cluster_data

    return (
        html_path.split(os.sep)[-1],
        fig_density,
        cocitnet['cluster_res'],
        degree_plot
    )