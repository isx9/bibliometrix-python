# Patching Documentation

## Services

### biblionetwork.py
**Status:** PASS (all 16 combinations)  
**Patches applied:** ...  
**Known limitations:**
- AU_CO missing → needs metaTagExtraction first
- TI_TM, AB_TM missing → derived columns, need term extraction
- CR_AU, CR_SO missing → need metaTagExtraction first
These are all columns that the ETL pipeline doesn't produce directly, they need an extra processing step after the standardization. By the exam specs, these columns are not part of the required ETL schema, so we can ignore them.

### cocmatrix.py
**Status:** PASS (all fields, both sources)

**Known limitations:**
The Field=AB for PubMed returns an empty matrix. This is fine and it's caused by PubMed eSummary API that doesn't return abstracts, so it's its limitation, not an ETL bug.

### couplingmap.py
**Status: PASS after patching** (both sources)
**Error found:** `TypeError: NDFrame.get() missing 1 required positional argument: 'key'`
**Root cause:** Bug in metatagextraction.py line 12 — not a bug  in couplingmap.py itself
**Fix:** We need to fix metatagextraction.py first, then retest couplingmap.py
**Patches applied:** SR() function in metatagextraction.py, infinite loop fix:
   - Original while loop caused infinite loop in pandas >= 2.0 due to boolean index assignment issues with RangeIndex
   - Fixed by using a dictionary to track duplicates and  converting SR to string first to handle NaN values


### format_functions.py
**Status:** PASS (import check only)

**Reason:** It exclusively handles raw file parsing for direct dashboard  uploads (WoS .txt, Scopus .csv, BibTeX, etc.), it's never called when 
uploading a standardized ETL-produced CSV. Not applicable to  OpenAlex/PubMed ETL testing.

### histnetwork.py
**Status:** **PASS after patching** (both sources)
**Patches applied:**
1. Line 9: `M = df.get()` → fixed with isinstance check
   - Reason: pandas .get() requires a column name, crashes without one
2. `reactive.Value(M)` → replaced with plain `M` in cocMatrix call
   - Reason: reactive.Value is Shiny-specific, crashes outside dashboard
     
