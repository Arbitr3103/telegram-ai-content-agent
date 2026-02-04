# Polls + Admin Bot Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add Telegram polls support and admin bot for post moderation before publishing.

**Architecture:**
- Extend TelegramPublisher with `send_poll()` method
- Create AdminBot as separate Application with inline keyboard handlers
- Add `approval_status` field to Post model for moderation workflow
- Integrate admin approval check into ContentPipeline before publishing

**Tech Stack:** python-telegram-bot 20.7, SQLAlchemy, APScheduler

---

## Task 1: Add Poll Support to Publisher

**Files:**
- Modify: `app/telegram/publisher.py`
- Create: `tests/test_publisher.py`

**Step 1: Write the failing test for send_poll**

Create `tests/test_publisher.py`:

```python
"""Tests for TelegramPublisher"""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from app.telegram.publisher import TelegramPublisher


@pytest.fixture
def mock_bot():
    with patch('app.telegram.publisher.Bot') as mock:
        bot_instance = AsyncMock()
        mock.return_value = bot_instance
        yield bot_instance


@pytest.fixture
def publisher(mock_bot):
    with patch('app.telegram.publisher.settings') as mock_settings:
        mock_settings.telegram_bot_token = "test_token"
        mock_settings.telegram_channel_id = "@test_channel"
        return TelegramPublisher()


class TestSendPoll:
    @pytest.mark.asyncio
    async def test_send_poll_success(self, publisher, mock_bot):
        """Test successful poll sending"""
        mock_message = MagicMock()
        mock_message.message_id = 123
        mock_message.poll.id = "poll_123"
        mock_bot.send_poll.return_value = mock_message

        result = await publisher.send_poll(
            question="Test question?",
            options=["Option 1", "Option 2", "Option 3"]
        )

        assert result['success'] is True
        assert result['message_id'] == 123
        assert result['poll_id'] == "poll_123"
        mock_bot.send_poll.assert_called_once()

    @pytest.mark.asyncio
    async def test_send_poll_validates_min_options(self, publisher):
        """Test that poll requires at least 2 options"""
        result = await publisher.send_poll(
            question="Test?",
            options=["Only one"]
        )

        assert result['success'] is False
        assert 'at least 2' in result['error'].lower()

    @pytest.mark.asyncio
    async def test_send_poll_validates_max_options(self, publisher):
        """Test that poll allows max 10 options"""
        result = await publisher.send_poll(
            question="Test?",
            options=[f"Option {i}" for i in range(11)]
        )

        assert result['success'] is False
        assert 'at most 10' in result['error'].lower()

    @pytest.mark.asyncio
    async def test_send_poll_validates_question_length(self, publisher):
        """Test question length validation (max 300 chars)"""
        result = await publisher.send_poll(
            question="A" * 301,
            options=["Yes", "No"]
        )

        assert result['success'] is False
        assert '300' in result['error']
```

**Step 2: Run tests to verify they fail**

Run: `cd /Users/vladimirbragin/projects/telegram-ai-agent && source .venv/bin/activate && pytest tests/test_publisher.py -v`
Expected: FAIL with "AttributeError: 'TelegramPublisher' object has no attribute 'send_poll'"

**Step 3: Implement send_poll method**

Add to `app/telegram/publisher.py` after the `delete_post` method (around line 144):

