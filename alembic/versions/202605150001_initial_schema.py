"""initial schema

Revision ID: 202605150001
Revises:
Create Date: 2026-05-15 00:00:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "202605150001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def timestamp_columns() -> list[sa.Column[sa.DateTime]]:
    return [
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
    ]


def upgrade() -> None:
    op.create_table(
        "people",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("first_name", sa.String(length=100), nullable=True),
        sa.Column("last_name", sa.String(length=100), nullable=True),
        sa.Column("full_name", sa.String(length=200), nullable=False),
        *timestamp_columns(),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_people")),
    )
    op.create_index(op.f("ix_people_full_name"), "people", ["full_name"], unique=False)

    op.create_table(
        "colleges",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("state", sa.String(length=100), nullable=True),
        sa.Column("division", sa.String(length=50), nullable=True),
        sa.Column("conference", sa.String(length=100), nullable=True),
        sa.Column("ncaa_school_id", sa.String(length=50), nullable=True),
        sa.Column("ipeds_id", sa.String(length=50), nullable=True),
        sa.Column("roster_url", sa.Text(), nullable=True),
        sa.Column("staff_url", sa.Text(), nullable=True),
        *timestamp_columns(),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_colleges")),
        sa.UniqueConstraint("ipeds_id", name=op.f("uq_colleges_ipeds_id")),
        sa.UniqueConstraint("name", name=op.f("uq_colleges_name")),
        sa.UniqueConstraint("ncaa_school_id", name=op.f("uq_colleges_ncaa_school_id")),
    )
    op.create_index(op.f("ix_colleges_conference"), "colleges", ["conference"], unique=False)
    op.create_index(op.f("ix_colleges_division"), "colleges", ["division"], unique=False)
    op.create_index(op.f("ix_colleges_name"), "colleges", ["name"], unique=False)
    op.create_index(op.f("ix_colleges_state"), "colleges", ["state"], unique=False)

    op.create_table(
        "high_schools",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("city", sa.String(length=100), nullable=True),
        sa.Column("state", sa.String(length=100), nullable=True),
        sa.Column("country", sa.String(length=100), nullable=True),
        *timestamp_columns(),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_high_schools")),
    )
    op.create_index(op.f("ix_high_schools_name"), "high_schools", ["name"], unique=False)
    op.create_index(op.f("ix_high_schools_state"), "high_schools", ["state"], unique=False)

    op.create_table(
        "positions",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("code", sa.String(length=50), nullable=False),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("position_type", sa.String(length=20), nullable=False),
        sa.Column("position_group", sa.String(length=50), nullable=True),
        *timestamp_columns(),
        sa.CheckConstraint(
            "position_type in ('player', 'coach')", name=op.f("ck_positions_valid_position_type")
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_positions")),
        sa.UniqueConstraint("code", "position_type", name="uq_positions_code_position_type"),
    )
    op.create_index(op.f("ix_positions_name"), "positions", ["name"], unique=False)
    op.create_index(
        op.f("ix_positions_position_group"), "positions", ["position_group"], unique=False
    )
    op.create_index(
        op.f("ix_positions_position_type"), "positions", ["position_type"], unique=False
    )

    op.create_table(
        "scrape_runs",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("year", sa.Integer(), nullable=False),
        sa.Column("source", sa.String(length=100), nullable=False),
        sa.Column(
            "started_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("status", sa.String(length=50), nullable=False),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_scrape_runs")),
    )
    op.create_index(op.f("ix_scrape_runs_source"), "scrape_runs", ["source"], unique=False)
    op.create_index(op.f("ix_scrape_runs_status"), "scrape_runs", ["status"], unique=False)
    op.create_index(op.f("ix_scrape_runs_year"), "scrape_runs", ["year"], unique=False)

    op.create_table(
        "players",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("person_id", sa.Integer(), nullable=False),
        sa.Column("bats", sa.String(length=10), nullable=True),
        sa.Column("throws", sa.String(length=10), nullable=True),
        sa.Column("height_inches", sa.Integer(), nullable=True),
        sa.Column("weight_lbs", sa.Integer(), nullable=True),
        sa.Column("hometown_city", sa.String(length=100), nullable=True),
        sa.Column("hometown_state", sa.String(length=100), nullable=True),
        sa.Column("hometown_country", sa.String(length=100), nullable=True),
        *timestamp_columns(),
        sa.ForeignKeyConstraint(
            ["person_id"], ["people.id"], name=op.f("fk_players_person_id_people")
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_players")),
        sa.UniqueConstraint("person_id", name=op.f("uq_players_person_id")),
    )
    op.create_index(op.f("ix_players_hometown_state"), "players", ["hometown_state"], unique=False)
    op.create_index(op.f("ix_players_person_id"), "players", ["person_id"], unique=False)

    op.create_table(
        "coaches",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("person_id", sa.Integer(), nullable=False),
        *timestamp_columns(),
        sa.ForeignKeyConstraint(
            ["person_id"], ["people.id"], name=op.f("fk_coaches_person_id_people")
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_coaches")),
        sa.UniqueConstraint("person_id", name=op.f("uq_coaches_person_id")),
    )
    op.create_index(op.f("ix_coaches_person_id"), "coaches", ["person_id"], unique=False)

    op.create_table(
        "scrape_pages",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("scrape_run_id", sa.Integer(), nullable=False),
        sa.Column("college_id", sa.Integer(), nullable=True),
        sa.Column("url", sa.Text(), nullable=False),
        sa.Column("page_type", sa.String(length=50), nullable=False),
        sa.Column("status_code", sa.Integer(), nullable=True),
        sa.Column(
            "fetched_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column("content_hash", sa.String(length=128), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(
            ["college_id"], ["colleges.id"], name=op.f("fk_scrape_pages_college_id_colleges")
        ),
        sa.ForeignKeyConstraint(
            ["scrape_run_id"],
            ["scrape_runs.id"],
            name=op.f("fk_scrape_pages_scrape_run_id_scrape_runs"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_scrape_pages")),
    )
    op.create_index(
        op.f("ix_scrape_pages_college_id"), "scrape_pages", ["college_id"], unique=False
    )
    op.create_index(
        op.f("ix_scrape_pages_content_hash"), "scrape_pages", ["content_hash"], unique=False
    )
    op.create_index(op.f("ix_scrape_pages_page_type"), "scrape_pages", ["page_type"], unique=False)
    op.create_index(
        op.f("ix_scrape_pages_scrape_run_id"), "scrape_pages", ["scrape_run_id"], unique=False
    )

    op.create_table(
        "player_rosters",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("player_id", sa.Integer(), nullable=False),
        sa.Column("college_id", sa.Integer(), nullable=False),
        sa.Column("year", sa.Integer(), nullable=False),
        sa.Column("roster_year", sa.String(length=50), nullable=True),
        sa.Column("normalized_roster_year", sa.String(length=50), nullable=True),
        sa.Column("primary_position_id", sa.Integer(), nullable=True),
        sa.Column("positions_raw", sa.String(length=100), nullable=True),
        sa.Column("high_school_id", sa.Integer(), nullable=True),
        sa.Column("previous_college_id", sa.Integer(), nullable=True),
        sa.Column("previous_school_raw", sa.String(length=200), nullable=True),
        sa.Column("is_transfer", sa.Boolean(), server_default="false", nullable=False),
        sa.Column("jersey_number", sa.String(length=20), nullable=True),
        sa.Column("roster_url", sa.Text(), nullable=True),
        sa.Column("profile_url", sa.Text(), nullable=True),
        *timestamp_columns(),
        sa.ForeignKeyConstraint(
            ["college_id"], ["colleges.id"], name=op.f("fk_player_rosters_college_id_colleges")
        ),
        sa.ForeignKeyConstraint(
            ["high_school_id"],
            ["high_schools.id"],
            name=op.f("fk_player_rosters_high_school_id_high_schools"),
        ),
        sa.ForeignKeyConstraint(
            ["player_id"], ["players.id"], name=op.f("fk_player_rosters_player_id_players")
        ),
        sa.ForeignKeyConstraint(
            ["previous_college_id"],
            ["colleges.id"],
            name=op.f("fk_player_rosters_previous_college_id_colleges"),
        ),
        sa.ForeignKeyConstraint(
            ["primary_position_id"],
            ["positions.id"],
            name=op.f("fk_player_rosters_primary_position_id_positions"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_player_rosters")),
        sa.UniqueConstraint(
            "player_id", "college_id", "year", name="uq_player_rosters_player_college_year"
        ),
    )
    op.create_index(
        op.f("ix_player_rosters_college_id"), "player_rosters", ["college_id"], unique=False
    )
    op.create_index(
        op.f("ix_player_rosters_high_school_id"), "player_rosters", ["high_school_id"], unique=False
    )
    op.create_index(
        op.f("ix_player_rosters_is_transfer"), "player_rosters", ["is_transfer"], unique=False
    )
    op.create_index(
        op.f("ix_player_rosters_normalized_roster_year"),
        "player_rosters",
        ["normalized_roster_year"],
        unique=False,
    )
    op.create_index(
        op.f("ix_player_rosters_player_id"), "player_rosters", ["player_id"], unique=False
    )
    op.create_index(
        op.f("ix_player_rosters_previous_college_id"),
        "player_rosters",
        ["previous_college_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_player_rosters_primary_position_id"),
        "player_rosters",
        ["primary_position_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_player_rosters_roster_year"), "player_rosters", ["roster_year"], unique=False
    )
    op.create_index(op.f("ix_player_rosters_year"), "player_rosters", ["year"], unique=False)

    op.create_table(
        "coach_assignments",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("coach_id", sa.Integer(), nullable=False),
        sa.Column("college_id", sa.Integer(), nullable=False),
        sa.Column("year", sa.Integer(), nullable=False),
        sa.Column("position_id", sa.Integer(), nullable=True),
        sa.Column("title_raw", sa.String(length=200), nullable=True),
        sa.Column("bio_url", sa.Text(), nullable=True),
        sa.Column("staff_url", sa.Text(), nullable=True),
        *timestamp_columns(),
        sa.ForeignKeyConstraint(
            ["coach_id"], ["coaches.id"], name=op.f("fk_coach_assignments_coach_id_coaches")
        ),
        sa.ForeignKeyConstraint(
            ["college_id"], ["colleges.id"], name=op.f("fk_coach_assignments_college_id_colleges")
        ),
        sa.ForeignKeyConstraint(
            ["position_id"],
            ["positions.id"],
            name=op.f("fk_coach_assignments_position_id_positions"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_coach_assignments")),
    )
    op.create_index(
        op.f("ix_coach_assignments_coach_id"), "coach_assignments", ["coach_id"], unique=False
    )
    op.create_index(
        op.f("ix_coach_assignments_college_id"), "coach_assignments", ["college_id"], unique=False
    )
    op.create_index(
        op.f("ix_coach_assignments_position_id"), "coach_assignments", ["position_id"], unique=False
    )
    op.create_index(op.f("ix_coach_assignments_year"), "coach_assignments", ["year"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_coach_assignments_year"), table_name="coach_assignments")
    op.drop_index(op.f("ix_coach_assignments_position_id"), table_name="coach_assignments")
    op.drop_index(op.f("ix_coach_assignments_college_id"), table_name="coach_assignments")
    op.drop_index(op.f("ix_coach_assignments_coach_id"), table_name="coach_assignments")
    op.drop_table("coach_assignments")

    op.drop_index(op.f("ix_player_rosters_year"), table_name="player_rosters")
    op.drop_index(op.f("ix_player_rosters_roster_year"), table_name="player_rosters")
    op.drop_index(op.f("ix_player_rosters_primary_position_id"), table_name="player_rosters")
    op.drop_index(op.f("ix_player_rosters_previous_college_id"), table_name="player_rosters")
    op.drop_index(op.f("ix_player_rosters_player_id"), table_name="player_rosters")
    op.drop_index(op.f("ix_player_rosters_normalized_roster_year"), table_name="player_rosters")
    op.drop_index(op.f("ix_player_rosters_is_transfer"), table_name="player_rosters")
    op.drop_index(op.f("ix_player_rosters_high_school_id"), table_name="player_rosters")
    op.drop_index(op.f("ix_player_rosters_college_id"), table_name="player_rosters")
    op.drop_table("player_rosters")

    op.drop_index(op.f("ix_scrape_pages_scrape_run_id"), table_name="scrape_pages")
    op.drop_index(op.f("ix_scrape_pages_page_type"), table_name="scrape_pages")
    op.drop_index(op.f("ix_scrape_pages_content_hash"), table_name="scrape_pages")
    op.drop_index(op.f("ix_scrape_pages_college_id"), table_name="scrape_pages")
    op.drop_table("scrape_pages")

    op.drop_index(op.f("ix_coaches_person_id"), table_name="coaches")
    op.drop_table("coaches")

    op.drop_index(op.f("ix_players_person_id"), table_name="players")
    op.drop_index(op.f("ix_players_hometown_state"), table_name="players")
    op.drop_table("players")

    op.drop_index(op.f("ix_scrape_runs_year"), table_name="scrape_runs")
    op.drop_index(op.f("ix_scrape_runs_status"), table_name="scrape_runs")
    op.drop_index(op.f("ix_scrape_runs_source"), table_name="scrape_runs")
    op.drop_table("scrape_runs")

    op.drop_index(op.f("ix_positions_position_type"), table_name="positions")
    op.drop_index(op.f("ix_positions_position_group"), table_name="positions")
    op.drop_index(op.f("ix_positions_name"), table_name="positions")
    op.drop_table("positions")

    op.drop_index(op.f("ix_high_schools_state"), table_name="high_schools")
    op.drop_index(op.f("ix_high_schools_name"), table_name="high_schools")
    op.drop_table("high_schools")

    op.drop_index(op.f("ix_colleges_state"), table_name="colleges")
    op.drop_index(op.f("ix_colleges_name"), table_name="colleges")
    op.drop_index(op.f("ix_colleges_division"), table_name="colleges")
    op.drop_index(op.f("ix_colleges_conference"), table_name="colleges")
    op.drop_table("colleges")

    op.drop_index(op.f("ix_people_full_name"), table_name="people")
    op.drop_table("people")
