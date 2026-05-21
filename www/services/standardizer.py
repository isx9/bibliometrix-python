"""
This takes raw data from any source and standardise it, whether data came from a file or the API.
This file detects which sourse it is (e.g. Scopus, PubMed, OpenAlex, etc.), renames the columns to WoS tags using mapping dictionaries,
splits strings into lists, replaces missing values with valid defaults ([] or ""), and computes the SR (Short Reference) field required for
bibliometric analysis.
"""