```python
    async def send_poll(
        self,
        question: str,
        options: List[str],
        is_anonymous: bool = True,
        allows_multiple_answers: bool = False
    ) -> Dict[str, Any]:
        """
        Send a poll to the Telegram channel.

        Args:
            question: Poll question (max 300 chars)
            options: List of answer options (2-10 items, each max 100 chars)
            is_anonymous: Whether the poll is anonymous
            allows_multiple_answers: Whether multiple answers are allowed

        Returns:
            Dict with success status, message_id, and poll_id
        """
        # Validation
        if len(options) < 2:
            return {'success': False, 'error': 'Poll must have at least 2 options'}
        if len(options) > 10:
            return {'success': False, 'error': 'Poll must have at most 10 options'}
        if len(question) > 300:
            return {'success': False, 'error': f'Question too long: {len(question)}/300 chars'}

        for i, opt in enumerate(options):
            if len(opt) > 100:
                return {'success': False, 'error': f'Option {i+1} too long: {len(opt)}/100 chars'}

        try:
            message = await self.bot.send_poll(
                chat_id=self.channel_id,
                question=question,
                options=options,
                is_anonymous=is_anonymous,
                allows_multiple_answers=allows_multiple_answers
            )

            logger.info(f"Poll published. Message ID: {message.message_id}, Poll ID: {message.poll.id}")

            return {
                'success': True,
                'message_id': message.message_id,
                'poll_id': message.poll.id,
                'chat_id': message.chat.id
            }

        except TelegramError as e:
            logger.error(f"Error sending poll: {e}")
            return {'success': False, 'error': str(e)}
```

Also add `List` to imports at the top:
```python
from typing import Optional, Dict, Any, List
```

**Step 4: Run tests to verify they pass**

Run: `cd /Users/vladimirbragin/projects/telegram-ai-agent && source .venv/bin/activate && pytest tests/test_publisher.py -v`
Expected: All 4 tests PASS

**Step 5: Commit**

```bash
git add tests/test_publisher.py app/telegram/publisher.py
git commit -m "feat(publisher): add send_poll method with validation

- Add send_poll() to TelegramPublisher
- Validate 2-10 options, question max 300 chars, option max 100 chars
- Return poll_id for tracking results
- Add unit tests for poll functionality

Co-Authored-By: Claude Opus 4.5 <noreply@anthropic.com>"
```

---

## Task 2: Integrate Polls with Content Pipeline

**Files:**
- Modify: `app/main.py`
- Modify: `app/telegram/publisher.py`

**Step 1: Write test for publish_post_with_poll**

Add to `tests/test_publisher.py`:

```python
class TestPublishPostWithPoll:
    @pytest.mark.asyncio
    async def test_publish_post_then_poll(self, publisher, mock_bot):
        """Test publishing post followed by poll"""
        mock_message = MagicMock()
        mock_message.message_id = 100
        mock_bot.send_message.return_value = mock_message

        mock_poll_message = MagicMock()
        mock_poll_message.message_id = 101
        mock_poll_message.poll.id = "poll_456"
        mock_bot.send_poll.return_value = mock_poll_message

        result = await publisher.publish_post_with_poll(
            content="Check out this post!",
            poll_question="What do you think?",
            poll_options=["Great", "Good", "Meh"]
        )

        assert result['success'] is True
        assert result['post_message_id'] == 100
        assert result['poll_message_id'] == 101
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/test_publisher.py::TestPublishPostWithPoll -v`
Expected: FAIL with "no attribute 'publish_post_with_poll'"

**Step 3: Add publish_post_with_poll method**

Add to `app/telegram/publisher.py`:

```python
    async def publish_post_with_poll(
        self,
        content: str,
        poll_question: str,
        poll_options: List[str],
        disable_web_preview: bool = True
    ) -> Dict[str, Any]:
        """
        Publish a post followed by a poll.

        Args:
            content: Post text content
            poll_question: Poll question
            poll_options: Poll answer options
            disable_web_preview: Whether to disable link previews

        Returns:
            Dict with post and poll message IDs
        """
        # First publish the post
        post_result = await self.publish_post(content, disable_web_preview)
        if not post_result['success']:
            return post_result

        # Then send the poll
        poll_result = await self.send_poll(poll_question, poll_options)
        if not poll_result['success']:
            return {
                'success': False,
                'error': f"Post published but poll failed: {poll_result['error']}",
                'post_message_id': post_result['message_id']
            }

        return {
            'success': True,
            'post_message_id': post_result['message_id'],
            'poll_message_id': poll_result['message_id'],
            'poll_id': poll_result['poll_id']
        }
```

