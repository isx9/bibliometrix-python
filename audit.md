# Bibliometrix-Python Codebase Audit

## Purpose
This document maps every file in services/ and functions/ to the columns it depends on and any hardcoded WoS logic it contains.
It is used to verify that our ETL pipeline produces all required columns and to track which files need patching.

---

## www/services/
- what it does
- issues found
- relevant for ETL: yes/no

### biblionetwork.py
...

### cocmatrix.py
...

(etc. for all files)

---

## functions/
- what it does
- breaks on non-WoS data: yes/no
- why it breaks (e.g. hardcoded column name "WoS")
- needs patching: yes/no

### get_annualproduction.py
...

(etc. for all files)

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

