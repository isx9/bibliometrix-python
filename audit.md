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
1) Computes cumulative scientific publication counts per affiliation over time, selects the top-k affiliations by total output at the latest year, and returns an interactive Plotly line chart (cumulative articles vs. year per affiliation) plus the filtered summary DataFrame.
2) **www.services** (wildcard — provides `pd`, `px`, `go`).
3) **AU_UN**, **PY**.
4) **No** explicit DB check, but `AU_UN` is a WoS-derived column (university/affiliation field). Non-WoS sources do not natively produce `AU_UN` — it is typically parsed and normalized from `C1` by a WoS-specific service. Any source lacking this pre-processed column will crash immediately.
5) `AU_UN` is expected to be a list of strings per row — if it arrives as a raw string (e.g. semicolon-delimited, as it would from a CSV), the `lambda x: [aff for aff in x if aff.strip() != ""]` will iterate over characters instead of affiliations, silently producing garbage. `PY` is never cast to `int` before `repeat()` and `astype(int)` — nulls in `PY` will propagate and cause a crash at the `astype(int)` call. No guard against `top_k_affiliations` exceeding the number of available affiliations.
6) **Yes**. `AU_UN` must be present and correctly typed as `list[str]` per row, and `PY` must be non-null and castable to `int`. The ETL pipeline must either populate `AU_UN` directly or derive it from `C1` during the Transform phase.

### get_annualproduction.py
1) Computes annual scientific publication counts from the `PY` column, fills in missing years with zero, and returns an interactive Plotly line chart (articles vs. year) plus the aggregated summary DataFrame.
2) **www.services** (wildcard — provides `pd`, `px`, `go`).
3) **PY** only.
4) **No** explicit DB check, but `PY` is the WoS tag for Publication Year. Any source using a different column name will cause an immediate `KeyError`.
5) `PY` is never cast to `int` before `range(min_year, max_year + 1)` if it arrives as a string or contains nulls it crashes with `TypeError`. `df.get()` assumes a custom wrapper object, not a plain DataFrame. Wildcard import hides actual dependencies. No guard against an empty or all-null `PY` column.
6) **Yes**. `PY` must be present, non-null, and cast to `int` by the ETL pipeline before this function is called. No patching of the function itself should be needed once that contract is met.

### get_authorlocalimpact.py
...

### get_authorproductionovertime.py
...

### get_averagecitations.py
...

### get_bradfordlaw.py
...

### get_citedcountries.py
...

### get_citeddocuments.py
...

### get_clusteringcoupling.py
...

### get_co_occurence_network.py
...

### get_cocitation.py
...

### get_collaborationnetwork.py
...

### get_correspondingauthorcountries.py
...

### get_countriesproduction.py
...

### get_countriesproductionovertime.py
...

### get_data.py
...

### get_database.py
...

### get_factorialanalysis.py
...

### get_filters.py
...

### get_frequentwords.py
...

### get_historiograph.py
...

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

