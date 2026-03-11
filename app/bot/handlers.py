"""Bot command and callback handlers."""

import logging

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import ContextTypes

from app.bot.helpers import format_headline, sources_keyboard
from app.db.repos import (
    HeadlineRepo,
    SourceRepo,
    SubscriptionRepo,
    UserActionRepo,
    UserRepo,
)
from app.db.session import get_session

logger = logging.getLogger(__name__)

HELP_TEXT = (
    "🤖 <b>News Aggregator Bot</b>\n\n"
    "Я собираю новостные заголовки из нескольких источников "
    "и могу отправлять их вам по запросу или по подписке.\n\n"
    "<b>Команды:</b>\n"
    "/start — запуск бота и приветствие\n"
    "/help — справка по командам\n"
    "/news — заголовки из источника по умолчанию\n"
    "/news_from — заголовки из выбранного источника\n"
    "/news_all — заголовки из всех источников\n"
    "/sources — список доступных источников\n"
    "/settings — настройки (источник по умолчанию, кол-во заголовков)\n"
    "/subscribe — подписаться на источник\n"
    "/unsubscribe — отписаться от источника\n"
    "/my_subs — мои активные подписки\n"
)


# ── /start ──────────────────────────────────────────────────────────────────

async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not update.effective_user or not update.message:
        return
    tg_user = update.effective_user
    async with await get_session() as session:
        user = await UserRepo.get_or_create(
            session, tg_user.id, tg_user.first_name, tg_user.username
        )
        await UserActionRepo.log(session, user.id, "start")

    await update.message.reply_text(
        f"Привет, {tg_user.first_name}! 👋\n\n" + HELP_TEXT,
        parse_mode="HTML",
    )


# ── /help ───────────────────────────────────────────────────────────────────

