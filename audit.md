# Bibliometrix-Python Codebase Audit

## Purpose
This document maps every file in services/ and functions/ to the columns it depends on and any hardcoded WoS logic it contains.
It is used to verify that our ETL pipeline produces all required columns and to track which files need patching.

---

## www/services/
1) what it does
2) dependencies
3) columns used
4) WoS-specific logic
5) issues found 
6) relevant for ETL: yes/no

### biblionetwork.py
1) Takes the bibliographic DataFrame and builds a matrix showing how items (authors,   sources, references, countries) are connected to each other. For example, two authors are "connected" if they cite the same references. It's the core function for generating all network analyses in the dashboard.
2) **utils.py, cocmatrix.py**.
3) **AU, CR, SO, ID, DE, DB** and derived ones.
4) It has **db_name == "SCOPUS"**.
5) If any of the above columns are absent (AU, CR, etc.), cocMatrix() will fail because it will try to read that column from the DataFrame without finding it. Python will throw a KeyError and the whole things crashes.
6) **Yes**. Our ETL is responsible for producing the DataFrame that gets fed into functions like this one, if it fails to include AU, CR or whatever other column in the output (even as an empty list []) this function crashes immediatly.

### cocmatrix.py
1) Takes the bibliographic DataFrame and a column name (like AU or CR), and builds a matrix where rows are articles and columns are unique items (authors, keywords, references etc.). Each cell is 1 if that article contains that item, 0 otherwise. It's the building block that biblionetwork.py calls to create all its networks.
2) **utils.py**.
3) **SR, CR, AU, ID, DE, TI, AB** and derived ones.
4) No explicit DB checks.
5) It will crash if SR is missing (M.index = M["SR"] throws a KeyError immediately) and if the requested Field column is missing, it just prints a message and returns None (which then causes biblionetwork.py to crash when it tries to use that None because there is no error handling between the two functions: biblionetwork.py calls cocMatrix() and stores the result in WA; if the column is missing, cocMatrix() prints a message and returns None; biblionetwork.py doesn't check if WA is None — it immediately uses it in crossprod(WA, WA); crossprod tries to do matrix multiplication on None, which crashes with a TypeError).
6) **Yes**, SR must be present and correctly computed.

### couplingmap.py
1)  Builds and visualizes a "coupling map" — a bubble chart where clusters of related documents, authors, or sources are plotted by centrality vs impact. It combines network analysis, citation scoring, and cluster labeling into one visualization. It's one of the more complex files — it orchestrates many other services together.
2) **utils.py, cocmatrix.py, biblionetwork.py, termextraction.py, networkplot.py, histnetwork.py, metatagextraction.py, tabletag.py**.
3) **SR, AU, TC, DI, PY, DE, ID, TI, AB, SO**.
4) No explicit DB checks.
5) It will crash if SR (crashes immediately at metaTagExtraction(df, "SR")), TC (crashes in localCitations() at M['TC'].fillna(0)), AU (crashes in localCitations() at M['AU'].explode()), DI and PY (crashes when building the LCS output DataFrame) are missing.
6) **Yes**. SR, TC, AU, DI, PY, SO must all be present and correctly typed.

### format_functions.py
1) It takes raw bibliographic data from any supported source (WoS, Scopus, PubMed, Dimensions, Lens, Cochrane) and converts it into a standardized dictionary with WoS-style column names. It has one formatting function per column (format_au_column, format_cr_column etc.) and a main entry point process_single_file() that calls all of them and assembles the final output. **This is the most important file for our ETL, it's basically a rough draft of what the ETL needs to be.** The project specs asks us to build a clean, robust version of what this file is already attempting. So rather than starting from scratch, for our ETL we should: study this file carefully to understand the existing column mappings; replace the fragile direct access (entry['Abstract']) with safe .get() calls; ensure null handling throughout (empty string "" or [] instead of None); make sure SR is always correctly computed.
2) **utils.py, parsers.py**.
3) **AB, AF, AU, AU_UN, AU1_UN, BP, EP, CR, C1, DB, DE, DI, DT, EM, FU, FX, IS, JI, ID, LA, OA, OI, PMID, PU, PY, RP, SC, SN, SO, SR, TC, TI, UT, VL**
4) **Yes**, every single formatting function branches on source (Web_of_Science, Scopus, PubMed, Dimensions, The_Lens, Cochrane) and file_type. This is basically the dispatcher that the specs asks us to build.
5) Yes, several functions access raw source columns directly without safety checks (e.g. entry['Abstract'], entry['Author full names']) which will crash with a KeyError if the raw file has different column names than expected.
6) **Yes**.

