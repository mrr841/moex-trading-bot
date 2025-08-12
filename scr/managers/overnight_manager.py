import asyncio
from datetime import datetime, time, timedelta, date
from typing import Dict, List, Optional, Union
import logging
from dataclasses import dataclass, field
from enum import Enum, auto
from pytz import timezone
from ..data.data_handler import DataHandler

logger = logging.getLogger(__name__)

class OvernightAction(Enum):
    HOLD = auto()
    CLOSE = auto()
    ADJUST = auto()
    HEDGE = auto()

@dataclass
class OvernightDecision:
    ticker: str
    action: OvernightAction
    quantity: Optional[int] = None
    reason: Optional[str] = None
    details: Dict = field(default_factory=dict)

class CorporateActionHandler:
    """Обработчик корпоративных действий"""
    def __init__(self, config: dict, data_handler: DataHandler):
        self.config = config
        self.data_handler = data_handler

    async def check_corporate_actions(self, ticker: str, current_date: date) -> Optional[Dict]:
        """
        Проверка корпоративных действий для тикера
        Возвращает dict с данными или None, если действий нет
        """
        try:
            # Здесь должна быть реализация проверки корпоративных действий
            # Заглушка для примера:
            if ticker == "GAZP":
                return {
                    'type': 'split',
                    'date': (current_date + timedelta(days=5)).isoformat(),
                    'ratio': 2,
                    'message': 'Предстоящий сплит 2:1'
                }
            return None
        except Exception as e:
            logger.error(f"Error checking corporate actions for {ticker}: {e}")
            return None

class DividendChecker:
    """Проверка дивидендных рисков с использованием DataHandler"""
    def __init__(self, config: dict, data_handler: DataHandler):
        self.config = config
        self.data_handler = data_handler
        self.dividend_threshold = config.get('dividend_threshold', 0.05)
        self.days_before_record = config.get('dividend_days_before', 2)

    async def check_dividend(self, ticker: str, current_date: date) -> Optional[Dict]:
        """Проверка дивидендов для тикера"""
        try:
            div_data = await self._fetch_dividend_data(ticker)
            if not div_data:
                return None

            relevant_divs = [
                d for d in div_data 
                if d['record_date'] and 
                current_date <= d['record_date'] <= (current_date + timedelta(days=30))
            ]

            if not relevant_divs:
                return None

            closest_div = min(relevant_divs, key=lambda x: x['record_date'])
            current_price = await self.data_handler.get_last_price(ticker)
            if not current_price:
                logger.warning(f"Couldn't get price for {ticker}")
                return None

            div_yield = closest_div['amount'] / current_price

            if div_yield >= self.dividend_threshold:
                days_to_record = (closest_div['record_date'] - current_date).days
                if days_to_record <= self.days_before_record:
                    return {
                        'amount': closest_div['amount'],
                        'currency': closest_div.get('currency', 'RUB'),
                        'record_date': closest_div['record_date'].isoformat(),
                        'yield': round(div_yield, 4),
                        'current_price': current_price,
                        'days_to_record': days_to_record,
                        'message': f'Высокий дивидендный риск ({div_yield:.1%})'
                    }
        except Exception as e:
            logger.error(f"Error checking dividend for {ticker}: {e}")
        return None

    async def _fetch_dividend_data(self, ticker: str) -> List[Dict]:
        """Получение данных о дивидендах"""
        cache_key = f"dividends_{ticker}"
        if cached := await self.data_handler.cache.get(cache_key):
            return cached

        try:
            if self.config['api_source'].startswith('moex'):
                data = await self._fetch_moex_dividends(ticker)
            else:
                data = await self._fetch_tinkoff_dividends(ticker)
            
            await self.data_handler.cache.set(cache_key, data, ttl=86400)
            return data
        except Exception as e:
            logger.error(f"Failed to fetch dividends for {ticker}: {e}")
            return []

    async def _fetch_moex_dividends(self, ticker: str) -> List[Dict]:
        """Получение дивидендов с MOEX ISS"""
        url = f"{self.data_handler.moex_base_url}/securities/{ticker}/dividends.json"
        async with self.data_handler.session.get(url) as resp:
            resp.raise_for_status()
            data = await resp.json()

        dividends = []
        for item in data['dividends']['data']:
            record_date = datetime.strptime(item[3], '%Y-%m-%d').date() if item[3] else None
            dividends.append({
                'isin': item[0],
                'amount': float(item[1]),
                'currency': item[2],
                'record_date': record_date,
                'payment_date': datetime.strptime(item[4], '%Y-%m-%d').date() if item[4] else None
            })
        return dividends

    async def _fetch_tinkoff_dividends(self, ticker: str) -> List[Dict]:
        """Получение дивидендов с Tinkoff API"""
        figi = await self.data_handler._get_figi(ticker)
        endpoint = f"{self.data_handler.tinkoff_base_url}/tinkoff.public.invest.api.contract.v1.InstrumentsService/GetDividends"
        
        payload = {
            "figi": figi,
            "from": (datetime.now() - timedelta(days=365)).isoformat() + 'Z',
            "to": (datetime.now() + timedelta(days=365)).isoformat() + 'Z'
        }

        async with self.data_handler.session.post(endpoint, json=payload) as resp:
            resp.raise_for_status()
            data = await resp.json()

        dividends = []
        for div in data['dividends']:
            dividends.append({
                'amount': self.data_handler._quotation_to_float(div['dividend_net']),
                'currency': div['dividend_net']['currency'],
                'record_date': datetime.strptime(div['record_date'], '%Y-%m-%dT%H:%M:%SZ').date(),
                'payment_date': datetime.strptime(div['payment_date'], '%Y-%m-%dT%H:%M:%SZ').date(),
                'status': div['dividend_status']
            })
        return dividends

