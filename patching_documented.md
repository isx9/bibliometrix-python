# Patching Documentation

## Services

### www/services/biblionetwork.py
**Status:** PASS (all fields, both sources)
**Patches applied:**
1. None check on input `M`: if `M` is None, prints a message and returns None gracefully instead of crashing downstream.
2. None checks on `cocMatrix` return values: each branch checks if `WA`, `WCR`, `WSO`, `WCO` etc. are None before attempting matrix multiplication — returns None gracefully if any required matrix is missing.
3. `M.get()` → isinstance check in final cleanup: after computing `NetMatrix`, unwrap `M` with isinstance check before accessing `M.columns`. Reason: `M` may already be a plain DataFrame after `term_extraction`.
4. `db_name` default changed from hardcoded `"web_of_science"` to `""`: unknown sources no longer silently get treated as WoS.
5. `db_name` normalization to lowercase: `str(M["DB"].iloc[0]).lower()` ensures consistent comparison regardless of DB value casing.
6. Scopus reference filter now checks `db_name == "scopus"` (lowercase) to match the normalized db_name.
7. `label_short` — added `"openalex"` and `"pubmed"` to the WoS branch: both sources produce SR strings in the same "Author, Year, Journal" format, so they are routed to the same label shortening logic.
8. `label_short` — unknown sources: labels returned unchanged instead of crashing.

### cocmatrix.py
**Status:** PASS (all fields, both sources)
**Patches applied:**
1. `df.get()` → isinstance check at the top: unwrap Shiny reactive or use plain DataFrame directly. Reason: pandas `.get()` requires a column name as argument, crashes without one. Fix: `df.get() if hasattr(df, 'get') and callable(df.get) and not isinstance(df, pd.DataFrame) else df`.
2. None/empty check on input: if `M` is None or empty, prints a message and returns None gracefully.
3. SR column fallback: if `LABEL` is not in columns, falls back to `SR` as the index — prints a message and returns None if SR is also missing.
4. Field existence check: if the requested field is not a column in `M`, prints a message and returns None instead of crashing with KeyError.
5. CR field safety: `DOI;` → `DOI ` replacement applied only when `CR` contains lists, avoiding TypeError on non-list entries.
6. Empty matrix guard: if `uniqueField` is empty after filtering, prints "Matrix is empty!!" and returns None gracefully instead of creating a zero-column matrix.
7. `reduceRefs` type check: skips non-string entries in refs list with `isinstance(ref, str)` check to avoid AttributeError on None or numeric values.


### couplingmap.py
**Status:** PASS (both sources)
**Patches applied:**
1. `couplingMap` — `df.get()` → isinstance check: after `metaTagExtraction`, unwrap result with isinstance check to get plain DataFrame `M`.
2. `couplingMap` — `network()` None guard: `network()` returns None when the matrix is empty (e.g. OpenAlex URL-based CR or empty CR for PubMed). Return None gracefully instead of crashing on `Net['graph']`.
3. `couplingMap` — `normalizeCitationScore()` None guard: `normalizeCitationScore` may return None if `localCitations` fails. Return None gracefully.
4. `couplingMap` — empty cluster filter guard: if `df` is empty after the frequency filter (`df['freq'] >= minfreq`), return None gracefully instead of crashing on downstream computations.
5. `normalizeCitationScore` — `localCitations` None guard: `localCitations` may return None if `histNetwork` finds no citations. Return None gracefully.
6. `normalizeCitationScore` — isinstance check for reactive unwrapping in global impact branch.
7. `localCitations` — `df.get()` → isinstance check after `metaTagExtraction`.
8. `localCitations` — None/empty check on `M` after unwrapping.
9. `localCitations` — `histNetwork` None guard: `histNetwork` may return None when no local citations are found. Return None gracefully.
10. `localCitations` — zero LCS guard: if all LCS values are 0, return None to avoid propagating empty results downstream.
11. `network` — isinstance check for `df_plain` before passing to `term_extraction` or `biblionetwork`.
12. `network` — None guard on `NetMatrix`: if `NetMatrix` is None or matrix is empty, print message and return None gracefully.
13. `labeling` — removed `reactive.Value` wrapper: `df` is already a plain DataFrame when passed to `term_extraction` inside `labeling`.