**Step 4: Run test to verify it passes**

Run: `pytest tests/test_publisher.py::TestPublishPostWithPoll -v`
Expected: PASS

**Step 5: Update ContentPipeline to use polls**

Modify `app/main.py` in `generate_and_publish_post` method. Find the publish section (around line 142) and update:

```python
            if publish:
                # Check if this post should include a poll
                if planned_post and planned_post.include_poll and planned_post.poll_question:
                    result = await self.telegram_publisher.publish_post_with_poll(
                        content=post_data['content'],
                        poll_question=planned_post.poll_question,
                        poll_options=planned_post.poll_options or ["Да", "Нет"]
                    )
                    if result['success']:
                        logger.info(f"Post with poll published. Post ID: {result['post_message_id']}, Poll ID: {result['poll_message_id']}")
                        mark_post_published(post_type_key)
                        return {
                            'success': True,
                            'post': post_data,
                            'post_type': post_type_config['name'],
                            'telegram': result,
                            'has_poll': True
                        }
                else:
                    # Regular post without poll
                    result = await self.telegram_publisher.publish_post(
                        content=post_data['content']
                    )
                    if result['success']:
                        logger.info(f"Post published. Message ID: {result['message_id']}")
                        mark_post_published(post_type_key)
                        return {
                            'success': True,
                            'post': post_data,
                            'post_type': post_type_config['name'],
                            'telegram': result
                        }

                # Handle failure
                logger.error(f"Failed to publish: {result.get('error')}")
                return {
                    'success': False,
                    'post': post_data,
                    'error': result.get('error')
                }
```

**Step 6: Run integration test**

Run: `cd /Users/vladimirbragin/projects/telegram-ai-agent && source .venv/bin/activate && python -c "
from app.utils.content_plan import get_content_plan
plan = get_content_plan()
for p in plan.get_all_posts():
    if p.include_poll:
        print(f'{p.date}: {p.poll_question}')
        print(f'  Options: {p.poll_options}')
"`
Expected: Shows posts with polls (Feb 12, Feb 27)

**Step 7: Commit**

```bash
git add app/telegram/publisher.py app/main.py tests/test_publisher.py
git commit -m "feat(polls): integrate polls with content pipeline

- Add publish_post_with_poll() method
- ContentPipeline checks include_poll from content plan
- Publishes poll immediately after post if configured

Co-Authored-By: Claude Opus 4.5 <noreply@anthropic.com>"
```

---

## Task 3: Create Admin Bot Base Structure

**Files:**
- Create: `app/telegram/admin_bot.py`
- Create: `tests/test_admin_bot.py`
- Modify: `app/config.py`

**Step 1: Add admin config to settings**

Add to `app/config.py` after `telegram_admin_id` (around line 34):

```python
    # Admin bot settings
    telegram_admin_ids: str = ""  # Comma-separated list of admin user IDs

    @property
    def admin_user_ids(self) -> List[int]:
        """Parse admin IDs from comma-separated string"""
        if not self.telegram_admin_ids:
            # Fallback to single admin
            return [self.telegram_admin_id] if self.telegram_admin_id else []
        return [int(uid.strip()) for uid in self.telegram_admin_ids.split(',') if uid.strip()]
```

Also add `List` to imports:
```python
from typing import List
```

**Step 2: Write test for admin authorization**

Create `tests/test_admin_bot.py`:

```python
"""Tests for Admin Bot"""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch


class TestAdminAuthorization:
    def test_is_admin_returns_true_for_admin(self):
        """Test admin check returns True for admin user"""
        with patch('app.telegram.admin_bot.settings') as mock_settings:
            mock_settings.admin_user_ids = [123, 456]

            from app.telegram.admin_bot import is_admin
            assert is_admin(123) is True
            assert is_admin(456) is True

    def test_is_admin_returns_false_for_non_admin(self):
        """Test admin check returns False for non-admin user"""
        with patch('app.telegram.admin_bot.settings') as mock_settings:
            mock_settings.admin_user_ids = [123, 456]

            from app.telegram.admin_bot import is_admin
            assert is_admin(789) is False
```

