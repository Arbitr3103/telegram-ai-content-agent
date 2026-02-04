"""Tests for Admin Bot"""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch


class TestAdminAuthorization:
    @patch('app.telegram.admin_bot.settings')
    def test_is_admin_returns_true_for_admin(self, mock_settings):
        """Test admin check returns True for admin user"""
        mock_settings.admin_user_ids = [123, 456]

        from app.telegram.admin_bot import is_admin

        assert is_admin(123) is True
        assert is_admin(456) is True

    @patch('app.telegram.admin_bot.settings')
    def test_is_admin_returns_false_for_non_admin(self, mock_settings):
        """Test admin check returns False for non-admin user"""
        mock_settings.admin_user_ids = [123, 456]

        from app.telegram.admin_bot import is_admin

        assert is_admin(789) is False