### format_functions.py
**Status:** PASS (import check only)
**Patches applied:**
1. PATCH 1 — `columns` NameError guard in `process_single_file`: `columns` was referenced without being defined in local scope, causing NameError. Fix: use `globals().get('columns', [])` to safely fall back to an empty list if `columns` is not defined.
2. PATCH 2 — `entry.get()` TypeError guard in `process_single_file`: entries from bibtexparser may not support `.get()` with a default — wrapped in try/except to avoid silent KeyError or AttributeError crashes.
3. PATCH 3 — author name unpacking guard in `format_au_column` for Scopus BibTeX: original code used `surname, names = person.split(", ")` without checking the number of parts — if the string contains no comma+space the unpacking crashes with ValueError. Fix: guard with `len(parts) == 2` check before unpacking.
4. `biblio_json` — ETL CSV passthrough: added support for standardized CSV files produced by the ETL pipeline. If the CSV contains the standard WoS-like columns (TI, AU, PY, SO, SR, DB), it is passed through directly as JSON without re-parsing through the old source-specific formatters.


### histnetwork.py
**Status:** PASS (both sources)
**Patches applied:**
1. `histNetwork` — `df.get()` → isinstance check: original code called `df.get()` without arguments, crashing on a plain pandas DataFrame. Fix: `if isinstance(df, pd.DataFrame): M = df.copy() else: M = df.get().copy()`.
2. `histNetwork` — None/empty check on `M` after unwrapping: if `M` is None or empty, return None gracefully.
3. `histNetwork` — DB column missing guard: if `DB` column is absent, return None gracefully instead of crashing on `M['DB'].iloc[0]`.
4. `histNetwork` — DI missing guard: if `DI` column is absent, fill with empty strings before processing.
5. `histNetwork` — CR missing guard: if `CR` column is absent, print message and return None gracefully.
6. `histNetwork` — CR list normalization: ensure CR entries are always lists before processing, handling string and NaN cases.
7. `histNetwork` — TC and PY numeric conversion: `pd.to_numeric(..., errors='coerce')` applied to both to avoid arithmetic errors on string values.
8. `histNetwork` — DB routing extended: added `"OPENALEX"` and `"PUBMED"` to the `wos()` branch. Both sources produce SR and DI fields in the format expected by `wos()`, so the same matching logic applies. Citation accuracy is lower for OpenAlex because CR contains URLs, but the function will not crash.
9. `wos` — required columns check: if PY or CR are missing, print message and return None gracefully.
10. `wos` — empty CR_df early return: if no valid references were parsed (e.g. OpenAlex URL-based CR), return early with `LCS=0` for all documents and `NetMatrix=None` instead of hanging.
11. `wos` — SR_FULL missing guard: if `SR_FULL` column is absent, fill with empty strings before building LABEL.
12. `wos` — optional columns guard: if TI, DE, or ID are missing, fill with empty strings before building histData.
13. `wos` — `reactive.Value(M)` removed before `cocMatrix` call: `reactive.Value` is a Shiny-specific object that crashes outside a running Shiny application. Fix: pass `M` directly since `cocMatrix` already handles plain DataFrames.
14. `scopus` — required columns check: if CR or SR are missing, print message and return None gracefully.
15. `scopus` — optional columns guard: if AU, BP, EP, SR_FULL, TI, DE, ID, or DI are missing, fill with safe defaults before processing.


