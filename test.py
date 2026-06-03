from www.services.api_retriever import retrieve
from www.services.standardizer import standardize
from www.services.validator import validate

# Test OpenAlex
records = retrieve(query="machine learning", platform="openalex", total=50)
df = standardize(records, source="openalex")
df = validate(df)
df.to_csv("test_openalex.csv", index=False)
print("OpenAlex CSV generato")

# Test PubMed
records = retrieve(query="machine learning", platform="pubmed", total=50)
df = standardize(records, source="pubmed")
df = validate(df)
df.to_csv("test_pubmed.csv", index=False)
print("PubMed CSV generato")