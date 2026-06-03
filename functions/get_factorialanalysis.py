from www.services import *
from scipy.spatial import ConvexHull, QhullError


def distance_to_y(dist, max_dist, scale_factor):
    norm = math.log1p(dist) / math.log1p(max_dist)
    return -norm * scale_factor


def get_leaf_clusters(node, label_to_new_index, labels_lower, node_to_cluster):
    if node.is_leaf():
        label = labels_lower[node.id]
        return {node_to_cluster[label_to_new_index[label]]}
    left_clusters = get_leaf_clusters(node.left, label_to_new_index, labels_lower, node_to_cluster)
    right_clusters = get_leaf_clusters(node.right, label_to_new_index, labels_lower, node_to_cluster)
    return left_clusters.union(right_clusters)


def _to_seq(val) -> List[str]:
    """Flatten *val* to a list of strings, dropping NaN/None."""
    if val is None or (isinstance(val, float) and pd.isna(val)):
        return []
    if isinstance(val, (list, tuple, set, np.ndarray)):
        seq: Sequence = val
    else:
        seq = [val]
    out: List[str] = []
    for x in seq:
        if x is None or (isinstance(x, float) and pd.isna(x)):
            continue
        out.append(str(x))
    return out


def assign_consistent_colors(clusters):
    palette = px.colors.qualitative.Plotly
    unique_clusters = sorted(set(clusters.dropna()))
    color_map = {cluster: palette[i % len(palette)] for i, cluster in enumerate(unique_clusters)}
    color_map[np.nan] = "#CCCCCC"
    return color_map


