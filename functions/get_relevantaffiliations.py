from www.services import *


def get_relevant_affiliations(df, num_of_affiliations, disambiguation):
    """
    Generate a plot and table of the most relevant authors with frequency options.
    
    Args:
        df: A DataFrame object containing the data.
        num_of_affiliations: The number of top affiliations to display.
        disambiguation: "yes" to use AU_UN field, anything else to use C1 field.
        
    Returns:
        A Plotly figure object and a DataFrame of the most relevant affiliations.
    """
    # PATCH: metaTagExtraction may return a reactive or a plain DataFrame
    if disambiguation == "yes":
        # AU_UN is a derived field — must be extracted before use
        df = metaTagExtraction(df, Field="AU_UN")

    data = df.get() if hasattr(df, 'get') and callable(df.get) and not isinstance(df, pd.DataFrame) else df

    # PATCH: safety check
    if data is None or data.empty:
        return go.FigureWidget(go.Figure()), pd.DataFrame()

    if disambiguation == "yes":
        # PATCH: AU_UN may be missing even after extraction
        if "AU_UN" not in data.columns:
            return go.FigureWidget(go.Figure()), pd.DataFrame()
        affiliations = data["AU_UN"].explode().dropna().replace('', None).dropna()
    else:
        # PATCH: C1 may be missing
        if "C1" not in data.columns:
            return go.FigureWidget(go.Figure()), pd.DataFrame()
        affiliations = data["C1"].explode().dropna()

    # PATCH: safety check if affiliations is empty after explode
    if affiliations.empty:
        return go.FigureWidget(go.Figure()), pd.DataFrame()

    # Count occurrences of each affiliation
    affiliation_counts = affiliations.value_counts().reset_index()
    affiliation_counts.columns = ["Affiliation", "Articles"]

    # Limit the number of affiliations to display
    if num_of_affiliations > len(affiliation_counts):
        num_of_affiliations = len(affiliation_counts)
    affiliation_counts = affiliation_counts.head(num_of_affiliations)

    # PATCH: safety check if affiliation_counts is empty
    if affiliation_counts.empty:
        return go.FigureWidget(go.Figure()), pd.DataFrame()

    fig = go.Figure()

    fig.add_trace(
        go.Scatter(
            x=affiliation_counts["Articles"],
            y=list(range(len(affiliation_counts))),
            mode="markers+text",
            marker=dict(
                size=18 + 6 * (affiliation_counts["Articles"] / affiliation_counts["Articles"].max()),
                color=affiliation_counts["Articles"],
                colorscale=[[0, "#B3D1F2"], [1, "#5567BB"]],
                line=dict(width=1, color="#E0E0E0"),
                opacity=0.95,
                showscale=False,
            ),
            text=affiliation_counts["Articles"],
            textposition="top center",
            textfont=dict(color="#5567BB", size=13),
            hovertemplate=(
                "<b>Affiliation:</b> %{customdata}<br>"
                "<b>Articles:</b> %{x}<extra></extra>"
            ),
            customdata=affiliation_counts["Affiliation"],
        )
    )

    fig.update_layout(
        yaxis=dict(
            autorange="reversed",
            showgrid=True,
            gridcolor="lightgrey",
            zeroline=False,
            tickmode='array',
            tickvals=list(range(len(affiliation_counts))),
            ticktext=affiliation_counts["Affiliation"]
        ),
        xaxis=dict(
            showgrid=True,
            gridcolor="lightgrey",
            zeroline=False,
            tick0=5,
            dtick=5,
            title="Articles"
        ),
        plot_bgcolor='white',
        title_font_size=24,
        font=dict(color="#444444"),
        margin=dict(l=200, r=40, t=40, b=40),
        height=800,
        showlegend=False
    )
    fig = go.FigureWidget(fig)
    fig._config = fig._config | {'modeBarButtonsToRemove': ['pan', 'select', 'lasso2d', 'toImage'],
                                 'displaylogo': False}

    return fig, affiliation_counts