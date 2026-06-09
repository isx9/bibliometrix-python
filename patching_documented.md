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

### get_annualproduction.py
**Status:** PASS (both sources) 
**Patches applied:** PY forced to int safely

### get_authorlocalimpact.py
**Status: PASS after patching** (both sources)
**Patches applied:** Line 16: `df = df.get()` → fixed with isinstance check. Reason: pandas DataFrames also have a .get() method which requires a column name as argument, calling it without arguments crashes with: TypeError: NDFrame.get() missing. 1 required positional argument: 'key'. Fix: replaced with isinstance(df, pd.DataFrame) check if it's a DataFrame → just copy it directly, if it's a Shiny reactive object → use .get() to unwrap it.

### get_authorproductionovertime.py
**Status: PASS after patching** (both sources)
**Patches applied:** Line 19: `data = df.get()` → fixed with isinstance check. Same reasons as in the previous file.

### get_averagecitations.py
**Status: PASS after patching** (both sources)
**Patches applied:** 
- Line 14: `data = df.get()` → fixed with isinstance check.
- Line 32: `current_year - table["PY"]` → TypeError. Reason: PY is stored as string in the standardized DataFrame but the function requires arithmetic subtraction which needs integers. Fix: added `pd.to_numeric(table["PY"], errors="coerce")` before the calculation.

### get_bradfordlaw.py
**Status: PASS after patching** (both sources)
**Patches applied:** 1. Line 15: `data = df.get()` → fixed with isinstance check

### get_citedcountries.py
**Status: PASS after patching** (both sources)
**Patches applied:** Line 110: `int(max_x // 10)` → ValueError: cannot convert float NaN to integer. Reason: PubMed has no affiliation data so AU1_CO is empty, x_values is empty, and x_values.max() returns NaN. int(NaN) crashes with ValueError. Fix: added safety check before plotting — if x_values is empty or max_x is NaN, return empty figure instead of crashing

### get_clusteringcoupling.py
**Status:** PASS (both sources) 
**Notes:** OpenAlex: coupling map cannot be built because CR contains URLs instead of formatted citation strings → NCS is None. PubMed: coupling map cannot be built because CR is empty from eSummary API → matrix is empty. Both cases handled gracefully, no crashes. This is a known CR field limitation, not a bug in the function.

### get_co_occurence_network.py
**Status: PASS after patching** (both sources)
**Patches applied:** field_by_year() line 425: `years = M['PY'].values` → added pd.to_numeric() conversion. Reason: PY is stored as string, np.percentile requires numeric values. Fix: `years = pd.to_numeric(M['PY'], errors='coerce').values`
**Warnings (non-blocking):**
- Line 437: `n[col_idx]` uses deprecated integer indexing on Series
  - Will break in future pandas versions
  - Fix: change to `n.iloc[col_idx]`
  - Not fixed now as it does not cause crashes in current version
 
### get_cocitation.py
**Status:** PASS (both sources) 

**Known limitations:**
- PubMed returns empty results for country analysis because eSummary API does not return affiliation data (C1 column is empty) so AU1_CO cannot be derived


---
