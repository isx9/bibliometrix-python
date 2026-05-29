from www.services import *
import ast


def is_legible_on_white(color):
    """Returns True if the color is legible on a white background."""
    r, g, b = mcolors.to_rgb(color)
    luminance = 0.299 * r + 0.587 * g + 0.114 * b
    return 0.2 < luminance < 0.6


def get_wordcloud(df, ngram, num_of_words_wc, field_wc, file_upload_terms_wc, file_upload_synonyms_wc):
    """
    Generate a word cloud and table of the most frequent words.

    Args:
        df: A DataFrame object containing the data.
        ngram: N-gram size for text fields.
        num_of_words_wc: The number of top frequent words to display.
        field_wc: The type of words to analyze (e.g., 'TI', 'AB').
        file_upload_terms_wc: File containing terms to remove.
        file_upload_synonyms_wc: File containing synonyms.

    Returns:
        The filename of the generated HTML word cloud and a DataFrame of
        the most frequent words.
    """

    # Load stopwords and synonyms
    remove_terms = None
    if file_upload_terms_wc:
        with open(file_upload_terms_wc[0]['datapath'], 'r', encoding='utf-8') as file:
            remove_terms = [line.strip() for line in file]

    synonyms = None
    if file_upload_synonyms_wc:
        with open(file_upload_synonyms_wc[0]['datapath'], 'r', encoding='utf-8') as file:
            synonyms = {}
            for line in file:
                terms = [term.strip() for term in line.split(',')]
                key = terms[0]
                values = terms[1:]
                synonyms[key] = values

    # Set ngrams based on field_wc
    ngrams = int(ngram) if field_wc in ['TI', 'AB'] else 1

    # Get word counts
    words = table_tag(df, field_wc, ngrams, remove_terms, synonyms)

    # Create DataFrame of most frequent words
    word_counts = pd.DataFrame(words.items(), columns=['Words', 'Occurrences'])
    word_counts["Words"] = word_counts["Words"].str.capitalize()
    table = word_counts.sort_values(by='Occurrences', ascending=False)
    word_counts = word_counts.sort_values(by='Occurrences', ascending=False).head(num_of_words_wc)
    radius = 400

    word_frequencies = dict(zip(word_counts["Words"], word_counts["Occurrences"]))
    G = nx.Graph()

    # PATCH 7: if no CSS4 color passes the legibility filter, random.choice([])
    # would crash with IndexError. Added a fallback to a safe default color list.
    colors = [c for c in mcolors.CSS4_COLORS.values() if is_legible_on_white(c)]
    if not colors:
        colors = ["#1f77b4", "#ff7f0e", "#2ca02c", "#d62728", "#9467bd"]

    sorted_words = sorted(word_frequencies.items(), key=lambda x: x[1], reverse=True)

    # PATCH 6: if word_frequencies is empty (e.g. all terms filtered out),
    # sorted_words is an empty list and sorted_words[0] raises IndexError.
    # → return an empty HTML file and the empty table instead of crashing.
    if not sorted_words:
        tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".html")
        with open(tmp.name, 'w', encoding="utf-8") as f:
            f.write("<html><body><p>No words to display.</p></body></html>")
        return tmp.name.split(os.sep)[-1], table

    center_word = sorted_words[0][0]
    compact_radius = radius * 0.6

    for word, count in sorted_words:
        size = max(500, min(2000, count * 2.5))
        font_size = max(20, min(120, count * 1.5))
        color = random.choice(colors)

        theta = random.uniform(0, 2 * math.pi)
        r = compact_radius * math.sqrt(random.uniform(0, 1))
        pos_x = r * math.cos(theta)
        pos_y = r * math.sin(theta)

        G.add_node(word, label=word, title=f"{word}: {count}", color="rgba(0,0,0,0)",
                   font={"size": font_size, "color": color, "strokeWidth": 1, "face": "Arial"},
                   x=pos_x, y=pos_y)

    # Build interactive network with Pyvis
    g = Network(width="100%", height="98vh", bgcolor="white", font_color="black")
    g.from_nx(G)

    for n in g.nodes:
        n["size"] = G.nodes[n["id"]]["size"]
        n["font"] = {
            "size": G.nodes[n["id"]]["font"]["size"],
            "color": G.nodes[n["id"]]["font"]["color"],
            "strokeWidth": 1,
            "face": "Arial"
        }
        n["shape"] = "text"

    g.force_atlas_2based(gravity=-30, central_gravity=0.01, spring_length=60,
                         spring_strength=0.08, damping=0.9)

    # Save the HTML file
    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".html")
    html_path = tmp.name
    with open(html_path, 'w', encoding="utf-8") as f:
        html = g.generate_html()
        new_css = "     .card {\n                 border: none;\n             }"
        updated_html = html.replace("</style>", new_css + "\n        </style>")
        updated_html = updated_html.replace("1px solid lightgray", "none")
        f.write(updated_html)

    return html_path.split(os.sep)[-1], table


def table_tag(df, tag, ngrams=1, remove_terms=None, synonyms=None):
    """
    Extract and count words from a specified field in the DataFrame.
    """
    # PATCH 1: df.get() is not a standard pandas method — it was a custom method
    # of a wrapper object that has since been removed. Using df.copy() to work on
    # a copy and avoid mutating the original DataFrame passed by the caller.
    M = df.copy()

    # Remove duplicates
    M = M.drop_duplicates(subset='SR')

    # Get text data based on tag
    if tag in ['AB', 'TI']:
        # PATCH 2: term_extraction returns a pandas DataFrame which does not have
        # a .get() method. Removed .get() and used the result directly.
        text_data = term_extraction(df, field=tag, stemming=False, verbose=False,
                                    ngrams=ngrams, remove_terms=remove_terms, synonyms=synonyms)
        text_data = text_data[f"{tag}_TM"]
    else:
        text_data = M[tag]

    # Handle list columns (DE and ID)
    if tag in ['DE', 'ID']:
        # PATCH 3: the original code used eval(x) on strings coming from external
        # files, which is unsafe and crashes if the string is not a valid Python
        # list. Replaced with ast.literal_eval inside a try/except to handle
        # malformed strings without crashing.
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
        # PATCH 4: iterating over text_data without type checking — if an element
        # is None or a string instead of a list, it crashes with
        # TypeError: 'NoneType' object is not iterable.
        # → filter only list elements before iterating.
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

    # PATCH 5: the remove_terms filter was conditioned on tag in ['DE', 'ID'],
    # so for TI and AB the terms to remove were passed to term_extraction but
    # never filtered on the final word_counts — effectively being ignored.
    # → removed the condition: remove_terms is now applied to all tags.
    if remove_terms:
        word_counts = {
            word: count for word, count in word_counts.items()
            if word.upper() not in [term.upper() for term in remove_terms]
        }

    return word_counts
