import logging
from typing import Dict, List, Optional, Union
from telegram import Bot, Update
from telegram.constants import ParseMode
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters
)
from telegram.error import TelegramError
from pathlib import Path
import json
from datetime import datetime
import asyncio

logger = logging.getLogger(__name__)

class TelegramBot:
    """Класс для управления Telegram-ботом и отправки уведомлений"""

    def __init__(self, token: str, chat_id: Union[str, int], config_path: str = "config.json"):
        self.token = token
        self.chat_id = chat_id
        self.config_path = Path(config_path)
        self.bot = Bot(token=token)
        self.application: Optional[Application] = None
        self._init_handlers()

    def _init_handlers(self):
        """Инициализация обработчиков команд"""
        self.command_handlers = {
            'start': self._handle_start,
            'stats': self._handle_stats,
            'positions': self._handle_positions,
            'stop': self._handle_stop,
            'config': self._handle_config
        }

    async def start_polling(self):
        """Запуск бота в режиме polling"""
        try:
            self.application = Application.builder().token(self.token).build()

            # Регистрация обработчиков
            for command, handler in self.command_handlers.items():
                self.application.add_handler(CommandHandler(command, handler))

            # Обработчик текстовых сообщений
            self.application.add_handler(
                MessageHandler(filters.TEXT & ~filters.COMMAND, self._handle_message)
            )

            logger.info("Starting Telegram bot in polling mode...")
            await self.application.run_polling()
        except Exception as e:
            logger.error(f"Failed to start Telegram bot: {str(e)}")
            raise

    async def send_message(self, 
                         text: str, 
                         parse_mode: Optional[str] = ParseMode.MARKDOWN,
                         reply_markup: Optional[Dict] = None) -> bool:
        """Асинхронная отправка сообщения"""
        try:
            await self.bot.send_message(
                chat_id=self.chat_id,
                text=text,
                parse_mode=parse_mode,
                reply_markup=reply_markup
            )
            return True
        except TelegramError as e:
            logger.error(f"Telegram send message error: {str(e)}")
            return False

    async def send_alert(self, alert_type: str, data: Dict) -> bool:
        """Отправка трейдингового алерта"""
        try:
            message = self._format_alert(alert_type, data)
            return await self.send_message(message)
        except Exception as e:
            logger.error(f"Failed to send alert: {str(e)}")
            return False

    def _format_alert(self, alert_type: str, data: Dict) -> str:
        """Форматирование трейдингового алерта"""
        if alert_type == "trade":
            return format_trade_message(data)
        elif alert_type == "signal":
            return format_signal_message(data)
        elif alert_type == "error":
            return f"🚨 *ERROR*\n{data.get('message', 'Unknown error')}"
        else:
            return json.dumps(data, indent=2)

    # Обработчики команд
    async def _handle_start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик команды /start"""
        await update.message.reply_text(
            "🤖 *Trading Bot Activated*\n\n"
            "Available commands:\n"
            "/stats - Performance metrics\n"
            "/positions - Current positions\n"
            "/config - Bot configuration\n"
            "/stop - Shutdown bot",
            parse_mode=ParseMode.MARKDOWN
        )

    async def _handle_stats(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик команды /stats"""
        stats = {"win_rate": 0.75, "pnl": 1500}
        await update.message.reply_text(
            f"📊 *Performance Stats*\n\n"
            f"• Win Rate: {stats['win_rate']:.2%}\n"
            f"• Total PnL: ${stats['pnl']:.2f}",
            parse_mode=ParseMode.MARKDOWN
        )

    async def _handle_config(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик команды /config"""
        try:
            with open(self.config_path) as f:
                config = json.load(f)
                await update.message.reply_text(
                    f"⚙️ *Current Config*\n\n"
                    f"```json\n{json.dumps(config, indent=2)}\n```",
                    parse_mode=ParseMode.MARKDOWN
                )
        except Exception as e:
            await update.message.reply_text(f"❌ Failed to load config: {str(e)}")

    async def _handle_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик текстовых сообщений"""
        await update.message.reply_text("ℹ️ Use commands to interact with bot")

# Функции модуля для прямого вызова
def format_trade_message(trade: Dict) -> str:
    """Форматирование сообщения о сделке"""
    return (
        f"🔄 *Trade Executed*\n\n"
        f"• Ticker: `{trade.get('ticker', 'N/A')}`\n"
        f"• Type: {trade.get('type', 'N/A')}\n"
        f"• Price: {trade.get('price', 0):.2f}\n"
        f"• Quantity: {trade.get('quantity', 0)}\n"
        f"• PnL: {trade.get('pnl', 0):.2f} ({trade.get('pnl_pct', 0):.2f}%)"
    )

def format_signal_message(signal: Dict) -> str:
    """Форматирование сообщения о сигнале"""
    return (
        f"🚦 *New Trading Signal*\n\n"
        f"• Ticker: `{signal.get('ticker', 'N/A')}`\n"
        f"• Direction: {signal.get('direction', 'N/A')}\n"
        f"• Confidence: {signal.get('confidence', 0):.2%}\n"
        f"• Price: {signal.get('price', 0):.2f}\n"
        f"• Stop Loss: {signal.get('stop_loss', 0):.2f}\n"
        f"• Take Profit: {signal.get('take_profit', 0):.2f}"
    )

async def send_alert(token: str, chat_id: Union[str, int], alert_type: str, data: Dict) -> bool:
    """Отправка алерта (обертка для удобного импорта)"""
    bot = TelegramBot(token=token, chat_id=chat_id)
    return await bot.send_alert(alert_type, data)

async def start_telegram_bot(token: str, chat_id: Union[str, int]):
    """Асинхронный запуск Telegram бота"""
    bot = TelegramBot(token=token, chat_id=chat_id)
    await bot.start_polling()