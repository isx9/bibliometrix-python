
from www.services import *


def get_references_spectroscopy(df, start_year, end_year=2005, field_separator_spec=';'):
    """
    Generates a Reference Publication Year Spectroscopy (RPYS) interactive plot and tables from a DataFrame of bibliographic data.

    Args:
        df (pd.DataFrame): DataFrame containing bibliographic records with a 'CR' (cited references) column.
        start_year (int): Start year for the RPYS analysis.
        end_year (int, optional): End year for the RPYS analysis (default: 2005).
        field_separator_spec (str, optional): Field separator for references (default: ';').

    Returns:
        fig: Plotly interactive figure showing RPYS results.
        rpys_table (pd.DataFrame): Table with RPYS data (years, citations, deviation from median, top references).
        cr_table (pd.DataFrame): Table of cited references with local citation counts and Google Scholar links.
    """

    df = df.get()
    # PATCH: if CR contains lists (as produced by the ETL pipeline),
    # join them into semicolon-separated strings before processing.
    df['CR'] = df['CR'].apply(
    lambda x: field_separator_spec.join(x) if isinstance(x, list) else (x or ""))

    # ---------------- SAFE CR PATCH ----------------
    c_references = df['CR'].fillna("").astype(str)

    c_references = c_references.apply(
        lambda x: [i for i in x] if len(x) > 0 else []
    ).explode()

    c_references = c_references.astype(str).str.replace(
        'DOI;',
        'DOI '
    )

    print(field_separator_spec)

    # ---------------- SAFE REFERENCES PATCH ----------------
    references = c_references.str.split(
        f"{field_separator_spec}"
    ).apply(
        lambda x: [
            ref.strip()
            for ref in x
            if isinstance(ref, str)
            and len(ref.strip()) > 10
        ]
        if isinstance(x, list)
        else []
    )

    # ---------------- SAFE YEAR EXTRACTION PATCH ----------------
    cited_years = references.apply(
        lambda refs: [
            int(re.findall(r'\b\d{4},', ref)[0][:-1])
            if re.findall(r'\b\d{4},', ref)
            else 0
            for ref in refs
        ]
        if isinstance(refs, list)
        else []
    ).explode()

    cited_years = pd.to_numeric(
        cited_years,
        errors='coerce'
    ).fillna(0).astype(int).reset_index(drop=True)

    references = references.explode().reset_index(drop=True)

    # ---------------- CREATE REFERENCE TABLE ----------------
    ref_df = pd.DataFrame({
        'Reference': references,
        'CitedYear': cited_years
    })

    # ---------------- YEAR FILTER ----------------
    current_year = pd.Timestamp.now().year

    start_year = (
        start_year
        if start_year is not None
        else 1700
    )

    end_year = (
        end_year
        if end_year is not None
        else current_year
    )

    ref_df = ref_df[
        (ref_df['CitedYear'] >= start_year)
        &
        (ref_df['CitedYear'] <= end_year)
    ]

    # ---------------- CITATION COUNTS ----------------
    cr_table = (
        ref_df
        .groupby(['CitedYear', 'Reference'])
        .size()
        .reset_index(name='Freq')
    )

    rpys_table = (
        cr_table
        .groupby('CitedYear')['Freq']
        .sum()
        .reset_index(name='Citations')
    )

    # ---------------- SAFE EMPTY TABLE PATCH ----------------
    year_seq = rpys_table['CitedYear']

    if len(year_seq) == 0:

        empty_fig = go.FigureWidget(go.Figure())

        return (
            empty_fig,
            pd.DataFrame(),
            pd.DataFrame()
        )

    # ---------------- MISSING YEARS PATCH ----------------
    missing_years = set(
        range(
            int(year_seq.min()),
            int(year_seq.max()) + 1
        )
    ) - set(year_seq)

    missing_years_df = pd.DataFrame({
        'CitedYear': list(missing_years),
        'Citations': [0] * len(missing_years)
    })

    rpys_table = pd.concat(
        [rpys_table, missing_years_df]
    ).sort_values(
        'CitedYear'
    ).reset_index(drop=True)

    # ---------------- MOVING MEDIAN ----------------
    YY = [0] * 4 + rpys_table['Citations'].tolist()

    Median = [
        np.median(YY[i - 4:i + 1])
        for i in range(4, len(YY))
    ]

    rpys_table['DiffMedian5'] = (
        rpys_table['Citations'] - Median
    )

    # ---------------- FILTER AGAIN ----------------
    rpys_table = rpys_table[
        (rpys_table['CitedYear'] >= start_year)
        &
        (rpys_table['CitedYear'] <= end_year)
    ]

    # ---------------- SAFE POSITIVE DEVIATION ----------------
    rpys_table['DiffMedian'] = rpys_table[
        'DiffMedian5'
    ].apply(
        lambda x: x if x > 0 else 0
    )

    # ---------------- TOP REFERENCES ----------------
    top_references = (
        cr_table
        .sort_values('Freq', ascending=False)
        .groupby('CitedYear')['Reference']
        .apply(lambda refs: '\n'.join(refs))
        .reset_index()
    )

    rpys_table = rpys_table.merge(
        top_references,
        left_on='CitedYear',
        right_on='CitedYear',
        how='left'
    ).rename(
        columns={'Reference': 'TopReferences'}
    )

    # ---------------- CREATE FIGURE ----------------
    fig = make_subplots(
        specs=[[{"secondary_y": True}]]
    )

    fig.add_trace(
        go.Scatter(
            x=rpys_table['CitedYear'],
            y=rpys_table['Citations'],
            mode='lines',
            name='Cited References',
            line=dict(color='#5567BB')
        ),
        secondary_y=False,
    )

    fig.add_trace(
        go.Scatter(
            x=rpys_table['CitedYear'],
            y=rpys_table['DiffMedian'],
            mode='lines',
            name='Deviation from Median',
            line=dict(color='firebrick')
        ),
        secondary_y=False,
    )

    fig.update_layout(
        xaxis_title='Year',
        yaxis_title='Cited References',
        plot_bgcolor='white',
        title_font_size=24,
        font=dict(color="#444444"),
        margin=dict(l=0, r=0, t=0, b=0),
        legend=dict(
            orientation='h',
            yanchor='bottom',
            y=1.02,
            xanchor='center',
            x=0.5
        ),
        height=600,
    )

    fig.update_xaxes(
        showgrid=True,
        gridwidth=1,
        gridcolor='#EFEFEF'
    )

    fig.update_yaxes(
        showgrid=True,
        gridwidth=1,
        gridcolor='#EFEFEF'
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

    # ---------------- GOOGLE SCHOLAR LINKS ----------------
    cr_table['GoogleLink'] = cr_table[
        'Reference'
    ].apply(
        lambda ref:
        f'<a href="https://scholar.google.it/scholar?q={ref}" target="_blank">link</a>'
    )

    cr_table = cr_table.rename(
        columns={
            'CitedYear': 'Year',
            'Freq': 'Local Citations'
        }
    )

    return fig, rpys_table, cr_table
