from __future__ import annotations

from app.models.schools import College, HighSchool
from app.repositories.base import Repository


class CollegeRepository(Repository[College]):
    def get(self, college_id: int) -> College | None:
        return self.session.get(College, college_id)

    def add(self, college: College) -> College:
        self.session.add(college)
        return college


class HighSchoolRepository(Repository[HighSchool]):
    def get(self, high_school_id: int) -> HighSchool | None:
        return self.session.get(HighSchool, high_school_id)

    def add(self, high_school: HighSchool) -> HighSchool:
        self.session.add(high_school)
        return high_school