### histnetwork.py
1) Builds a historical citation network. It figures out which papers in the dataset cite other papers in the same dataset (called "Local Citation Score" or LCS). It has two separate implementations: one for WoS and one for Scopus, and returns a network matrix plus citation statistics.
2) **utils.py, cocmatrix.py**.
3) **DB, DI, CR, TC, PY, SR, SR_FULL, TI, DE, ID, AU, BP, EP, LCS**
4) **Yes**. It explicitly checks **db == "Web_of_Science"** or **db == "Scopus"** and calls completely different functions for each. If DB contains anything else (e.g. "PUBMED", "DIMENSIONS"), it prints "Database not compatible" and returns None, meaning it silently fails for any source other than WoS and Scopus.
5) It will crash if: CR is missing (returns None immediately); SR_FULL is missing (crashes in the WoS branch when building LABEL); PY, AU, BP, EP are missing (crashes in the Scopus branch during merges).
6) **Yes**. DB values must exactly match "Web_of_Science" or "Scopus" for this function to work at all, and CR, PY, SR, TC must all be correctly populated.

### histplot.py
1) Takes the output of histNetwork() and draws a historical citation network chart: papers are plotted as bubbles positioned by publication year on the x-axis, with edges showing which papers cite which. It's purely a visualization function, it doesn't touch the raw DataFrame directly.
2) **utils.py, networkplot.py**
3) **None directly** from the bibliographic DataFrame, it only reads from histResults which is the output of histNetwork(). Internally it uses histResults['NetMatrix'] and histResults['histData'] which contain Paper, Title, Author_Keywords, KeywordsPlus.
4) **No**.
5) **Only indirectly**, if histNetwork() failed to produce a proper NetMatrix or histData, this function will crash. But that's histNetwork()'s problem, not yours.
6) **No**. This is a pure visualization layer, it never reads our standardized DataFrame directly.

### htmldownload.py
1) Takes an HTML file, renders it to a PNG screenshot using a headless Chrome browser, then overlays the bibliometrix logo on the bottom right. It's a utility for exporting visualizations as images.
2) **utils.py**.
3) **None**.
4) **No**.
5) **No**.
6) **No**.

### igraph2vis.py
1) Converts an igraph graph object into an interactive vis.js network visualization, saves it as an HTML file, and returns the path. It handles node sizing, coloring by cluster, edge styling, and label overlap removal. Pure visualization utility.
2) **utils.py**.
3) **None**.
4) **No**.
5) **No**.
6) **No**.

### metatagextraction.py
1) Computes derived columns that other functions need but that aren't in the raw data. Given a Field parameter, it generates one of: SR (short reference key), CR_AU (authors from cited references), CR_SO (sources from cited references), AU_CO (countries from affiliations), AU1_CO (first author's country), AU_UN (universities from affiliations). This is the file that generates most of the derived columns we shouldn't be our responsability based on the project specs (**must ask**).
2) **utils.py**.
3) **AU, JI, SO, PY, DB, CR, C1, RP**.
4) **Yes**, in multiple places: SR() checks db == "scopus" to format author names differently; CR_SO() checks db != "SCOPUS" to parse references differently; AU_UN() checks db in ["ISI", "OPENALEX"] for university extraction.
5) SR() crashes if AU, JI, SO, or PY are missing. AU_CO() and AU1_CO() crash if C1 and RP are both missing. CR_AU() and CR_SO() crash if CR is missing or not a list.
6) **Yes**. AU, JI, SO, PY, C1, RP must all be present and correctly typed for SR generation to work
**N.B.** This file is what *generates SR*, which is in our target schema and is required by almost every other function. So while we don't need to generate AU_CO, CR_AU etc., we do need to ensure AU, JI, SO, PY, C1, RP are correctly populated so that SR() inside this file can run without crashing. Our ETL feeds this function indirectly.

### networkplot.py
1) Takes a co-occurrence/coupling matrix (the output of biblionetwork.py) and builds an interactive network graph from it — handling clustering, layout, node sizing, edge weights, and color assignment. It's the core visualization engine for all network analyses in the dashboard.
2) **utils.py, cocmatrix.py**.
3) None directly from the bibliographic DataFrame, it only receives a pre-built NetMatrix as input.
4) **No**.
5) **No**.
6) **No**. If our ETL produces correct columns so that biblionetwork.py and cocmatrix.py can build the matrix successfully, this function will work automatically.

