
from www.services import *


def get_main_informations(df, log=False):
    """
    Calculate various filters and metrics for the DataFrame.
    """

    data = df.get()

    #### Min and Max Year ####
    start_time = time.time()

    data["PY"] = pd.to_numeric(
        data["PY"],
        errors="coerce"
    )

    data["Min_Year"] = data["PY"].min()
    data["Max_Year"] = data["PY"].max()

    print(
        f"Min and Max Year calculation time: "
        f"{time.time() - start_time:.4f} seconds"
    )

    #### Unique Sources ####
    start_time = time.time()

    data["SO"] = data["SO"].fillna("").astype(str)

    data["Unique_SO"] = data["SO"].nunique()

    print(
        f"Unique Sources calculation time: "
        f"{time.time() - start_time:.4f} seconds"
    )

    #### Annual Growth Rate (CAGR) ####
    start_time = time.time()

    publications_per_year = (
        data["PY"]
        .dropna()
        .value_counts()
        .sort_index()
    )

    ny = data["PY"].max() - data["PY"].min()

    if (
        len(publications_per_year) > 1
        and ny > 0
        and publications_per_year.iloc[0] > 0
    ):

        cagr = round(
            (
                (
                    publications_per_year.iloc[-1]
                    /
                    publications_per_year.iloc[0]
                ) ** (1 / ny) - 1
            ) * 100,
            2
        )

    else:
        cagr = 0

    data["CAGR"] = cagr

    print(
        f"CAGR calculation time: "
        f"{time.time() - start_time:.4f} seconds"
    )

    #### Unique Authors ####
    start_time = time.time()

    if "AU" not in data.columns:
        data["AU"] = [[]]

    data["AU"] = data["AU"].apply(
        lambda x: x if isinstance(x, list) else []
    )

    AU_list = data["AU"]

    listAU = [
        author
        for sublist in AU_list
        for author in sublist
        if author
    ]

    listAU = list(set(listAU))

    if log:

        with open(
            "authors_list.txt",
            "w",
            encoding="utf-8"
        ) as file:

            for authors in listAU:
                file.write(f"{authors}\n")

    count_AU = len(listAU)

    data["Unique_AU"] = count_AU

    print(
        f"Unique Authors calculation time: "
        f"{time.time() - start_time:.4f} seconds"
    )

    #### Authors of single-authored docs ####
    start_time = time.time()

    def count_authors(entry):

        if isinstance(entry, list):
            return len(entry)

        elif isinstance(entry, str):
            return len(entry.split(';'))

        else:
            return 0

    nAU = data['AU'].apply(count_authors)

    single_authored_docs = len(
        data[nAU == 1]['AU']
        .apply(
            lambda x:
            x[0]
            if isinstance(x, list) and len(x) > 0
            else ""
        )
        .unique()
    )

    data["Authors_of_single_authored_docs"] = (
        single_authored_docs
    )

    print(
        f"Authors of single-authored docs calculation time: "
        f"{time.time() - start_time:.4f} seconds"
    )

    #### International Co-Authorship ####
    start_time = time.time()

    if "AU_CO" not in data.columns:

        data = metaTagExtraction(df, "AU_CO")

    data["AU_CO"] = data["AU_CO"].apply(
        lambda x: x if isinstance(x, list) else []
    )

    data["Country_Count"] = data["AU_CO"].apply(
        lambda x: len(set(x))
    )

    coll = data[
        data["Country_Count"] > 1
    ].shape[0]

    if data.shape[0] > 0:
        data["International_Co_Authorship"] = (
            100 * coll / data.shape[0]
        )
    else:
        data["International_Co_Authorship"] = 0

    if log:

        with open(
            "international_co_authorship.txt",
            "w",
            encoding="utf-8"
        ) as file:

            for row in data["AU_CO"]:
                file.write(f"{row}\n")

    print(
        f"International Co-Authorship calculation time: "
        f"{time.time() - start_time:.4f} seconds"
    )

    #### Co-Authors per Doc ####
    start_time = time.time()

    data["Co_Authors_per_Doc"] = round(
        nAU.mean(),
        2
    )

    print(
        f"Co-Authors per Doc calculation time: "
        f"{time.time() - start_time:.4f} seconds"
    )

    #### Author Keywords (DE) ####
    start_time = time.time()

    if "DE" not in data.columns:
        data["DE"] = [[]]

    data["DE"] = data["DE"].apply(
        lambda x: x if isinstance(x, list) else []
    )

    DE = pd.Series([
        item.upper()
        for sublist in data["DE"]
        for item in sublist
    ])

    DE = (
        DE.str.replace(
            r"\s+|\.|,",
            " ",
            regex=True
        )
        .str.strip()
        .unique()
    )

    DE = DE[~pd.isna(DE)]

    DE = DE[DE != "NAN"]

    if log:

        with open(
            "unique_keywords.txt",
            "w",
            encoding="utf-8"
        ) as file:

            for keyword in DE:
                file.write(f"{keyword}\n")

    data["Authors_Keywords_DE"] = len(DE)

    print(
        f"Author's Keywords (DE) calculation time: "
        f"{time.time() - start_time:.4f} seconds"
    )

    #### References per Doc ####
    start_time = time.time()

    if "CR" not in data.columns:
        data["CR"] = [[]]

    data["CR"] = data["CR"].apply(
        lambda x: x if isinstance(x, list) else []
    )

    CR = pd.Series([
        item.upper()
        for sublist in data["CR"]
        for item in sublist
    ])

    CR = (
        CR.str.replace(
            r"\s+|\|,",
            " ",
            regex=True
        )
        .str.strip()
        .unique()
    )

    CR = CR[~pd.isna(CR)]

    if log:

        with open(
            "unique_references.txt",
            "w",
            encoding="utf-8"
        ) as file:

            for reference in CR:
                file.write(f"{reference}\n")

    nCR = len(CR)

    if nCR == 1:
        nCR = 0

    data["References_per_Doc"] = nCR

    print(
        f"References per Doc calculation time: "
        f"{time.time() - start_time:.4f} seconds"
    )

    #### Document Average Age ####
    start_time = time.time()

    current_year = pd.Timestamp.now().year

    data["Document_Age"] = (
        current_year - data["PY"]
    )

    data["Document_Average_Age"] = round(
        data["Document_Age"].mean(),
        2
    )

    print(
        f"Document Average Age calculation time: "
        f"{time.time() - start_time:.4f} seconds"
    )

    #### Average citations per doc ####
    start_time = time.time()

    data["TC"] = pd.to_numeric(
        data["TC"],
        errors="coerce"
    ).fillna(0)

    data["Average_Citations_per_Doc"] = round(
        data["TC"].mean(),
        2
    )

    print(
        f"Average citations per doc calculation time: "
        f"{time.time() - start_time:.4f} seconds"
    )

    return data