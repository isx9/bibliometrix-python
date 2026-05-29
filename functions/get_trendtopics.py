from www.services import *


def get_trend_topics(df, ngram, field_tt, time_window, file_upload_terms_tt, file_upload_synonyms_tt, word_minimum_frequency, number_of_words_year):
    """
    Generate a plot of trend topics over time.

    Args:
        df: A DataFrame object containing the data.
        ngram: The number of n-grams to consider.
        field_tt: The field to analyze for trend topics.
        time_window: The time window to consider.
        file_upload_terms_tt: File containing terms to remove.
        file_upload_synonyms_tt: File containing synonyms.
        word_minimum_frequency: The minimum frequency of words to consider.
        number_of_words_year: The number of words to display per year.

    Returns:
        A Plotly FigureWidget object representing the trend topics over time
        and a DataFrame of trend topics.
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

    # Extract terms
    # PATCH 4: term_extraction returns a pandas DataFrame directly — the result
    # is assigned to df and then passed to field_by_year, where df.get() was
    # called. The root crash is fixed in field_by_year (PATCH 1), but noted here
    # as the origin of the df.get() call chain.
    if field_tt in ["TI", "AB"]:
        df = term_extraction(df, field=field_tt, stemming=False, verbose=False,
                             ngrams=ngrams, remove_terms=remove_terms, synonyms=synonyms)
        field = f"{field_tt}_TM"
    else:
        field = field_tt

    # Get trend topics
    trend_topics = field_by_year(df, field, time_window, word_minimum_frequency, number_of_words_year, remove_terms, synonyms)

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

    Args:
        df: A DataFrame with bibliometric data.
        field: The column to analyze.
        timespan: A list [start_year, end_year] to filter results.
        min_freq: Minimum frequency threshold for terms.
        n_items: Maximum number of terms to display per year.
        remove_terms: List of terms to remove.
        synonyms: Dict {replacement_term: [list_of_synonyms]}.

    Returns:
        A DataFrame with columns: year_q1, year_med, year_q3, freq, item.
    """
    # Create co-occurrence matrix
    A = cocMatrix(df, Field=field, binary=False, remove_terms=remove_terms, synonyms=synonyms)
    n = A.sum(axis=0).to_numpy()

    # PATCH 1: df.get() is not a standard pandas method — it was a custom method
    # of a wrapper object that has since been removed. Using df.copy() to work on
    # a copy and avoid mutating the original DataFrame passed by the caller.
    df = df.copy()

    # PATCH 2: if a column in A has all-zero frequencies, np.repeat(df['PY'], x)
    # produces an empty array and np.quantile([]) crashes with ValueError.
    # → skip columns with zero total frequency when computing quantiles.
    def safe_quantile(x):
        repeated = np.repeat(df['PY'].values, x.astype(int))
        if len(repeated) == 0:
            return pd.Series([np.nan, np.nan, np.nan])
        return pd.Series(np.round(np.quantile(repeated, [0.25, 0.5, 0.75])))

    trend_med = pd.DataFrame(A.values).apply(safe_quantile, axis=0).T
    trend_med.columns = ['year_q1', 'year_med', 'year_q3']
    trend_med['freq'] = n
    trend_med['item'] = A.columns

    # Drop rows where quantiles could not be computed (zero-frequency terms)
    trend_med = trend_med.dropna(subset=['year_med'])

    # PATCH 3: if trend_med is empty after quantile computation, .min() and
    # .max() return NaN and the subsequent filter silently drops all rows.
    # → return an empty DataFrame early instead of producing a silent no-op.
    if trend_med.empty:
        return trend_med

    # Filter by timespan and frequency
    if timespan is None or len(timespan) != 2:
        timespan = [trend_med['year_med'].min(), trend_med['year_med'].max()]

    trend_med = trend_med[(trend_med['year_med'] >= timespan[0]) & (trend_med['year_med'] <= timespan[1])]
    trend_med = trend_med[trend_med['freq'] >= min_freq]
    trend_med = trend_med.groupby('year_med').apply(lambda x: x.nlargest(n_items, 'freq')).reset_index(drop=True)

    return trend_med