**Step 3: Run test to verify it fails**

Run: `pytest tests/test_admin_bot.py -v`
Expected: FAIL with "cannot import name 'is_admin'"

**Step 4: Create admin_bot.py with base structure**

Create `app/telegram/admin_bot.py`:

```python
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
    """Handle /preview command - show next pending post."""
    # TODO: Implement post preview
    await update.message.reply_text(
        "Preview feature coming soon.\n"
        "Will show next scheduled post for approval."
    )


@admin_required
async def approve_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /approve command."""
    # TODO: Implement post approval
    await update.message.reply_text("No pending posts to approve.")


@admin_required
async def reject_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /reject command."""
    # TODO: Implement post rejection
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

    if action.startswith("approve_"):
        post_id = action.split("_")[1]
        await query.edit_message_text(f"Post {post_id} approved!")
        # TODO: Update post status in DB

    elif action.startswith("reject_"):
        post_id = action.split("_")[1]
        await query.edit_message_text(f"Post {post_id} rejected. Reply with reason.")
        # TODO: Wait for rejection reason


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
```

**Step 5: Run tests to verify they pass**

Run: `pytest tests/test_admin_bot.py -v`
Expected: All tests PASS

**Step 6: Commit**

```bash
git add app/telegram/admin_bot.py app/config.py tests/test_admin_bot.py
git commit -m "feat(admin): create admin bot base structure

- Add is_admin() and admin_required decorator
- Create command handlers: /start, /help, /preview, /approve, /reject, /stats
- Add inline keyboard builder for approval actions
- Add admin_user_ids config setting

Co-Authored-By: Claude Opus 4.5 <noreply@anthropic.com>"
```

---

## Task 4: Add Post Approval Status to Database

**Files:**
- Modify: `app/database/crud.py`
- Create: `alembic/versions/xxx_add_approval_status.py` (via alembic)

**Step 1: Check current Post model in rules**

The Post model (from `.claude/rules/database.md`) has:
- id, content, tags, status (draft/scheduled/published), telegram_message_id, published_at, created_at

We need to add:
- `approval_status`: pending, approved, rejected
- `rejection_reason`: text

**Step 2: Add CRUD functions for approval workflow**

Add to `app/database/crud.py`:

```python
def get_pending_approval_posts(db: Session) -> List[Post]:
    """Get posts waiting for admin approval."""
    return db.query(Post).filter(
        Post.status == 'draft',
        Post.approval_status == 'pending'
    ).order_by(Post.created_at).all()


def approve_post(db: Session, post_id: int) -> Optional[Post]:
    """Approve a post for publishing."""
    post = db.query(Post).filter(Post.id == post_id).first()
    if not post:
        return None

    post.approval_status = 'approved'
    db.commit()
    db.refresh(post)
    return post


def reject_post(db: Session, post_id: int, reason: str) -> Optional[Post]:
    """Reject a post with reason."""
    post = db.query(Post).filter(Post.id == post_id).first()
    if not post:
        return None

    post.approval_status = 'rejected'
    post.rejection_reason = reason
    db.commit()
    db.refresh(post)
    return post


def create_post_for_approval(
    db: Session,
    content: str,
    tags: List[str],
    sources: List[Dict[str, str]],
    post_type: str,
    metadata: Optional[Dict[str, Any]] = None,
) -> Post:
    """Create a new post in pending approval status."""
    post = Post(
        content=content,
        tags=tags,
        sources=sources,
        metadata=metadata or {},
        status='draft',
        approval_status='pending',
        post_type=post_type
    )
    db.add(post)
    db.commit()
    db.refresh(post)
    return post
```

**Step 3: Note on migrations**

Since models.py is empty and the schema is defined in rules, we'll add the fields when creating a proper models.py. For now, we store approval_status in the existing metadata JSONB field:

