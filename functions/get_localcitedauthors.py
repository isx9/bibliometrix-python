from www.services import *


def get_local_cited_authors(df, num_of_cited_authors, fast_search=False):
    """
    Generate a plot and table of the most local cited authors.
    """

    # SAFETY CHECK
    if df is None:
        return None, pd.DataFrame()

    # ENSURE SR EXISTS
    df = metaTagExtraction(df, "SR")

    # PATCH: metaTagExtraction may return a reactive or a plain DataFrame
    M = df.get() if hasattr(df, 'get') and callable(df.get) and not isinstance(df, pd.DataFrame) else df

    # EMPTY CHECK
    if M is None or M.empty:
        return None, pd.DataFrame()

    # REQUIRED COLUMNS
    required_cols = ['AU', 'TC']

    for col in required_cols:

        if col not in M.columns:

            if col == 'AU':
                M[col] = [[] for _ in range(len(M))]
            else:
                M[col] = 0

    # OPTIONAL COLUMN
    if 'LCS' not in M.columns:
        M['LCS'] = 0

    # SAFE NUMERIC CONVERSION
    M['TC'] = pd.to_numeric(
        M['TC'],
        errors='coerce'
    ).fillna(0)

    M['LCS'] = pd.to_numeric(
        M['LCS'],
        errors='coerce'
    ).fillna(0)

    # SAFE AUTHOR FORMAT
    import ast

    M['AU'] = M['AU'].apply(
    lambda x:
    x if isinstance(x, list)
    else ast.literal_eval(x)
         if isinstance(x, str) and x.startswith("[")
         else [i.strip() for i in str(x).split(";")]
         if pd.notna(x)
         else []
)
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

    # PATCH: if all LCS are 0 (common with OpenAlex due to URL-based references),
    # return empty result immediately instead of hanging.
        M = H['M']

        # OpenAlex fallback
    if 'LCS' not in M.columns:
        M['LCS'] = M['TC']

    if M['LCS'].sum() == 0:
        M['LCS'] = M['TC']

    # ENSURE REQUIRED OUTPUT COLUMNS
    required_output_cols = ['AU', 'LCS']

    for col in required_output_cols:

        if col not in M.columns:

            if col == 'AU':
                M[col] = [[] for _ in range(len(M))]
            else:
                M[col] = 0

    # SAFE AUTHOR FORMAT AGAIN
    M['AU'] = M['AU'].apply(
        lambda x: x
        if isinstance(x, list)
        else [i.strip() for i in str(x).split(";")] if pd.notna(x)
        else []
    )

    # SPLIT AUTHORS
    AU = M['AU'].explode()

    # REMOVE EMPTY AUTHORS
    AU = AU[
        AU.astype(str).str.strip() != ""
    ]

    # EMPTY CHECK
    if len(AU) == 0:
        return None, pd.DataFrame()

    n = AU.groupby(level=0).size()

    # AUTHOR TABLE
    df_authors = pd.DataFrame({
        'AU': AU,
        'LCS': M['LCS'].repeat(n).values
    })

    author_counts = (
        df_authors.groupby('AU')['LCS']
        .sum()
        .reset_index()
    )

    author_counts.columns = [
        "Authors",
        "N. of Local Citations"
    ]

    author_counts = author_counts.sort_values(
        by="N. of Local Citations",
        ascending=False
    )

    # EMPTY CHECK
    if author_counts.empty:
        return None, pd.DataFrame()

    # LIMIT AUTHORS
    num_of_cited_authors = min(
        int(num_of_cited_authors),
        len(author_counts)
    )

    # SAFE STRING HANDLING
    author_counts["Authors"] = (
        author_counts["Authors"]
        .astype(str)
        .str[:50]
    )

    table_located_authors = author_counts.copy()

    author_counts = (
        author_counts.head(num_of_cited_authors)
        .reset_index(drop=True)
    )

    frequency = "N. of Local Citations"

    # PLOT
    fig = go.Figure()

    # SAFE MAX VALUE
    max_freq = max(
        author_counts[frequency].max(),
        1
    )

    # SHAPES
    for i, row in author_counts.iterrows():

        fig.add_shape(
            type="line",
            x0=0,
            x1=row[frequency],
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
            x=author_counts[frequency],

            y=list(range(len(author_counts))),

            mode="markers+text",

            marker=dict(
                size=18 + 6 * (
                    author_counts[frequency] / max_freq
                ),

                color=author_counts[frequency],

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

            text=author_counts[frequency],

            textposition="top center",

            textfont=dict(
                color="#5567BB",
                size=13
            ),

            hovertemplate=(
                "<b>Author:</b> %{customdata}<br>"
                "<b>" + frequency + ":</b> %{x}<extra></extra>"
            ),

            customdata=author_counts["Authors"],
        )
    )

    # GRID LINES
    for i in range(len(author_counts)):

        fig.add_shape(
            type="line",
            x0=0,
            x1=max_freq,
            y0=i,
            y1=i,
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
            int(max_freq) + tick_step,
            tick_step
        )
    )

    if len(x_ticks) == 0:
        x_ticks = [0]

    # AXES
    fig.update_yaxes(
        tickvals=list(range(len(author_counts))),
        ticktext=author_counts["Authors"],
        autorange="reversed",
        showgrid=False,
        title="Authors",
        tickfont=dict(size=13),
    )

    fig.update_xaxes(
        showgrid=True,
        gridcolor="#F0F0F0",
        zeroline=False,
        tickvals=x_ticks,
        title=frequency,
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
            50 + 90 * len(author_counts)
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

    return fig, table_located_authors