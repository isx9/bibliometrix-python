from www.services import *


def get_trend_topics(df, ngram, field_tt, time_window, file_upload_terms_tt, file_upload_synonyms_tt, word_minimum_frequency, number_of_words_year):
    """
    Generate a plot of trend topics over time.
    """

    # Load terms to remove
    remove_terms = None
    if file_upload_terms_tt:
        with open(file_upload_terms_tt[0]['datapath'], 'r', encoding='utf-8') as file:
            remove_terms = [line.strip() for line in file]

    # Load synonyms
    synonyms = None
    if file_upload_synonyms_tt:
        with open(file_upload_synonyms_tt[0]['datapath'], 'r', encoding='utf-8') as file:
            synonyms = {}
            for line in file:
                terms = [term.strip() for term in line.split(',')]
                key = terms[0]
                values = terms[1:]
                synonyms[key] = values

    # Set ngrams based on field_tt
    ngrams = int(ngram) if field_tt in ['TI', 'AB'] else 1

    # PATCH: extract plain DataFrame before passing to term_extraction
    df_plain = df.get() if hasattr(df, 'get') and callable(df.get) and not isinstance(df, pd.DataFrame) else df

    if field_tt in ["TI", "AB"]:
        df_plain = term_extraction(df_plain, field=field_tt, stemming=False, verbose=False,
                                   ngrams=ngrams, remove_terms=remove_terms, synonyms=synonyms)
        field = f"{field_tt}_TM"
    else:
        field = field_tt

    # Get trend topics
    trend_topics = field_by_year(df_plain, field, time_window, word_minimum_frequency, number_of_words_year, remove_terms, synonyms)

    # PATCH: safety check if trend_topics is empty
    if trend_topics is None or trend_topics.empty:
        return go.FigureWidget(go.Figure()), pd.DataFrame()

    # Plot
    fig = px.scatter(trend_topics, x='year_med', y='item', size='freq',
                     hover_data=['year_q1', 'year_q3'], height=800)
    fig.update_layout(
        xaxis_title='Year',
        yaxis_title='Term',
        showlegend=False,
        plot_bgcolor='white',
        xaxis=dict(showgrid=False),
        yaxis=dict(showgrid=True, gridcolor='lightgrey'),
        hoverlabel=dict(
            bgcolor="white",
            font_size=13,
            font_family="Segoe UI, Arial",
            bordercolor="#5567BB"
        ),
    )
    fig.update_traces(
        hovertemplate=
            "<b>Term:</b> %{y}<br>" +
            "<b>Median Year:</b> %{x}<br>" +
            "<b>Frequency:</b> %{marker.size}<br>" +
            "<b>Q1 Year:</b> %{customdata[0]}<br>" +
            "<b>Q3 Year:</b> %{customdata[1]}<br>" +
            "<extra></extra>",
        customdata=trend_topics[['year_q1', 'year_q3']].values
    )

    for i in range(len(trend_topics)):
        fig.add_shape(
            type='line',
            x0=trend_topics['year_q1'].iloc[i],
            y0=trend_topics['item'].iloc[i],
            x1=trend_topics['year_q3'].iloc[i],
            y1=trend_topics['item'].iloc[i],
            line=dict(color='lightblue', width=5),
            layer='below'
        )

    fig.update_traces(marker=dict(color='dodgerblue', opacity=1), selector=dict(mode='markers'))
    fig = go.FigureWidget(fig)
    fig._config = fig._config | {'modeBarButtonsToRemove': ['pan', 'select', 'lasso2d', 'toImage'],
                                 'displaylogo': False}

    return fig, trend_topics


def field_by_year(df, field, timespan, min_freq, n_items, remove_terms=None, synonyms=None):
    """
    Compute trend topics statistics (median year, Q1, Q3, frequency) per term.
    """
    # PATCH: df may be a Shiny reactive Value or a plain DataFrame
    df = df.get() if hasattr(df, 'get') and callable(df.get) and not isinstance(df, pd.DataFrame) else df
    df = df.copy()

    # Create co-occurrence matrix
    A = cocMatrix(df, Field=field, binary=False, remove_terms=remove_terms, synonyms=synonyms)

    # PATCH: safety check if cocMatrix returns None or empty
    if A is None or A.empty:
        return pd.DataFrame()

    n = A.sum(axis=0).to_numpy()

    # PATCH: PY is stored as string in ETL output — convert to numeric
    # before passing to np.quantile to avoid TypeError on string subtraction.
    df['PY'] = pd.to_numeric(df['PY'], errors='coerce')

    # PATCH: skip columns with zero total frequency when computing quantiles
    def safe_quantile(x):
        repeated = np.repeat(df['PY'].values, x.astype(int))
        if len(repeated) == 0:
            return pd.Series([np.nan, np.nan, np.nan])
        return pd.Series(np.round(np.quantile(repeated, [0.25, 0.5, 0.75])))

    trend_med = pd.DataFrame(A.values).apply(safe_quantile, axis=0).T
    trend_med.columns = ['year_q1', 'year_med', 'year_q3']
    trend_med['freq'] = n
    trend_med['item'] = A.columns

    trend_med = trend_med.dropna(subset=['year_med'])

    if trend_med.empty:
        return trend_med

    # PATCH: timespan may be passed as an integer (time_window) rather than a
    # [start, end] list — len() on an int crashes with TypeError.
    # Treat any non-list value as missing and fall back to the data range.
    if timespan is None or not isinstance(timespan, (list, tuple)) or len(timespan) != 2:
        timespan = [trend_med['year_med'].min(), trend_med['year_med'].max()]

    trend_med = trend_med[(trend_med['year_med'] >= timespan[0]) & (trend_med['year_med'] <= timespan[1])]
    trend_med = trend_med[trend_med['freq'] >= min_freq]
    trend_med = trend_med.groupby('year_med').apply(lambda x: x.nlargest(n_items, 'freq')).reset_index(drop=True)

    return trend_med