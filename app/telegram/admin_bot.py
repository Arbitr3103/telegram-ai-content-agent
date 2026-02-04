"""
Admin Bot for moderating posts before publication.

Commands:
- /start - Welcome message
- /help - Show available commands
- /preview - Preview next scheduled post
- /approve - Approve pending post
- /reject - Reject pending post with reason
- /stats - Show posting statistics
"""
import logging
from typing import Optional

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    ContextTypes,
    MessageHandler,
    filters
)

from app.config import settings

logger = logging.getLogger(__name__)


def is_admin(user_id: int) -> bool:
    """Check if user is an authorized admin."""
    return user_id in settings.admin_user_ids


def admin_required(func):
    """Decorator to restrict handler to admins only."""
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE):
        user_id = update.effective_user.id
        if not is_admin(user_id):
            await update.message.reply_text("Access denied. You are not an admin.")
            logger.warning(f"Unauthorized access attempt from user {user_id}")
            return
        return await func(update, context)
    return wrapper


# === Command Handlers ===

@admin_required
async def start_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /start command."""
    await update.message.reply_text(
        "Admin Bot for @smart_analytics_mp\n\n"
        "Commands:\n"
        "/preview - Preview next post\n"
        "/approve - Approve pending post\n"
        "/reject - Reject post\n"
        "/stats - View statistics\n"
        "/help - Show this message"
    )


@admin_required
async def help_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /help command."""
    await start_handler(update, context)


@admin_required
async def preview_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /preview command - generate and show next post for approval."""
    await update.message.reply_text("Generating preview...")

    try:
        from app.main import ContentPipeline

        pipeline = ContentPipeline()

        # Collect sources and generate post without publishing
        sources = await pipeline.collect_sources()
        result = await pipeline.generate_and_publish_post(sources, publish=False)

        await pipeline.close()

        if result['success']:
            post_content = result['post']['content']
            post_type = result.get('post_type', 'unknown')

            # Store in context for approval
            context.user_data['pending_post'] = {
                'content': post_content,
                'post_type': post_type,
                'sources': result['post'].get('sources', [])
            }

            # Send preview with approval buttons
            keyboard = InlineKeyboardMarkup([
                [
                    InlineKeyboardButton("Approve & Publish", callback_data="approve_preview"),
                    InlineKeyboardButton("Reject", callback_data="reject_preview"),
                ],
                [
                    InlineKeyboardButton("Regenerate", callback_data="regenerate_preview"),
                ]
            ])

            await update.message.reply_text(
                f"POST PREVIEW\n"
                f"Type: {post_type}\n\n"
                f"{post_content}",
                reply_markup=keyboard
            )
        else:
            await update.message.reply_text(f"Failed to generate: {result.get('error')}")

    except Exception as e:
        logger.error(f"Preview error: {e}")
        await update.message.reply_text(f"Error: {e}")


@admin_required
async def approve_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /approve command."""
    await update.message.reply_text("No pending posts to approve.")


@admin_required
async def reject_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /reject command."""
    await update.message.reply_text("No pending posts to reject.")


@admin_required
async def stats_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /stats command."""
    from app.utils.post_types import get_rotation_status
    status = get_rotation_status()
    await update.message.reply_text(status)


# === Callback Query Handlers ===

async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle inline button callbacks."""
    query = update.callback_query
    await query.answer()

    user_id = query.from_user.id
    if not is_admin(user_id):
        await query.edit_message_text("Access denied.")
        return

    action = query.data

    if action == "approve_preview":
        pending = context.user_data.get('pending_post')
        if not pending:
            await query.edit_message_text("No pending post. Use /preview first.")
            return

        # Publish the post
        from app.telegram.publisher import TelegramPublisher
        publisher = TelegramPublisher()
        result = await publisher.publish_post(pending['content'])

        if result['success']:
            from app.utils.post_types import mark_post_published
            # Mark in rotation system
            mark_post_published(pending.get('post_type', 'useful'))

            await query.edit_message_text(
                f"Published!\n"
                f"Message ID: {result['message_id']}\n\n"
                f"Post type: {pending['post_type']}"
            )
            context.user_data.pop('pending_post', None)
        else:
            await query.edit_message_text(f"Publish failed: {result.get('error')}")

    elif action == "reject_preview":
        context.user_data.pop('pending_post', None)
        await query.edit_message_text("Post rejected. Use /preview to generate a new one.")

    elif action == "regenerate_preview":
        await query.edit_message_text("Regenerating... Use /preview again.")
        context.user_data.pop('pending_post', None)

    elif action.startswith("approve_"):
        post_id = action.split("_")[1]
        await query.edit_message_text(f"Post {post_id} approved!")

    elif action.startswith("reject_"):
        post_id = action.split("_")[1]
        await query.edit_message_text(f"Post {post_id} rejected.")


def create_approval_keyboard(post_id: int) -> InlineKeyboardMarkup:
    """Create inline keyboard for post approval."""
    keyboard = [
        [
            InlineKeyboardButton("Approve", callback_data=f"approve_{post_id}"),
            InlineKeyboardButton("Reject", callback_data=f"reject_{post_id}"),
        ],
        [
            InlineKeyboardButton("Regenerate", callback_data=f"regenerate_{post_id}"),
        ]
    ]
    return InlineKeyboardMarkup(keyboard)


# === Application Builder ===

def create_admin_bot() -> Application:
    """Create and configure the admin bot application."""
    app = Application.builder().token(settings.telegram_bot_token).build()

    # Add handlers
    app.add_handler(CommandHandler("start", start_handler))
    app.add_handler(CommandHandler("help", help_handler))
    app.add_handler(CommandHandler("preview", preview_handler))
    app.add_handler(CommandHandler("approve", approve_handler))
    app.add_handler(CommandHandler("reject", reject_handler))
    app.add_handler(CommandHandler("stats", stats_handler))
    app.add_handler(CallbackQueryHandler(button_callback))

    return app


async def run_admin_bot():
    """Run the admin bot."""
    logger.info("Starting Admin Bot...")
    app = create_admin_bot()
    await app.run_polling()


if __name__ == "__main__":
    import asyncio
    asyncio.run(run_admin_bot())
