from __future__ import annotations

from app.models.schools import College
from app.schemas.school_sources import SchoolSourceRow
from app.services.imports import SchoolSourceImportService


class FakeCollegeRepository:
    def __init__(self) -> None:
        self.colleges: list[College] = []
        self.next_id = 1

    def get_by_source_keys(
        self, school_id: str | None, ipeds_id: str | None, name: str
    ) -> College | None:
        for college in self.colleges:
            if school_id and college.ncaa_school_id == school_id:
                return college
            if ipeds_id and college.ipeds_id == ipeds_id:
                return college
            if college.name == name:
                return college
        return None

    def get_or_create_by_source_keys(
        self, school_id: str | None, ipeds_id: str | None, name: str
    ) -> tuple[College, bool]:
        college = self.get_by_source_keys(school_id, ipeds_id, name)
        if college is not None:
            return college, False
        college = College(id=self.next_id, name=name, ncaa_school_id=school_id, ipeds_id=ipeds_id)
        self.next_id += 1
        self.colleges.append(college)
        return college, True


def test_school_source_import_service_creates_and_updates_colleges() -> None:
    repository = FakeCollegeRepository()
    service = SchoolSourceImportService(colleges=repository)  # type: ignore[arg-type]

    first_summary = service.import_rows(
        [
            SchoolSourceRow(
                school_id="S1",
                ipeds_id="1001",
                school_name="Example State",
                city="Example City",
                state="TX",
                public_private="Public",
                division="NCAA D1",
                conference="Example Conf",
                roster_url="https://example.edu/sports/baseball/roster",
                roster_vendor="sidearm",
                is_sidearm=True,
                import_enabled=True,
            )
        ]
    )
    second_summary = service.import_rows(
        [
            SchoolSourceRow(
                school_id="S1",
                ipeds_id="1001",
                school_name="Example State University",
                city="Example City",
                state="TX",
                public_private="Public",
                division="NCAA D1",
                conference="Example Conference",
                roster_url="https://example.edu/sports/baseball/roster",
                roster_vendor="sidearm",
                is_sidearm=True,
                import_enabled=True,
                notes="verified",
            )
        ]
    )

    assert first_summary.colleges_created == 1
    assert second_summary.colleges_updated == 1
    assert len(repository.colleges) == 1
    assert repository.colleges[0].name == "Example State University"
    assert repository.colleges[0].conference == "Example Conference"
    assert repository.colleges[0].source_notes == "verified"