### parsers.py
1) Contains three raw file parsers, one each for Web of Science (parse_wos_data), PubMed (parse_pubmed_data), and Cochrane (parse_cochrane_data). Each parser reads a raw text file line by line and returns a list of dictionaries, one per article, with raw field tags as keys. This is the **Extract phase of the ETL**, it turns raw files into Python data structures before any column renaming or type enforcement happens.
2) **utils.py**.
3) **None**, these functions produce raw dictionaries from files, they don't read a DataFrame.
4) **Yes**, parse_wos_data is specifically built around the WoS plaintext format (two-letter tags, ER record separators, continuation lines starting with two spaces). The other parsers handle their own formats independently.
5) **No**. Even though parse_pubmed_data has a minor bug, if a continuation line appears before any key is set, key will be undefined and it will crash with a NameError.
6) **Yes**,  these are our Extract phase building blocks, especially parse_wos_data and parse_pubmed_data.

### plotlydownload.py
1) Takes an existing Plotly figure, adds the bibliometrix logo and a title, scales it up to high resolution, and exports it as a PNG image. Pure export utility.
2) **utils.py**.
3) **None**.
4) **No**.
5) **No**.
6) **No**.

### savereport.py
1) Saves analysis results (tables and plots) into a formatted Excel file with multiple sheets. Each sheet contains a styled table and the corresponding visualization. It's the reporting/export layer of the dashboard.
2) **utils.py, plotlydownload.py, htmldownload.py**.
3) **None**.
4) **No**.
5) **No**.
6) **No**.

### tabletag.py
1) Takes a specified column from the DataFrame, extracts all individual terms from it, counts their frequency, and returns a sorted dictionary of term → count. Used for word frequency analysis, keyword counts, citation counts etc. For AB and TI fields it first runs text mining to extract meaningful terms before counting.
2) **utils.py, termextraction.py**.
3) **SR, CR, DE, ID, C1, AB, TI (whichever is passed as tag parameter)**
4) **No** explicit DB checks.
5) If SR is missing it crashes immediately on drop_duplicates(subset=["SR"]); if whatever column is passes as tag is missing it crashes when trying to process it.
6) **Yes**, SR must always be present and all the tag columns (CR, DE, ID, AB, TI, C1) must exist and contain properly formatted lists for this function to work correctly.
   
### termextraction.py
1) Takes a text column (TI or AB), cleans it, removes stopwords, optionally applies stemming, and extracts n-grams using scikit-learn's CountVectorizer. Stores the result as a new column TI_TM or AB_TM. Called by tabletag.py before word frequency counting.
2) **utils.py**.
3) **TI** (default), **AB** (passed in by tabletag.py).
4) **No**
5) It crashes at M[field].astype(str) if whichever column is passed as field is absent.
6) **Yes**, both TI and AB must be present and populated as strings.

### thematicmap.py
1) Builds a thematic map, a bubble chart plotting research clusters by their "centrality" vs "density". It combines keyword co-occurrence network analysis, community detection, and cluster characterization into one visualization. One of the most complex files in the codebase, it orchestrates biblionetwork, termextraction, and networkplot together.
2) **utils.py, igraph2vis.py, termextraction.py, biblionetwork.py**.
3) **ID, DE, TI, AB, SR, TC, PY, DI, AU, SO**.
4) **No** explicit DB check, but heavily assumes WoS-style keyword fields (ID, DE) are properly populated.
5) If SR is missing, it crashes in cluster_assignment() immediately. If TC or PY missing, it crashes in cluster_assignment() when computing TCpY. If ID or DE missing, it crashes when building the network matrix via biblionetwork().
6) **Yes**. ID, DE, TC, PY, DI, AU, SO, SR must all be present and correctly populated

### utils.py
1) Central imports file for the entire services layer — every other service file starts with from .utils import *. It also defines two important shared things: the columns list (the master list of all expected DataFrame columns) and the ICONS dictionary for the UI. Think of it as the shared foundation the whole codebase builds on.
2) //
3) Defines the master columns list: AB, AF, AU, AU1_UN, AU_UN, BP, C1, CR, DB, DE, DI, DT, EM, EP, FU, FX, ID, IS, JI, LA, OA, OI, PMID, PU, PY, RP, SC, SN, SO, SR, TC, TI, UT, VL.
4) **No**.
5) **No**, it's an imports file.
6) **Yes**. This columns list is used in format_functions.py to add extra columns to each entry, so our ETL output must at minimum cover what's in the target schema.
**N.B.** The columns list defined here is our ground truth for what columns the codebase expects. Cross-referencing it with the target schema from the exam spec:
- Columns in utils.py but not in the target schema are AU1_UN, AU_UN, EM, FU, FX, OA, OI, PU, SC, SN. These are extra columns the codebase uses but our ETL doesn't need to guarantee;
- Column in the target schema but not in utils.py is SR_FULL, generated by metatagextraction.py as a derived column.

