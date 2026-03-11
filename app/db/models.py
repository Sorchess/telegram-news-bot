import datetime

from sqlalchemy import BigInteger, DateTime, ForeignKey, Index, Integer, String, Text, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


class Source(Base):
    """News source (e.g. reuters.com, kommersant.ru)."""

    __tablename__ = "sources"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    slug: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    url: Mapped[str] = mapped_column(String(500), nullable=False)

    headlines: Mapped[list["Headline"]] = relationship(back_populates="source")
    subscriptions: Mapped[list["Subscription"]] = relationship(back_populates="source")

    def __repr__(self) -> str:
        return f"<Source {self.slug}>"


class Headline(Base):
    """A single news headline scraped from a source."""

    __tablename__ = "headlines"
    __table_args__ = (
        Index("ix_headlines_source_published", "source_id", "published_at"),
        Index("ix_headlines_url", "url", unique=True),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    source_id: Mapped[int] = mapped_column(ForeignKey("sources.id"), nullable=False)
    title: Mapped[str] = mapped_column(Text, nullable=False)
    url: Mapped[str] = mapped_column(String(1000), nullable=False, unique=True)
    published_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    created_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    source: Mapped["Source"] = relationship(back_populates="headlines")

    # Track which users have already received this headline via subscription
    delivered_to: Mapped[list["DeliveryLog"]] = relationship(back_populates="headline")

    def __repr__(self) -> str:
        return f"<Headline {self.id}: {self.title[:40]}>"


class User(Base):
    """Telegram user who interacted with the bot."""

    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    telegram_id: Mapped[int] = mapped_column(BigInteger, unique=True, nullable=False)
    first_name: Mapped[str | None] = mapped_column(String(255))
    username: Mapped[str | None] = mapped_column(String(255))
    default_source_slug: Mapped[str | None] = mapped_column(String(50))
    headlines_count: Mapped[int] = mapped_column(Integer, default=5, server_default="5")
    created_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    subscriptions: Mapped[list["Subscription"]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )
    actions: Mapped[list["UserAction"]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<User tg={self.telegram_id}>"


class Subscription(Base):
    """User subscription to a news source."""

    __tablename__ = "subscriptions"
    __table_args__ = (
        Index("ix_subscriptions_user_source", "user_id", "source_id", unique=True),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    source_id: Mapped[int] = mapped_column(ForeignKey("sources.id"), nullable=False)
    created_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    user: Mapped["User"] = relationship(back_populates="subscriptions")
    source: Mapped["Source"] = relationship(back_populates="subscriptions")

    def __repr__(self) -> str:
        return f"<Subscription user={self.user_id} source={self.source_id}>"


class DeliveryLog(Base):
    """Tracks which headlines have been delivered to which users (via subscription)."""

    __tablename__ = "delivery_log"
    __table_args__ = (
        Index("ix_delivery_user_headline", "user_id", "headline_id", unique=True),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    headline_id: Mapped[int] = mapped_column(ForeignKey("headlines.id"), nullable=False)
    delivered_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    headline: Mapped["Headline"] = relationship(back_populates="delivered_to")

    def __repr__(self) -> str:
        return f"<DeliveryLog user={self.user_id} headline={self.headline_id}>"


class UserAction(Base):
    """Audit log of user actions for analytics."""

    __tablename__ = "user_actions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    action: Mapped[str] = mapped_column(String(100), nullable=False)
    detail: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    user: Mapped["User"] = relationship(back_populates="actions")

    def __repr__(self) -> str:
        return f"<UserAction {self.action} by user={self.user_id}>"
