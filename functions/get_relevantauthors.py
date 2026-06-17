"k7d2pw"
from www.services import *


def get_relevant_authors(df, num_of_authors, frequency="N. of Documents"):
    """
    Generate a plot and table of the most relevant authors with frequency options.
    """

    # SAFETY CHECK
    if df is None:
        return None, pd.DataFrame()

    # PATCH: original code called df.get() without arguments, which crashes on a
    # plain pandas DataFrame because pandas .get() requires a column name as argument.
    # Fixed by checking isinstance(df, pd.DataFrame) first.
    data = df if isinstance(df, pd.DataFrame) else df.get()

    if data is None or data.empty:
        return None, pd.DataFrame()

    # ENSURE AU COLUMN EXISTS
    if "AU" not in data.columns:
        data["AU"] = [[] for _ in range(len(data))]

    # REMOVE NULLS
    data = data.copy()

    # ENSURE LIST FORMAT
    data["AU"] = data["AU"].apply(
        lambda x: x
        if isinstance(x, list)
        else [i.strip() for i in str(x).split(";")] if pd.notna(x)
        else []
    )

    # FLATTEN AUTHORS
    all_authors = [
        author
        for sublist in data["AU"]
        for author in sublist
        if str(author).strip()
    ]

    # EMPTY CHECK
    if len(all_authors) == 0:
        return None, pd.DataFrame()

    author_counts = pd.Series(all_authors).value_counts()

    # FREQUENCY MODES
    if frequency.lower() == "percentage":

        author_counts = (
            author_counts / max(len(data), 1) * 100
        ).round(1)

    elif frequency.lower() in ["fractionalized", "freq_measure"]:

        fractional_counts = data["AU"].apply(
            lambda authors: 1 / len(authors)
            if len(authors) > 0
            else 0
        )

        fractional_authors = [
            (author, fractional_counts.iloc[i])
            for i, authors in enumerate(data["AU"])
            for author in authors
        ]

        fractional_df = pd.DataFrame(
            fractional_authors,
            columns=["Author", "Weight"]
        )

        if not fractional_df.empty:

            author_counts = (
                fractional_df.groupby("Author")["Weight"]
                .sum()
                .sort_values(ascending=False)
                .round(1)
            )

    # CONVERT TO DATAFRAME
    author_counts = author_counts.reset_index()

    author_counts.columns = ["Authors", frequency]

    # SAFE STRING HANDLING
    author_counts["Authors"] = (
        author_counts["Authors"]
        .astype(str)
        .str[:50]
    )

    table_relevant_authors = author_counts.copy()

    # LIMIT AUTHORS
    num_of_authors = min(
        int(num_of_authors),
        len(author_counts)
    )

    author_counts = author_counts.head(num_of_authors)

    # EMPTY CHECK
    if author_counts.empty:
        return None, table_relevant_authors

    # PLOT
    fig = go.Figure()

    # SAFE MAX VALUE
    max_freq = max(author_counts[frequency].max(), 1)

    # LINES
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

        height=max(400, 50 + 90 * len(author_counts)),

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

    return fig, table_relevant_authors