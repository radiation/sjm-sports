from __future__ import annotations

from sqlalchemy import func, select

from app.models.schools import College, HighSchool
from app.repositories.base import Repository


class CollegeRepository(Repository[College]):
    def get(self, college_id: int) -> College | None:
        return self.session.get(College, college_id)

    def add(self, college: College) -> College:
        self.session.add(college)
        return college

    def count_all(self) -> int:
        return self.session.scalar(select(func.count(College.id))) or 0

    def get_by_name(self, name: str) -> College | None:
        return self.session.scalar(select(College).where(College.name == name))

    def get_or_create_by_name(self, name: str) -> tuple[College, bool]:
        college = self.get_by_name(name)
        if college is not None:
            return college, False

        college = College(name=name)
        self.session.add(college)
        self.session.flush()
        return college, True


class HighSchoolRepository(Repository[HighSchool]):
    def get(self, high_school_id: int) -> HighSchool | None:
        return self.session.get(HighSchool, high_school_id)

    def add(self, high_school: HighSchool) -> HighSchool:
        self.session.add(high_school)
        return high_school

    def get_by_identity(
        self, name: str, city: str | None, state: str | None, country: str | None
    ) -> HighSchool | None:
        return self.session.scalar(
            select(HighSchool).where(
                HighSchool.name == name,
                HighSchool.city == city,
                HighSchool.state == state,
                HighSchool.country == country,
            )
        )

    def get_or_create_by_identity(
        self, name: str, city: str | None, state: str | None, country: str | None
    ) -> tuple[HighSchool, bool]:
        high_school = self.get_by_identity(name, city, state, country)
        if high_school is not None:
            return high_school, False

        high_school = HighSchool(name=name, city=city, state=state, country=country)
        self.session.add(high_school)
        self.session.flush()
        return high_school, True