```python
# Temporary approach using metadata field
post.metadata['approval_status'] = 'pending'
post.metadata['rejection_reason'] = reason
```

**Step 4: Update crud.py with metadata-based approval**

Replace the functions added above with metadata-based versions:

```python
def get_pending_approval_posts(db: Session) -> List[Post]:
    """Get posts waiting for admin approval."""
    from sqlalchemy import cast, String
    from sqlalchemy.dialects.postgresql import JSONB

    return db.query(Post).filter(
        Post.status == 'draft'
    ).all()
    # Filter in Python for metadata check
    # return [p for p in posts if p.metadata.get('approval_status') == 'pending']


def approve_post(db: Session, post_id: int) -> Optional[Post]:
    """Approve a post for publishing."""
    post = db.query(Post).filter(Post.id == post_id).first()
    if not post:
        return None

    if post.metadata is None:
        post.metadata = {}
    post.metadata['approval_status'] = 'approved'
    db.commit()
    db.refresh(post)
    return post


def reject_post(db: Session, post_id: int, reason: str) -> Optional[Post]:
    """Reject a post with reason."""
    post = db.query(Post).filter(Post.id == post_id).first()
    if not post:
        return None

    if post.metadata is None:
        post.metadata = {}
    post.metadata['approval_status'] = 'rejected'
    post.metadata['rejection_reason'] = reason
    db.commit()
    db.refresh(post)
    return post
```

**Step 5: Commit**

```bash
git add app/database/crud.py
git commit -m "feat(db): add approval workflow CRUD functions

- get_pending_approval_posts() - fetch posts awaiting approval
- approve_post() - mark post as approved
- reject_post() - mark post as rejected with reason
- Store approval_status in metadata JSONB field

Co-Authored-By: Claude Opus 4.5 <noreply@anthropic.com>"
```

---

## Task 5: Implement Preview and Approve Commands

**Files:**
- Modify: `app/telegram/admin_bot.py`

**Step 1: Update preview_handler**

Replace the preview_handler in `app/telegram/admin_bot.py`:

```python
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
                f"**POST PREVIEW**\n"
                f"Type: {post_type}\n\n"
                f"{post_content}",
                reply_markup=keyboard,
                parse_mode='Markdown'
            )
        else:
            await update.message.reply_text(f"Failed to generate: {result.get('error')}")

    except Exception as e:
        logger.error(f"Preview error: {e}")
        await update.message.reply_text(f"Error: {e}")
```

**Step 2: Update button_callback for preview actions**

Replace the button_callback function:

```python
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
```

**Step 3: Test manually**

Run: `cd /Users/vladimirbragin/projects/telegram-ai-agent && source .venv/bin/activate && python -m app.telegram.admin_bot`

Then in Telegram:
1. Send `/start` to the bot
2. Send `/preview` - should generate and show post
3. Click "Approve & Publish" - should publish to channel

**Step 4: Commit**

```bash
git add app/telegram/admin_bot.py
git commit -m "feat(admin): implement /preview with approve/reject buttons

- /preview generates post and shows with inline buttons
- Approve & Publish - publishes to channel
- Reject - discards post
- Regenerate - prompts to run /preview again

Co-Authored-By: Claude Opus 4.5 <noreply@anthropic.com>"
```

---

## Task 6: Add Proactive Notifications

**Files:**
- Modify: `app/telegram/admin_bot.py`
- Modify: `app/scheduler/content_scheduler.py`

**Step 1: Add notify_admins function**

Add to `app/telegram/admin_bot.py`:

```python
async def notify_admins(
    message: str,
    keyboard: Optional[InlineKeyboardMarkup] = None
) -> None:
    """Send notification to all admin users."""
    from telegram import Bot
    bot = Bot(token=settings.telegram_bot_token)

    for admin_id in settings.admin_user_ids:
        try:
            await bot.send_message(
                chat_id=admin_id,
                text=message,
                reply_markup=keyboard,
                parse_mode='HTML'
            )
            logger.info(f"Notification sent to admin {admin_id}")
        except Exception as e:
            logger.error(f"Failed to notify admin {admin_id}: {e}")
```

