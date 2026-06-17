from www.services import *
from pyvis.network import Network
import tempfile
import pandas as pd
import networkx as nx
import os
from matplotlib.colors import to_rgba

def hex_to_rgba(hex_color, alpha):
    if not isinstance(hex_color, str) or not hex_color.startswith("#") or len(hex_color) != 7:
        hex_color = "#999999"  # neutral grey fallback
    try:
        r, g, b = tuple(int(hex_color.lstrip("#")[i:i+2], 16) for i in (0, 2, 4))
    except Exception:
        r, g, b = (153, 153, 153)  # fallback rgb(153,153,153)
    return f"rgba({r},{g},{b},{alpha})"



def get_historiograph(df, node_label="AU1", histNodes=20, hist_isolates=True, histlabelsize=3, histsize=4, sep=";"):
    """
    Generates the historiograph and returns an interactive HTML file via Pyvis.

    Returns:
        hist_plot: object with layout and networkx graph
        hist_data: dataframe with metadata, clickable DOIs, clusters, years
        filename: name of the temporarily saved interactive HTML file
    """
    # Pre-processing
    _df = df.get() if hasattr(df, 'get') and not isinstance(df, pd.DataFrame) else df
    if 'SR' not in _df.columns or _df['SR'].eq('').all():
        df = metaTagExtraction(df, "SR")
    # PATCH: metaTagExtraction may return a plain DataFrame — wrap in reactive
    # so histNetwork/cocMatrix can call .get() on it
    hist_results = histNetwork(df, min_citations=0, sep=sep, network=True)
    # CR data limitation: OpenAlex CR = URLs, PubMed CR = empty
    # histNetwork returns None or empty NetMatrix — return gracefully
    if hist_results is None or hist_results.get('NetMatrix') is None:
        empty_df = pd.DataFrame(columns=["Paper", "Title", "Year", "DOI", "LCS", "GCS", "cluster"])
        tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".html")
        return None, empty_df, tmp.name.split(os.sep)[-1]
    # 1. Initial graph construction
    hist_plot = histPlot(
        hist_results,
        n=histNodes,
        size=histsize,
        remove_isolates=False,
        label=node_label,
        verbose=False
    )

    # 2. Retrieve layout and initial network
    layout_df = pd.DataFrame(hist_plot["layout"]).copy()
    full_net = hist_plot["net"]

    # 3. Filter edges to keep only those with nodes in top-N
    selected_nodes = set(full_net.nodes())
    edges_filtered = [(u, v) for u, v in full_net.edges() if u in selected_nodes and v in selected_nodes]

    # 4. Rebuild filtered network
    net_nx = nx.DiGraph()
    net_nx.add_nodes_from(selected_nodes)
    net_nx.add_edges_from(edges_filtered)

    # 5. Optionally remove isolated components
    if hist_isolates:
        connected_components = list(nx.connected_components(net_nx.to_undirected()))
        valid_components = [c for c in connected_components if len(c) > 1]
        valid_nodes = set().union(*valid_components)
        net_nx = net_nx.subgraph(valid_nodes).copy()
    else:
        valid_nodes = set(net_nx.nodes)

    # 6. Filter layout
    layout_df = layout_df[layout_df.index.isin(valid_nodes)].copy()
    layout_df["name"] = layout_df.index
    layout_df.reset_index(drop=True, inplace=True)

    # 7. Filter hist_data based on nodes present in the graph
    hist_data = hist_results["histData"].copy()
    hist_data = hist_data[hist_data["Paper"].isin(valid_nodes)].copy()
    hist_data = hist_data.merge(layout_df, left_on="Paper", right_on="name", how="left")

    # Cluster from color
    if "color" in hist_data.columns:
        unique_colors = hist_data['color'].dropna().unique()
        color_to_cluster = {color: idx + 1 for idx, color in enumerate(unique_colors)}
        hist_data['cluster'] = hist_data['color'].map(color_to_cluster)
    else:
        hist_data['color'] = "gray"
        hist_data['cluster'] = -1

    # Clickable DOI formatting
    hist_data['DOI'] = hist_data['DOI'].apply(
        lambda doi: f'<a href="https://doi.org/{doi}" target="_blank">{doi}</a>' if pd.notnull(doi) else ""
    )

    # Remove missing Year rows
    hist_data = hist_data[hist_data["Year"].notna()].copy()
    if hist_data.empty:
        raise ValueError("No data with valid 'Year' for the historiograph.")

    # Horizontal temporal positioning
    hist_data = hist_data.sort_values(['cluster', 'Year'])
    min_year = hist_data["Year"].min()
    hist_data["x"] = (hist_data["Year"] - min_year) * 60

    # Vertical spacing between clusters
    hist_data["y"] = hist_data["cluster"] * 150 + np.random.uniform(-30, 30, size=len(hist_data))

    # Robust tooltips and labels
    hist_data["tooltip"] = hist_data.apply(
        lambda row: (
            f"<b>{str(row.get('Title', 'No Title')).replace('<', '&lt;').replace('>', '&gt;')}</b>"
            f"<br><b>Year:</b> {row.get('Year', 'n.d.')}"
            f"<br><b>DOI:</b> {row.get('DOI', '')}"
            f"<br><b>LCS:</b> {int(row.get('LCS', 0))}"
            f"<br><b>GCS:</b> {int(row.get('GCS', 0))}"
        ),
        axis=1
    )
    hist_data["label"] = hist_data.apply(
        lambda row: str(row.get("Title", "No Title"))[:40] + "..." if len(str(row.get("Title", ""))) > 40 else str(row.get("Title", "No Title")),
        axis=1
    )

    # Dynamic opacity and font size
    min_font_size = 10
    max_font_size = 130
    font_opacity = np.sqrt((histlabelsize - min_font_size) / (max_font_size - min_font_size)) * 0.8 + 0.3
    font_opacity = max(0.1, min(1, font_opacity))

    # Node size proportional to LCS
    if "LCS" in hist_data.columns and not hist_data["LCS"].isnull().all():
        lcs_min = hist_data["LCS"].min()
        lcs_max = hist_data["LCS"].max()
        lcs_range = lcs_max - lcs_min if lcs_max > lcs_min else 1
        hist_data["node_size"] = hist_data["LCS"].apply(lambda lcs: 10 + ((lcs - lcs_min) / lcs_range) * 10)
    else:
        hist_data["node_size"] = histsize

    # Initialize Pyvis graph
    net = Network(height="98vh", width="100%", directed=True, notebook=True, cdn_resources="in_line")
    net.toggle_physics(False)

    # Add nodes
    for _, row in hist_data.iterrows():
        base_color = row.get("color", "#999999")
        color_rgba = hex_to_rgba(base_color, 0.8)
        border_color = hex_to_rgba(base_color, 0.4)

        if node_label == "AU1":
            label_value = row.get("id", f"{row.get('name', 'unknown')}, {row.get('Year', 'n.d.')}")

        elif node_label == "TI":
            label_value = row.get("Title", "No Title")

        elif node_label == "ID":
            # PATCH: replaced eval() with safe parser — eval() crashes on
            # non-Python strings (e.g. semicolon-separated values produced
            # after DataFrame merges). Handles list, semicolon, or comma formats.
            raw = row.get("Author_Keywords", [])
            if isinstance(raw, list):
                keywords = raw
            elif isinstance(raw, str) and raw.strip():
                keywords = [k.strip() for k in raw.replace(";", ",").split(",") if k.strip()]
            else:
                keywords = []
            label_value = "; ".join(keywords) if keywords else "No keywords"

        elif node_label == "DE":
            # PATCH: same safe parser for KeywordsPlus field.
            raw = row.get("KeywordsPlus", [])
            if isinstance(raw, list):
                keywords = raw
            elif isinstance(raw, str) and raw.strip():
                keywords = [k.strip() for k in raw.replace(";", ",").split(",") if k.strip()]
            else:
                keywords = []
            label_value = "; ".join(keywords) if keywords else "No keywords"

        else:
            label_value = "unknown"

        net.add_node(
            n_id=row["Paper"],
            label=label_value,
            title=row["tooltip"],
            color={
                "background": color_rgba,
                "border": border_color,
                "highlight": {
                    "background": color_rgba,
                    "border": "#000000"
                }
            },
            x=row["x"],
            y=row["y"],
            size=row["node_size"],
            font={
                "size": histlabelsize,
                "face": "arial",
                "color": f"rgba(0,0,0,{font_opacity})"
            },
            borderWidth=2,
            borderWidthSelected=3,
            physics=False,
            fixed={"x": True, "y": False}
        )

    # Add edges with shading
    existing_nodes = set(net.get_nodes())
    for source, target in net_nx.edges():
        if source in existing_nodes and target in existing_nodes:
            source_color = hist_data.loc[hist_data["Paper"] == source, "color"].values[0]
            edge_color = hex_to_rgba(source_color, 0.4)
            net.add_edge(source, target, color=edge_color, width=1.5)

    # Save temporary HTML
    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".html")
    html_path = tmp.name
    with open(html_path, 'w', encoding="utf-8") as f:
        html = net.generate_html()
        new_css = "     .card {\n                 border: none;\n             }"
        updated_html = html.replace("</style>", new_css + "\n        </style>")
        updated_html = updated_html.replace("1px solid lightgray", "none")
        f.write(updated_html)

    return hist_plot, hist_data, html_path.split(os.sep)[-1]