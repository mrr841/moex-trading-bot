"""
Core module of the trading bot.

Exports:
- TradingBot: Main bot class
- StateManager: State management system
- BotState: Bot state enum
"""

from .bot import TradingBot
from .state_manager import StateManager, BotState

__all__ = ['TradingBot', 'StateManager', 'BotState']