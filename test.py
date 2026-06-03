from www.services.api_retriever import retrieve
from www.services.standardizer import standardize
from www.services.validator import validate

# Test OpenAlex
records = retrieve(query="machine learning", platform="openalex", total=50)
df = standardize(records, source="openalex")
df = validate(df)
print(df.head())
df.to_csv("test_openalex.csv", index=False)
print("OpenAlex CSV generato")

# Test OpenAlex (200 record)
records = retrieve(query="machine learning", platform="openalex", total=200)
df = standardize(records, source="openalex")
df = validate(df)
print(df.head())
df.to_csv("test_openalex_200.csv", index=False)
print("OpenAlex CSV 200 generato")

# Test PubMed
records = retrieve(query="machine learning", platform="pubmed", total=50)
df = standardize(records, source="pubmed")
df = validate(df)
print(df.head())
df.to_csv("test_pubmed.csv", index=False)
print("PubMed CSV generato")