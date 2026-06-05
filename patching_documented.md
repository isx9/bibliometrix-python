# Patching Documentation

## Services

### biblionetwork.py
**Status:** PASS (all 16 combinations)  
**Patches applied:** ...  
**Known limitations:**
- AU_CO missing → needs metaTagExtraction first
- TI_TM, AB_TM missing → derived columns, need term extraction
- CR_AU, CR_SO missing → need metaTagExtraction first
These are all columns that the ETL pipeline doesn't produce directly, they need an extra processing step after the standardization.
The question is whether that step works correctly for OpenAlex and PubMed data, which leads to fixing metatagextraction.py first, if needed-

---

## Functions

### get_annualproduction.py
**Status:** PASS (OpenAlex, PubMed)  
**Patches applied:** PY forced to int safely

---
