from __future__ import annotations

from sqlalchemy.orm import Session

from app.models.people import Coach, Person, Player
from app.repositories.base import Repository


class PersonRepository(Repository[Person]):
    def get(self, person_id: int) -> Person | None:
        return self.session.get(Person, person_id)

    def add(self, person: Person) -> Person:
        self.session.add(person)
        return person

    def get_or_create_by_full_name(
        self, full_name: str, first_name: str | None = None, last_name: str | None = None
    ) -> tuple[Person, bool]:
        person = Person(first_name=first_name, last_name=last_name, full_name=full_name)
        self.session.add(person)
        self.session.flush()
        return person, True


class PlayerRepository(Repository[Player]):
    def get(self, player_id: int) -> Player | None:
        return self.session.get(Player, player_id)

    def add(self, player: Player) -> Player:
        self.session.add(player)
        return player

    def create_for_person(
        self,
        person: Person,
        bats: str | None = None,
        throws: str | None = None,
        height_inches: int | None = None,
        weight_lbs: int | None = None,
        hometown_city: str | None = None,
        hometown_state: str | None = None,
        hometown_country: str | None = None,
    ) -> Player:
        player = Player(
            person=person,
            bats=bats,
            throws=throws,
            height_inches=height_inches,
            weight_lbs=weight_lbs,
            hometown_city=hometown_city,
            hometown_state=hometown_state,
            hometown_country=hometown_country,
        )
        self.session.add(player)
        self.session.flush()
        return player


class CoachRepository(Repository[Coach]):
    def get(self, coach_id: int) -> Coach | None:
        return self.session.get(Coach, coach_id)

    def add(self, coach: Coach) -> Coach:
        self.session.add(coach)
        return coach


def build_person_repository(session: Session) -> PersonRepository:
    return PersonRepository(session)
