"""
This is a quality control module for the ETL pipeline, 
it runs after standardizer.py to verify the output is correct before it reaches the dashboard.

Responsibilities:
- Confirm all mandatory WoS columns exist;
- Confirm no NaN or None values remain;
- Confirm list fields (AU, CR, DE etc.) are actual lists;
- Raise a clear, descriptive error if anything is wrong.

This represents the last checkpoint, if validator.py passes then the DataFrame is safe to use.
"""
