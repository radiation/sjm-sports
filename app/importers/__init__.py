"""Importer boundary.

Importers transform scraped pages, CSV rows, spreadsheets, or future source records into
application-level commands and call services to persist data. They should not use SQLAlchemy
sessions directly.
"""