### metatagextraction.py
**Status: PASS after patching** (all fields, both sources)
**Patches applied:**
**Patches applied:**
1. `metaTagExtraction` — `isinstance` check replacing `hasattr(df, "get")`: original code used `hasattr(df, "get")` to detect Shiny reactive objects, but pandas DataFrames also have `.get()`, so the check always resolved to True and called `df.get()` without arguments — crashing because pandas `.get()` requires a column name. Fix: `if isinstance(df, pd.DataFrame): M = df.copy() else: M = df.get().copy()`.
2. `SR` — infinite loop fix: original `while` loop caused an infinite loop in pandas >= 2.0 when deduplicating SR values. Fix: replaced with a `dict`-based seen-counter that iterates over the index once, appending `-b`, `-c`, etc. for duplicates.
3. `SR` — NaN guard before deduplication loop: added `.fillna("").astype(str).reset_index(drop=True)` before the seen-counter loop to prevent NaN values from being stored as keys and producing malformed SR strings.
4. `SR` — `JI` empty string fallback: `M.loc[no_art, "JI"] = M.loc[no_art, "SO"]` fills rows where `JI` is `""` with `SO`, preventing `", , "` gaps in the SR string when `JI` is missing.
5. `SR` — DB case normalization in author formatting: `M["DB"].iloc[0].lower() == "scopus"` normalizes the DB value to lowercase before comparison, making the author name reformatting robust to mixed-case DB values like `"Scopus"` or `"SCOPUS"`.
6. `CR_SO` — `None` replaced with `""` for empty rows: original returned `None` for articles with no parsed cited sources (`lambda l: ";".join(l) if l else None`). `None` in a string column crashes downstream `.str.*` operations. Fix: `lambda l: ";".join(l) if l else ""`.
7. `AU_CO` / `AU1_CO` — `fillna` float NaN guard: `M["C1"].fillna(M["RP"])` can produce `numpy.float64` NaN when both `C1` and `RP` are missing, making the cell non-iterable and crashing the country extraction loop. Fix: added `.infer_objects(copy=False)` and a follow-up `.apply(lambda x: x if isinstance(x, list) else ([] if pd.isna(x) else [x]))` to guarantee every cell is a list before iteration.
8. `AU_CO` / `AU1_CO` — empty list fallback when both `C1` and `RP` are missing: the explicit `for` loop after `fillna` sets `C1.at[i] = []` when the cell is still an empty list and `RP` is also NaN, preventing downstream iteration over `None` or float.
9. `AU_CO` / `AU1_CO` — country name normalization before regex search: `"RUSSIAN FEDERATION"` is not present in `countries.txt` (listed as `"RUSSIA"`), so matches silently failed. Fix: applied `.replace("RUSSIAN FEDERATION", "RUSSIA")` and equivalent aliases (`UNITED STATES → USA`, `ENGLAND / SCOTLAND / WALES / NORTH IRELAND → UNITED KINGDOM`) to the input string before the regex search, not only to the output list.
10. `AU1_CO` — `None` replaced with `""` for country not found: original returned `None` when no country matched. Fix: `if pd.notna(country) else ""`. **Note:** downstream consumers checking `if country is None` must be updated to `if not country` to catch the empty string.
11. `AU_UN` — `M.loc[condition, "AU_UN"]` replacing `M["AU_UN"].loc[...]`: original assignment syntax triggered `SettingWithCopyWarning` and could silently fail to modify the underlying DataFrame in some pandas versions. Fix: `M.loc[M["C3"].notna() & (M["C3"] != ""), "AU_UN"] = M["C3"]`.
12. `AU_UN` — `None` replaced with `""` in `replace` dict: original used `replace({"NOTDECLARED": None, "NOTREPORTED": None})`, which inserts `None` into a string column and crashes subsequent `.str.*` calls. Fix: `replace({"NOTDECLARED": "", "NOTREPORTED": ""})`.

### networkplot.py
**Status:** PASS (all sources)
**Patches applied:**
1. `network_plot` — empty graph guard on entry: after building `bsk_network` from `NetMatrix`, if the graph has no vertices or `deg` is empty, return `None` immediately instead of crashing on subsequent operations.
2. `network_plot` — `deg` recomputed after degree-based filtering: after `delete_vertices()` in the `degree` branch, `deg` and `bsk_network.vs["deg"]` were stale. Fix: recompute both immediately after deletion.
3. `network_plot` — `deg` recomputed after `n`-based filtering: same stale-`deg` issue in the `n` branch. Fix: recompute both immediately after deletion.
4. `network_plot` — empty graph guard after filtering: after either filtering branch, check `len(bsk_network.vs) == 0` and return `None` gracefully before attempting simplification or clustering.
5. `network_plot` — `deg` recomputed after isolate removal: after `delete_vertices(isolates)`, `deg` and `bsk_network.vs["deg"]` were stale. Fix: recompute both immediately after deletion.
6. `network_plot` — empty graph guard after isolate removal: after removing isolates, check `len(bsk_network.vs) == 0` and return `None` gracefully before attempting clustering.
7. `network_plot` — safe `deg` attribute access in label filtering: `bsk_network.vs["deg"]` raises a `KeyError` if the attribute was never set (e.g. after external filtering). Fix: `deg_vals = bsk_network.vs["deg"] if "deg" in bsk_network.vs.attributes() else bsk_network.degree()`.
8. `clustering_network` — `try/except` around all clustering calls: several igraph community detection algorithms (`spinglass`, `leading_eigenvector`, `infomap`) raise exceptions on small, disconnected, or unweighted graphs. Fix: wrapped the entire `if/elif` chain in `try/except Exception`, falling back to a single-cluster assignment (`membership = [0] * n`) so the rest of the pipeline can continue.
9. `switch_layout` — division-by-zero guard in coordinate normalization: when all nodes share the same layout coordinate on an axis (e.g. a single-node graph or perfectly collinear layout), `range_coords` is zero and normalization produces `NaN`. Fix: `range_coords[range_coords == 0] = 1` before dividing.