def get_factorial_analysis(
    df: pd.DataFrame,
    ngram: Union[int, str] = 1,
    field: str = "ID",
    terms_data_wm: Optional[Sequence[str]] = None,
    synonyms_data_wm: Optional[Dict[str, str]] = None,
    n_terms: int = 50,
    n_clusters: int = 5,
    num_documents: Optional[int] = None,
    method: str = "MCA",
    dimX: int = 1,
    dimY: int = 2,
    topWordPlot: Union[int, float] = np.inf,
    threshold: float = 0.10,
    labelsize: int = 16,
    size: int = 5,
):
    """Generate a 2-D interactive word map for bibliometric data."""

    # Load terms to remove
    remove_term = None
    if terms_data_wm:
        with open(terms_data_wm[0]['datapath'], 'r', encoding='utf-8') as file:
            remove_term = [line.strip() for line in file]

    # Load synonyms
    synonym = None
    if synonyms_data_wm:
        with open(synonyms_data_wm[0]['datapath'], 'r', encoding='utf-8') as file:
            synonym = {}
            for line in file:
                terms = [term.strip() for term in line.split(',')]
                key = terms[0]
                values = terms[1:]
                synonym[key] = values

    # Set ngrams based on field
    ngrams = int(ngram) if field in ['TI', 'AB'] else 1

    # PATCH: df may be a Shiny reactive Value or a plain DataFrame
    df_plain = df.get() if hasattr(df, 'get') and callable(df.get) and not isinstance(df, pd.DataFrame) else df
    M = df_plain.copy()
    tab = table_tag(M, field, ngrams)

    if len(tab) >= 2:
        min_degree = list(tab.values())[min(n_terms, len(tab) - 1)]

        CS = conceptual_structure(
            df=df_plain, #patch
            method=method,
            field=field,
            min_degree=min_degree,
            n_clusters=n_clusters,
            k_max=8,
            stemming=False,
            labelsize=int(labelsize / 2),
            documents=num_documents,
            graph=False,
            ngrams=ngrams,
            remove_terms=remove_term,
            synonyms=synonym
        )

        if method != "MDS":
            CSData = CS["docCoord"].copy()
            CSData = CSData.reset_index().rename(columns={"index": "Documents"})
            CSData["dim1"] = CSData["dim1"].round(2)
            CSData["dim2"] = CSData["dim2"].round(2)
            CSData["contrib"] = CSData["contrib"].round(2)
            CS["CSData"] = CSData
        else:
            CS["CSData"] = pd.DataFrame({"Documents": [None], "dim1": [None], "dim2": [None]})

        if method in {"CA", "MCA"}:
            WData = pd.DataFrame(CS["km_res"]["data"], columns=["Dim1", "Dim2"])
            WData["word"] = CS["km_res"]["data"].index
            WData["cluster"] = CS["km_res"]["data"]["cluster"]
        elif method == "MDS":
            WData = pd.DataFrame(CS["res"], columns=["Dim1", "Dim2"])
            WData["word"] = CS["res"].index
            WData["cluster"] = CS["km_res"]["cluster"]

        WData = WData.round({"Dim1": 2, "Dim2": 2})
        CS["WData"] = WData

        LABEL = WData["word"]

        if method in {"CA", "MCA"}:
            WData = CS["km_res"]["data"].copy()
            WData = WData.reset_index().rename(columns={"index": "word"})
            if "cluster" not in WData.columns and "cluster" in CS["km_res"]:
                WData["cluster"] = CS["km_res"]["cluster"]
            elif "cluster" not in WData.columns:
                WData["cluster"] = np.nan
            wordCoord = WData[["Dim1", "Dim2", "word", "cluster"]].copy()
            wordCoord.rename(columns={"word": "label", "cluster": "groups"}, inplace=True)
            contrib = CS["coord"]["contrib"].sum(axis=1) / 2
            wordCoord["label"] = wordCoord["label"].values
            wordCoord["contrib"] = np.array(contrib).flatten()

            if CS["res"] is not None and hasattr(CS["res"], "eigCorr"):
                xlabel = f"Dim 1 ({CS['res'].eigCorr['perc'][dimX]:.2f}%)"
                ylabel = f"Dim 2 ({CS['res'].eigCorr['perc'][dimY]:.2f}%)"
            else:
                xlabel, ylabel = "Dim 1", "Dim 2"

        elif method == "MDS":
            wordCoord = WData[["Dim1", "Dim2", "word", "cluster"]].copy()
            wordCoord.rename(columns={"word": "label", "cluster": "groups"}, inplace=True)
            wordCoord["contrib"] = size / 2
            xlabel, ylabel = "Dim 1", "Dim 2"

        ymax = wordCoord["Dim2"].max() - wordCoord["Dim2"].min()
        xmax = wordCoord["Dim1"].max() - wordCoord["Dim1"].min()
        threshold2 = threshold * np.mean([xmax, ymax])

        wordCoord["dotSize"] = wordCoord["contrib"] + size
        wordCoord["dotSize"] = wordCoord["dotSize"].replace([np.inf, -np.inf], np.nan)
        wordCoord["dotSize"] = wordCoord["dotSize"].fillna(1)
        wordCoord["dotSize"] = wordCoord["dotSize"].clip(lower=1)
        thres = sorted(wordCoord["dotSize"], reverse=True)[min(int(topWordPlot), len(wordCoord) - 1)]
        wordCoord["labelToPlot"] = np.where(wordCoord["dotSize"] >= thres, wordCoord["label"], "")

        group_colors = assign_consistent_colors(wordCoord["groups"])

        hoverText = [
            f"<b>{row['label']}</b><br>Cluster: {row['groups'] if 'groups' in row else ''}<br>Contrib: {row['contrib']:.3f}"
            for _, row in wordCoord.iterrows()
        ]

        fig = go.Figure()

        for g in sorted(wordCoord["groups"].dropna().unique()):
            group_df = wordCoord[wordCoord["groups"] == g]
            fig.add_trace(
                go.Scatter(
                    x=group_df["Dim1"],
                    y=group_df["Dim2"],
                    mode="markers",
                    marker=dict(
                        size=group_df["dotSize"],
                        color=group_colors.get(g, "#FF0000"),
                        opacity=0.7,
                        line=dict(width=0.7, color="black"),
                        symbol="circle",
                    ),
                    opacity=0.7,
                    text=group_df["label"],
                    hovertext=[
                        f"<b>{row['label']}</b><br>Cluster: {row['groups']}<br>Contrib: {row['contrib']:.3f}"
                        for _, row in group_df.iterrows()
                    ],
                    hoverinfo="text",
                    name=f"Cluster {g}",
                    showlegend=False,
                )
            )

        group_df_nan = wordCoord[wordCoord["groups"].isna()]
        if not group_df_nan.empty:
            fig.add_trace(
                go.Scatter(
                    x=group_df_nan["Dim1"],
                    y=group_df_nan["Dim2"],
                    mode="markers",
                    marker=dict(
                        size=group_df_nan["dotSize"],
                        color="#FF9999",
                        opacity=0.7,
                        line=dict(width=0.7, color="black"),
                        symbol="circle",
                    ),
                    opacity=0.7,
                    text=group_df_nan["label"],
                    hovertext=[
                        f"<b>{row['label']}</b><br>Cluster: N/A<br>Contrib: {row['contrib']:.3f}"
                        for _, row in group_df_nan.iterrows()
                    ],
                    hoverinfo="text",
                    name="No Cluster",
                    showlegend=False,
                )
            )

        if n_clusters != 1 and "hull_data" in CS and CS["hull_data"] is not None and not CS["hull_data"].empty:
            hull_data = CS["hull_data"]
            for cluster_id in hull_data["cluster"].unique():
                group = hull_data[hull_data["cluster"] == cluster_id]
                fig.add_trace(
                    go.Scatter(
                        x=group["Dim1"],
                        y=group["Dim2"],
                        mode="lines",
                        line=dict(color=group_colors.get(cluster_id, "gray"), width=2),
                        fill="toself",
                        opacity=0.15,
                        hoverinfo="skip",
                        showlegend=False
                    )
                )

        # PATCH 2: if all Dim2 values are equal, the range is 0 and label_offset
        # becomes 0, causing labels to overlap markers with no visual separation.
        # → added a fallback minimum offset based on the x range to ensure
        # labels are always displaced from their markers.
        dim2_range = wordCoord["Dim2"].max() - wordCoord["Dim2"].min()
        dim1_range = wordCoord["Dim1"].max() - wordCoord["Dim1"].min()
        label_offset = 0.03 * dim2_range if dim2_range > 0 else 0.03 * dim1_range if dim1_range > 0 else 0.1

        for _, row in wordCoord[wordCoord["labelToPlot"] != ""].iterrows():
            fig.add_annotation(
                x=row["Dim1"],
                y=row["Dim2"] + label_offset,
                text=row["labelToPlot"],
                font=dict(size=labelsize, color=group_colors.get(row["groups"], "black")),
                showarrow=False,
            )

        fig.add_shape(
            type="line",
            x0=wordCoord["Dim1"].min(), x1=wordCoord["Dim1"].max(),
            y0=0, y1=0,
            line=dict(color="#B0B0B0", width=1.5, dash="dash"),
            layer="below"
        )
        fig.add_shape(
            type="line",
            x0=0, x1=0,
            y0=wordCoord["Dim2"].min(), y1=wordCoord["Dim2"].max(),
            line=dict(color="#B0B0B0", width=1.5, dash="dash"),
            layer="below"
        )

        for trace in fig.data:
            trace.hovertemplate = (
                "<b>%{text}</b><br>"
                "Cluster: %{marker.color}<br>"
                "Contribuzione: %{marker.size:.2f}<extra></extra>"
            )

        fig.update_layout(
            xaxis=dict(
                title=xlabel,
                zeroline=True, zerolinewidth=1.5, zerolinecolor="#B0B0B0",
                showgrid=True, gridcolor="lightgray",
                showline=False, showticklabels=True
            ),
            yaxis=dict(
                title=ylabel,
                zeroline=True, zerolinewidth=1.5, zerolinecolor="#B0B0B0",
                showgrid=True, gridcolor="lightgray",
                showline=False, showticklabels=True
            ),
            plot_bgcolor="rgba(0,0,0,0)",
            paper_bgcolor="rgba(0,0,0,0)",
            showlegend=False,
            height=800,
            hoverlabel=dict(
                bgcolor="white",
                font_size=13,
                font_family="Segoe UI, Arial",
                bordercolor="#5567BB"
            ),
        )
        fig = go.FigureWidget(fig)
        fig._config = fig._config | {'modeBarButtonsToRemove': ['pan', 'select', 'lasso2d', 'toImage'],
                                     'displaylogo': False}

        import networkx as nx
        from pyvis.network import Network
        from scipy.cluster.hierarchy import linkage, to_tree
        from pathlib import Path
        from scipy.cluster.hierarchy import optimal_leaf_ordering
        from scipy.spatial.distance import pdist
        import math
        import tempfile
        import os

        labels_lower = CS["km_res"]["data"].index.str.lower().tolist()
        coords = CS["km_res"]["data"][["Dim1", "Dim2"]].values
        linkage_matrix = CS["linkage"]

        word_to_cluster = dict(zip(WData["word"], WData["cluster"]))
        group_colors = assign_consistent_colors(WData["cluster"])
        leaf_offset = len(labels_lower)

        ddata = dendrogram(linkage_matrix, labels=labels_lower, no_plot=True)
        words_sorted = ddata["ivl"]
        n_terms = len(words_sorted)
        scale_factor = int(500 * math.log2(n_terms + 1))

        tree, nodes = to_tree(linkage_matrix, rd=True)
        net = Network(height="98vh", width="100%", directed=True, notebook=True, cdn_resources="in_line")
        net.toggle_physics(False)
        positions = {}
        label_boxes = []
        node_to_cluster = {}

        leaf_x = 0
        x_spacing = 100
        label_to_new_index = {label: i for i, label in enumerate(words_sorted)}
        cut_lines = {}

        for i, label in enumerate(words_sorted):
            node_id = i
            x = leaf_x
            y = 0
            cluster = word_to_cluster.get(label.lower(), -1)
            color = group_colors.get(cluster, "#999999")
            node_to_cluster[node_id] = cluster
            positions[node_id] = (x, y)

            net.add_node(
                node_id, label=" ", color=color, shape="dot", size=6,
                title=label, font={"size": 18, "face": "arial"},
                physics=False, x=x, y=y + 40
            )

            stub_y = y - 20
            stub_id = f"stub_{node_id}"
            positions[stub_id] = (x, stub_y)
            net.add_node(
                stub_id, label=" ", title=" ", color="#00000000",
                shape="dot", size=1, physics=False, x=x, y=stub_y,
                font={"color": "#00000000", "size": 1}
            )
            net.add_edge(
                stub_id, node_id, label=" ", color=color, width=10,
                smooth=False, physics=False, arrows=""
            )

            box_html = f"""
            <div id="label-{node_id}" class="floating-label" style="background-color: {color};">
            {label.upper()}
            </div>
            """
            label_boxes.append(box_html)
            leaf_x += x_spacing

        def add_internal_nodes(node):
            if node.is_leaf():
                label = labels_lower[node.id]
                new_id = label_to_new_index[label]
                stub_id = f"stub_{new_id}"
                return positions[stub_id], stub_id

            left_pos, left_stub_id = add_internal_nodes(node.left)
            right_pos, right_stub_id = add_internal_nodes(node.right)

            x_center = (left_pos[0] + right_pos[0]) / 2
            y = min(left_pos[1], right_pos[1])
            max_dist = linkage_matrix[:, 2].max()
            stub_y = distance_to_y(node.dist, max_dist, scale_factor)

            node_id = node.id + leaf_offset
            stub_id = f"stub_{node_id}"
            positions[node_id] = (x_center, y)
            positions[stub_id] = (x_center, stub_y)
            total = node.count

            left_cluster = node_to_cluster.get(
                node.left.id + leaf_offset if not node.left.is_leaf() else label_to_new_index[labels_lower[node.left.id]], -1
            )
            right_cluster = node_to_cluster.get(
                node.right.id + leaf_offset if not node.right.is_leaf() else label_to_new_index[labels_lower[node.right.id]], -1
            )

            cluster = left_cluster
            node_to_cluster[node_id] = cluster
            color = group_colors.get(cluster, "#999999")

            net.add_node(
                node_id, label=" ", shape="dot", size=20, physics=False,
                x=x_center, y=y,
                title=f"Distance: {node.dist:.2f} Words: {total}",
                color={"background": "#FFFFFF", "border": "#3399FF", "highlight": "#000000"},
                borderWidth=2,
            )
            net.add_node(
                stub_id, label=" ", title=f"Distance: {node.dist:.2f} Words: {total}",
                color="#00000000", shape="dot", size=4, physics=False,
                x=x_center, y=stub_y, font={"color": "#00000000", "size": 1}
            )

            if node != tree:
                net.add_edge(
                    stub_id, node_id, label=" ",
                    title=f"Distance: {node.dist:.2f} Words: {node.count}",
                    color=color, width=10, smooth=False, physics=False, arrows=""
                )

            for child_stub_id in [left_stub_id, right_stub_id]:
                child_x, child_y = positions[child_stub_id]
                inter_id = f"{node_id}_{child_stub_id}_v"
                inter_y = y

                net.add_node(
                    inter_id, label=" ", title=" ", color="#00000000",
                    shape="dot", size=1, physics=False, x=child_x, y=inter_y
                )
                net.add_edge(
                    node_id, inter_id, color=color,
                    title=f"Distance: {node.dist:.2f} Words: {node.count}",
                    width=10, smooth=False, physics=False, arrows=""
                )
                net.add_edge(
                    inter_id, child_stub_id, color=color,
                    title=f"Distance: {node.dist:.2f} Words: {node.count}",
                    width=10, smooth=False, physics=False, arrows=""
                )

            left_leaf_clusters = get_leaf_clusters(node.left, label_to_new_index, labels_lower, node_to_cluster)
            right_leaf_clusters = get_leaf_clusters(node.right, label_to_new_index, labels_lower, node_to_cluster)

            if left_leaf_clusters.isdisjoint(right_leaf_clusters):
                cl1 = min(left_leaf_clusters)
                cl2 = min(right_leaf_clusters)
                cluster_pair = tuple(sorted((cl1, cl2)))
                if cluster_pair not in cut_lines:
                    cut_lines[cluster_pair] = y

            return (x_center, stub_y), stub_id

        _, root_stub_id = add_internal_nodes(tree)

        if cut_lines:
            (cl1, cl2), y = max(cut_lines.items(), key=lambda x: x[1])
            net.add_node(f"cut_{cl1}_{cl2}_left", x=0, y=y, label="", shape="dot", size=0.1, color="#FF0000", physics=False)
            net.add_node(f"cut_{cl1}_{cl2}_right", x=(leaf_x - x_spacing), y=y, label="", shape="dot", size=0.1, color="#FF0000", physics=False)
            net.add_edge(
                f"cut_{cl1}_{cl2}_left", f"cut_{cl1}_{cl2}_right",
                label=f"cut @ y={y:.1f}", color="#FF0000", width=20, physics=False, arrows=""
            )

        html = net.generate_html()

        injection = f"""
        <style>
        .floating-label {{
            position: absolute;
            writing-mode: vertical-rl;
            transform: rotate(180deg);
            font-size: 14px;
            border: 1px solid #999;
            padding: 2px;
            text-align: center;
            line-height: 1.1;
            z-index: 999;
            pointer-events: none;
        }}
        </style>
        {''.join(label_boxes)}
        <script>
        function updateLabels() {{
            var canvas = document.getElementsByTagName("canvas")[0];
            var rect = canvas.getBoundingClientRect();
            var pos = network.getPositions();
            for (var id in pos) {{
                var domPos = network.canvasToDOM(pos[id]);
                var el = document.getElementById("label-" + id);
                if (el) {{
                    el.style.left = (rect.left + domPos.x + window.scrollX -5) + "px";
                    el.style.top = (rect.top + domPos.y + window.scrollY + 10) + "px";
                }}
            }}
        }}
        network.on("afterDrawing", updateLabels);
        window.addEventListener("resize", updateLabels);
        </script>
        """

        html = html.replace("</body>", injection + "\n</body>")

        tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".html")
        html_path = tmp.name
        with open(html_path, 'w', encoding="utf-8") as f:
            new_css = "     .card {\n                 border: none;\n             }"
            updated_html = html.replace("</style>", new_css + "\n        </style>")
            updated_html = updated_html.replace("1px solid lightgray", "none")
            f.write(updated_html)

        words_by_cluster = WData[["word", "Dim1", "Dim2", "cluster"]].copy()

        return fig, html_path.split(os.sep)[-1], words_by_cluster, CS["CSData"]


