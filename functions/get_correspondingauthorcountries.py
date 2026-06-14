from www.services import *


def get_corresponding_author_countries(df, top_k_countries):
    """
    Generate a plot and table of the most common corresponding author countries.
    
    Args:
        df: A DataFrame object containing the data.
        top_k_countries: The number of top countries to display.
    
    Returns:
        A Plotly figure object and a DataFrame of the most common corresponding author countries.
    """
    df = metaTagExtraction(df, Field="AU_CO")
    df = metaTagExtraction(df, Field="AU1_CO")

    # PATCH: metaTagExtraction may return a reactive or a plain DataFrame
    data = df.get() if hasattr(df, 'get') and callable(df.get) and not isinstance(df, pd.DataFrame) else df
    if data is None or data.empty:
        return go.FigureWidget(go.Figure()), pd.DataFrame()

    # Remove missing values and empty country strings
    data = data.dropna(subset=["AU1_CO", "AU_CO"])
    data = data[data["AU1_CO"].str.strip() != ""]  # PATCH: filter empty country strings

    # PATCH: safety check after filtering — may be empty if all countries were blank
    if data.empty:
        return go.FigureWidget(go.Figure()), pd.DataFrame()

    data["AU_CO"] = data["AU_CO"].apply(lambda x: ", ".join(x) if isinstance(x, list) else str(x))
    data["AU"] = data["AU"].apply(lambda x: ", ".join(x) if isinstance(x, list) else str(x))

    # Determine number of collaborations per row
    data["nCO"] = data["AU_CO"].apply(lambda x: 1 if len(set(x.split(", "))) > 1 else 0)

    # Count articles, SCP and MCP per country
    country_counts = data.groupby("AU1_CO").agg(
        Articles=("AU", "count"),
        SCP=("nCO", lambda x: (x == 0).sum()),
        MCP=("nCO", lambda x: (x == 1).sum())
    ).reset_index()

    country_counts = country_counts.rename(columns={"AU1_CO": "Country"})

    top_countries = country_counts.sort_values(by="Articles", ascending=False)
    top_country_names = top_countries["Country"].tolist()

    filtered_country_counts = country_counts[country_counts["Country"].isin(top_country_names)]

    filtered_country_counts["Country"] = pd.Categorical(
        filtered_country_counts["Country"], categories=top_country_names, ordered=True
    )

    filtered_country_counts = filtered_country_counts.sort_values(by="Articles", ascending=False)
    table = filtered_country_counts

    total_articles = filtered_country_counts["Articles"].sum()
    filtered_country_counts["Article_Freq"] = filtered_country_counts["Articles"] / total_articles
    filtered_country_counts["MCP_Ratio"] = filtered_country_counts["MCP"] / filtered_country_counts["Articles"]
    
    print("ROWS BEFORE FILTER:", len(filtered_country_counts))
    print(filtered_country_counts.head())
    filtered_country_counts = filtered_country_counts.dropna(subset=["Country"])
    print("ROWS AFTER FILTER:", len(filtered_country_counts))
    print(filtered_country_counts.head())
    filtered_country_counts = filtered_country_counts.head(top_k_countries)
    filtered_country_counts = filtered_country_counts.sort_values(by="Articles", ascending=True)

    fig = px.bar(
        filtered_country_counts.melt(id_vars="Country", value_vars=["SCP", "MCP"], var_name="Collaboration", value_name="Freq"),
        x="Freq",
        y="Country",
        color="Collaboration",
        orientation="h",
        labels={"Country": "Countries", "Freq": "N. of Documents", "Collaboration": "Collaboration"},
        template="simple_white"
    )

    fig.update_layout(
        height=600,
        xaxis=dict(title="N. of Documents", showgrid=True, gridcolor="lightgrey"),
        yaxis=dict(title="Countries", showgrid=True, gridcolor="lightgrey"),
        margin=dict(l=0, r=0, t=0, b=0),
        legend=dict(
            title="Collaboration",
            orientation="h",
            x=0.5,
            xanchor="center",
            y=1.1
        )
    )
    fig = go.FigureWidget(fig)
    fig._config = fig._config | {'modeBarButtonsToRemove': ['pan', 'select', 'lasso2d', 'toImage'],
                                 'displaylogo': False}

    return fig, table