## Master Column Dependency Table — services/

### Columns from target schema

| Column | Used by |
|--------|---------|
| `DB` | biblionetwork, histnetwork, metatagextraction, cocmatrix |
| `SR` | cocmatrix, histnetwork, tabletag, thematicmap, metatagextraction |
| `AU` | biblionetwork, histnetwork, metatagextraction, thematicmap |
| `CR` | biblionetwork, cocmatrix, histnetwork, metatagextraction |
| `TI` | histnetwork, termextraction, thematicmap |
| `AB` | termextraction, thematicmap |
| `DE` | biblionetwork, thematicmap |
| `ID` | biblionetwork, thematicmap |
| `SO` | biblionetwork, histnetwork, metatagextraction |
| `JI` | metatagextraction |
| `PY` | histnetwork, thematicmap, metatagextraction |
| `TC` | histnetwork, thematicmap |
| `DI` | histnetwork, thematicmap |
| `C1` | metatagextraction |
| `RP` | metatagextraction |
| `AF` | format_functions |
| `BP` | histnetwork |
| `EP` | histnetwork |
| `VL` | format_functions |
| `IS` | format_functions |
| `LA` | format_functions |
| `DT` | format_functions |
| `PMID` | format_functions |
| `UT` | format_functions |


### Key takeaways

- `SR` is the most critical column — used by almost everything, computed from `AU`, `JI`, `PY`, `SO`
- `DB` must exactly match `"Web_of_Science"` or `"Scopus"` where branch logic exists
- `CR` must be a parsed Python list, not a raw semicolon-separated string
- `AU` must also be a parsed Python list
- `SR`, `TC`, `PY` have no crash protection — must always be present and correctly typed


---

## functions/
1) what it does
2) dependencies
3) columns used
4) WoS-specific logic
5) issues found 
6) relevant for ETL: yes/no



### get_affiliationproductionovertime.py
1) Counts cumulative publications per institution over time and draws a line chart for the top-k institutions.
2) **www.services**.
3) **AU_UN**, **PY**.
4) **No**, but `AU_UN` is only produced by WoS natively.
5) Crashes if `AU_UN` is a plain string instead of a list, or if `PY` contains nulls.
6) **Yes**. `AU_UN` must be a `list[str]` per row, `PY` must be non-null and numeric. The ETL must build `AU_UN` from `C1` for non-WoS sources.

### get_annualproduction.py
1) Counts how many papers were published each year and draws a line chart.
2) **www.services**.
3) **PY**.
4) **No**.
5) Crashes if `PY` is missing, non-numeric, or contains nulls.
6) **Yes**. `PY` must be present, non-null, and numeric.


### get_authorlocalimpact.py
1) Calculates impact scores (h-index, g-index, m-index, total citations) for each author and draws a bubble chart of the top authors.
2) **www.services**.
3) **AU**, **TC**, **PY**.
4) **No**.
5) Crashes if `AU` is not a list. Index calculations may produce wrong results due to incorrect use of `transform`.
6) **Yes**. `AU` must be a `list[str]`, `TC` and `PY` must be non-null and numeric.


### get_authorproductionovertime.py
1) Counts publications and citations per author per year and draws a scatter plot for the top-k authors.
2) **www.services**.
3) **AU**, **PY**, **TC** (core); **TI**, **SO**, **DI** (secondary — used for the document table, missing ones handled with a warning).
4) **No**, but the fallback author splitting uses a comma which is WoS-specific.
5) Wrong author names for non-WoS sources due to comma-based splitting. Missing `DI` silently returns an empty document table.
6) **Yes**. `AU` must be a `list[str]`, `PY` and `TC` must be numeric, `TI`, `SO`, `DI` must be present as strings.


### get_averagecitations.py
1) Calculates average citations per year and draws a line chart.
2) **www.services**.
3) **PY**, **TC**.
4) **No**.
5) Crashes if `PY` or `TC` are missing or non-numeric. Division by zero possible if `PY` equals the current year.
6) **Yes**. `PY` and `TC` must be present, non-null, and numeric.


### get_bradfordlaw.py
1) Applies Bradford's Law to rank journals by publications, divides them into three zones, and draws a log-scale chart highlighting the core journals.
2) **www.services**.
3) **SO**.
4) **No**.
5) Crashes if `SO` is missing. Null values in `SO` are silently ignored, potentially skewing zone boundaries.
6) **Yes**. `SO` must be present, non-null, and a string.


