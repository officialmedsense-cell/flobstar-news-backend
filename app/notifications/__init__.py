"""
Notifications package for Flobstar News Intelligence.
"""

from .telegram import telegram, TelegramNotifier

__all__ = ["telegram", "TelegramNotifier"]
