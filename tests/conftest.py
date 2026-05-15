from __future__ import annotations

import os

import pytest


def pytest_collection_modifyitems(items: list[pytest.Item]) -> None:
    if os.getenv("SJM_RUN_DB_TESTS") == "1":
        return

    skip_db = pytest.mark.skip(reason="set SJM_RUN_DB_TESTS=1 to run database-dependent tests")
    for item in items:
        if "requires_db" in item.keywords:
            item.add_marker(skip_db)