### get_citedcountries.py
1) Ranks countries by total or average citations and draws a dot chart of the top-k countries.
2) **www.services**.
3) **TC** (core); **C1** or **RP** (secondary — needed by `metaTagExtraction` to extract the country).
4) **Yes**. `metaTagExtraction` is built for WoS-style affiliation strings.
5) If `C1` or `RP` are missing or wrongly formatted, the chart will be empty with no clear error. `TC` non-numeric values will cause a crash.
6) **Yes**. `TC` must be numeric and non-null. `C1` or `RP` must be populated correctly for country extraction to work.


### get_citeddocuments.py
1) Ranks papers by total citations or citations per year and draws a dot chart of the top-k documents.
2) **www.services**.
3) **SR**, **TC**, **PY** (core); **DI** (secondary — included in the output table).
4) **No**, but `SR` is expected in WoS format.
5) Empty chart with no error if `SR` is missing. Crashes if `TC` or `PY` are non-numeric. Division by zero possible if `PY` equals current year.
6) **Yes**. `SR` must be correctly built by the ETL, `TC` and `PY` must be numeric, `DI` should be present as a string.


### get_clusteringcoupling.py
1) Groups papers or authors into clusters based on shared references or keywords and draws an interactive network. Saves the result as an HTML file.
2) **www.services**; **couplingMap**, **avoid_net_overlaps**.
3) **None directly** — all column access is delegated to `couplingMap`.
4) **Yes**. `couplingMap` is built for WoS-style data, especially `SR` and `CR`.
5) No validation on the network returned by `couplingMap` — a broken network causes a hard crash. Temporary HTML file is never deleted.
6) **Indirect**. The ETL must ensure `SR`, `CR`, `AU`, `TC`, `PY`, `DE`, `ID` are correctly formatted for `couplingMap` to work.

### get_co_occurence_network.py
1) Builds a word or keyword co-occurrence network, plus a density heatmap, a statistics table, and a degree distribution plot.
2) **www.services**; **biblionetwork**, **network_plot**, **term_extraction**, **cocMatrix**, **avoid_net_overlaps**, **field_by_year**.
3) **None directly** — all column access delegated to internal functions. **PY** is accessed directly inside `field_by_year`.
4) **Yes**. Field names `ID`, `DE`, `TI`, `AB`, `WC` are WoS tags — non-WoS sources will produce an empty network.
5) If no field condition matches, the function silently returns nothing. Cluster colors are random on every run. Temporary HTML file is never deleted.
6) **Indirect**. The ETL must ensure `ID`, `DE`, `TI`, `AB`, `WC`, and `PY` are all present and correctly formatted.

### get_cocitation.py
1) Builds a co-citation network — meaning it finds which references, authors, or sources are cited together most often across papers, and draws an interactive network where each bubble is a reference/author/source and lines show how often they are cited together. Also produces a density heatmap, a cluster statistics table, and a degree distribution plot.
2) **www.services**; **biblionetwork**, **network_plot**, **metaTagExtraction**, **avoid_net_overlaps**.
3) **None directly** — all column access is delegated to `biblionetwork` and `metaTagExtraction`. `CR`, `CR_AU`, and `CR_SO` are checked for existence but not read directly.
4) **Yes**. `biblionetwork` and `metaTagExtraction` are built for WoS-style reference strings. Non-WoS sources with differently formatted references will produce empty or broken networks.
5) If `biblionetwork` returns an empty network the function crashes with no clear error. Cluster colors are randomly generated on every run. Temporary HTML file is never deleted.
6) **Indirect**. The ETL must ensure `CR` is present as a properly split list of reference strings, and `CR_AU`/`CR_SO` can be derived from it if needed.

### get_collaborationnetwork.py
1) Generates a collaboration network between authors, universities, or countries from a bibliographic DataFrame. It builds a graph via biblionetwork(), then produces four outputs: an interactive PyVis HTML network, a density heatmap, a cluster statistics table, and a normalized degree plot.
2) **www.services**
3) **AU**, then AU_UN, AU_CO.
4) **Yes**. There are two: metaTagExtraction() is called to derive AU_UN and AU_CO, this function is known to have hardcoded WoS parsing logic (affiliation string formats, country extraction patterns), so if affiliations from Scopus/PubMed are formatted differently it will silently produce empty or wrong values; biblionetwork() likely expects AU, AU_UN, AU_CO in WoS delimiter/format (semicolon-separated strings or lists).
5) **Yes**, metaTagExtraction() has hardcoded WoS affiliation parsing, so AU_UN and AU_CO will silently produce empty or wrong values for non-WoS sources.
6) **Indirectly**. The function itself is downstream of the ETL, but the pipeline must guarantee that AU is a proper list[str] and C1 is a list[str] with standardized affiliation strings so metaTagExtraction() can correctly extract AU_UN and AU_CO.

