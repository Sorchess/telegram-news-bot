from sqlalchemy import delete, select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.db.models import (
    DeliveryLog,
    Headline,
    Source,
    Subscription,
    User,
    UserAction,
)


class SourceRepo:
    @staticmethod
    async def get_all(session: AsyncSession) -> list[Source]:
        result = await session.execute(select(Source).order_by(Source.slug))
        return list(result.scalars().all())

    @staticmethod
    async def get_by_slug(session: AsyncSession, slug: str) -> Source | None:
        result = await session.execute(select(Source).where(Source.slug == slug))
        return result.scalar_one_or_none()

    @staticmethod
    async def upsert(session: AsyncSession, slug: str, name: str, url: str) -> Source:
        stmt = (
            pg_insert(Source)
            .values(slug=slug, name=name, url=url)
            .on_conflict_do_update(index_elements=["slug"], set_={"name": name, "url": url})
            .returning(Source)
        )
        result = await session.execute(stmt)
        await session.commit()
        return result.scalar_one()


class HeadlineRepo:
    @staticmethod
    async def bulk_upsert(
        session: AsyncSession,
        items: list[dict],
    ) -> int:
        """Insert headlines ignoring duplicates by url. Returns number of inserted rows."""
        if not items:
            return 0
        stmt = pg_insert(Headline).values(items).on_conflict_do_nothing(index_elements=["url"])
        result = await session.execute(stmt)
        await session.commit()
        return result.rowcount  # type: ignore[return-value]

    @staticmethod
    async def get_latest(
        session: AsyncSession,
        source_id: int | None = None,
        limit: int = 5,
    ) -> list[Headline]:
        query = select(Headline).order_by(Headline.published_at.desc()).limit(limit)
        if source_id is not None:
            query = query.where(Headline.source_id == source_id)
        result = await session.execute(query)
        return list(result.scalars().all())

    @staticmethod
    async def get_undelivered_for_user(
        session: AsyncSession,
        user_id: int,
        source_id: int,
        limit: int = 10,
    ) -> list[Headline]:
        """Get headlines from a source that haven't been delivered to this user yet."""
        subq = select(DeliveryLog.headline_id).where(DeliveryLog.user_id == user_id)
        query = (
            select(Headline)
            .where(Headline.source_id == source_id, Headline.id.notin_(subq))
            .order_by(Headline.published_at.desc())
            .limit(limit)
        )
        result = await session.execute(query)
        return list(result.scalars().all())


class UserRepo:
    @staticmethod
    async def get_or_create(
        session: AsyncSession,
        telegram_id: int,
        first_name: str | None = None,
        username: str | None = None,
    ) -> User:
        result = await session.execute(
            select(User).where(User.telegram_id == telegram_id)
        )
        user = result.scalar_one_or_none()
        if user is None:
            user = User(
                telegram_id=telegram_id,
                first_name=first_name,
                username=username,
            )
            session.add(user)
            await session.commit()
            await session.refresh(user)
        return user

    @staticmethod
    async def update_default_source(
        session: AsyncSession, user: User, slug: str | None
    ) -> None:
        user.default_source_slug = slug
        session.add(user)
        await session.commit()

    @staticmethod
    async def update_headlines_count(
        session: AsyncSession, user: User, count: int
    ) -> None:
        user.headlines_count = count
        session.add(user)
        await session.commit()


class SubscriptionRepo:
    @staticmethod
    async def get_user_subscriptions(
        session: AsyncSession, user_id: int
    ) -> list[Subscription]:
        result = await session.execute(
            select(Subscription)
            .where(Subscription.user_id == user_id)
            .options(selectinload(Subscription.source))
            .join(Source)
            .order_by(Source.slug)
        )
        return list(result.scalars().all())

    @staticmethod
    async def add(session: AsyncSession, user_id: int, source_id: int) -> bool:
        """Add subscription. Returns False if already exists."""
        stmt = (
            pg_insert(Subscription)
            .values(user_id=user_id, source_id=source_id)
            .on_conflict_do_nothing(index_elements=["user_id", "source_id"])
        )
        result = await session.execute(stmt)
        await session.commit()
        return result.rowcount > 0  # type: ignore[union-attr]

    @staticmethod
    async def remove(session: AsyncSession, user_id: int, source_id: int) -> bool:
        result = await session.execute(
            delete(Subscription).where(
                Subscription.user_id == user_id,
                Subscription.source_id == source_id,
            )
        )
        await session.commit()
        return result.rowcount > 0  # type: ignore[union-attr]

    @staticmethod
    async def get_all_with_users(session: AsyncSession) -> list[Subscription]:
        """Get all subscriptions with eager-loaded user and source."""
        result = await session.execute(
            select(Subscription)
            .options(
                selectinload(Subscription.user),
                selectinload(Subscription.source),
            )
        )
        return list(result.scalars().all())


class DeliveryLogRepo:
    @staticmethod
    async def mark_delivered(
        session: AsyncSession, user_id: int, headline_ids: list[int]
    ) -> None:
        if not headline_ids:
            return
        values = [{"user_id": user_id, "headline_id": hid} for hid in headline_ids]
        stmt = pg_insert(DeliveryLog).values(values).on_conflict_do_nothing(
            index_elements=["user_id", "headline_id"]
        )
        await session.execute(stmt)
        await session.commit()


class UserActionRepo:
    @staticmethod
    async def log(
        session: AsyncSession, user_id: int, action: str, detail: str | None = None
    ) -> None:
        session.add(UserAction(user_id=user_id, action=action, detail=detail))
        await session.commit()
