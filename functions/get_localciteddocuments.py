"m8v2qp"
from www.services import *


def get_local_cited_documents(df, num_of_local_cited_docs, field_separator, fast_search=False):
    """
    Generate a plot and table of the most local cited documents.
    """

    # SAFETY CHECK
    if df is None:
        return None, pd.DataFrame()

    # ENSURE SR EXISTS
    df = metaTagExtraction(df, "SR")

    M = df.get()

    # EMPTY CHECK
    if M is None or M.empty:
        return None, pd.DataFrame()

    # REQUIRED COLUMNS
    required_cols = ['SR', 'TC', 'PY']

    for col in required_cols:

        if col not in M.columns:

            if col in ['TC', 'PY']:
                M[col] = 0
            else:
                M[col] = ""

    # OPTIONAL COLUMNS
    optional_cols = ['DI', 'LCS']

    for col in optional_cols:

        if col not in M.columns:

            if col == 'LCS':
                M[col] = 0
            else:
                M[col] = ""

    # SAFE NUMERIC CONVERSION
    M['TC'] = pd.to_numeric(
        M['TC'],
        errors='coerce'
    ).fillna(0)

    M['PY'] = pd.to_numeric(
        M['PY'],
        errors='coerce'
    )

    M['LCS'] = pd.to_numeric(
        M['LCS'],
        errors='coerce'
    ).fillna(0)

    # LOCAL CITATION THRESHOLD
    if fast_search:
        loccit = M['TC'].quantile(0.75)
    else:
        loccit = 1

    # HIST NETWORK
    H = histNetwork(
        df,
        min_citations=loccit,
        sep=";",
        network=False
    )

    # SAFETY CHECK
    if H is None:
        return None, pd.DataFrame()

    M = H['M']

    # ENSURE REQUIRED OUTPUT COLUMNS
    required_output_cols = ['SR', 'DI', 'PY', 'LCS', 'TC']

    for col in required_output_cols:

        if col not in M.columns:

            if col in ['LCS', 'TC', 'PY']:
                M[col] = 0
            else:
                M[col] = ""

    # BUILD DOCUMENT TABLE
    df_documents = pd.DataFrame({
        'Document': M['SR'].astype(str),
        'DOI': M['DI'].astype(str),
        'Year': M['PY'],
        'Local Citations': M['LCS'],
        'Global Citations': M['TC']
    })

    # SAFE LC/GC RATIO
    df_documents['LC/GC Ratio'] = df_documents.apply(
        lambda row:
        round(
            (row['Local Citations'] / row['Global Citations']) * 100,
            2
        )
        if row['Global Citations'] > 0
        else 0,
        axis=1
    )

    # SAFE NORMALIZATION
    df_documents['Normalized Local Citations'] = (
        df_documents.groupby('Year')['Local Citations']
        .transform(
            lambda x:
            (x / x.mean()).round(2)
            if x.mean() not in [0, np.nan]
            else 0
        )
    )

    df_documents['Normalized Global Citations'] = (
        df_documents.groupby('Year')['Global Citations']
        .transform(
            lambda x:
            (x / x.mean()).round(2)
            if x.mean() not in [0, np.nan]
            else 0
        )
    )

    # SORT
    df_documents = df_documents.sort_values(
        by='Local Citations',
        ascending=False
    )

    # EMPTY CHECK
    if df_documents.empty:
        return None, pd.DataFrame()

    # LIMIT RESULTS
    num_of_local_cited_docs = min(
        int(num_of_local_cited_docs),
        len(df_documents)
    )

    table_located_documents = df_documents.copy()

    df_documents = df_documents.head(
        num_of_local_cited_docs
    )

    # PLOT
    fig = go.Figure()

    # SAFE MAX VALUE
    max_local = max(
        df_documents["Local Citations"].max(),
        1
    )

    # SHAPES
    for idx, (i, row) in enumerate(df_documents.iterrows()):

        fig.add_shape(
            type="line",
            x0=0,
            x1=row["Local Citations"],
            y0=idx,
            y1=idx,
            line=dict(
                color="#e0e0e0",
                width=5
            ),
            layer="below",
        )

    # SCATTER
    fig.add_trace(

        go.Scatter(
            x=df_documents["Local Citations"],

            y=list(range(len(df_documents))),

            mode="markers+text",

            marker=dict(
                size=18 + 6 * (
                    df_documents["Local Citations"] / max_local
                ),

                color=df_documents["Local Citations"],

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

            text=df_documents["Local Citations"],

            textposition="top center",

            textfont=dict(
                color="#5567BB",
                size=13
            ),

            hovertemplate=(
                "<b>Document:</b> %{customdata[0]}<br>"
                "<b>Year:</b> %{customdata[1]}<br>"
                "<b>Local Citations:</b> %{x}<br>"
                "<b>Global Citations:</b> %{customdata[2]}<extra></extra>"
            ),

            customdata=df_documents[
                ["Document", "Year", "Global Citations"]
            ].values,
        )
    )

    # GRID LINES
    for idx in range(len(df_documents)):

        fig.add_shape(
            type="line",
            x0=0,
            x1=max_local,
            y0=idx,
            y1=idx,
            line=dict(
                color="#E0E0E0",
                width=2
            ),
            layer="below",
        )

    # X TICKS
    tick_step = 5

    x_ticks = list(
        range(
            0,
            int(max_local) + tick_step,
            tick_step
        )
    )

    if len(x_ticks) == 0:
        x_ticks = [0]

    # AXES
    fig.update_yaxes(
        tickvals=list(range(len(df_documents))),
        ticktext=df_documents["Document"],
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
        title="Local Citations",
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
            l=250,
            r=40,
            t=40,
            b=40
        ),

        height=max(
            400,
            50 + 90 * len(df_documents)
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

    return fig, table_located_documents