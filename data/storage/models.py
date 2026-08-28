from datetime import date, datetime

from sqlalchemy import ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class Event(Base):
    __tablename__ = "events"

    id: Mapped[int] = mapped_column(primary_key=True)
    source: Mapped[str] = mapped_column(String(32))
    source_event_id: Mapped[str] = mapped_column(String(64))
    name: Mapped[str]
    date: Mapped[date]
    location: Mapped[str | None]
    raw_html_path: Mapped[str | None]

    __table_args__ = (UniqueConstraint("source", "source_event_id"),)


class Fighter(Base):
    __tablename__ = "fighters"

    id: Mapped[int] = mapped_column(primary_key=True)
    ufcstats_id: Mapped[str | None] = mapped_column(String(32), unique=True)
    bestfightodds_id: Mapped[str | None] = mapped_column(String(64), unique=True)
    sherdog_id: Mapped[str | None] = mapped_column(String(64), unique=True)
    name_raw: Mapped[str]
    name_normalized: Mapped[str]
    dob: Mapped[date | None]
    height_cm: Mapped[float | None]
    reach_cm: Mapped[float | None]
    stance: Mapped[str | None]
    raw_html_path: Mapped[str | None]


class Fight(Base):
    __tablename__ = "fights"

    id: Mapped[int] = mapped_column(primary_key=True)
    event_id: Mapped[int] = mapped_column(ForeignKey("events.id"))
    ufcstats_id: Mapped[str] = mapped_column(String(32), unique=True)
    fighter_a_id: Mapped[int] = mapped_column(ForeignKey("fighters.id"))
    fighter_b_id: Mapped[int] = mapped_column(ForeignKey("fighters.id"))
    winner_id: Mapped[int | None] = mapped_column(ForeignKey("fighters.id"))
    weight_class: Mapped[str | None]
    method: Mapped[str | None]
    method_detail: Mapped[str | None]
    round: Mapped[int | None]
    time: Mapped[str | None]
    is_title_fight: Mapped[bool | None]
    kd_a: Mapped[int | None]
    kd_b: Mapped[int | None]
    str_a: Mapped[int | None]
    str_b: Mapped[int | None]
    td_a: Mapped[int | None]
    td_b: Mapped[int | None]
    sub_a: Mapped[int | None]
    sub_b: Mapped[int | None]
    raw_html_path: Mapped[str | None]


class FightRoundStats(Base):
    __tablename__ = "fight_round_stats"

    id: Mapped[int] = mapped_column(primary_key=True)
    fight_id: Mapped[int] = mapped_column(ForeignKey("fights.id"))
    fighter_id: Mapped[int] = mapped_column(ForeignKey("fighters.id"))
    round: Mapped[int]
    kd: Mapped[int | None]
    sig_str_landed: Mapped[int | None]
    sig_str_att: Mapped[int | None]
    total_str_landed: Mapped[int | None]
    total_str_att: Mapped[int | None]
    td_landed: Mapped[int | None]
    td_att: Mapped[int | None]
    sub_att: Mapped[int | None]
    rev: Mapped[int | None]
    ctrl_time_sec: Mapped[int | None]
    sig_str_head: Mapped[int | None]
    sig_str_body: Mapped[int | None]
    sig_str_leg: Mapped[int | None]
    sig_str_distance: Mapped[int | None]
    sig_str_clinch: Mapped[int | None]
    sig_str_ground: Mapped[int | None]

    __table_args__ = (UniqueConstraint("fight_id", "fighter_id", "round"),)


class FightOdds(Base):
    __tablename__ = "fight_odds"

    id: Mapped[int] = mapped_column(primary_key=True)
    fight_id: Mapped[int] = mapped_column(ForeignKey("fights.id"))
    fighter_id: Mapped[int] = mapped_column(ForeignKey("fighters.id"))
    sportsbook: Mapped[str]
    moneyline: Mapped[int]
    scraped_at: Mapped[datetime]

    __table_args__ = (UniqueConstraint("fight_id", "fighter_id", "sportsbook"),)


class ScrapeCheckpoint(Base):
    __tablename__ = "scrape_checkpoints"

    source: Mapped[str] = mapped_column(String(32), primary_key=True)
    last_event_source_id: Mapped[str | None]
    last_run_at: Mapped[datetime | None]