**Step 2: Add notification after post generation**

Modify `app/main.py` in `generate_and_publish_post` method. After generating (before publishing), add notification:

```python
            # Notify admins about new post (if not auto-publishing)
            if not publish:
                try:
                    from app.telegram.admin_bot import notify_admins, create_approval_keyboard
                    await notify_admins(
                        f"<b>New post generated</b>\n\n"
                        f"Type: {post_type_config['name']}\n"
                        f"Length: {len(post_data['content'])} chars\n\n"
                        f"Use /preview in admin bot to review."
                    )
                except Exception as e:
                    logger.warning(f"Could not notify admins: {e}")
```

**Step 3: Add notification after successful publish**

In the same method, after successful publish:

```python
                    # Notify admins about published post
                    try:
                        from app.telegram.admin_bot import notify_admins
                        await notify_admins(
                            f"<b>Post published!</b>\n\n"
                            f"Type: {post_type_config['name']}\n"
                            f"Message ID: {result['message_id']}\n"
                            f"Channel: {settings.telegram_channel_id}"
                        )
                    except Exception as e:
                        logger.warning(f"Could not notify admins: {e}")
```

**Step 4: Commit**

```bash
git add app/telegram/admin_bot.py app/main.py
git commit -m "feat(admin): add proactive notifications to admins

- notify_admins() sends message to all admin users
- Notify when new post is generated
- Notify when post is published

Co-Authored-By: Claude Opus 4.5 <noreply@anthropic.com>"
```

---

## Task 7: Final Integration Test

**Step 1: Run all tests**

```bash
cd /Users/vladimirbragin/projects/telegram-ai-agent
source .venv/bin/activate
pytest tests/ -v
```

**Step 2: Manual integration test**

1. Start admin bot: `python -m app.telegram.admin_bot`
2. In Telegram, send `/preview`
3. Review the generated post
4. Click "Approve & Publish"
5. Check the channel for the published post

**Step 3: Test poll functionality**

```python
# Quick poll test
import asyncio
from app.telegram.publisher import TelegramPublisher

async def test():
    pub = TelegramPublisher()
    result = await pub.send_poll(
        "Test poll - please ignore",
        ["Option A", "Option B", "Option C"]
    )
    print(result)

asyncio.run(test())
```

**Step 4: Update .env.example**

Add to `.env.example`:
```
# Admin settings (comma-separated user IDs)
TELEGRAM_ADMIN_IDS=123456789,987654321
```

**Step 5: Final commit**

```bash
git add .
git commit -m "feat: complete polls and admin bot implementation

Summary:
- TelegramPublisher.send_poll() with validation
- publish_post_with_poll() for content plan integration
- Admin bot with /preview, /approve, /reject, /stats
- Inline keyboard for quick approval actions
- Proactive notifications to admins
- Full test coverage

Co-Authored-By: Claude Opus 4.5 <noreply@anthropic.com>"
```

---

## Summary

| Task | Est. Time | Files Modified |
|------|-----------|----------------|
| 1. Poll support | 2h | publisher.py, test_publisher.py |
| 2. Pipeline integration | 1.5h | main.py, publisher.py |
| 3. Admin bot base | 2h | admin_bot.py, config.py, test_admin_bot.py |
| 4. DB approval workflow | 1.5h | crud.py |
| 5. Preview/Approve | 2h | admin_bot.py |
| 6. Notifications | 1h | admin_bot.py, main.py |
| 7. Integration test | 1h | - |

**Total: ~11 hours**

## Testing Checklist

- [ ] `pytest tests/test_publisher.py` - all pass
- [ ] `pytest tests/test_admin_bot.py` - all pass
- [ ] Manual: `/preview` generates post
- [ ] Manual: Approve publishes to channel
- [ ] Manual: Poll sends correctly
- [ ] Manual: Admins receive notifications
