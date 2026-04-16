"""
Worker application for Polymarket data ingestion.

This worker will:
- Fetch market data from Polymarket API
- Process and transform the data
- Ingest into PostgreSQL via shared models
"""