def conceptual_structure(
    df: pd.DataFrame,
    field: str = "ID",
    ngrams: int = 1,
    method: str = "MCA",
    min_degree: int = 2,
    n_clusters: Union[str, int] = "auto",
    k_max: int = 5,
    stemming: bool = False,
    labelsize: int = 10,
    documents: int = 2,
    graph: bool = True,
    remove_terms: Optional[Sequence[str]] = None,
    synonyms: Optional[Dict[str, str]] = None
) -> Dict:

    binary = method == "MCA"

    if field == "ID":
        CW = cocMatrix(df, Field="ID", binary=binary, remove_terms=remove_terms, synonyms=synonyms)
        CW = CW.loc[:, CW.sum() >= min_degree]
        CW = CW.loc[CW.sum(axis=1) > 0]
        CW = CW.loc[:, ~CW.columns.isin(["NA"])]

    elif field == "DE":
        CW = cocMatrix(df, Field="DE", binary=binary, remove_terms=remove_terms, synonyms=synonyms)
        CW = CW.loc[:, CW.sum() >= min_degree]
        CW = CW.loc[CW.sum(axis=1) > 0]
        CW = CW.loc[:, ~CW.columns.isin(["NA"])]

    elif field == "ID_TM":
        df = term_extraction(df, field="ID", stemming=stemming, remove_terms=remove_terms, synonyms=synonyms, ngrams=ngrams)
        CW = cocMatrix(df, Field="ID_TM", binary=binary)
        CW = CW.loc[:, CW.sum() >= min_degree]
        CW = CW.loc[CW.sum(axis=1) > 0]
        CW = CW.loc[:, ~CW.columns.isin(["NA"])]

    elif field == "DE_TM":
        df = term_extraction(df, field="DE", stemming=stemming, remove_terms=remove_terms, synonyms=synonyms, ngrams=ngrams)
        CW = cocMatrix(df, Field="DE_TM", binary=binary)
        CW = CW.loc[:, CW.sum() >= min_degree]
        CW = CW.loc[CW.sum(axis=1) > 0]
        CW = CW.loc[:, ~CW.columns.isin(["NA"])]

    elif field == "TI":
        df = term_extraction(df, field="TI", stemming=stemming, remove_terms=remove_terms, synonyms=synonyms, ngrams=ngrams)
        CW = cocMatrix(df, Field="TI_TM", binary=binary)
        CW = CW.loc[:, CW.sum() >= min_degree]
        CW = CW.loc[CW.sum(axis=1) > 0]
        CW = CW.loc[:, ~CW.columns.isin(["NA"])]

    elif field == "AB":
        df = term_extraction(df, field="AB", stemming=stemming, remove_terms=remove_terms, synonyms=synonyms, ngrams=ngrams)
        CW = cocMatrix(df, Field="AB_TM", binary=binary)
        CW = CW.loc[:, CW.sum() >= min_degree]
        CW = CW.loc[CW.sum(axis=1) > 0]
        CW = CW.loc[:, ~CW.columns.isin(["NA"])]

    # PATCH 4: if all terms are filtered out by min_degree, CW is an empty
    # DataFrame and factorial() crashes on matrix operations (pdist, X.T @ X).
    # → return an empty result dict early instead of crashing.
    if CW.empty:
        return {
            'net': CW, 'res': None, 'km_res': {'data': pd.DataFrame(), 'centers': pd.DataFrame()},
            'docCoord': None, 'coord': None, 'hull_data': pd.DataFrame(), 'linkage': None,
            'CSData': pd.DataFrame(), 'WData': pd.DataFrame(), 'params': pd.DataFrame()
        }

    CW.columns = CW.columns.str.lower()
    CW.index = CW.index.str.lower()

    results = factorial(CW, method=method, n_clusters=n_clusters, k_max=k_max)
    res_mca = results['res_mca'] if 'res_mca' in results else None

    if res_mca is not None:
        doc_coord = results['docCoord']
    else:
        doc_coord = None

    # PATCH 3: results.get('df', results.get('res')) can return None if neither
    # key is present in the dict — calling df.index = ... on None crashes with
    # AttributeError. → raise an explicit error to surface the root cause.
    df = results.get('df', results.get('res'))
    if df is None:
        raise ValueError(
            f"factorial() returned no 'df' or 'res' key for method='{method}'. "
            "Check that the method is supported and the input matrix is valid."
        )

    df.index = CW.columns
    doc_coord = results['docCoord']

    if "TC" in df.columns and method != "MDS":
        doc_coord = doc_coord.copy()
        doc_coord_index_upper = doc_coord.index.astype(str).str.upper()
        df_index_upper = df.index.astype(str).str.upper()
        tc_map = dict(zip(df_index_upper, df["TC"].astype(float)))
        doc_coord["TC"] = doc_coord_index_upper.map(tc_map)

    km_res = linkage(pdist(df, metric='euclidean'), method='average')
    results['linkage'] = km_res

    # PATCH 5: n_clusters greater than the number of available terms causes
    # fcluster to produce unexpected behavior or crash.
    # → clamp n_clusters to [1, len(CW.columns)] before calling fcluster.
    max_clusters = len(CW.columns)
    if n_clusters == "auto":
        heights = np.diff(km_res[:, 2])
        n_clusters = min(len(heights) - np.argmax(heights) + 1, k_max, max_clusters)
    else:
        n_clusters = max(1, min(int(n_clusters), k_max, max_clusters))

    cluster_labels = fcluster(km_res, n_clusters, criterion='maxclust')
    df = df.copy()
    df['cluster'] = cluster_labels

    data_clust = df.copy()
    centers = data_clust.groupby('cluster').agg({'Dim1': 'mean', 'Dim2': 'mean'}).reset_index()
    centers = centers[['Dim1', 'Dim2', 'cluster']]

    data_clust['shape'] = "1"
    data_clust['label'] = data_clust.index.astype(str)
    centers['shape'] = "0"
    centers['label'] = ""

    df_clust = pd.concat([data_clust, centers], ignore_index=True, sort=False)
    colorlist = px.colors.qualitative.Plotly
    df_clust['color'] = df_clust['cluster'].apply(
        lambda x: colorlist[int(x) % len(colorlist)] if pd.notnull(x) else "#CCCCCC"
    )

    hull_data_list = []
    for cluster in df_clust['cluster'].dropna().unique():
        group = df_clust[df_clust['cluster'] == cluster]
        if len(group) >= 3:
            try:
                hull_idx = ConvexHull(group[['Dim1', 'Dim2']]).vertices
                hull_points = group.iloc[hull_idx]
                hull_points = pd.concat([hull_points, hull_points.iloc[[0]]])
            except QhullError:
                x_min, x_max = group["Dim1"].min(), group["Dim1"].max()
                y_min, y_max = group["Dim2"].min(), group["Dim2"].max()
                hull_points = pd.DataFrame({
                    "Dim1": [x_min, x_max, x_max, x_min, x_min],
                    "Dim2": [y_min, y_min, y_max, y_max, y_min],
                    "cluster": cluster
                })
            hull_data_list.append(hull_points)

    if hull_data_list:
        hull_data = pd.concat(hull_data_list)
        hull_data = pd.concat([hull_data, hull_data.groupby('cluster').head(1)])
        hull_data = hull_data.reset_index(drop=True)
        hull_data['id'] = hull_data.groupby('cluster').cumcount() + 1
        hull_data = hull_data.sort_values(['cluster', 'id'])
    else:
        hull_data = pd.DataFrame()

    if doc_coord is not None:
        results = {
            'net': CW, 'res': res_mca,
            'km_res': {'data': df, 'centers': centers},
            'docCoord': doc_coord,
            'coord': results['coord'] if 'coord' in results else None,
            'hull_data': hull_data,
            'linkage': km_res
        }
    else:
        results = {
            'net': CW, 'res': df,
            'km_res': {'data': df, 'centers': centers, 'cluster': df['cluster']},
            'docCoord': None, 'coord': None,
            'hull_data': hull_data, 'linkage': km_res
        }

    params = {
        'field': field, 'ngrams': ngrams, 'method': method,
        'min_degree': min_degree, 'n_clusters': n_clusters, 'k_max': k_max,
        'stemming': stemming, 'labelsize': labelsize, 'documents': documents,
        'graph': graph, 'remove_terms': remove_terms, 'synonyms': synonyms
    }
    params_df = pd.DataFrame({'params': list(params.keys()), 'values': [str(params[k]) for k in params]})
    results['params'] = params_df

    return results