### get_correspondingauthorcountries.py
1) Extracts the corresponding author's country (AU1_CO) and all author countries (AU_CO) via metaTagExtraction(), then counts articles, single-country publications (SCP), and multi-country publications (MCP) per country. Returns a horizontal bar chart and a summary table.
2) **www.services**
3) AU1_CO (derived), AU_CO (derived), AU, C1, RP (implicitly required by metaTagExtraction()).
4) **Yes**. Both metaTagExtraction(Field="AU_CO") and metaTagExtraction(Field="AU1_CO") rely on WoS-style affiliation parsing of C1 and RP, as flagged in metatagextraction.py. Non-WoS sources will silently produce empty or wrong country values.
5) Issues: data.dropna(subset=["AU1_CO", "AU_CO"]) silently drops all rows if metaTagExtraction() fails to parse affiliations from non-WoS sources, producing an empty DataFrame with no error; no validation that C1 or RP exist before calling metaTagExtraction(), mirroring the crash pattern flagged in metatagextraction.py; top_k_countries is applied after sorting but the earlier top_country_names already takes all countries — the filtering step is redundant and misleading.
6) **Yes**. C1 and RP must be present and correctly formatted as list[str] with standardized affiliation strings so metaTagExtraction() can correctly derive AU_CO and AU1_CO. Without this, the function silently returns an empty result.

### get_countriesproduction.py
1) Extracts author countries via metaTagExtraction(), counts publication frequency per country, downloads world boundary geodata, and produces an interactive choropleth map and a summary table of scientific production by country.
2) **www.services**
3) AU_CO (derived), C1 (implicitly required by metaTagExtraction()).
4) **Yes**. metaTagExtraction(Field="AU_CO") relies on WoS-style affiliation parsing of C1, as flagged in metatagextraction.py.
5) No validation that C1 exists before calling metaTagExtraction(), mirroring the crash pattern flagged in metatagextraction.py. Country name normalization only corrects "USA" → "UNITED STATES OF AMERICA"; all other country name mismatches between the source data and the shapefile silently result in unmatched rows and zero counts. dropna is never called on AU_CO after explode(), so empty list entries produce NaN rows that pollute the country counts.
6) **Yes**. C1 must be present and correctly formatted as list[str] with standardized affiliation strings so metaTagExtraction() can correctly derive AU_CO. Country name formatting in C1 should also conform to WoS conventions to maximize matches against the shapefile.

### get_countriesproductionovertime.py
1) Extracts author countries via metaTagExtraction(), pairs each country with its publication year, computes cumulative article counts over time, and returns a line chart of the top-k countries' production over time plus the underlying DataFrame.
2) **www.services**.
3) AU_CO (derived), PY, C1 (implicitly required by metaTagExtraction())
4) **Yes**. metaTagExtraction(Field="AU_CO") relies on WoS-style affiliation parsing of C1, as flagged in metatagextraction.py. Non-WoS sources will silently produce empty or wrong country values.
5) Issues: no validation that C1 or PY exist before use, mirroring the crash pattern flagged in metatagextraction.py and thematicmap.py; years = data["PY"].repeat(nAFF).values[:len(affiliations)] silently misaligns years with affiliations if any AU_CO entry was NaN and got dropped by dropna() — the repeat is based on the full DataFrame length but AFF has already dropped rows; PY is never cast to a numeric type before astype(int) — if PY contains empty strings (as our ETL schema allows), this will crash.
6) **Yes**. C1 must be present and correctly formatted as list[str] so metaTagExtraction() can derive AU_CO. PY must be present, non-empty, and castable to integer for the year alignment logic to work correctly.


### get_data.py
1) Handles file upload from the Shiny dashboard UI. Depending on the selected mode, it processes one or more bibliographic files via biblio_json() or process_multiple_files(), loads the result into the reactive DataFrame df, and returns a status message to display in the UI.
2) **www.services**.
3) **No**.
4) **Indirectly**. biblio_json() and process_multiple_files() are the functions that actually parse and standardize the data — if those have WoS-specific assumptions (as flagged in parsers.py), the DataFrame loaded here will reflect those issues.
5) //
6) **Yes**. This is the entry point where our ETL must be plugged in. The "1B" path in particular must be routed through the standardization pipeline rather than calling pd.read_excel() directly, to ensure all downstream functions receive a correctly typed and validated DataFrame.

