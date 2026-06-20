# OpenAlex Data-Characteristic Limitations

This document records dashboard behaviors that stem from inherent gaps between OpenAlex's data model and the Web of Science (WoS) schema the dashboard was originally built for, rather than from bugs in the ETL pipeline or dashboard code.

## Keywords Plus (`ID`) — structurally absent from OpenAlex

OpenAlex has no equivalent of WoS's proprietary Keywords Plus algorithm, so the `ID` field is populated as an empty list for every record (consistent with PubMed, where it is equally absent). This propagates into every panel that depends on `ID` as a text source:

- Most Frequent Words
- WordCloud
- TreeMap
- Words' Frequency over Time
- Trend Topics
- Co-occurrence Network
- Thematic Map
- Thematic Evolution
- Factorial Approach

All of the above return empty results when Keywords Plus is selected as the field. This is not a processing failure, there is no underlying text to analyze.

## Subject Categories (`WC`) — no OpenAlex equivalent exists

Unlike `ID`, which is explicitly created and filled with an empty value, `WC` is never added to the standardized schema for OpenAlex at all, since WoS-style subject category classification has no corresponding field in either source API. Selecting Subject Categories in Most Frequent Words / WordCloud / TreeMap surfaces a raw error rather than a graceful empty result, because the absent column is accessed directly rather than checked for first.

## Author Institutions (`AU_UN`) — affiliation string format incompatible with WoS-style parsing

Collaboration Network produces no output when Field is set to Institutions. The institution-extraction logic scans comma-separated segments of the affiliation string for WoS-convention tags (e.g. `UNIV`, `INST`, `COLL`); OpenAlex's `raw_affiliation_strings` don't follow that same comma-segmented structure, so the heuristic largely fails to isolate clean institution names. This is the same underlying affiliation-format mismatch already documented for author-country extraction, just manifesting in a different downstream feature.

# PubMed Data-Characteristic Limitations

This document records dashboard behaviors that stem from inherent gaps between what PubMed's API returns and the Web of Science (WoS) schema the dashboard was originally built for, rather than from bugs in the ETL pipeline or dashboard code.

## Cited References (`CR`) — recovered for only a small fraction of records

PubMed's reference list is captured for roughly 7.5% of records in the 200-row test sample. Every analysis that depends on matching cited references within the sample itself, rather than simply storing them, is sensitive to this sparsity:
- Sources' Local Impact
- Most Local Cited Authors
- Authors' Local Impact
- Co-citation Network
- Cluster by Coupling
- Historiograph
- Three-Field Plot (when Cited Sources is selected)
With so few within-sample citation links available, these panels have nothing to build a network or score from. This is not a processing failure, there is no underlying reference data to match against.

## Keywords Plus (`ID`) — structurally absent from PubMed

PubMed has no equivalent of WoS's proprietary Keywords Plus algorithm, so the `ID` field is populated as an empty list for every record (consistent with OpenAlex, where it is equally absent). This propagates into every panel that depends on `ID` as a text source:
- Most Frequent Words
- WordCloud
- TreeMap
- Words' Frequency over Time
- Co-occurrence Network
- Thematic Map
- Factorial Approach
- Historiograph
- Three-Field Plot (when Keywords Plus is selected)
All of the above return empty results when Keywords Plus is selected as the field. This is not a processing failure, there is no underlying text to analyze.

## Publication Year (`PY`) distribution — narrow and skewed in the test sample
Thematic Evolution produces no output for any field, including Titles, which is fully populated text-wise. The 200-row test sample spans only 4 distinct publication years (2023–2026), with 139 of the 200 rows concentrated in 2024 alone, leaving the year-binning step without enough spread across periods to form usable time slices. This is a property of the test sample's composition rather than a defect in the field content or the binning logic itself.
