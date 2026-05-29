from www.services import *

import json
import tempfile
import os
import numpy as np
import pandas as pd

from pyvis.network import Network


def get_collaboration_network(
    df,
    field,
    network_layout,
    clustering_algorithm,
    repulsion,
    shape,
    opacity,
    shadow,
    curved,
    colnormalize,
    labelsize,
    edgesize,
    label_cex,
    nodes,
    isolates,
    edges_min
):

    """
    Generate collaboration network visualization.
    """

    print("Generating collaboration network...")

    M = df
    m = df.get()

    NetRefs = None
    Title = ""

    # --------------------------------------------------
    # BUILD NETWORK
    # --------------------------------------------------

    if field == "COL_AU":

        NetRefs = biblionetwork(
            M,
            analysis="collaboration",
            network="authors",
            n=nodes
        )

        Title = "Author Collaboration network"

    elif field == "COL_UN":

        if "AU_UN" not in m.columns:
            M = metaTagExtraction(M, Field="AU_UN")

        NetRefs = biblionetwork(
            M,
            analysis="collaboration",
            network="universities",
            n=nodes
        )

        Title = "Edu Collaboration network"

    elif field == "COL_CO":

        if "AU_CO" not in m.columns:
            M = metaTagExtraction(M, Field="AU_CO")

        NetRefs = biblionetwork(
            M,
            analysis="collaboration",
            network="countries",
            n=nodes
        )

        Title = "Country Collaboration network"

    else:
        raise ValueError("Invalid field for collaboration network.")

    # --------------------------------------------------
    # SAFE NETWORK PATCH
    # --------------------------------------------------

    if NetRefs is None or len(NetRefs) == 0:

        empty_fig = go.FigureWidget(go.Figure())

        empty_table = pd.DataFrame()

        return (
            "",
            empty_fig,
            empty_table,
            empty_fig
        )

    # --------------------------------------------------
    # LABELS
    # --------------------------------------------------

    label_n = min(nodes, labelsize)

    normalize = None if colnormalize == "none" else colnormalize

    # --------------------------------------------------
    # NETWORK PLOT
    # --------------------------------------------------

    netplot = network_plot(
        NetMatrix=NetRefs,
        normalize=normalize,
        Title=Title,
        type=network_layout if network_layout != "worldmap" else "auto",
        size_cex=True,
        size=5,
        remove_multiple=False,
        edgesize=edgesize * 3,
        labelsize=labelsize,
        label_cex=label_cex,
        curved=curved,
        label_n=label_n,
        edges_min=edges_min,
        label_color=False,
        remove_isolates=isolates,
        alpha=opacity,
        cluster=clustering_algorithm,
        community_repulsion=repulsion / 2,
        verbose=False
    )

    # --------------------------------------------------
    # PYVIS NETWORK
    # --------------------------------------------------

    net = Network(
        height="98vh",
        width="100%",
        notebook=True,
        cdn_resources="in_line"
    )

    net.toggle_physics(False)

    unique_clusters = set(
        netplot['cluster_obj'].membership
    )

    cluster_colors = {}

    for cluster_id in unique_clusters:

        r = np.random.randint(0, 255)
        g = np.random.randint(0, 255)
        b = np.random.randint(0, 255)

        cluster_colors[cluster_id] = (
            f"rgba({r},{g},{b},{opacity})"
        )

    layout = netplot['graph']['layout']

    coords = np.array([
        [pos[0], pos[1]]
        for pos in layout
    ])

    if np.abs(coords).max() != 0:
        coords = coords / np.abs(coords).max()

    coords[:, 0] *= 1000
    coords[:, 1] *= 400

    node_labels = [
        v["name"]
        if "name" in v.attributes()
        else f"Node {v.index}"
        for v in netplot['graph'].vs
    ]

    node_sizes = []

    nodes_list = []

    min_deg = min(netplot['graph'].degree())
    max_deg = max(netplot['graph'].degree())

    for idx, vertex in enumerate(netplot['graph'].vs):

        cluster_id = netplot['cluster_obj'].membership[
            vertex.index
        ]

        node_color = cluster_colors[cluster_id]

        if max_deg == min_deg:
            node_size = 10
        else:
            node_size = (
                15 *
                (
                    (vertex.degree() - min_deg)
                    /
                    (max_deg - min_deg)
                )
            ) + 10

        node_size = max(10, min(130, node_size))

        font_size = node_size * 2

        node_sizes.append(node_size)

        min_font_size = 10
        max_font_size = 130

        safe_ratio = max(
            0,
            (
                (font_size - min_font_size)
                /
                max((max_font_size - min_font_size), 1)
            )
        )

        font_opacity = (
            np.sqrt(safe_ratio) * 0.7
        ) + 0.3

        font_opacity = max(
            0.1,
            min(1, font_opacity)
        )

        nodes_list.append({

            'id': vertex.index,

            'label': (
                vertex["name"]
                if "name" in vertex.attributes()
                else f"Node {vertex.index}"
            ),

            'title': (
                vertex["name"]
                if "name" in vertex.attributes()
                else f"Node {vertex.index}"
            ),

            'color': node_color,

            'size': node_size,

            'font': {
                'size': font_size,
                'color': f'rgba(0,0,0,{font_opacity})',
                'vadjust': (
                    -0.7 * font_size
                    if shape.lower() in ['dot', 'square']
                    else 0
                )
            },

            'shadow': shadow,

            'shape': shape,

            'x': layout[idx][0] * 1000,

            'y': layout[idx][1] * 1000
        })

    # --------------------------------------------------
    # REMOVE LABEL OVERLAPS
    # --------------------------------------------------

    noOverlap = True

    if noOverlap:

        threshold = 0.05

        ymax = np.ptp(coords[:, 1])
        xmax = np.ptp(coords[:, 0])

        threshold2 = threshold * np.mean([xmax, ymax])

        labels_to_remove = avoid_net_overlaps(
            coords,
            node_labels,
            node_sizes,
            threshold=threshold2
        )

    else:

        labels_to_remove = []

    unique_nodes = {
        node['id']: node
        for node in nodes_list
    }.values()

    for node in unique_nodes:

        if node['label'] in labels_to_remove:
            node['label'] = ''

        net.add_node(
            node['id'],
            **node
        )

    # --------------------------------------------------
    # EDGES
    # --------------------------------------------------

    added_edges = set()

    edge_weights = [
        e.attributes().get('weight', 1)
        for e in netplot['graph'].es
    ]

    max_weight = (
        max(edge_weights)
        if edge_weights
        else 1
    )

    for edge in netplot['graph'].es:

        source, target = edge.tuple

        cluster_source = (
            netplot['cluster_obj'].membership[source]
        )

        cluster_target = (
            netplot['cluster_obj'].membership[target]
        )

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

        edge_weight = edge.attributes().get(
            'weight',
            1
        )

        normalized_weight = (
            (edge_weight ** 2)
            /
            (max_weight ** 2)
        ) * (10 + 2.5)

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
                width=normalized_weight,
                smooth={
                    'type': 'horizontal'
                } if curved else False,
                dashes=False
            )

            added_edges.add(edge_tuple)

    # --------------------------------------------------
    # OPTIONS
    # --------------------------------------------------

    options_dict = {

        "nodes": {
            "shadow": bool(shadow)
        },

        "edges": {
            "smooth": {
                "type": "horizontal"
            } if curved else False
        },

        "interaction": {
            "dragNodes": True,
            "hideEdgesOnDrag": True,
            "navigationButtons": False,
            "zoomSpeed": 0.4
        },

        "physics": {
            "enabled": False
        },

        "manipulation": {
            "enabled": False
        }
    }

    net.set_options(
        json.dumps(options_dict)
    )

    # --------------------------------------------------
    # SAVE HTML
    # --------------------------------------------------

    tmp = tempfile.NamedTemporaryFile(
        delete=False,
        suffix=".html"
    )

    html_path = tmp.name

    with open(
        html_path,
        'w',
        encoding="utf-8"
    ) as f:

        html = net.generate_html()

        new_css = (
            "     .card {\n"
            "                 border: none;\n"
            "             }"
        )

        updated_html = html.replace(
            "</style>",
            new_css + "\n        </style>"
        )

        updated_html = updated_html.replace(
            "1px solid lightgray",
            "none"
        )

        f.write(updated_html)

    # --------------------------------------------------
    # EMPTY FIGURES PLACEHOLDER
    # --------------------------------------------------

    fig_density = go.FigureWidget(go.Figure())

    degree_plot = go.FigureWidget(go.Figure())

    cluster_data = pd.DataFrame({
        'Node': [
            v['name']
            if 'name' in v.attributes()
            else f'Node {v.index}'
            for v in netplot['graph'].vs
        ],

        'Cluster': netplot['cluster_obj'].membership,

        'Betweenness': netplot['graph'].betweenness(),

        'Closeness': netplot['graph'].closeness(),

        'PageRank': netplot['graph'].pagerank()
    })

    numeric_cols = [
        'Betweenness',
        'Closeness',
        'PageRank'
    ]

    cluster_data[numeric_cols] = (
        cluster_data[numeric_cols]
        .round(3)
    )

    # --------------------------------------------------
    # RETURN
    # --------------------------------------------------

    return (
        html_path.split(os.sep)[-1],
        fig_density,
        cluster_data,
        degree_plot
    )