async def cmd_help(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not update.message:
        return
    await update.message.reply_text(HELP_TEXT, parse_mode="HTML")


# ── /sources ────────────────────────────────────────────────────────────────

async def cmd_sources(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not update.message:
        return
    async with await get_session() as session:
        sources = await SourceRepo.get_all(session)

    if not sources:
        await update.message.reply_text("Источники пока не загружены. Попробуйте позже.")
        return

    lines = ["📋 <b>Доступные источники:</b>\n"]
    for s in sources:
        lines.append(f"• <b>{s.name}</b> ({s.slug}) — {s.url}")
    await update.message.reply_text("\n".join(lines), parse_mode="HTML")


# ── /news — from default source ────────────────────────────────────────────

async def cmd_news(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not update.effective_user or not update.message:
        return
    async with await get_session() as session:
        user = await UserRepo.get_or_create(session, update.effective_user.id)
        await UserActionRepo.log(session, user.id, "news")

        source = None
        if user.default_source_slug:
            source = await SourceRepo.get_by_slug(session, user.default_source_slug)

        if source is None:
            # Fall back to first available source
            sources = await SourceRepo.get_all(session)
            if sources:
                source = sources[0]

        if source is None:
            await update.message.reply_text("Источники пока не загружены. Попробуйте позже.")
            return

        headlines = await HeadlineRepo.get_latest(session, source.id, user.headlines_count)

    if not headlines:
        await update.message.reply_text(
            f"Пока нет заголовков от <b>{source.name}</b>.", parse_mode="HTML"
        )
        return

    lines = [f"📰 <b>{source.name}</b> — последние заголовки:\n"]
    for h in headlines:
        lines.append(format_headline(h.title, h.url))
    await update.message.reply_text(
        "\n".join(lines), parse_mode="HTML", disable_web_page_preview=True
    )


# ── /news_from — choose source ─────────────────────────────────────────────

async def cmd_news_from(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not update.message:
        return
    async with await get_session() as session:
        sources = await SourceRepo.get_all(session)

    if not sources:
        await update.message.reply_text("Источники пока не загружены.")
        return

    await update.message.reply_text(
        "Выберите источник:",
        reply_markup=sources_keyboard(sources, "newsfrom"),
    )


async def cb_news_from(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    if not query or not query.data or not update.effective_user:
        return
    await query.answer()
    slug = query.data.split(":", 1)[1]

    async with await get_session() as session:
        user = await UserRepo.get_or_create(session, update.effective_user.id)
        await UserActionRepo.log(session, user.id, "news_from", slug)
        source = await SourceRepo.get_by_slug(session, slug)
        if source is None:
            await query.edit_message_text("Источник не найден.")
            return
        headlines = await HeadlineRepo.get_latest(session, source.id, user.headlines_count)

    if not headlines:
        await query.edit_message_text(
            f"Пока нет заголовков от <b>{source.name}</b>.", parse_mode="HTML"
        )
        return

    lines = [f"📰 <b>{source.name}</b> — последние заголовки:\n"]
    for h in headlines:
        lines.append(format_headline(h.title, h.url))
    await query.edit_message_text(
        "\n".join(lines), parse_mode="HTML", disable_web_page_preview=True
    )


# ── /news_all — from all sources ───────────────────────────────────────────

async def cmd_news_all(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not update.effective_user or not update.message:
        return
    async with await get_session() as session:
        user = await UserRepo.get_or_create(session, update.effective_user.id)
        await UserActionRepo.log(session, user.id, "news_all")
        sources = await SourceRepo.get_all(session)

        if not sources:
            await update.message.reply_text("Источники пока не загружены.")
            return

        all_lines: list[str] = []
        for source in sources:
            headlines = await HeadlineRepo.get_latest(
                session, source.id, user.headlines_count
            )
            if headlines:
                all_lines.append(f"\n📰 <b>{source.name}</b>:\n")
                for h in headlines:
                    all_lines.append(format_headline(h.title, h.url))

    if not all_lines:
        await update.message.reply_text("Пока нет загруженных заголовков.")
        return

    await update.message.reply_text(
        "\n".join(all_lines), parse_mode="HTML", disable_web_page_preview=True
    )


# ── /settings ──────────────────────────────────────────────────────────────

async def cmd_settings(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not update.effective_user or not update.message:
        return
    async with await get_session() as session:
        user = await UserRepo.get_or_create(session, update.effective_user.id)

    default_src = user.default_source_slug or "не выбран (используется первый)"
    buttons = [
        [InlineKeyboardButton("Изменить источник по умолчанию", callback_data="settings:source")],
        [InlineKeyboardButton("Изменить кол-во заголовков", callback_data="settings:count")],
    ]
    await update.message.reply_text(
        f"⚙️ <b>Настройки</b>\n\n"
        f"Источник по умолчанию: <b>{default_src}</b>\n"
        f"Кол-во заголовков за раз: <b>{user.headlines_count}</b>\n",
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup(buttons),
    )


async def cb_settings(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    if not query or not query.data:
        return
    await query.answer()
    action = query.data.split(":", 1)[1]

    if action == "source":
        async with await get_session() as session:
            sources = await SourceRepo.get_all(session)
        buttons = [
            [InlineKeyboardButton(s.name, callback_data=f"setsource:{s.slug}")]
            for s in sources
        ]
        buttons.append(
            [InlineKeyboardButton("Сбросить (авто)", callback_data="setsource:__reset__")]
        )
        await query.edit_message_text(
            "Выберите источник по умолчанию:",
            reply_markup=InlineKeyboardMarkup(buttons),
        )
    elif action == "count":
        buttons = [
            [
                InlineKeyboardButton(str(n), callback_data=f"setcount:{n}")
                for n in [3, 5, 10, 15, 20]
            ]
        ]
        await query.edit_message_text(
            "Сколько заголовков показывать за раз?",
            reply_markup=InlineKeyboardMarkup(buttons),
        )


async def cb_set_source(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    if not query or not query.data or not update.effective_user:
        return
    await query.answer()
    slug = query.data.split(":", 1)[1]

    async with await get_session() as session:
        user = await UserRepo.get_or_create(session, update.effective_user.id)
        new_slug = None if slug == "__reset__" else slug
        await UserRepo.update_default_source(session, user, new_slug)
        await UserActionRepo.log(session, user.id, "set_default_source", slug)

    label = slug if slug != "__reset__" else "авто"
    await query.edit_message_text(f"✅ Источник по умолчанию: <b>{label}</b>", parse_mode="HTML")


async def cb_set_count(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    if not query or not query.data or not update.effective_user:
        return
    await query.answer()
    count = int(query.data.split(":", 1)[1])

    async with await get_session() as session:
        user = await UserRepo.get_or_create(session, update.effective_user.id)
        await UserRepo.update_headlines_count(session, user, count)
        await UserActionRepo.log(session, user.id, "set_headlines_count", str(count))

    await query.edit_message_text(
        f"✅ Кол-во заголовков за раз: <b>{count}</b>", parse_mode="HTML"
    )


# ── /subscribe ─────────────────────────────────────────────────────────────

async def cmd_subscribe(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not update.message:
        return
    async with await get_session() as session:
        sources = await SourceRepo.get_all(session)

    if not sources:
        await update.message.reply_text("Источники пока не загружены.")
        return

    await update.message.reply_text(
        "Выберите источник для подписки:",
        reply_markup=sources_keyboard(sources, "sub"),
    )


async def cb_subscribe(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    if not query or not query.data or not update.effective_user:
        return
    await query.answer()
    slug = query.data.split(":", 1)[1]

    async with await get_session() as session:
        user = await UserRepo.get_or_create(session, update.effective_user.id)
        source = await SourceRepo.get_by_slug(session, slug)
        if source is None:
            await query.edit_message_text("Источник не найден.")
            return
        added = await SubscriptionRepo.add(session, user.id, source.id)
        await UserActionRepo.log(session, user.id, "subscribe", slug)

    if added:
        await query.edit_message_text(
            f"✅ Вы подписались на <b>{source.name}</b>.\n"
            "Новые заголовки будут приходить автоматически.",
            parse_mode="HTML",
        )
    else:
        await query.edit_message_text(
            f"Вы уже подписаны на <b>{source.name}</b>.", parse_mode="HTML"
        )


# ── /unsubscribe ───────────────────────────────────────────────────────────

async def cmd_unsubscribe(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not update.effective_user or not update.message:
        return
    async with await get_session() as session:
        user = await UserRepo.get_or_create(session, update.effective_user.id)
        subs = await SubscriptionRepo.get_user_subscriptions(session, user.id)

    if not subs:
        await update.message.reply_text("У вас нет активных подписок.")
        return

    buttons: list[list[InlineKeyboardButton]] = []
    for sub in subs:
        buttons.append([
            InlineKeyboardButton(
                f"❌ {sub.source.name}", callback_data=f"unsub:{sub.source.slug}"
            )
        ])
    await update.message.reply_text(
        "Выберите подписку для отмены:",
        reply_markup=InlineKeyboardMarkup(buttons),
    )


async def cb_unsubscribe(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    if not query or not query.data or not update.effective_user:
        return
    await query.answer()
    slug = query.data.split(":", 1)[1]

    async with await get_session() as session:
        user = await UserRepo.get_or_create(session, update.effective_user.id)
        source = await SourceRepo.get_by_slug(session, slug)
        if source is None:
            await query.edit_message_text("Источник не найден.")
            return
        removed = await SubscriptionRepo.remove(session, user.id, source.id)
        await UserActionRepo.log(session, user.id, "unsubscribe", slug)

    if removed:
        await query.edit_message_text(
            f"✅ Подписка на <b>{source.name}</b> отменена.", parse_mode="HTML"
        )
    else:
        await query.edit_message_text("Подписка не найдена.")


# ── /my_subs ───────────────────────────────────────────────────────────────

async def cmd_my_subs(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not update.effective_user or not update.message:
        return
    async with await get_session() as session:
        user = await UserRepo.get_or_create(session, update.effective_user.id)
        subs = await SubscriptionRepo.get_user_subscriptions(session, user.id)

    if not subs:
        await update.message.reply_text(
            "У вас нет активных подписок.\nИспользуйте /subscribe, чтобы подписаться."
        )
        return

    lines = ["📬 <b>Ваши подписки:</b>\n"]
    for sub in subs:
        lines.append(f"• {sub.source.name} ({sub.source.slug})")
    await update.message.reply_text("\n".join(lines), parse_mode="HTML")