### tabletag.py
**Status:** PASS (both sources)

### termextraction.py
**Status:** PASS (both sources)
**Patches applied:**
1. `term_extraction` — reactive vs DataFrame detection fixed: original used `hasattr(df, 'get')` to detect Shiny reactive objects, but pandas DataFrames also have a `.get()` method, causing `df.get()` to be called without arguments on plain DataFrames and crashing. Fix: `is_reactive = hasattr(df, 'get') and callable(df.get) and not isinstance(df, pd.DataFrame)`, then `M = df.get() if is_reactive else df.copy()`.
2. `term_extraction` — reactive return path: original always called `df.set(M)` and returned `df` regardless of whether `df` was reactive. For plain DataFrames `df.set()` does not exist and crashes. Fix: `if is_reactive: df.set(M); return df` else `return M` — only the reactive path calls `.set()`.

### thematicmap.py
**Status:** PASS (both sources)
**Patches applied:**
1. `thematic_map` — reactive vs DataFrame detection fixed: original used `hasattr(df, 'get')` which is True for plain pandas DataFrames too. Fix: `not isinstance(df, pd.DataFrame)` guard added so `df.get()` is only called on actual Shiny reactive objects; plain DataFrames are copied directly.
2. `thematic_map` — `M_plain` extracted for `term_extraction` calls: `term_extraction` expects a plain DataFrame, not a reactive wrapper. Fix: `M_plain` is unwrapped from the reactive object before being passed to `term_extraction` in the `TI` and `AB` branches.
3. `thematic_map` — `TI` branch: `term_extraction` run on `M_plain`, then result wrapped back in `reactive.Value` before passing to `biblionetwork`, and `m["TI_TM"]` updated so `cluster_assignment` can access it downstream.
4. `thematic_map` — `AB` branch: same pattern as `TI` — `term_extraction` run on `M_plain`, result wrapped in `reactive.Value` for `biblionetwork`, and `m["AB_TM"]` updated for `cluster_assignment`.
5. `thematic_map` — `NetMatrix` empty/None guard: `biblionetwork` can return `None` or an empty DataFrame when the keyword column is absent or has no co-occurrences (e.g. PubMed `DE` is always empty from the eSummary API). Fix: `if NetMatrix is not None and not NetMatrix.empty` check before calling `network_plot`, returning a graceful `None, None, pd.DataFrame(), pd.DataFrame(), pd.DataFrame()` tuple otherwise.
6. `thematic_map` — `Net` None guard: `network_plot` can return `None` on small or empty graphs. Fix: explicit `if Net is None` check after the `network_plot` call, returning the same safe empty tuple.
7. `thematic_map` — `node_colors` None guard: `net.vs['color']` can contain `None` entries if clustering produced uncolored nodes. Fix: `node_colors = ["#D3D3D3" if c is None else c for c in node_colors]` applied immediately after extraction.
8. `thematic_map` — `DI` missing guard in `cluster_assignment`: if `DI` is absent from the DataFrame, the column selection `['DI', 'AU', 'TI', 'SO', 'PY', 'TC', 'TCpY', 'NTC', 'SR']` crashes with a `KeyError`. Fix: `if 'DI' not in M.columns: M['DI'] = np.nan` before the assign block.
9. `thematic_map` — `TC` non-numeric guard in `cluster_assignment`: `M['TC'] / (year - M['PY'])` crashes if `TC` contains strings or `NaN`. Fix: `pd.to_numeric(M['TC'], errors='coerce').fillna(0)` applied before the arithmetic.
10. `thematic_map` — `PY` non-numeric guard in `cluster_assignment`: same arithmetic crashes if `PY` is stored as a string. Fix: `pd.to_numeric(M['PY'], errors='coerce')` applied before `TCpY` calculation.
11. `cluster_assignment` — `field` column missing guard: if the requested `field` (or its derived `_TM` variant) is absent from `M`, the function crashes immediately on `M[field]`. Fix: `if field not in M.columns: return pd.DataFrame()` early return.
12. `cluster_assignment` — `filtered_df` empty guard raised as `ValueError`: after filtering `sEij_df` by `df_lab['words']`, if no rows survive (e.g. all keywords were too infrequent or filtered out), the subsequent `.groupby().agg()` produces a silent empty result or crashes. Fix: explicit `if filtered_df.empty: raise ValueError(...)` with a descriptive message before the aggregation block.



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
***Status**: PASS (both sources)
***Patches applied:**

