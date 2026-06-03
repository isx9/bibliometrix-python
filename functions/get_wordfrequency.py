from www.services import *


def get_word_frequency(df, ngram, field_wf, file_upload_terms_wf, file_upload_synonyms_wf, occurrences, top_words):
    """
    Generate a plot of word frequency over time.

    Args:
        df: A DataFrame object containing the data.
        ngram: The number of n-grams to consider.
        field_wf: The field to analyze for word frequency.
        file_upload_terms_wf: File containing terms to remove.
        file_upload_synonyms_wf: File containing synonyms.
        occurrences: Type of occurrences ('cumulate' or 'per_year').
        top_words: The number of top words to display.

    Returns:
        A Plotly FigureWidget object representing the word frequency over time
        and a DataFrame of word frequencies per year.
    """
    # Load terms to remove
    remove_terms = None
    if file_upload_terms_wf:
        with open(file_upload_terms_wf[0]['datapath'], 'r', encoding='utf-8') as file:
            remove_terms = [line.strip() for line in file]

    # Load synonyms
    synonyms = None
    if file_upload_synonyms_wf:
        with open(file_upload_synonyms_wf[0]['datapath'], 'r', encoding='utf-8') as file:
            synonyms = {}
            for line in file:
                terms = [term.strip() for term in line.split(',')]
                key = terms[0]
                values = terms[1:]
                synonyms[key] = values

    # Set ngrams based on field_wf
    ngrams = int(ngram) if field_wf in ['TI', 'AB'] else 1

    
    # PATCH: extract plain DataFrame before passing to term_extraction
    df_plain = df.get() if hasattr(df, 'get') and callable(df.get) and not isinstance(df, pd.DataFrame) else df
    data = term_extraction(df_plain, field=field_wf, stemming=False, verbose=False,
                        ngrams=ngrams, remove_terms=remove_terms, synonyms=synonyms)
    if field_wf == 'TI':
        print(data[f"{field_wf}_TM"])

    # Calculate word frequency
    if field_wf in ['AB', 'TI']:
        word_freq = keyword_growth(data, tag=f"{field_wf}_TM", top=top_words[1], cdf=(occurrences == 'cumulate'),
                                   remove_terms=remove_terms, synonyms=synonyms)
    else:
        word_freq = keyword_growth(data, tag=field_wf, top=top_words[1], cdf=(occurrences == 'cumulate'),
                                   remove_terms=remove_terms, synonyms=synonyms)

    # PATCH 2: top_words[1] was used both as the max number of terms in
    # keyword_growth and as a column slice index. If top_words[0] >= number of
    # available columns, or top_words has fewer than 2 elements, this crashes
    # with IndexError. Added bounds clamping to avoid out-of-range slicing.
    available_cols = [c for c in word_freq.columns if c != 'Year']
    start = max(0, min(top_words[0], len(available_cols)))
    end = max(0, min(top_words[1] + 1, len(available_cols)))
    selected_cols = available_cols[start:end]
    word_freq = word_freq[['Year'] + selected_cols]

    # Reshape the data for plotting
    word_freq_melted = word_freq.melt(id_vars=['Year'], var_name='Term', value_name='Frequency')

    # Create the plot
    fig = px.line(
        word_freq_melted,
        x='Year',
        y='Frequency',
        color='Term',
        labels={'Year': 'Year', 'Frequency': 'Frequency', 'Term': 'Term'},
    )

    # Customize the layout
    fig.update_layout(
        xaxis=dict(
            tickmode='array',
            tickvals=word_freq['Year'].unique()[::max(1, len(word_freq['Year'].unique()) // 20)]
        ),
        yaxis_title="Frequency",
        xaxis_title="Year",
        plot_bgcolor='white',
        title_font_size=24,
        font=dict(color="#444444"),
        margin=dict(l=40, r=40, t=40, b=40),
        height=800,
        legend=dict(
            title="Term",
            orientation="h",
            yanchor="top",
            y=-0.2,
            xanchor="center",
            x=0.5,
            font=dict(size=10)
        )
    )

    # Customize the grid
    fig.update_xaxes(showgrid=True, gridwidth=1, gridcolor='#EFEFEF')
    fig.update_yaxes(showgrid=True, gridwidth=1, gridcolor='#EFEFEF')
    fig = go.FigureWidget(fig)
    fig._config = fig._config | {'modeBarButtonsToRemove': ['pan', 'select', 'lasso2d', 'toImage'],
                                 'displaylogo': False}

    return fig, word_freq


def trim_years(w, year_range, cdf=True):
    """
    Calculate cumulative or annual frequencies aligned to a year range.

    Args:
        w: A pandas Series indexed by year with frequency values.
        year_range: The range of years to align to.
        cdf: If True, compute cumulative frequencies.

    Returns:
        A pandas Series with frequencies aligned to year_range.
    """
    # PATCH 5: if year_range is empty (e.g. after filtering), return an empty
    # Series immediately instead of producing an inconsistent zero-length result.
    if len(year_range) == 0:
        return pd.Series([], dtype=float)

    W = np.zeros(len(year_range))
    Y = np.array(list(w.index))
    w_values = np.array(w)

    for i in range(len(year_range)):
        if len(Y) > 0 and Y[0] == year_range[i]:
            W[i] = w_values[0]
            Y = Y[1:]
            w_values = w_values[1:]

    if cdf:
        W = np.cumsum(W)

    W = pd.Series(W, index=year_range)

    return W


def keyword_growth(df, tag, sep=";", top=10, cdf=True, remove_terms=None, synonyms=None):
    """
    Compute keyword frequency growth over time.

    Args:
        df: DataFrame with bibliometric data.
        tag: Column to analyze.
        sep: Separator for string parsing.
        top: Maximum number of terms to consider.
        cdf: If True, compute cumulative occurrences.
        remove_terms: List of terms to remove.
        synonyms: Dict {replacement_term: [list_of_synonyms]}.

    Returns:
        A DataFrame with one column per top term and one row per year.
    """
    df = df.dropna(subset=[tag])

    # PATCH 4: iterating over elements without type checking — if an element is
    # neither a string nor a list (e.g. None or float NaN after dropna on other
    # columns), iterating over it crashes with TypeError.
    # → skip elements that are not string or list before expanding.
    def safe_split(x):
        if isinstance(x, str):
            return x.split(sep)
        if isinstance(x, list):
            return x
        return []

    expanded = [item.upper() for sublist in df[tag].apply(safe_split) for item in sublist]
    years = df.loc[
        df.index.repeat(df[tag].apply(lambda x: len(x.split(sep)) if isinstance(x, str) else len(x) if isinstance(x, list) else 0)),
        'PY'
    ].values
    data = pd.DataFrame({'Term': expanded, 'Year': years})

    # Remove terms
    if remove_terms:
        data = data[~data['Term'].str.upper().isin([term.upper() for term in remove_terms])]

    # Handle synonyms
    if synonyms:
        for main_term, syns in synonyms.items():
            data['Term'] = data['Term'].replace(syns, main_term.upper())

    # PATCH 3: if data is empty after filtering (all terms removed or no valid
    # rows), data['Year'].min() and .max() return NaN and range(NaN, NaN)
    # crashes with TypeError.
    # → return an empty DataFrame with just a Year column instead of crashing.
    if data.empty:
        return pd.DataFrame(columns=['Year'])

    # Aggregation
    freq = data.groupby(['Term', 'Year']).size().reset_index(name='Freq')
    year_range = range(int(data['Year'].min()), int(data['Year'].max()) + 1)

    # Select most frequent terms
    top_terms = freq.groupby('Term')['Freq'].sum().nlargest(top).index
    freq = freq[freq['Term'].isin(top_terms)]

    # Build final DataFrame
    results = pd.DataFrame({'Year': year_range})
    for term in top_terms:
        term_freq = freq[freq['Term'] == term].set_index('Year')['Freq']
        term_freq = term_freq.reindex(year_range, fill_value=0)
        results[term] = trim_years(term_freq, year_range, cdf=cdf).values

    return results
