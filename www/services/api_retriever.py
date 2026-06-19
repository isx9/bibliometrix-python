import time
import requests

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


def fetch_pubmed_ids(query: str, total_wanted: int = 100, mindate: str = None, maxdate: str = None) -> list:
    """
    Searches PubMed for a query and returns a list of PubMed IDs (PMIDs).
    PubMed requires two steps: first get IDs, then fetch paper details.
    If mindate/maxdate are provided, restricts the search to that
    publication-date range (format: "YYYY"), so results are spread
    across multiple years instead of defaulting to the most recent ones.
    Returns a list of PMID strings.
    """
    url = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi"
    params = {
        "db": "pubmed",
        "term": query,
        "retmax": total_wanted,
        "retmode": "json"
    }
    if mindate and maxdate:
        params["datetype"] = "pdat"
        params["mindate"] = mindate
        params["maxdate"] = maxdate

    data = fetch_page(url, params)
    if data is None:
        return []
    return data["esearchresult"]["idlist"]


def fetch_pubmed(query: str, total_wanted: int = 100, mindate: str = None, maxdate: str = None) -> list:
    """
    Fetches paper details from PubMed for a given query.
    First retrieves PMIDs via fetch_pubmed_ids(), then fetches
    paper summaries in batches of 20.
    If mindate/maxdate are provided (format: "YYYY"), restricts results
    to that publication-date range.
    Returns a list of raw paper dictionaries.
    """
    ids = fetch_pubmed_ids(query=query, total_wanted=total_wanted, mindate=mindate, maxdate=maxdate)
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


def retrieve(query: str, platform: str = "openalex", total: int = 100, mindate: str = None, maxdate: str = None) -> list:
    """
    Main entry point for the API retriever.
    Takes a search query and platform selection from the user.
    Returns a list of raw paper dictionaries ready for standardizer.py.

    mindate/maxdate (format: "YYYY") are currently only applied to the
    "pubmed" platform, to spread results across a publication-year
    range instead of defaulting to the most recent ones.

    Supported platforms: "openalex", "pubmed"
    """
    if platform == "openalex":
        return fetch_openalex(query=query, total_wanted=total)
    
    elif platform == "pubmed":
        return fetch_pubmed(query=query, total_wanted=total, mindate=mindate, maxdate=maxdate)
    
    else:
        raise ValueError(f"Unsupported platform: {platform}. Choose 'openalex' or 'pubmed'.")