### get_database.py
1) Maps the user's UI selection to a human-readable database name string. Reads two Shiny input controls, input.select() (which tab is active) and input.database() (which source was chosen), and returns a plain string like "Web of Science" or "Scopus".
2) **www.services**.
3) **No**.
4) **None directly**. However this function is the gatekeeper that sets the DB value downstream. The string it returns must match whatever the ETL pipeline uses as the DB column value.
5) Two: DB value mismatch, the exam spec requires DB to hold standardised identifiers like "WEB_OF_SCIENCE" or "SCOPUS" while this function returns display strings ("Web of Science", "Scopus"), which are not the same - if DB is populated from this output, the contract is broken; UnboundLocalError risk, if input.select() returns anything outside "1A", "1B", "1C", the function reaches return database without ever assigning it, so it needs an else branch or a default.
6) **Yes**. Either this function's return values must be updated to match the schema DB identifiers, or the ETL Transform phase must normalise the returned string into the correct DB value before writing to the DataFrame.

### get_factorialanalysis.py
1) Builds a 2D interactive word map for conceptual structure analysis. It takes a DataFrame and a field (ID, DE, TI, AB), constructs a document-term matrix, runs a dimensionality reduction method (MCA, CA, or MDS), clusters the resulting term coordinates with hierarchical clustering, and returns an annotated Plotly scatter figure plus coordinate/cluster DataFrames. Also contains helpers: _to_seq (flatten values to list), eig_correction (Benzecri eigenvalue correction), avoidOverlaps (label deduplication — currently commented out), and assign_consistent_colors.
2) **www.services**.
3) **ID, DE, TI, AB**.
4) field="ID" default. ID (Keywords Plus) is a WoS-exclusive field — it does not exist in Scopus, PubMed, or Dimensions exports. Using ID as the default silently produces an empty or broken analysis on non-WoS data.
5) //
6) **Yes**. The ETL must ensure that: ID is a list[str] (WoS Keywords Plus) and dor non-WoS sources that lack ID, populate it as [] per the null contract — but also ensure the UI defaults field to DE (author keywords) for those sources, since an all-empty ID column will produce no usable analysis; DE, TI, AB are correctly typed (list[str] for DE, str for TI/AB).

### get_filters.py
1) Two functions. get_filters() enriches the DataFrame with computed filter metadata: min/max publication year, average citations per year, and Bradford's Law zone assignment per source journal. get_filtered_table() applies user-driven UI filters (year range, language, document type, avg citations, Bradford zone) to the enriched DataFrame, then passes the result to get_table() for display.
2) **www.services**.
3) **PY, TC, SO, LA, DT**.
4) **Yes**. LA and DT value sets are implicitly WoS-formatted. The UI populates filter options from whatever values exist in these columns. WoS uses "English" and "Article"; Scopus may use "English" but "Journal Article" for DT. If not normalised by ETL, the filter checkboxes will show mixed values and users may filter out valid records unintentionally. || Bradford zone logic assumes SO is a clean, standardised journal name. WoS and Scopus capitalise journal names differently, so the same journal can appear as two separate sources, splitting its frequency and producing wrong zone assignments.
5) Division by zero in Average_Citations_Per_Year. If PY == current_year, Years_Since_Publication = 1 — safe. But if PY > current_year (malformed data), the denominator goes negative. No guard exists. ETL should clamp PY to <= current_year. || TC nulls not handled. If TC contains NaN (not coerced to 0 by ETL), Average_Citations_Per_Year will be NaN, silently breaking the citations slider filter in get_filtered_table().
6) **Yes**. The ETL must: Cast TC to int, nulls → 0 || Cast PY to int, no nulls, clamped to valid range || Normalise SO to a consistent casing (uppercase) across sources || Normalise DT to a controlled vocabulary (e.g. "Article", "Review") so UI filters work identically regardless of source || Normalise LA to a consistent format (e.g. "ENGLISH").

