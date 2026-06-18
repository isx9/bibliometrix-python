import time
import requests
import xml.etree.ElementTree as ET

def fetch_page(url: str, params: dict, retries: int = 3):
    """
    Sends a single HTTP GET request to the given URL with the given params.
    Retries up to 3 times if the request fails or returns a 429 error.
    Returns the JSON response as a dictionary, or None if all retries fail.
    """
    for attempt in range(retries):
        response = requests.get(url, params=params)
        
        if response.status_code == 200:
            return response.json()
        
        elif response.status_code == 429:
            print(f"Rate limited. Waiting before retry {attempt + 1}...")
            time.sleep(2)
        
        else:
            print(f"Error {response.status_code}. Retrying...")
            time.sleep(1)
    
    return None


def fetch_page_xml(url: str, params: dict, retries: int = 3):
    """
    Sends a single HTTP GET request expecting an XML response.
    Retries up to 3 times if the request fails or returns a 429 error.
    Returns the raw XML text, or None if all retries fail.
    """
    for attempt in range(retries):
        response = requests.get(url, params=params)

        if response.status_code == 200:
            return response.text

        elif response.status_code == 429:
            print(f"Rate limited. Waiting before retry {attempt + 1}...")
            time.sleep(2)

        else:
            print(f"Error {response.status_code}. Retrying...")
            time.sleep(1)

    return None


def fetch_openalex(query: str, total_wanted: int = 100, per_page: int = 25) -> list:
    """
    Fetches multiple pages of results from the OpenAlex API.
    Loops through pages until the desired number of results is reached.
    Returns a list of raw paper dictionaries.
    """
    url = "https://api.openalex.org/works"
    all_results = []
    page = 1

    while len(all_results) < total_wanted:
        params = {
            "search": query,
            "per-page": per_page,
            "page": page
        }
        data = fetch_page(url, params)
        if data is None:
            print("Failed to fetch page. Stopping.")
            break
        all_results.extend(data["results"])
        page += 1
        time.sleep(0.5)

    return all_results[:total_wanted]


def fetch_pubmed_ids(query: str, total_wanted: int = 100) -> list:
    """
    Searches PubMed for a query and returns a list of PubMed IDs (PMIDs).
    PubMed requires two steps: first get IDs, then fetch paper details.
    Returns a list of PMID strings.
    """
    url = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi"
    params = {
        "db": "pubmed",
        "term": query,
        "retmax": total_wanted,
        "retmode": "json"
    }
    data = fetch_page(url, params)
    if data is None:
        return []
    return data["esearchresult"]["idlist"]


def fetch_pubmed(query: str, total_wanted: int = 100) -> list:
    """
    Fetches paper details from PubMed for a given query using the
    eSummary endpoint (lightweight metadata: title, journal, authors,
    dates, IDs).

    NOTE: eSummary does not return abstracts, affiliations, keywords,
    MeSH headings, or reference lists. Use fetch_pubmed_efetch() for
    that richer data — standardizer.py merges both sources together.

    First retrieves PMIDs via fetch_pubmed_ids(), then fetches
    paper summaries in batches of 20.
    Returns a list of raw paper dictionaries.
    """
    ids = fetch_pubmed_ids(query=query, total_wanted=total_wanted)
    if not ids:
        print("No PubMed IDs found. Stopping.")
        return []

    url = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esummary.fcgi"
    all_results = []
    batch_size = 20

    for i in range(0, len(ids), batch_size):
        batch = ids[i:i + batch_size]
        params = {
            "db": "pubmed",
            "id": ",".join(batch),
            "retmode": "json"
        }
        data = fetch_page(url, params)
        if data is None:
            print("Failed to fetch batch. Skipping.")
            continue
        
        for pmid in batch:
            if pmid in data["result"]:
                all_results.append(data["result"][pmid])
        
        time.sleep(0.5)

    return all_results[:total_wanted]


def _parse_pubmed_article_xml(article_elem) -> dict:
    """
    Parses a single <PubmedArticle> XML element into a flat dictionary
    of the fields not available from eSummary: abstract, affiliations,
    author keywords, MeSH headings, and references (when present).

    Returns a dict with keys: pmid, abstract, affiliations (list),
    keywords (list), mesh_headings (list), references (list).
    """
    result = {
        "pmid": "",
        "abstract": "",
        "affiliations": [],
        "keywords": [],
        "mesh_headings": [],
        "references": []
    }

    pmid_elem = article_elem.find(".//MedlineCitation/PMID")
    if pmid_elem is not None and pmid_elem.text:
        result["pmid"] = pmid_elem.text.strip()

    # Abstract — may have multiple AbstractText blocks (structured abstracts)
    abstract_texts = article_elem.findall(".//Article/Abstract/AbstractText")
    if abstract_texts:
        parts = []
        for ab in abstract_texts:
            label = ab.get("Label", "")
            text = (ab.text or "").strip()
            if not text:
                continue
            parts.append(f"{label}: {text}" if label else text)
        result["abstract"] = " ".join(parts)

    # Affiliations — one or more per author, deduplicated
    affiliations = article_elem.findall(".//AuthorList/Author/AffiliationInfo/Affiliation")
    seen = set()
    for aff in affiliations:
        text = (aff.text or "").strip()
        if text and text not in seen:
            seen.add(text)
            result["affiliations"].append(text)

    # Author keywords — not always present, depends on the journal
    keywords = article_elem.findall(".//KeywordList/Keyword")
    for kw in keywords:
        text = (kw.text or "").strip()
        if text:
            result["keywords"].append(text)

    # MeSH headings — editorially assigned subject terms (NLM controlled
    # vocabulary). Conceptually closer to WoS's KeywordsPlus (ID) than to
    # author keywords (DE), since both are externally-assigned rather
    # than author-chosen. See standardizer.py for the mapping decision.
    mesh_headings = article_elem.findall(".//MeshHeadingList/MeshHeading/DescriptorName")
    for mesh in mesh_headings:
        text = (mesh.text or "").strip()
        if text:
            result["mesh_headings"].append(text)

    # References — only present for a subset of records (mostly those
    # linked to PMC full text). Most PubMed records will have none.
    references = article_elem.findall(".//PubmedData/ReferenceList/Reference/Citation")
    for ref in references:
        text = (ref.text or "").strip()
        if text:
            result["references"].append(text)

    return result