- Lines 93–98: removed reactive.Value(Mk) wrapper — passing Mk directly to thematic_map. Reason: reactive.Value is a Shiny-specific object that crashes outside a running Shiny application with "No current reactive context". thematic_map already handles plain DataFrames via its own isinstance check.

- Lines 87–88: added early return when timeslice returns empty dict. Reason: timeslice returns {} when PY is all NaN (PubMed), causing the subsequent for loop to silently skip and results to be None, crashing on results['Nodes'] downstream.

- Line 45: added None check on results after thematic_evolution call. Reason: thematic_evolution returns None when PY is all NaN or no topics are found — accessing results['Nodes'] on None crashes with TypeError.

 — missing 'Nodes' key guard: thematic_evolution can also return {"check": False} (no 'Nodes' key) when one or more periods have zero topic clusters — typically because the chosen field is empty for the data source (e.g. Keywords Plus ID is exclusive to Web of Science and is always empty for OpenAlex/PubMed). Fix: check not results.get("check", True) or "Nodes" not in results before unpacking, instead of crashing with KeyError: 'Nodes'.

 — empty-result HTML generation: in both fallback cases above (results is None and missing 'Nodes'), the function previously returned None for the HTML network path, which the UI rendered as a broken "Not Found" page. Fix: generate a valid but empty pyvis.Network graph (no nodes/edges) and save it as a temporary HTML file, so the Map tab renders a blank canvas instead of an error.

 — TM return value: the third return value (TM, consumed by the "Time Slice 1/2" tabs) was set to None in the fallback cases above, causing object of type 'NoneType' has no len() in the UI, which calls len() on it. Fix: return an empty list [] instead of None.

- timeslice — NaN PY guard: if PY is entirely NaN, return {} gracefully instead of crashing in pd.cut.

- timeslice — dropna before pd.cut: drop rows with NaN PY before cutting to avoid non-monotonic bin errors.

 timeslice — sorted breaks: wrap break points with sorted(set(breaks)) to guarantee strictly increasing, duplicate-free bin edges regardless of whether the user-provided Cutting Year falls outside the actual PY range of the data (previous cause of "bins must increase monotonically"). If fewer than 3 unique edges remain, return {} instead of calling pd.cut.

 timeslice — empty-period guard: even after deduplication, an out-of-range Cutting Year can produce a bin that is valid for pd.cut but contains zero rows. Downstream code (min()/max() on each period's PY values) crashed with "min() arg is an empty sequence" on such empty periods. Fix: filter out empty sub-DataFrames after splitting; if fewer than 2 non-empty periods remain, return {}.

- normalize_to_minus1_1: if all values are equal, return zeros instead of dividing by zero (range = 0 produces NaN everywhere).

- resk_tuple unpacking: thematic_map returns exactly 5 values; original code tried to access index 5 which is always out of range.

- nclust derivation: derived directly from clusters DataFrame row count instead of always being None.

- inc_matrix accumulation: moved pd.concat and downstream processing outside the loop so all periods are accumulated before building the final result.

Known limitations:
-  Keywords Plus (ID) as Text Source: always empty for OpenAlex/PubMed data (exclusive to Web of Science). With the patches above, this no longer crashes — it produces an empty Map/Table/Time Slice result instead. Use TI, AB, or DE for these data sources.
- PubMed: if PY parsing from the eSummary pubdate field fails entirely, the function returns (None, empty DataFrame, None) gracefully (now an empty network graph + empty table + empty list, per the [SESSIONE ATTUALE] patches above).
- OpenAlex: DE keywords are sparse; thematic evolution output may be minimal depending on the year range chosen.


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


