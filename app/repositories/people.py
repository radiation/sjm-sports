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


class PlayerRepository(Repository[Player]):
    def get(self, player_id: int) -> Player | None:
        return self.session.get(Player, player_id)

    def add(self, player: Player) -> Player:
        self.session.add(player)
        return player


class CoachRepository(Repository[Coach]):
    def get(self, coach_id: int) -> Coach | None:
        return self.session.get(Coach, coach_id)

    def add(self, coach: Coach) -> Coach:
        self.session.add(coach)
        return coach


def build_person_repository(session: Session) -> PersonRepository:
    return PersonRepository(session)
