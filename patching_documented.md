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
     - 

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


To add:
- CR matrix is empty for both sources → coupling map cannot 
  be built





---



## Functions

### get_annualproduction.py
**Status:** PASS (OpenAlex, PubMed)  
**Patches applied:** PY forced to int safely

---