### get_frequentwords.py
1) Two functions. get_frequent_words() produces a lollipop scatter chart and full frequency table of the most common words/keywords in a chosen field. It supports n-grams (for TI/AB), custom stopword removal, and synonym merging. table_tag() is the core extraction engine: it deduplicates by SR, routes to either term_extraction() (for free text fields TI/AB) or direct column access (for keyword fields DE/ID), then counts terms using Counter.
2) **www.services**.
3) SR, and one of DE, ID, TI, AB depending on word_type
4) **Yes**. ID (Keywords Plus) is WoS-exclusive. Selecting word_type="ID" on non-WoS data will operate on an empty or absent column with no error. || SR deduplication assumes SR is always populated. SR is a calculated field ("FirstAuthor, Year, Journal") generated by the WoS pipeline. If ETL does not produce it, drop_duplicates(subset='SR') will raise a KeyError. || eval(x) on DE/ID strings assumes the column was serialised as a Python list literal (e.g. "['kw1', 'kw2']"), which is a WoS/internal serialisation convention. Scopus CSV exports use semicolon-delimited strings, causing eval() to raise a SyntaxError or return the wrong structure.
5) remove_terms only applied for DE/ID, not for TI/AB. The guard if remove_terms and tag in ['DE', 'ID'] means stopword removal is silently skipped when analysing titles or abstracts, which is likely unintentional. || SR missing crashes silently. If SR is absent, drop_duplicates(subset='SR') raises KeyError with no informative message to the user.
6) **Yes**. The ETL must: Populate SR for all rows (non-empty string). || Ensure DE and ID are list[str], not raw strings — this eliminates the eval() hazard entirely. || Ensure ID is [] for non-WoS sources so the function degrades gracefully rather than crashing. || TI and AB must be str, not NaN/None.

### get_historiograph.py
1) Builds an interactive historiographic network map showing citation relationships between key papers over time. It calls metaTagExtraction() and histNetwork() from services to construct the citation graph, then histPlot() for the initial layout. It then rebuilds the graph with networkx, optionally removes isolated nodes, positions nodes on a timeline (x = year, y = cluster), computes node sizes from local citation scores (LCS), and renders an interactive pyvis HTML network saved to a temp file. Returns the plot object, a metadata DataFrame, and the temp HTML filename.
2) **www.services**.
3) **SR, CR, DOI, AU, TI, DE, ID, PY**.
4) **Yes**. histNetwork() parses CR using WoS reference string format ("Author, Year, Journal, Vol, Page"). This is the most WoS-specific dependency in the entire codebase. Non-WoS CR strings will produce zero or wrong citation matches, resulting in an empty or disconnected graph. || metaTagExtraction(df, "SR") regenerates SR from WoS-style author/year/journal fields. If SR was not correctly populated by ETL, this call may produce malformed node identifiers that break edge matching. || node_label="ID" and node_label="DE" are swapped. The code maps "ID" → row.get("Author_Keywords") and "DE" → row.get("KeywordsPlus"), which is the reverse of the standard schema (DE = author keywords, ID = Keywords Plus). This is a WoS internal naming artefact from histNetwork() output columns.
5) DE/ID label mapping is inverted (as noted above). A user selecting node_label="DE" gets Keywords Plus, not author keywords. Needs a one-line swap or renaming in histNetwork() output. || eval() used again for DE/ID node labels (same pattern as get_frequentwords.py). Unsafe and redundant if ETL guarantees list[str].
6) **Yes, high priority**. The ETL must: Populate SR correctly as "FirstAuthor, Year, Journal" — it is the primary node key for the entire graph. || Normalise CR entries to WoS reference string format, as histNetwork() depends on it for edge construction. This is the single highest-risk dependency in the project for non-WoS sources. || Ensure DOI is str, empty string "" if missing (not NaN). || Ensure DE and ID are list[str] to eliminate the eval() calls.


### get_localcitedauthors.py
...

### get_localciteddocuments.py
...

### get_localcitedreferences.py
...

### get_localcitedsources.py
...

### get_lotkalaw.py
...

### get_maininformations.py
...

### get_referencesspectroscopy.py
...

### get_relevantaﬃliations.py
...

### get_relevantauthors.py
...

### get_relevantsources.py
...

### get_sourceslocalimpact.py
...

### get_sourcesproduction.py
...

### get_status.py
...

### get_table.py
...

### get_thematicevolution.py
...

### get_thematicmap.py
...

### get_threefieldplot.py
...

### get_treemap.py
...

### get_trendtopics.py
...

### get_wordcloud.py
...

### get_wordfrequency.py
...

### get_worldmapcollaboration.py
...



---

## Summary

### All columns required across the entire codebase
| Column | Used by |
|--------|---------|
| AU | biblionetwork.py, get_relevantauthors.py, ... |
| TI | ... |

### Files that need patching
| File | Line | Issue |
|------|------|-------|
| histnetwork.py | 37 | if db == "Web_of_Science" |
| biblionetwork.py | 94 | if db == "web_of_science" |
| format_functions.py | multiple | if source == "Web_of_Science" |

