from www.services import *


def get_local_cited_sources(df, num_of_cited_sources):
    """
    Generate a plot and table of the most local cited sources.
    """

    df = metaTagExtraction(df, "CR_SO")
    # PATCH: original code called df.get() without arguments, which crashes on a
    # plain pandas DataFrame because pandas .get() requires a column name as argument.
    # Fixed by checking isinstance(df, pd.DataFrame) first.
    data = df.copy() if isinstance(df, pd.DataFrame) else df.get().copy()

    # Ensure CR_SO exists
    if "CR_SO" not in data.columns:
        print("CR_SO column missing")
        return go.FigureWidget(go.Figure()), pd.DataFrame()

    # Fill missing values safely
    data["CR_SO"] = data["CR_SO"].fillna("")

    # Handle both list and string formats safely
    if len(data) == 0:
        return go.FigureWidget(go.Figure()), pd.DataFrame()

    first_valid = data["CR_SO"].dropna()

    if len(first_valid) == 0:
        return go.FigureWidget(go.Figure()), pd.DataFrame()

    first_value = first_valid.iloc[0]

    if isinstance(first_value, list):

        exploded = data["CR_SO"].explode()

        exploded = exploded.dropna()
        exploded = exploded.astype(str).str.strip()
        exploded = exploded[exploded != ""]

        source_counts = (
            exploded.value_counts()
            .reset_index()
        )

        source_counts.columns = ["Sources", "N. of Local Citations"]

    else:

        exploded = (
            data["CR_SO"]
            .astype(str)
            .str.split(";")
            .explode()
        )

        exploded = exploded.dropna()
        exploded = exploded.astype(str).str.strip()
        exploded = exploded[exploded != ""]

        source_counts = (
            exploded.value_counts()
            .reset_index()
        )

        source_counts.columns = ["Sources", "N. of Local Citations"]

    # Handle empty results
    if source_counts.empty:
        print("No cited sources found")
        return go.FigureWidget(go.Figure()), pd.DataFrame()

    # Remove invalid rows
    source_counts["Sources"] = source_counts["Sources"].astype(str).str.strip()
    source_counts = source_counts[source_counts["Sources"] != ""]

    # Numeric safety
    source_counts["N. of Local Citations"] = pd.to_numeric(
        source_counts["N. of Local Citations"],
        errors="coerce"
    ).fillna(0)

    source_counts = source_counts.sort_values(
        by="N. of Local Citations",
        ascending=False
    )

    # Limit safely
    num_of_cited_sources = min(num_of_cited_sources, len(source_counts))

    table_located_sources = source_counts.copy()

    source_counts = source_counts.head(num_of_cited_sources).reset_index(drop=True)

    # Safe wrapping
    def wrap_label(label, width=50):
        label = str(label)
        return '<br>'.join(
            [label[i:i + width] for i in range(0, len(label), width)]
        )

    source_counts["Sources_wrapped"] = source_counts["Sources"].apply(wrap_label)

    fig = go.Figure()

    max_value = max(
        source_counts["N. of Local Citations"].max(),
        1
    )

    # Scatter plot
    fig.add_trace(
        go.Scatter(
            x=source_counts["N. of Local Citations"],
            y=list(range(len(source_counts))),
            mode="markers+text",
            marker=dict(
                size=18 + 6 * (
                    source_counts["N. of Local Citations"] / max_value
                ),
                color=source_counts["N. of Local Citations"],
                colorscale=[[0, "#B3D1F2"], [1, "#5567BB"]],
                line=dict(width=1, color="#E0E0E0"),
                opacity=0.95,
                showscale=False,
            ),
            text=source_counts["N. of Local Citations"],
            textposition="top center",
            textfont=dict(color="#5567BB", size=13),
            hovertemplate=(
                "<b>Source:</b> %{customdata}<br>"
                "<b>N. of Local Citations:</b> %{x}<extra></extra>"
            ),
            customdata=source_counts["Sources_wrapped"],
        )
    )

    # Background lines
    for i, x_val in enumerate(source_counts["N. of Local Citations"]):

        fig.add_shape(
            type="line",
            x0=0,
            x1=x_val,
            y0=i,
            y1=i,
            line=dict(color="#E0E0E0", width=4),
            layer="below",
        )

        fig.add_shape(
            type="line",
            x0=0,
            x1=max_value,
            y0=i,
            y1=i,
            line=dict(color="#E0E0E0", width=2),
            layer="below",
        )

    # Tick safety
    tick_step = max(1, int(max_value // 5))

    x_ticks = list(
        range(0, int(max_value) + tick_step, tick_step)
    )

    if x_ticks[-1] < max_value:
        x_ticks.append(int(max_value))

    fig.update_yaxes(
        tickvals=list(range(len(source_counts))),
        ticktext=source_counts["Sources_wrapped"],
        autorange="reversed",
        showgrid=False,
        title="Sources",
        tickfont=dict(size=13),
    )

    fig.update_xaxes(
        showgrid=True,
        gridcolor="#F0F0F0",
        zeroline=False,
        tickvals=x_ticks,
        title="N. of Local Citations",
        tickfont=dict(size=13),
    )

    fig.update_layout(
        plot_bgcolor='white',
        font=dict(
            color="#222222",
            size=14,
            family="Segoe UI, Arial"
        ),
        margin=dict(l=220, r=40, t=60, b=40),
        height=50 + 90 * len(source_counts),
        showlegend=False,
        hoverlabel=dict(
            bgcolor="white",
            font_size=13,
            font_family="Segoe UI, Arial",
            bordercolor="#5567BB"
        ),
    )

    fig = go.FigureWidget(fig)

    fig._config = fig._config | {
        'modeBarButtonsToRemove': [
            'pan',
            'select',
            'lasso2d',
            'toImage'
        ],
        'displaylogo': False
    }

    return fig, table_located_sources