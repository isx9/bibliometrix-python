""" 
Retrieves raw bibliographic data from external APIs (OpenAlex and PubMed) based on a user-provided query.
It needs to:

- Send HTTP requests to the selected API endpoint;
- Handle pagination to retrieve all available results;
- Respect rate limits and retry on failure;
- Return raw data ready for standardizer.py to process.

This module knows nothing about columns or WoS schema, its only job is fetching raw data from the internet.
"""
