from __future__ import annotations


class ImportService:
    """Future importer-facing workflow service.

    Importers should normalize source records and call service methods here instead of using
    SQLAlchemy sessions or repositories directly.
    """
