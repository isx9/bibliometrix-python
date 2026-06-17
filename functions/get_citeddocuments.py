
from www.services import *


def get_cited_documents(df, num_of_cited_docs, cited_docs_measure):
    """
    Generate a plot and table of the most cited documents.
    """

    # SAFETY CHECK
    if df is None:
        return None, pd.DataFrame()

    # EXTRACT SR
    _df = df.get() if hasattr(df, 'get') and not isinstance(df, pd.DataFrame) else df
    if 'SR' not in _df.columns or _df['SR'].eq('').all():
        df = metaTagExtraction(df, "SR")

    # PATCH: original code called df.get() without arguments, which crashes on a
    # plain pandas DataFrame because pandas .get() requires a column name as argument.
    # Fixed by checking isinstance(df, pd.DataFrame) first.
    data = df if isinstance(df, pd.DataFrame) else df.get()

    # EMPTY CHECK
    if data is None or data.empty:
        return None, pd.DataFrame()

    # REQUIRED COLUMNS
    required_cols = ["SR", "TC", "PY"]

    for col in required_cols:

        if col not in data.columns:

            if col in ["TC", "PY"]:
                data[col] = 0
            else:
                data[col] = ""

    # OPTIONAL COLUMN
    if "DI" not in data.columns:
        data["DI"] = ""

    # SAFE NUMERIC CONVERSION
    data["TC"] = pd.to_numeric(
        data["TC"],
        errors="coerce"
    ).fillna(0)

    data["PY"] = pd.to_numeric(
        data["PY"],
        errors="coerce"
    )

    # CURRENT YEAR
    current_year = pd.to_datetime("today").year

    # PREVENT DIVISION BY ZERO
    data["TCperYear"] = data.apply(
        lambda row:
        row["TC"] / max((current_year + 1 - row["PY"]), 1)
        if pd.notna(row["PY"])
        else 0,
        axis=1
    )

    # SAFE NORMALIZATION
    data["NormalizedTC"] = data.groupby("PY")["TC"].transform(
        lambda x:
        (x / x.mean()).round(2)
        if x.mean() not in [0, np.nan]
        else 0
    )

    # CLEAN SR
    data["SR"] = (
        data["SR"]
        .fillna("")
        .astype(str)
        .str.strip()
    )

    # BUILD TABLE
    tab = (
        data.reset_index(drop=True)
        .dropna(subset=["SR"])
        .query("SR != ''")
        .groupby("SR", as_index=False)
        .agg(
            DI=("DI", "first"),
            TotalCitation=("TC", "sum"),
            TCperYear=("TCperYear", lambda x: round(x.sum(), 1)),
            NormalizedTC=("NormalizedTC", "sum")
        )
        .rename(columns={"SR": "Document"})
        .sort_values(by="TotalCitation", ascending=False)
    )

    # EMPTY CHECK
    if tab.empty:
        return None, pd.DataFrame()

    # SAFE NUMERIC CONVERSION
    for col in ["TotalCitation", "TCperYear", "NormalizedTC"]:

        tab[col] = pd.to_numeric(
            tab[col],
            errors="coerce"
        ).fillna(0)

    table = tab.copy()

    # LIMIT RESULTS
    num_of_cited_docs = min(
        int(num_of_cited_docs),
        len(tab)
    )

    tab = tab.head(num_of_cited_docs)

    # MEASURE SELECTION
    if cited_docs_measure == "total_cit":

        tab = tab[
            ["Document", "TotalCitation", "NormalizedTC"]
        ]

        laby = "Global Citations"

    else:

        tab = (
            tab.sort_values(
                by="TCperYear",
                ascending=False
            )[
                ["Document", "TCperYear", "NormalizedTC"]
            ]
        )

        laby = "Global Citations per Year"

    # EMPTY CHECK
    if tab.empty:
        return None, table

    # PLOT
    fig = go.Figure()

    y_labels = tab["Document"]
    y_vals = list(range(len(tab)))

    metric_col = tab.columns[1]

    # SAFE MAX VALUE
    max_metric = max(
        tab[metric_col].max(),
        1
    )

    # SHAPES
    for i, row in enumerate(tab.itertuples()):

        fig.add_shape(
            type="line",
            x0=0,
            x1=getattr(row, metric_col),
            y0=i,
            y1=i,
            line=dict(
                color="#e0e0e0",
                width=5
            ),
            layer="below",
        )

    # SCATTER
    fig.add_trace(

        go.Scatter(
            x=tab[metric_col],
            y=y_vals,

            mode="markers+text",

            marker=dict(
                size=18 + 6 * (
                    tab[metric_col] / max_metric
                ),

                color=tab[metric_col],

                colorscale=[
                    [0, "#B3D1F2"],
                    [1, "#5567BB"]
                ],

                line=dict(
                    width=1,
                    color="#E0E0E0"
                ),

                opacity=0.95,
                showscale=False,
            ),

            text=tab[metric_col],

            textposition="top center",

            textfont=dict(
                color="#5567BB",
                size=13
            ),

            hovertemplate=(
                "<b>Document:</b> %{customdata}<br>"
                "<b>" + laby + ":</b> %{x}<extra></extra>"
            ),

            customdata=tab["Document"],
        )
    )

    # GRID LINES
    for i in range(len(tab)):

        fig.add_shape(
            type="line",
            x0=0,
            x1=max_metric,
            y0=i,
            y1=i,
            line=dict(
                color="#E0E0E0",
                width=2
            ),
            layer="below",
        )

    # X TICKS
    tick_step = max(
        1,
        int(max_metric // 6)
    )

    x_ticks = list(
        range(
            0,
            int(max_metric) + tick_step,
            tick_step
        )
    )

    if len(x_ticks) == 0:
        x_ticks = [0]

    # AXES
    fig.update_yaxes(
        tickvals=y_vals,
        ticktext=y_labels,
        autorange="reversed",
        showgrid=False,
        title="Document",
        tickfont=dict(size=13),
    )

    fig.update_xaxes(
        showgrid=True,
        gridcolor="#F0F0F0",
        zeroline=False,
        tickvals=x_ticks,
        title=laby,
        tickfont=dict(size=13),
    )

    # LAYOUT
    fig.update_layout(
        plot_bgcolor='white',

        font=dict(
            color="#222222",
            size=14,
            family="Segoe UI, Arial"
        ),

        margin=dict(
            l=0,
            r=0,
            t=0,
            b=0
        ),

        height=max(
            400,
            50 + 90 * len(tab)
        ),

        showlegend=False,

        hoverlabel=dict(
            bgcolor="white",
            font_size=13,
            font_family="Segoe UI, Arial",
            bordercolor="#5567BB"
        ),

        coloraxis_showscale=False,
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

    return fig, table