def factorial(X, method, n_clusters=5, k_max=5):
    """
    Perform factorial analysis on the input data.

    Args:
        X: Input data (e.g., co-occurrence matrix).
        method: Analysis method ("CA", "MCA", "MDS").

    Returns:
        A dictionary containing the results of the factorial analysis.
    """
    if method == "CA":
        res_mca = CA(n_components=2).fit(X)
        row_coords = res_mca.row_coordinates(X)
        col_coords = res_mca.column_coordinates(X)
        K = 2
        I, J = row_coords.shape[0], col_coords.shape[0]
        singular_values = np.linalg.norm(row_coords.values, axis=0)[:K]
        evF = np.tile(singular_values, (I, 1))
        evG = np.tile(singular_values, (J, 1))
        rpc = row_coords.iloc[:, :K].values * evF
        cpc = col_coords.iloc[:, :K].values * evG
        column_masses = (X.sum(axis=0) / X.values.sum()).values
        column_distances = np.sum(cpc ** 2, axis=1)
        coord = {
            "coord": pd.DataFrame(cpc[:, :2], columns=["Dim1", "Dim2"], index=col_coords.index),
            "contrib": pd.DataFrame((cpc[:, :2] ** 2) * column_masses[:, None] / singular_values, columns=["Dim1", "Dim2"], index=col_coords.index),
            "cos2": pd.DataFrame((cpc[:, :2] ** 2) / column_distances[:, None], columns=["Dim1", "Dim2"], index=col_coords.index)
        }
        coord_doc = {
            "coord": pd.DataFrame(rpc[:, :2], columns=["Dim1", "Dim2"], index=row_coords.index),
            "contrib": pd.DataFrame((rpc[:, :2] ** 2), columns=["Dim1", "Dim2"], index=row_coords.index),
            "cos2": pd.DataFrame((rpc[:, :2] ** 2) / np.sum(rpc[:, :2] ** 2, axis=1)[:, None], columns=["Dim1", "Dim2"], index=row_coords.index)
        }

    elif method == "MCA":
        X = X.apply(lambda col: col.astype("category"))
        res_mca = MCA(n_components=2).fit(X)
        levelnames = [f"{col}_{val}" for col in X.columns for val in X[col].cat.categories]
        K = 2
        row_coords = res_mca.row_coordinates(X)
        col_coords = res_mca.column_coordinates(X)
        I, J = row_coords.shape[0], col_coords.shape[0]
        singular_values = np.linalg.norm(row_coords.values, axis=0)[:2]
        evF = np.tile(singular_values, (I, 1))
        evG = np.tile(singular_values, (J, 1))
        rpc = row_coords.iloc[:, :K].values * evF
        cpc = col_coords.iloc[:, :K].values * evG
        column_frequencies = X.apply(lambda col: col.value_counts(normalize=True)).fillna(0)
        column_mass = column_frequencies.values.flatten()
        column_distances = np.sum(cpc ** 2, axis=1)
        coord_df = pd.DataFrame({"Dim1": cpc[:, 0], "Dim2": cpc[:, 1], "label": levelnames})
        mask = coord_df["label"].str[-2:] == "_1"
        coord = {
            "coord": coord_df[mask].drop(columns=["label"]).reset_index(drop=True),
            "contrib": pd.DataFrame((cpc ** 2) * column_mass[:, np.newaxis] / singular_values, columns=["Dim1", "Dim2"]).assign(label=levelnames)[mask].drop(columns=["label"]).reset_index(drop=True),
            "cos2": pd.DataFrame((cpc ** 2) / column_distances[:, np.newaxis], columns=["Dim1", "Dim2"]).assign(label=levelnames)[mask].drop(columns=["label"]).reset_index(drop=True)
        }
        row_names = coord["coord"].index.astype(str).str[:-2]
        coord["coord"].index = row_names
        coord["contrib"].index = row_names
        coord["cos2"].index = row_names
        coord_doc = {
            "coord": pd.DataFrame({"Dim1": rpc[:, 0], "Dim2": rpc[:, 1]}, index=X.index),
            "contrib": pd.DataFrame((rpc[:, :2] ** 2) * res_mca.row_masses_.values[:, np.newaxis] / singular_values, columns=["Dim1", "Dim2"]),
            "cos2": pd.DataFrame(res_mca.row_masses_.values[:, np.newaxis] * rpc ** 2 / res_mca.total_inertia_, columns=["Dim1", "Dim2"])
        }

    elif method == "MDS":
        net_matrix = X.T @ X
        net_matrix_np = net_matrix.to_numpy()
        row_sums = net_matrix_np.sum(axis=1, keepdims=True)
        col_sums = net_matrix_np.sum(axis=0, keepdims=True)
        expected = row_sums @ col_sums / net_matrix_np.sum()
        norm_matrix = np.divide(net_matrix_np, expected, where=expected != 0)
        norm_matrix = np.nan_to_num(norm_matrix, nan=0.0, posinf=0.0, neginf=0.0)
        dissim_matrix = 1 - norm_matrix
        np.fill_diagonal(dissim_matrix, 0)
        mds = SK_MDS(n_components=2, dissimilarity="precomputed", random_state=42)
        coords = mds.fit_transform(dissim_matrix)
        coords = StandardScaler().fit_transform(coords)
        df = pd.DataFrame(coords, columns=["Dim1", "Dim2"], index=X.columns)
        km_res = linkage(pdist(df), method='average')

        if n_clusters == "auto":
            heights = np.diff(km_res[:, 2])
            n_clusters = min(len(heights) - np.argmax(heights) + 1, k_max)
        else:
            n_clusters = max(1, min(int(n_clusters), k_max))

        cluster_labels = fcluster(km_res, n_clusters, criterion='maxclust')
        df["cluster"] = cluster_labels

        centroids = df.groupby("cluster")[["Dim1", "Dim2"]].transform("mean")
        contrib_raw = np.sqrt((df["Dim1"] - centroids["Dim1"]) ** 2 + (df["Dim2"] - centroids["Dim2"]) ** 2)

        # PATCH 6: if all points are equidistant from their centroid, the
        # normalization range is 0 and the division produces NaN everywhere.
        # → added a check: if range is 0, assign uniform contrib of 1.0.
        contrib_range = contrib_raw.max() - contrib_raw.min()
        if contrib_range > 0:
            df["contrib"] = (contrib_raw - contrib_raw.min()) / contrib_range + 1
        else:
            df["contrib"] = 1.0

        sv = np.linalg.norm(coords, axis=0)
        eig_benz = np.where(
            sv ** 2 > 1 / len(sv),
            ((len(sv) / (len(sv) - 1)) ** 2) * (sv ** 2 - 1 / len(sv)) ** 2,
            0
        )
        perc = eig_benz / eig_benz.sum() * 100 if eig_benz.sum() > 0 else np.zeros_like(eig_benz)
        cum_perc = np.cumsum(perc)
        eig_corr = pd.DataFrame({"eig": sv ** 2, "eigBenz": eig_benz, "perc": perc, "cumPerc": cum_perc})

        results = {
            "res_mca": {"eigCorr": eig_corr, "sv": sv},
            "df": df,
            "df_doc": None,
            "docCoord": None,
            "coord": None
        }
        return results

    else:
        raise ValueError(f"Unsupported method: {method}")

    if method != "MDS":
        res_mca = eig_correction(res_mca, singular_values)
        docCoord = pd.DataFrame(
            np.hstack([coord_doc["coord"], coord_doc["contrib"].sum(axis=1).to_numpy()[:, None]]),
            columns=["dim1", "dim2", "contrib"],
        ).sort_values(by="contrib", ascending=False)
        res_mca.coord_doc = coord_doc
        results = {
            "res_mca": res_mca,
            "df": coord["coord"],
            "df_doc": coord_doc["coord"],
            "docCoord": docCoord,
            "coord": coord,
        }

    return results