def fetch_pubmed_efetch(ids: list) -> dict:
    """
    Fetches full PubmedArticle XML records via the eFetch endpoint for
    the given list of PMIDs, in batches of 20.

    Unlike eSummary, eFetch returns the full MEDLINE record, including
    abstracts, author affiliations, author keywords (when submitted),
    MeSH headings, and reference lists (when linked to PMC full text).

    Returns a dict mapping PMID (str) -> parsed fields dict (see
    _parse_pubmed_article_xml for the structure). PMIDs that fail to
    parse or are missing from the response are simply absent from the
    returned dict; callers should use .get(pmid, {}) defensively.
    """
    if not ids:
        return {}

    url = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi"
    batch_size = 20
    results = {}

    for i in range(0, len(ids), batch_size):
        batch = ids[i:i + batch_size]
        params = {
            "db": "pubmed",
            "id": ",".join(batch),
            "rettype": "abstract",
            "retmode": "xml"
        }
        xml_text = fetch_page_xml(url, params)
        if xml_text is None:
            print("Failed to fetch eFetch batch. Skipping.")
            continue

        try:
            root = ET.fromstring(xml_text)
        except ET.ParseError:
            print("Failed to parse eFetch XML batch. Skipping.")
            continue

        for article in root.findall(".//PubmedArticle"):
            parsed = _parse_pubmed_article_xml(article)
            pmid = parsed.get("pmid", "")
            if pmid:
                results[pmid] = parsed

        time.sleep(0.5)

    return results

def fetch_pubmed_icite(ids: list) -> dict:
    """
    Fetches citation counts for the given list of PMIDs from NIH's iCite
    API, in batches of 200.

    PubMed's own eSummary/eFetch endpoints never report how many times a
    paper has been cited — MEDLINE's data model doesn't track inbound
    citations at all. iCite is a separate NIH service that computes
    citation counts for PubMed-indexed papers, so it's used here purely
    to backfill TC, not to replace any bibliographic metadata already
    coming from eSummary/eFetch.

    Returns a dict mapping PMID (str) -> citation_count (int). PMIDs
    missing from the response (e.g. pre-1995 papers, or papers iCite
    hasn't indexed yet) are simply absent; callers should use
    .get(pmid, 0) defensively.
    """
    if not ids:
        return {}

    url = "https://icite.od.nih.gov/api/pubs"
    batch_size = 200
    results = {}

    for i in range(0, len(ids), batch_size):
        batch = ids[i:i + batch_size]
        params = {
            "pmids": ",".join(batch),
            "fl": "pmid,citation_count"
        }
        data = fetch_page(url, params)
        print("ICITE RAW PARAMS:", params)
        print("ICITE RAW RESPONSE TYPE:", type(data))
        print("ICITE RAW RESPONSE SAMPLE:", str(data)[:800])
        if data is None:
            print("Failed to fetch iCite batch. Skipping.")
            continue

        pubs = data.get("data", data) if isinstance(data, dict) else data
        for pub in pubs:
            pmid = str(pub.get("pmid", ""))
            if pmid:
                results[pmid] = pub.get("citation_count", 0) or 0

        time.sleep(0.5)

    return results

def retrieve(query: str, platform: str = "openalex", total: int = 100) -> list:
    """
    Main entry point for the API retriever.
    Takes a search query and platform selection from the user.
    Returns a list of raw paper dictionaries ready for standardizer.py.

    For PubMed, this fetches both eSummary (lightweight metadata) and
    eFetch (full XML: abstract, affiliations, keywords, MeSH, references)
    and merges them per-record under an "_efetch" key, so standardizer.py
    can draw on the richer fields without duplicating the retrieval logic.

    Supported platforms: "openalex", "pubmed"
    """
    if platform == "openalex":
        return fetch_openalex(query=query, total_wanted=total)
    
    elif platform == "pubmed":
        summary_results = fetch_pubmed(query=query, total_wanted=total)
        if not summary_results:
            return []

        ids = [record.get("uid", "") for record in summary_results if record.get("uid", "")]
        efetch_data = fetch_pubmed_efetch(ids)

        icite_data = fetch_pubmed_icite(ids)
        print("ICITE DEBUG:", len(ids), "PMIDs sent,", len(icite_data), "matched. Sample:", list(icite_data.items())[:3])

        for record in summary_results:
            pmid = record.get("uid", "")
            record["_efetch"] = efetch_data.get(pmid, {})
            record["_icite_tc"] = icite_data.get(pmid, 0)

        return summary_results
    
    else:
        raise ValueError(f"Unsupported platform: {platform}. Choose 'openalex' or 'pubmed'.")
