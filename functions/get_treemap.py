from www.services import *
import ast


def get_treemap(df, ngram, num_of_words, word_type, file_upload_terms, file_upload_synonyms, field_separator_frequent=';'):
    """
    Generate a treemap plot and table of the most frequent words.
    
    Args:
        df: A DataFrame object containing the data.
        num_of_words: The number of top frequent words to display.
        word_type: The type of words to analyze (e.g., 'TI', 'AB').
        field_separator_frequent: The separator used in the field.
        file_upload_terms: File containing terms to remove.
        file_upload_synonyms: File containing synonyms.
        
    Returns:
        A Plotly FigureWidget object and a DataFrame of the most frequent words.
    """

    # Load stopwords and synonyms
    remove_terms = None
    if file_upload_terms:
        with open(file_upload_terms[0]['datapath'], 'r', encoding='utf-8') as file:
            remove_terms = [line.strip() for line in file]

    synonyms = None
    if file_upload_synonyms:
        with open(file_upload_synonyms[0]['datapath'], 'r', encoding='utf-8') as file:
            synonyms = {}
            for line in file:
                terms = [term.strip() for term in line.split(',')]
                key = terms[0]
                values = terms[1:]
                synonyms[key] = values

    # Set ngrams based on word_type
    ngrams = int(ngram) if word_type in ['TI', 'AB'] else 1
    print(ngrams)

    # Get word counts
    words = table_tag(df, word_type, ngrams, remove_terms, synonyms)

    # Create DataFrame of most frequent words
    word_counts = pd.DataFrame(words.items(), columns=['Words', 'Occurrences'])
    table = word_counts.sort_values(by='Occurrences', ascending=False)
    word_counts = word_counts.sort_values(by='Occurrences', ascending=False).head(num_of_words)

    # PATCH: safety check if word_counts is empty
    if word_counts.empty:
        return go.FigureWidget(go.Figure()), table

    # Create TreeMap plot
    fig = px.treemap(
        word_counts,
        path=[px.Constant("Tree"), 'Words'],
        values='Occurrences',
        color='Occurrences',
        color_continuous_scale=[(0, "lightblue"), (1, "darkblue")],
    )

    fig.update_layout(
        margin=dict(l=10, r=10, t=40, b=10),
        height=800,
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
        showlegend=False
    )

    fig.data[0].texttemplate = "%{label}<br>%{value} Occurrences<br>%{percentParent:.2%}"
    fig = go.FigureWidget(fig)
    fig._config = fig._config | {'modeBarButtonsToRemove': ['pan', 'select', 'lasso2d', 'toImage'],
                                 'displaylogo': False}

    return fig, table


def table_tag(df, tag, ngrams=1, remove_terms=None, synonyms=None):
    """
    Extract and count words from a specified field in the DataFrame.
    """
    # PATCH: df may be a Shiny reactive Value or a plain DataFrame
    M = df.get() if hasattr(df, 'get') and callable(df.get) and not isinstance(df, pd.DataFrame) else df
    M = M.copy()

    # Remove duplicates
    M = M.drop_duplicates(subset='SR')

    # Get text data based on tag
    if tag in ['AB', 'TI']:
        # PATCH: pass plain DataFrame to term_extraction — it does not accept reactives
        df_plain = df.get() if hasattr(df, 'get') and callable(df.get) and not isinstance(df, pd.DataFrame) else df
        text_data = term_extraction(df_plain, field=tag, stemming=False, verbose=False,
                                    ngrams=ngrams, remove_terms=remove_terms, synonyms=synonyms)
        text_data = text_data[f"{tag}_TM"]
    else:
        text_data = M[tag]

    # Handle list columns (DE and ID)
    if tag in ['DE', 'ID']:
        def safe_parse(x):
            if isinstance(x, list):
                return x
            try:
                return ast.literal_eval(x)
            except (ValueError, SyntaxError):
                return []

        text_data = text_data.dropna().apply(lambda x: ', '.join(safe_parse(x)))

    # Process words
    if tag in ['DE', 'ID']:
        words = text_data.dropna().astype(str).str.cat(sep=', ').upper()
        words = [word.strip() for word in words.split(',') if word and word.strip()]
    else:
        # PATCH: filter only list elements before iterating to avoid TypeError
        words = [
            item
            for sublist in text_data
            if isinstance(sublist, list)
            for item in sublist
        ]

    # Replace synonyms
    if synonyms:
        for key, syn_list in synonyms.items():
            words = [key if word in syn_list else word for word in words]

    # Count words
    word_counts = Counter(words)

    # PATCH: apply remove_terms to all tags
    if remove_terms:
        word_counts = {
            word: count for word, count in word_counts.items()
            if word.upper() not in [term.upper() for term in remove_terms]
        }

    return word_counts