def eig_correction(res_mca, singular_values):
    """
    Apply Benzecri eigenvalue correction to the results of factorial analysis.

    Args:
        res_mca: Results of factorial analysis.
        singular_values: Array or list of singular values from the analysis.

    Returns:
        Corrected results with eigCorr attribute attached.
    """
    n = len(singular_values)
    e = np.array(singular_values) ** 2
    eig_benz = np.where(e > 1 / n, ((n / (n - 1)) ** 2) * (e - (1 / n)) ** 2, 0)
    perc = eig_benz / np.sum(eig_benz) * 100 if np.sum(eig_benz) > 0 else np.zeros_like(eig_benz)
    cum_perc = np.cumsum(perc)
    eig_corr = pd.DataFrame({"eig": e, "eigBenz": eig_benz, "perc": perc, "cumPerc": cum_perc})

    if hasattr(res_mca, '__dict__'):
        res_mca.eigCorr = eig_corr
    else:
        res_mca['eigCorr'] = eig_corr
    return res_mca


def avoidOverlaps(df, threshold=0.10, dimX=0, dimY=1):
    """
    Avoid overlapping labels in a scatter plot.

    Args:
        df: DataFrame containing the coordinates and labels.
        threshold: Distance threshold for avoiding overlaps.
        dimX: Index of the x-coordinate column.
        dimY: Index of the y-coordinate column.

    Returns:
        Set of labels to remove to avoid overlaps.
    """
    df["Dim2"] = df["Dim2"] / 3
    filtered_df = df[df["labelToPlot"] != ""].copy()
    distances = pd.DataFrame(pdist(filtered_df[["Dim1", "Dim2"]], metric="cityblock"), columns=["dist"])
    distances["from"] = np.repeat(filtered_df["labelToPlot"].values, len(filtered_df))
    distances["to"] = np.tile(filtered_df["labelToPlot"].values, len(filtered_df))
    distances = distances[distances["from"] != distances["to"]]
    distances = distances.merge(
        filtered_df[["labelToPlot", "dotSize"]].rename(columns={"dotSize": "w_from"}),
        left_on="from", right_on="labelToPlot"
    ).drop(columns=["labelToPlot"])
    distances = distances.merge(
        filtered_df[["labelToPlot", "dotSize"]].rename(columns={"dotSize": "w_to"}),
        left_on="to", right_on="labelToPlot"
    ).drop(columns=["labelToPlot"])
    distances = distances[distances["dist"] < threshold]

    labels_to_remove = []
    while not distances.empty:
        row = distances.iloc[0]
        label = row["to"] if row["w_from"] > row["w_to"] else row["from"]
        labels_to_remove.append(label)
        distances = distances[(distances["from"] != label) & (distances["to"] != label)]

    return set(labels_to_remove)