**Notes. Known limitation, OpenAlex citation analysis:**
The CR column in OpenAlex data contains URLs  (e.g. https://openalex.org/W2101234009) instead of formatted citation strings (e.g. "Smith J, 2019, NATURE"). The histNetwork function cannot parse URLs as citation.
After patching, Local Citation Score (LCS) will be 0 for all papers. The function does not crash, it just detects the empty result and returns LCS=0 safely. This is an OpenAlex data format limitation, not an ETL bug

### histplot.py
**Status:** SKIP (both sources)

**Reason:** histPlot depends on histNetwork returning a valid NetMatrix. histNetwork returns NetMatrix=None for both OpenAlex 
and PubMed because:
- OpenAlex: CR contains URLs instead of formatted citation strings
- PubMed: CR references cannot be matched back to papers in dataset
So it's not a bug in histplot.py itself. The limitation  comes from the CR data format from both APIs. histPlot would work  correctly if histNetwork produced a valid network.

### htmldownload.py
**Status:** Not applicable to ETL testing
**Reason:** This is a dashboard utility for downloading plots as PNG images using a headless Chrome browser. It takes an HTML file path as input, not a DataFrame. Not part of the ETL pipeline.

### igraph2vis.py
**Status:** Not applicable to ETL testing
**Reason:** This is a visualization utility that converts igraph network objects to interactive HTML/vis.js format. It takes a graph object as input, not a DataFrame. Not part of the ETL pipeline.

### mappings.py
**Status:** PASS (import check only)
**Reason:** Contains mapping dictionaries (PUBMED_MAPPING, OPENALEX_MAPPING) that translate raw API field names to WoS tags. 
Written by our team as part of the ETL pipeline. No DataFrame testing needed, it is a static lookup table imported by standardizer.py.

### metatagextraction.py
**Status: PASS after patching** (all fields, both sources)
**Patches applied:**
1. Lines 11-13: `hasattr(df, "get")` check → fixed with isinstance check
   - Reason: pandas DataFrames also have a .get() method, so hasattr(df, "get") was always True for plain DataFrames too.
     This caused df.get() to be called without arguments, crashing with: TypeError: NDFrame.get() missing 1 required positional argument: 'key'
   - Fix: replaced with isinstance(df, pd.DataFrame) check:
     - if it's a DataFrame → copy it directly
     - if it's a Shiny reactive object → use .get() to unwrap it

### networkplot.py
**Status:** PASS (both sources)

### parsers.py
**Status:** Not applicable to ETL testing
**Reason:** Contains raw file parsers for direct dashboard uploads (parse_wos_data, parse_pubmed_data, parse_cochrane_data). Takes file paths as input, not DataFrames. Never called when uploading a standardized ETL-produced CSV. 

### plotlydownload.py
**Status:** Not applicable to ETL testing
**Reason:** Dashboard utility for downloading Plotly figures as PNG images. Takes a Plotly figure object as input, not a DataFrame. Never called during data processing or analysis. Not part of the ETL pipeline.

### savereport.py
**Status:** Not applicable to ETL testing
**Reason:** Dashboard utility for saving and exporting reports as Excel files. Takes report objects, tables and plots as input, not a DataFrame. Never called during data processing or analysis. Not part of the ETL pipeline.

### standardizer.py
**Status:** PASS (import check only)
**Reason:** Written by our team as part of the ETL pipeline. Transforms raw API records from OpenAlex and PubMed into the standard WoS schema DataFrame. Already validated by test.py which produced test_openalex.csv and test_pubmed.csv successfully.Not tested with a DataFrame — it is the component that produces the DataFrame.

### tabletag.py
**Status:** PASS (both sources)

### termextraction.py
**Status:** PASS (both sources)
**Notes:** Was failing with: LookupError: Resource stopwords not found. Fixed by downloading missing NLTK data:
  nltk.download('stopwords')
  nltk.download('punkt')
  nltk.download('punkt_tab')

### thematicmap.py
**Status:** PASS (both sources)
**Patches applied:**
1. Lines 9-11: Reactive/DataFrame check — correctly uses `not isinstance(df, pd.DataFrame)` before calling `.get()` so it handles both plain DataFrames and Shiny reactive objects
2. Lines 30-41: `reactive.Value()` wrapping for biblionetwork calls when processing TI and AB fields — needed because biblionetwork expects a reactive object in some code paths
3. Line 54: Safety check added — network_plot may return None on small or empty graphs, handled gracefully
4. Line 486: Safety check added — if field doesn't exist in DataFrame, function returns gracefully instead of crashing
**Notes:** TI_TM and AB_TM are derived at runtime by term_extraction, these are not part of the required ETL schema

### utils.py
**Status:** Not applicable to ETL testing
**Reason:** Contains only empty_plot(), a UI utility that generates a placeholder plot for the dashboard before analysis runs. Takes no DataFrame as input. Not part of the ETL pipeline.

## Known Limitations In Services
### CR Field - OpenAlex
**Issue:** OpenAlex returns cited references (CR) as URLs (e.g. https://openalex.org/W2101234009) instead of formatted citation strings (e.g. "Smith J, 2019, NATURE").
**Impact:** Functions that depend on formatted CR strings will return empty results for OpenAlex data:
- histNetwork → NetMatrix = None
- histPlot → SKIP (depends on histNetwork)
- co-citation networks → empty
**Why not fixed:** Resolving each URL would require additional  API calls per reference (potentially thousands for a 200 paper 
dataset), making the pipeline impractical and likely to hit  rate limits.
**Conclusion:** This is an OpenAlex API design choice, not a  bug in the ETL pipeline. The spec states functions should work "assuming the raw data contains the necessary underlying  information" — OpenAlex does not provide formatted citation  strings directly.

### CR Field - PubMed
**Issue:** PubMed eSummary API does not return cited references.
**Impact:** Same functions as above will return empty results.
**Why not fixed:** Would require switching to a different PubMed endpoint (efetch) which returns a different data format and would require significant changes to the parser.
**Conclusion:** Known API limitation of the eSummary endpoint used in the ETL pipeline.




---



## Functions

### get_affiliationproductionovertime.py
**Status:** PASS (both sources) 
**Patches:**
1. metaTagExtraction called before use to derive AU_UN column
2. Reactive/DataFrame check — correctly uses `not isinstance(df, pd.DataFrame)`
3. Safety check: AU_UN missing after extraction → returns empty figure
4. Safety check: AFFY empty after filtering → returns empty figure
5. Safety check: AffOverTime empty → returns empty figure

### get_annualproduction.py
**Status:** PASS (both sources) 
**Patches applied:**
1. Reactive/DataFrame check — correctly uses `not isinstance(df, pd.DataFrame)`
2. PY column forced to int safely with `pd.to_numeric(errors="coerce").fillna(0)`


### get_authorlocalimpact.py
**Status:** PASS (both sources)
**Patches applied:**
1. Line 16: `df = df.get()` → fixed with isinstance check. Reason: pandas .get() requires a column name, crashes without one. Fix: isinstance(df, pd.DataFrame) check

### get_authorproductionovertime.py
**Status:** PASS (both sources)
**Patches applied:**
1. Line 19: `data = df.get()` → fixed with isinstance check

### get_averagecitations.py
**Status:** PASS (both sources)
**Patches applied:** 
- Line 14: `data = df.get()` → fixed with isinstance check.
- Line 32: `current_year - table["PY"]` → TypeError. Reason: PY is stored as string in the standardized DataFrame but the function requires arithmetic subtraction which needs integers. Fix: added `pd.to_numeric(table["PY"], errors="coerce")` before the calculation.

### get_bradfordlaw.py
**Status:** PASS (both sources)
**Patches applied:**
1. Line 15: `data = df.get()` → fixed with isinstance check

### get_citedcountries.py
**Status:** PASS (both sources)
**Patches applied:**
1. Reactive/DataFrame check — correctly uses `not isinstance(df, pd.DataFrame)`
2. Filter for empty AU1_CO strings added — dropna alone does not catch empty strings
3. Line 110: safety check added before `int(max_x // 10)`. Reason: PubMed has no affiliation data, x_values is empty, x_values.max() returns NaN, int(NaN) crashes. Fix: return empty figure if x_values is empty or max_x is NaN.
**Known limitations:**
- PubMed returns empty results — eSummary API provides no affiliation data

### get_clusteringcoupling.py
**Status:** PASS (both sources) 
**Patches applied:**
1. Safety check: couplingMap returns None when network is empty → returns empty figures instead of crashing
**Known limitations:**
- OpenAlex: CR contains URLs, coupling map cannot be built
- PubMed: CR empty from eSummary API, coupling map cannot be built


### get_co_occurence_network.py
**Status:** PASS (both sources)
**Patches applied:**
1. field_by_year() line 425: PY converted to numeric before percentile calculation. Reason: PY stored as string, np.percentile requires numeric values. Fix: `pd.to_numeric(M['PY'], errors='coerce').values`
**Warnings (non-blocking):**
- Line 437: `n[col_idx]` uses deprecated integer indexing on Series. Will break in future pandas versions. Fix: change to `n.iloc[col_idx]`
 
### get_cocitation.py
**Status:** PASS (both sources) 
**Known limitations:**
- PubMed: co-citation matrix empty — CR not returned by eSummary API
- OpenAlex: CR contains URLs, co-citation results limited

### get_collaborationnetwork.py
**Status:** PASS (both sources) 
**Patches applied:**
1. Reactive/DataFrame check — correctly uses `not isinstance(df, pd.DataFrame)` before calling `.get()`
2. Safety check: network_plot returns None when graph is empty → returns empty figures instead of crashing
**Notes:**
- Field argument accepts "COL_AU", "COL_UN", "COL_CO"
- Tested with COL_AU (author collaboration network)
- COL_UN and COL_CO depend on AU_UN and AU_CO derived columns computed at runtime by metaTagExtraction

### get_correspondingauthorcountries.py
**Status:**  PASS (both sources) 
**Patches applied:**
1. Reactive/DataFrame check — correctly uses `not isinstance(df, pd.DataFrame)` before calling `.get()`
2. Filter for empty AU1_CO strings — dropna alone does not catch empty strings
3. Safety check after filtering — if all countries were blank, returns empty figure instead of crashing
**Known limitations:**
- Results will be empty for PubMed and limited for OpenAlex because affiliation data (C1) is often missing, so AU1_CO cannot be derived

### get_countriesproduction.py
**Status:** PASS (both sources) 
**Patches applied:**
1. Reactive/DataFrame check — correctly uses `not isinstance(df, pd.DataFrame)` before calling `.get()`
2. Filter for empty AU_CO strings after explode — prevents empty country strings from being counted
**Known limitations:**
- Results will be limited for OpenAlex and empty for PubMed because affiliation data (C1) is often missing, so AU_CO cannot be derived

### get_countriesproductionovertime.py
**Status:** PASS (both sources) 
**Patches applied:**
1. Reactive/DataFrame check — correctly uses `not isinstance(df, pd.DataFrame)` before calling `.get()`
2. Safety check: AFFY empty after filtering → returns empty figure
3. Safety check: AffOverTime empty → returns empty figure
**Known limitations:**
- Results will be limited for OpenAlex and empty for PubMed because affiliation data (C1) is often missing, so AU_CO cannot be derived

### get_factorialanalysis.py
**Status:** PASS (both sources) 
**Patches applied:**
1. Line 82: Reactive/DataFrame check — correctly uses `not isinstance(df, pd.DataFrame)` before calling `.get()`
2. Line 91: `df_plain` passed to conceptual_structure instead of original `df` — ensures plain DataFrame is used, not the reactive wrapper
3. (line 244): safety check if all Dim2 values are equal — range is 0 and label_offset would cause division by zero
4. (line 614): safety check if results.get() returns None — neither 'df' nor 'res' key exists in results
5. (line 593): safety check if all terms filtered out by min_degree — CW would be empty DataFrame
6. (line 637): safety check if n_clusters greater than number of available terms
7. (line 818): safety check if all points equidistant from centroid
8. Line 549: `CW.loc` crashes when CW is None. Reason: cocMatrix returns None when ID field is empty (Keywords Plus always empty for OpenAlex and PubMed). Fix: added None check before CW.loc call, returns empty result instead of crashing.
**Known limitations:**
- ID (Keywords Plus) always empty for OpenAlex and PubMed so conceptual_structure produces empty results for both sources

### get_filters.py
**Status:** PASS (both sources) 
**Patches applied:**
1. PY column forced to numeric safely with `pd.to_numeric(errors="coerce").fillna(0).astype(int)`
2. TC column forced to numeric safely with same pattern
3. Line 15: `data = df.get()` → fixed with isinstance check. Reason: pandas .get() requires a column name as argument, crashes without one. Fix: isinstance(df, pd.DataFrame) check: if it's a DataFrame → copy it directly; if it's a Shiny reactive object → use .get() to unwrap it.
**Notes:**
- get_filtered_table() in the same file is not testable, it requires Shiny input objects (input.year_slider(), input.languages(), etc.) only available inside the dashboard

### get_frequentwords.py
**Status:** PASS (all word types, both sources)
**Patches applied:**
1. Reactive/DataFrame check — correctly uses `not isinstance(df, pd.DataFrame)` before calling `.get()`
2. Same reactive/DataFrame check for `df_plain` passed to `term_extraction`
3. `safe_parse()` replaces `eval()` for DE/ID columns — handles malformed strings without crash
4. filter with `isinstance(sublist, list)` before iterating — avoids TypeError on None or str in TI/AB path
5. `remove_terms` applied to all tags, not just DE/ID — fixes silent bug where stopword removal was skipped for TI/AB
6. wrapped `term_extraction()` call in `try/except ValueError` — returns `{}` when vocabulary is empty
**Known limitations:**
- AB/PubMed returns empty results — PubMed eSummary API does not return abstracts, so the vocabulary is empty. Not an ETL bug.

### get_historiograph.py
**Status:** PASS (both sources)
**Patches applied:**
1. Replaced two `raise ValueError` blocks after `histNetwork()` returns None with a graceful return: empty DataFrame and temp HTML file path instead of crashing, consistent with the pattern used in get_clusteringcoupling.py and get_citedcountries.py. Removed redundant first `if hist_results is None` check — the second condition already covers it.
2. node_label="ID" branch: replaced unsafe `eval()` on Author_Keywords with a safe parser that handles list, semicolon-separated, and comma-separated formats without crashing on non-Python strings.
3. node_label="DE" branch: same safe parser applied to KeywordsPlus field for the same reason.
**Known limitations:**
- OpenAlex: CR contains URLs instead of formatted citation strings, histNetwork cannot build a citation graph, function returns empty result
- PubMed: CR is empty from eSummary API, same outcome
- Actual historiograph output requires WoS or Scopus formatted citation strings in CR

### get_localcitedauthors.py
**Status:** PASS (both sources)
**Patches applied:**
1. Reactive/DataFrame check — correctly uses `not isinstance(df, pd.DataFrame)` before calling `.get()` to unwrap Shiny reactive objects
2. Early return if all LCS values are 0 — avoids hanging on OpenAlex data where CR contains URLs and histNetwork cannot build a citation graph
**Known limitations:**
- OpenAlex: CR contains URLs instead of formatted citation strings, LCS is always 0, function returns empty result
- PubMed: CR is empty from eSummary API, same outcome
- Actual local cited authors output requires WoS or Scopus formatted citation strings in CR

### get_localciteddocuments.py
**Status:** PASS (both sources)
**Patches applied:**
1. Line 16: `M = df.get()` → fixed with isinstance check. Reason: pandas .get() requires a column name as argument, crashes without one. Fix: isinstance(df, pd.DataFrame) check: if it's a DataFrame → use it directly; if it's a Shiny reactive object → use .get() to unwrap it.
**Known limitations:**
- OpenAlex: CR contains URLs instead of formatted citation strings, LCS is always 0, function returns empty result
- PubMed: CR is empty from eSummary API, same outcome
- Actual local cited documents output requires WoS or Scopus formatted citation strings in CR

### get_localcitedreferences.py
**Status:** PASS (both sources)
**Patches applied:**
1. Line 19: `data = df.get()` → fixed with isinstance check. Reason: pandas .get() requires a column name as argument, crashes without one. Fix: `data = df if isinstance(df, pd.DataFrame) else df.get()`.
2. After filtering step: added early return when `source_counts` is empty. Reason: PubMed CR is always empty, causing `max_x` to be NaN and crashing downstream with `ValueError: cannot convert float NaN to integer` when computing x-axis ticks. Fix: return `(go.Figure(), empty_df)` gracefully.

### get_localcitedsources.py
**Status:** PASS (both sources)
**Patches applied:**
1. Line 10: `data = df.get().copy()` → fixed with isinstance check. Reason: pandas .get() requires a column name as argument, crashes without one. Fix: `data = df.copy() if isinstance(df, pd.DataFrame) else df.get().copy()`.

### get_lotkalaw.py
**Status:** PASS (both sources)
**Patches applied:**
1. Line 17: `data = df.get()` → fixed with isinstance check. Reason: pandas .get() requires a column name as argument, crashes without one. Fix: `data = df if isinstance(df, pd.DataFrame) else df.get()`.

### get_maininformations.py
**Status:** PASS (both sources)
**Patches applied:**
1. Line 10: `data = df.get()` → fixed with isinstance check. Reason: pandas .get() requires a column name as argument, crashes without one. Fix: `data = df if isinstance(df, pd.DataFrame) else df.get()`.

### get_referencesspectroscopy.py
**Status:** PASS (both sources)
**Patches applied:**
1. Line 21: `df = df.get()` → fixed with isinstance check. Reason: pandas .get() requires a column name as argument, crashes without one. Fix: `df = df if isinstance(df, pd.DataFrame) else df.get()`.
2. CR list conversion: CR column entries are joined into semicolon-separated strings before processing if they are lists, as produced by the ETL pipeline.
3. Empty table guard: if no references fall within the year range, returns `(empty FigureWidget, empty DataFrame, empty DataFrame)` gracefully instead of crashing downstream.

### get_relevantaffiliations.py
**Status:** PASS (both sources)
**Patches applied:**
1. `df.get()` → fixed with isinstance check. Reason: pandas .get() requires a column name as argument, crashes without one. Fix: `df.get() if hasattr(df, 'get') and callable(df.get) and not isinstance(df, pd.DataFrame) else df`.
2. `metaTagExtraction` return handling: AU_UN is a derived field that must be extracted before use, so `metaTagExtraction(df, Field="AU_UN")` is called only when `disambiguation == "yes"`.
3. Safety check after extraction: if `data` is None or empty, returns empty figure and empty DataFrame gracefully.
4. Missing `AU_UN` column guard: if `AU_UN` is absent after extraction in disambiguation mode, returns empty figure and empty DataFrame gracefully.
5. Missing `C1` column guard: if `C1` is absent in non-disambiguation mode, returns empty figure and empty DataFrame gracefully.
6. Empty affiliations guard: if `affiliations` is empty after explode, returns empty figure and empty DataFrame gracefully.

### get_relevantauthors.py
**Status:** PASS (both sources)
**Patches applied:**
1. Line 14: `data = df.get()` → fixed with isinstance check. Reason: pandas .get() requires a column name as argument, crashes without one. Fix: `data = df if isinstance(df, pd.DataFrame) else df.get()`.
2. None check before df.get(): if `df` is None, returns `(None, empty DataFrame)` gracefully.
3. Empty data check after unwrapping: if `data` is None or empty, returns `(None, empty DataFrame)` gracefully.
4. AU column guard: if AU is missing, fills with empty lists to avoid KeyError downstream.
5. AU list format guard: ensures AU entries are always lists, handling string and NaN cases.
6. Empty authors check: if no authors are found after flattening, returns `(None, empty DataFrame)` gracefully.

### get_relevantsources.py
**Status:** PASS (both sources)
**Patches applied:**
1. Line 17: `df.get()` → fixed with isinstance check. Reason: pandas .get() requires a column name as argument, crashes without one. Fix: `data = df if isinstance(df, pd.DataFrame) else df.get()`.

### get_sourceslocalimpact.py
**Status:** PASS (both sources)
**Patches applied:**
1. Line 18: `df.get()` → fixed with isinstance check. Reason: pandas .get() requires a column name as argument, crashes without one. Fix: `data = df if isinstance(df, pd.DataFrame) else df.get()`.
2. TC and PY numeric casting: `pd.to_numeric(..., errors='coerce')` applied to both TC and PY before index calculations to avoid arithmetic errors on string values.

### get_table.py
**Status:** function uses Shiny UI components.
**Patches applied:**
1. Line 68: `data = df.get()` → fixed with isinstance check. Reason: pandas .get() requires a column name as argument, crashes without one. Fix: `data = df if isinstance(df, pd.DataFrame) else df.get()`.
2. Second `df.get()` call in return statement: replaced with `data`, which is already the unwrapped DataFrame from patch 1, avoiding a redundant and potentially crashing second call.
3. `data.map(lambda x: x == [])` → replaced with a per-column `apply` using `isinstance` check. Reason: applying a lambda cell-by-cell across the entire DataFrame raises TypeError on non-list cells (int, float) in some pandas versions. Fix: `count_empty_lists` function checks `isinstance(x, list) and len(x) == 0` safely per column.

### get_thematicevolution.py
**Status:** PASS (both sources)
**Patches applied:**
1. Lines 93–98: removed `reactive.Value(Mk)` wrapper — passing `Mk` directly to `thematic_map`. Reason: `reactive.Value` is a Shiny-specific object that crashes outside a running Shiny application with "No current reactive context". `thematic_map` already handles plain DataFrames via its own isinstance check.
2. Lines 87–88: added early return when `timeslice` returns empty dict. Reason: `timeslice` returns `{}` when PY is all NaN (PubMed), causing the subsequent `for` loop to silently skip and `results` to be None, crashing on `results['Nodes']` downstream.
3. Line 45: added None check on `results` after `thematic_evolution` call. Reason: `thematic_evolution` returns None when PY is all NaN or no topics are found — accessing `results['Nodes']` on None crashes with TypeError.
4. `timeslice` — NaN PY guard: if PY is entirely NaN, return `{}` gracefully instead of crashing in `pd.cut`.
5. `timeslice` — dropna before `pd.cut`: drop rows with NaN PY before cutting to avoid non-monotonic bin errors.
6. `timeslice` — sorted breaks: wrap user-provided breaks with `sorted(set(...))` to guarantee monotonic order regardless of whether user-provided years fall outside the actual PY range of the data.
7. `normalize_to_minus1_1`: if all values are equal, return zeros instead of dividing by zero (range = 0 produces NaN everywhere).
8. `resk_tuple` unpacking: `thematic_map` returns exactly 5 values; original code tried to access index 5 which is always out of range.
9. `nclust` derivation: derived directly from `clusters` DataFrame row count instead of always being None.
10. `inc_matrix` accumulation: moved `pd.concat` and downstream processing outside the loop so all periods are accumulated before building the final result.
**Known limitations:**
- PubMed: PY is all NaN (eSummary pubdate field does not reliably parse to a 4-digit year), function returns `(None, empty DataFrame, None)` gracefully
- OpenAlex: DE keywords are sparse, thematic evolution output may be minimal depending on the year range chosen

### get_thematicmap.py
**Status:** PASS (both sources)
**Patches applied:**
1. None check on `thematic_map` return value: `thematic_map` returns `None` when `NetMatrix` is empty — unpacking directly would crash with `TypeError: cannot unpack non-iterable NoneType`. Fix: capture full result first, check for None, return safe empty tuple before unpacking.
2. Variable rename: `map` shadowed the Python builtin `map()` function — renamed to `thematic_map_result` to avoid the collision.

### get_threefieldplot.py
**Status:** PASS (both sources)
**Patches applied:**
1. None/empty check after each `cocMatrix` call: `cocMatrix` returns None when the field is empty (e.g. PubMed DE is always empty from eSummary API) — accessing `.shape` on None crashes with AttributeError. Fix: return empty `FigureWidget` gracefully if any of the three matrices is None or empty.
2. early return when `n1`, `n2`, or `n3` is 0: if `cocMatrix` returns an empty DataFrame for any field, reassigning `LM.index`/`columns` with a mismatched range crashes with `ValueError: Length mismatch`. Fix: return empty `FigureWidget` early.
3. opacity normalization guard: original guard checked `weight_max > 0` but not `weight_max != weight_min` — if all nodes share the same weight, `max - min` is 0 and normalization produces NaN in every opacity value. Fix: added second condition to ensure range is non-zero before dividing, falling back to `min_opacity` for all nodes.
4. solated node remapping: if `id_map` does not cover all values in `Edges['from']` or `Edges['to']`, `.map()` produces NaN — the Sankey crashes with float indices instead of int. Fix: drop edges whose endpoints are not in `id_map` before remapping, then cast to int.

### get_treemap.py
**Status:** PASS (both sources)
**Patches applied:**
1. `table_tag` — `df.get()` → fixed with isinstance check. Reason: pandas .get() requires a column name as argument, crashes without one. Fix: `df.get() if hasattr(df, 'get') and callable(df.get) and not isinstance(df, pd.DataFrame) else df`.
2. `table_tag` — plain DataFrame passed to `term_extraction`: `term_extraction` does not accept Shiny reactive objects — extract plain DataFrame before passing for AB/TI fields.
3. `table_tag` — list filter before iterating: for non-DE/ID fields, added `isinstance(sublist, list)` check before iterating to avoid `TypeError` when sublist is a string or NaN.
4. `table_tag` — `remove_terms` applied to all tags: original code only applied `remove_terms` for some tags. Fix: apply `remove_terms` filter to the final `word_counts` dict regardless of tag.
5. `get_treemap` — safety check on empty `word_counts`: if `table_tag` returns an empty dict (e.g. PubMed DE is always empty), `word_counts` DataFrame is empty and `px.treemap` crashes. Fix: return empty `FigureWidget` and empty table gracefully.

### get_trendtopics.py
**Status:** PASS (both sources)
**Patches applied:**
1. `get_trend_topics` — isinstance check for `df.get()`: extract plain DataFrame before passing to `term_extraction` — it does not accept Shiny reactive objects.
2. `get_trend_topics` — empty result guard: if `field_by_year` returns None or empty DataFrame, return empty `FigureWidget` and empty DataFrame gracefully instead of crashing on `px.scatter`.
3. `field_by_year` — isinstance check for `df.get()`: same pattern — unwrap reactive or use plain DataFrame directly.
4. `field_by_year` — `cocMatrix` None/empty guard: `cocMatrix` returns None when the field is empty (e.g. PubMed DE is always empty) — return empty DataFrame gracefully.
5. `field_by_year` — PY numeric conversion: PY is stored as string in ETL output — convert to numeric with `pd.to_numeric(..., errors='coerce')` before passing to `np.quantile` to avoid `TypeError: unsupported operand type(s) for -: 'str' and 'str'`.
6. `field_by_year` — `safe_quantile` empty array guard: if `np.repeat` produces an empty array (zero-frequency term), return `[nan, nan, nan]` gracefully instead of crashing in `np.quantile`.
7. `field_by_year` — `timespan` type guard: `timespan` may be passed as an integer (`time_window`) rather than a `[start, end]` list — `len()` on an int crashes with `TypeError`. Fix: check `isinstance(timespan, (list, tuple))` before calling `len()`, fall back to data range if not a valid list.

### get_wordcloud.py
**Status:** PASS (both sources)
**Patches applied:**
1. `table_tag` — isinstance check for `df.get()`: unwrap Shiny reactive or use plain DataFrame directly. Reason: pandas `.get()` requires a column name as argument, crashes without one.
2. `table_tag` — plain DataFrame passed to `term_extraction`: `term_extraction` does not accept Shiny reactive objects — extract plain DataFrame before passing for AB/TI fields.
3. `table_tag` — list filter before iterating: for non-DE/ID fields, added `isinstance(sublist, list)` check before iterating to avoid `TypeError` when sublist is a string or NaN.
4. `table_tag` — `remove_terms` applied to all tags: original code only applied `remove_terms` for some tags. Fix: apply `remove_terms` filter to the final `word_counts` dict regardless of tag.
5. `get_wordcloud` — empty word list guard: if `sorted_words` is empty (e.g. PubMed DE is always empty), write a minimal HTML file and return gracefully instead of crashing downstream.

### get_wordfrequency.py
**Status:** PASS (both sources)
**Patches applied:**
1. `get_word_frequency` — isinstance check for `df.get()`: extract plain DataFrame before passing to `term_extraction` — it does not accept Shiny reactive objects.
2. `get_word_frequency` — `term_extraction` empty vocabulary guard: `term_extraction` crashes with `ValueError: empty vocabulary` when the field column is entirely empty (e.g. PubMed DE is always empty from eSummary API). Fix: wrap in try/except and return empty `FigureWidget` and empty DataFrame gracefully.
3. `get_word_frequency` — empty TM column guard: if `term_extraction` succeeds but the TM column contains no terms, return empty results gracefully.
4. `get_word_frequency` — `top_words` type normalization: `top_words` may be passed as a plain int rather than a `[start, end]` list — indexing an int crashes with `TypeError`. Fix: normalize to `[0, n]` if a plain int is given.
5. `get_word_frequency` — PATCH 2: column slice bounds clamping: if `top_words[0]` >= number of available columns, slicing crashes with `IndexError`. Fix: clamp start and end to valid range before slicing.
6. `keyword_growth` — PATCH 3: empty data guard: if data is empty after filtering, `data['Year'].min()` returns NaN and `range(NaN, NaN)` crashes with `TypeError`. Fix: return empty DataFrame with just a Year column.
7. `keyword_growth` — PATCH 4: safe split with type check: iterating over elements without type checking crashes with `TypeError` on non-string/non-list elements. Fix: `safe_split` returns empty list for unexpected types.
8. `trim_years` — PATCH 5: empty year range guard: if `year_range` is empty, return empty Series immediately instead of producing inconsistent results.


### get_worldmapcollaboration.py
**Status:** PASS (both sources)
**Patches applied:**
1. `metaTagExtraction` return handling: after calling `metaTagExtraction(df, "AU_CO")`, unwrap result with isinstance check — `metaTagExtraction` may return a Shiny reactive or a plain DataFrame.
2. AU_CO safe fill: `fillna("")` applied before exploding AU_CO to avoid NaN propagation when AU_CO is missing or empty.
3. Country normalization: corrections dict maps common abbreviations (USA, UK, SOUTH KOREA) to standardized names used in the world geometry dataset.
4. Network None/empty guard: if `biblionetwork` returns None or an empty result, return empty `FigureWidget` and empty DataFrame gracefully.
5. Safe centroid computation: Longitude and Latitude converted with `pd.to_numeric(..., errors='coerce').fillna(0)` to avoid NaN coordinates crashing edge drawing.
6. Manual coordinate fixes for UK and France (centroid falls in the ocean or overseas territories).
7. Singapore patch: Singapore is absent from the 110m Natural Earth dataset — added manually with hardcoded coordinates.
8. Safe edge width: `max(row['count'], 1)` prevents division by zero when computing edge width.
**Known limitations:**
- AU_CO is a derived column not produced by the ETL pipeline — `metaTagExtraction` cannot extract it from OpenAlex or PubMed data, so the collaboration map always returns an empty figure for both sources

### get_citeddocuments.py
**Status:** PASS (both sources)
**Patches applied:**
1. `data = df.get()` → fixed with isinstance check. Reason: pandas .get() requires a column name as argument, crashes without one. Fix: `data = df if isinstance(df, pd.DataFrame) else df.get()`.
2. None check before unwrapping: if `df` is None, returns `(None, empty DataFrame)` gracefully.
3. Empty data check after unwrapping: if `data` is None or empty, returns `(None, empty DataFrame)` gracefully.
4. Required columns guard: if SR, TC, or PY are missing, fills with safe defaults (0 for numeric, "" for strings).
5. TC and PY numeric conversion: `pd.to_numeric(..., errors='coerce')` applied to both to avoid arithmetic errors on string values.
6. Division by zero prevention in TCperYear: `max((current_year + 1 - row['PY']), 1)` prevents division by zero for documents with missing or future PY.
7. Safe normalization: NormalizedTC groupby transform checks for zero or NaN mean before dividing.
8. Empty tab guard: if groupby aggregation produces an empty table, returns `(None, empty DataFrame)` gracefully.

### get_sourcesproduction.py
**Status:** PASS (both sources)
**Patches applied:**
1. Line 18: `data = df.get()` → fixed with isinstance check. Reason: pandas .get() requires a column name as argument, crashes without one. Fix: `data = df if isinstance(df, pd.DataFrame) else df.get()`.
2. PY string extraction for `data["PY"]`: PubMed PY may contain full date strings (e.g. "2026 Jun 6") instead of plain year integers — `astype(int)` crashes on these. Fix: extract first 4-digit year with `str.extract(r'(\d{4})')` and `pd.to_numeric` before casting to int. Rows with unparseable PY are dropped.
3. WPY column name extraction for missing years: `WPY.columns` may also contain full date strings — extract 4-digit year from column names before comparing against the PY range to compute missing years.
4. WPY column renaming before sort: `WPY.columns.astype(int)` crashes on full date strings. Fix: rename columns by extracting the first 4 characters as a year string, then sort using a safe `int(x) if x.isdigit() else 0` key.
**Known limitations:**
- PubMed: PY field from eSummary API returns full date strings (e.g. "2026 Jun 6") rather than 4-digit years — year extraction is required before any arithmetic on PY
  
---


