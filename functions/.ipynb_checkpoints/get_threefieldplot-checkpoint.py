from www.services import *
import textwrap


def get_three_field_plot(df, left_field, middle_field, right_field, left_field_items, middle_field_items, right_field_items):
    """
    Generate a three-field plot (Sankey diagram) to visualize the main items
    of three fields and their relationships.

    Args:
        df: A DataFrame object containing the data.
        left_field: The field for the left side of the plot.
        middle_field: The field for the middle of the plot.
        right_field: The field for the right side of the plot.
        left_field_items: Number of items to plot for the left field.
        middle_field_items: Number of items to plot for the middle field.
        right_field_items: Number of items to plot for the right field.

    Returns:
        A Plotly FigureWidget representing the three-field Sankey diagram.
    """
    fields = [left_field, middle_field, right_field]
    n = [left_field_items, middle_field_items, right_field_items]

    if "CR_SO" in fields:
        df = metaTagExtraction(df, "CR_SO")
    if "AU_CO" in fields:
        df = metaTagExtraction(df, "AU_CO")
    if "AB_TM" in fields:
        df = term_extraction(df, field="AB")
    if "TI_TM" in fields:
        df = term_extraction(df, field="TI")

    # PATCH: cocMatrix returns None when the field is empty (e.g. PubMed DE is
    # always empty from eSummary API) — accessing .shape on None crashes with
    # AttributeError. Return an empty figure gracefully if any matrix is None or empty.
    # Document x Attribute matrix — LEFT field
    WL = cocMatrix(df, fields[0], binary=True, n=n[0])
    if WL is None or WL.empty:
        return go.FigureWidget(go.Figure())
    n1 = min(n[0], WL.shape[1])
    TopL = WL.columns.tolist()

    # Document x Attribute matrix — MIDDLE field
    WM = cocMatrix(df, fields[1], binary=True, n=n[1])
    if WM is None or WM.empty:
        return go.FigureWidget(go.Figure())
    n2 = min(n[1], WM.shape[1])
    TopM = WM.columns.tolist()

    # Document x Attribute matrix — RIGHT field
    WR = cocMatrix(df, fields[2], binary=True, n=n[2])
    if WR is None or WR.empty:
        return go.FigureWidget(go.Figure())
    n3 = min(n[2], WR.shape[1])
    TopR = WR.columns.tolist()

    # PATCH 1: if cocMatrix returns an empty DataFrame for any field, n1/n2/n3
    # is 0 and reassigning LM.index/columns with a mismatched range crashes
    # with ValueError: Length mismatch.
    # → return an empty figure early if any of the three matrices is empty.
    if n1 == 0 or n2 == 0 or n3 == 0:
        empty_fig = go.FigureWidget(go.Figure())
        return empty_fig

    # Co-occurrence matrices
    LM = WL.T.dot(WM)
    MR = WM.T.dot(WR)

    LM.index = range(1, n1 + 1)
    LM.columns = range(n1 + 1, n1 + n2 + 1)
    MR.index = range(n1 + 1, n1 + n2 + 1)
    MR.columns = range(n1 + n2 + 1, n1 + n2 + n3 + 1)

    # Melt matrices to get edge lists
    def melt_matrix(matrix):
        var1 = np.repeat(matrix.index.values, matrix.shape[1])
        var2 = np.tile(matrix.columns.values, matrix.shape[0])
        values = matrix.values.flatten()
        return pd.DataFrame({'Var1': var1, 'Var2': var2, 'Value': values})

    LMm = melt_matrix(LM)
    LMm["group"] = None
    MRm = melt_matrix(MR)
    MRm["group"] = None

    Edges = pd.concat([LMm, MRm], ignore_index=True)
    Edges['Var1'] = Edges['Var1'].astype(int)
    Edges['Var2'] = Edges['Var2'].astype(int)
    Edges.columns = ["from", "to", "Value", "group"]
    Edges = Edges.dropna(subset=['to', 'from'])
    Edges['from'] = Edges['from'] - 1
    Edges['to'] = Edges['to'] - 1
    Edges = Edges.drop(columns=['group'])
    Edges = Edges[Edges["Value"] >= 1]

    Nodes = pd.DataFrame({
        "Nodes": [*TopL, *TopM, *TopR],
        "group": [fields[0]] * len(TopL) + [fields[1]] * len(TopM) + [fields[2]] * len(TopR),
        "level": [1] * len(TopL) + [2] * len(TopM) + [3] * len(TopR)
    })
    Nodes["id"] = range(len(Nodes))
    min_flow = 1
    Edges.rename(columns={"Value": "weight"}, inplace=True)
    Edges = Edges[Edges["weight"] >= min_flow]

    Kx = len(Nodes['group'].unique())
    Ky = len(Nodes)
    level_counts = Nodes['level'].value_counts().sort_index()
    Kx = len(level_counts)
    Nodes['coordX'] = np.repeat(np.linspace(0, 1, Kx), level_counts.values)
    Nodes['coordY'] = np.repeat(0.1, Ky)

    group_colors = {
        fields[0]: "#3288BD",
        fields[1]: "#F46D43",
        fields[2]: "#66C2A5",
    }

    node_weights = pd.concat([
        Edges.groupby('from')['weight'].sum(),
        Edges.groupby('to')['weight'].sum()
    ], axis=1).fillna(0).sum(axis=1)
    Nodes['weight'] = Nodes['id'].map(node_weights).fillna(0)

    def hex_to_rgba(hex_color, opacity):
        hex_color = hex_color.lstrip('#')
        rgb = tuple(int(hex_color[i:i + 2], 16) for i in (0, 2, 4))
        return f'rgba({rgb[0]},{rgb[1]},{rgb[2]},{opacity:.2f})'

    min_opacity, max_opacity = 0.3, 1.0

    # PATCH 2: the original guard checked max > 0 but not max != min — if all
    # nodes share the same weight, max - min is 0 and the normalization produces
    # NaN in every opacity value.
    # → added a second condition to ensure the range is non-zero before dividing.
    weight_min = Nodes['weight'].min()
    weight_max = Nodes['weight'].max()
    if weight_max > 0 and weight_max != weight_min:
        norm_weights = (Nodes['weight'] - weight_min) / (weight_max - weight_min)
        opacities = norm_weights * (max_opacity - min_opacity) + min_opacity
    else:
        opacities = np.full(len(Nodes), min_opacity)

    Nodes['color'] = [
        hex_to_rgba(group_colors[g], o)
        for g, o in zip(Nodes['group'], opacities)
    ]

    def wrap_label(label, width=45):
        return "<br>".join(textwrap.wrap(str(label), width=width))

    Nodes['wrapped_label'] = Nodes['Nodes'].apply(lambda x: wrap_label(x, width=35))

    # Remove isolated nodes (not connected to any edge)
    ind = set(Nodes['id']) - set(Edges['from']).union(set(Edges['to']))
    if ind:
        Nodes = Nodes[~Nodes['id'].isin(ind)]
        Nodes['idnew'] = range(len(Nodes))
        id_map = dict(zip(Nodes['id'], Nodes['idnew']))

        # PATCH 3: if id_map does not cover all values in Edges['from'] or
        # Edges['to'] (e.g. isolated nodes still referenced in edges after
        # filtering), .map() produces NaN — the Sankey crashes with float
        # indices instead of int.
        # → drop edges whose endpoints are not in id_map before remapping,
        # then cast to int to ensure valid Sankey indices.
        Edges = Edges[Edges['from'].isin(id_map) & Edges['to'].isin(id_map)]
        Edges['from'] = Edges['from'].map(id_map).astype(int)
        Edges['to'] = Edges['to'].map(id_map).astype(int)
        Nodes['id'] = Nodes['idnew']

    fig = go.Figure(data=[go.Sankey(
        arrangement="snap",
        node=dict(
            pad=20,
            thickness=28,
            line=dict(color="black", width=1),
            label=Nodes["wrapped_label"],
            color=Nodes["color"],
            x=Nodes["coordX"],
            y=Nodes["coordY"],
            customdata=Nodes["Nodes"],
            hovertemplate='%{customdata}<extra></extra>',
        ),
        link=dict(
            source=Edges["from"],
            target=Edges["to"],
            value=Edges["weight"],
            color="rgba(120,120,120,0.25)",
            hovertemplate='From: %{source.label}<br>To: %{target.label}<br>Value: %{value}<extra></extra>',
        )
    )])

    for level, field in enumerate(fields, start=1):
        group_nodes = Nodes[Nodes['level'] == level]
        if not group_nodes.empty:
            x_pos = group_nodes['coordX'].mean()
            fig.add_annotation(
                x=x_pos,
                y=1.13,
                text=f"<b>{wrap_label(field, width=18)}</b>",
                showarrow=False,
                xanchor='center',
                font=dict(color=group_colors[field], family="Arial", size=15)
            )

    fig.update_layout(
        font=dict(size=11, color='Black'),
        margin=dict(l=80, r=80, b=50, t=120, pad=4),
        height=820,
        plot_bgcolor='white',
        paper_bgcolor='white',
    )
    fig = go.FigureWidget(fig)
    fig._config = fig._config | {
        'modeBarButtonsToRemove': [
            'sendDataToCloud', 'pan', 'select', 'lasso2d', 'toImage',
            'toggleSpikelines', 'hoverClosestCartesian', 'hoverCompareCartesian'
        ],
        'displaylogo': False
    }

    return fig