class RolloverAnalyzer:
    """Анализатор ролловера фьючерсов"""
    def __init__(self, config: Dict):
        self.config = config
        self.rollover_threshold_days = config.get('rollover_threshold_days', 5)

    async def analyze(self, ticker: str, current_date: date, futures_info: Dict) -> Optional[Dict]:
        """Анализ необходимости ролловера"""
        expiry_date = futures_info.get('expiry_date')
        days_to_expiry = (expiry_date - current_date).days if expiry_date else None

        if days_to_expiry is not None and days_to_expiry <= self.rollover_threshold_days:
            return {
                'type': 'rollover',
                'days_to_expiry': days_to_expiry,
                'expiry_date': expiry_date.isoformat(),
                'message': f'Ролловер через {days_to_expiry} дней'
            }
        return None

class OvernightManager:
    """Управление позициями на ночь и выходные"""
    def __init__(self, config: Dict, data_handler: DataHandler):
        self.config = config
        self.data_handler = data_handler
        self.tz = timezone(config.get('timezone', 'Europe/Moscow'))
        self.close_before = self._parse_time(config.get('close_before', '18:40'))
        self.leverage_close_before = self._parse_time(
            config.get('leverage_close_before', '18:00')
        )
        self.check_dividends = config.get('check_dividends', True)
        self.max_overnight_positions = config.get('max_overnight_positions', 5)
        self.holidays = self._load_holidays()
        self.rollover_analyzer = RolloverAnalyzer(config)
        self.dividend_checker = DividendChecker(config, data_handler)
        self.corporate_action_handler = CorporateActionHandler(config, data_handler)

    def _parse_time(self, time_str: str) -> time:
        """Парсинг времени из строки"""
        return datetime.strptime(time_str, '%H:%M').time()

    def _load_holidays(self) -> List[date]:
        """Загрузка праздников"""
        return [
            date(2023, 1, 1), date(2023, 1, 2), date(2023, 1, 3),
            date(2023, 1, 4), date(2023, 1, 5), date(2023, 1, 6),
            date(2023, 1, 7), date(2023, 2, 23), date(2023, 3, 8),
            date(2023, 5, 1), date(2023, 5, 9), date(2023, 6, 12),
            date(2023, 11, 4),
        ]

    def _is_weekend(self, date_: date) -> bool:
        """Проверка выходного дня"""
        return date_.weekday() >= 5

    def _is_pre_holiday(self, dt: datetime) -> bool:
        """Проверка предпраздничного дня"""
        next_day = dt.date() + timedelta(days=1)
        return next_day in self.holidays or self._is_weekend(next_day)

    async def check_overnight_actions(self,
                                    positions: Dict[str, Dict],
                                    is_leveraged: bool = False,
                                    current_time: Optional[datetime] = None,
                                    futures_info: Optional[Dict[str, Dict]] = None
                                    ) -> List[OvernightDecision]:
        """Определение действий перед закрытием сессии"""
        decisions = []
        if not current_time:
            current_time = datetime.now(self.tz)

        is_pre_holiday = self._is_pre_holiday(current_time)
        total_positions = len(positions)
        
        for ticker, pos in positions.items():
            qty = pos.get('quantity', 0)
            abs_qty = abs(qty)

            if is_leveraged:
                leverage_close_dt = datetime.combine(current_time.date(), self.leverage_close_before, tzinfo=self.tz)
                if current_time >= leverage_close_dt:
                    decisions.append(OvernightDecision(
                        ticker=ticker,
                        action=OvernightAction.CLOSE,
                        quantity=abs_qty,
                        reason="leverage_overnight_risk"
                    ))
                    continue

            if self.check_dividends:
                dividend_check = await self._check_dividend_risk(ticker, current_time.date())
                if dividend_check:
                    decisions.append(OvernightDecision(
                        ticker=ticker,
                        action=OvernightAction.CLOSE,
                        quantity=qty,
                        reason="dividend_risk",
                        details=dividend_check
                    ))
                    continue

            corp_action = await self._check_corporate_actions(ticker, current_time.date())
            if corp_action:
                decisions.append(OvernightDecision(
                    ticker=ticker,
                    action=OvernightAction.ADJUST,
                    quantity=qty,
                    reason=corp_action.get('type', 'corporate_action'),
                    details=corp_action
                ))
                continue

            if futures_info and ticker in futures_info:
                rollover_decision = await self.rollover_analyzer.analyze(
                    ticker, current_time.date(), futures_info[ticker]
                )
                if rollover_decision:
                    decisions.append(OvernightDecision(
                        ticker=ticker,
                        action=OvernightAction.ADJUST,
                        quantity=abs_qty,
                        reason="rollover_required",
                        details=rollover_decision
                    ))
                    continue

            if is_pre_holiday or total_positions > self.max_overnight_positions:
                reduced_qty = int(qty * 0.5)
                if reduced_qty == 0:
                    decisions.append(OvernightDecision(
                        ticker=ticker,
                        action=OvernightAction.HOLD,
                        reason="position_too_small_to_reduce"
                    ))
                else:
                    decisions.append(OvernightDecision(
                        ticker=ticker,
                        action=OvernightAction.ADJUST,
                        quantity=abs(reduced_qty),
                        reason="pre_holiday" if is_pre_holiday else "too_many_positions"
                    ))
            else:
                decisions.append(OvernightDecision(
                    ticker=ticker,
                    action=OvernightAction.HOLD
                ))

        return decisions

    async def execute_overnight_actions(self, executor, decisions: List[OvernightDecision]) -> Dict[str, Dict]:
        """Исполнение решений по позициям"""
        results = {}
        for decision in decisions:
            try:
                if decision.action == OvernightAction.CLOSE:
                    if decision.quantity is None or decision.quantity == 0:
                        logger.warning(f"Close action without quantity for {decision.ticker}")
                        continue
                    action_type = 'sell' if decision.quantity > 0 else 'buy'
                    result = await executor.execute_order(
                        ticker=decision.ticker,
                        action=action_type,
                        quantity=abs(decision.quantity),
                        reason=decision.reason
                    )
                    results[decision.ticker] = result

                elif decision.action == OvernightAction.ADJUST:
                    if decision.quantity is None or decision.quantity == 0:
                        logger.warning(f"Adjust action without quantity for {decision.ticker}")
                        continue
                    current_qty = decision.details.get('current_quantity', None)
                    action_type = 'sell' if current_qty > 0 else 'buy' if current_qty is not None else 'sell'
                    result = await executor.execute_order(
                        ticker=decision.ticker,
                        action=action_type,
                        quantity=abs(decision.quantity),
                        reason=decision.reason
                    )
                    results[decision.ticker] = result

                elif decision.action == OvernightAction.HEDGE:
                    pass

                elif decision.action == OvernightAction.HOLD:
                    results[decision.ticker] = {'status': 'held'}

            except Exception as e:
                logger.error(f"Error executing action for {decision.ticker}: {e}")
        return results

    async def _check_dividend_risk(self, ticker: str, date: date) -> Optional[Dict]:
        """Проверка дивидендных рисков"""
        return await self.dividend_checker.check_dividend(ticker, date)

    async def _check_corporate_actions(self, ticker: str, date: date) -> Optional[Dict]:
        """Проверка корпоративных действий"""
        return await self.corporate_action_handler.check_corporate_actions(ticker, date)

    def is_overnight_time(self, current_time: Optional[datetime] = None) -> bool:
        """Проверка ночного периода"""
        if not current_time:
            current_time = datetime.now(self.tz)
        close_dt = datetime.combine(current_time.date(), self.close_before, tzinfo=self.tz)
        open_dt = datetime.combine(current_time.date() + timedelta(days=1), time(9, 50), tzinfo=self.tz)
        return current_time >= close_dt or current_time < open_dt

    def time_until_close(self, current_time: Optional[datetime] = None) -> timedelta:
        """Время до закрытия сессии"""
        if not current_time:
            current_time = datetime.now(self.tz)
        close_dt = datetime.combine(current_time.date(), self.close_before, tzinfo=self.tz)
        return close_dt - current_time