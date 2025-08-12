import asyncio
from datetime import datetime, time, timedelta
from typing import Dict, List, Optional, Tuple
import logging
from dataclasses import dataclass
from enum import Enum, auto
import pandas as pd
from pytz import timezone

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

class OvernightManager:
    """Менеджер управления позициями в overnight-период и перед выходными"""

    def __init__(self, config: Dict):
        self.config = config
        self.tz = timezone(config.get('timezone', 'Europe/Moscow'))
        self.close_before = self._parse_time(config.get('close_before', '18:40'))
        self.leverage_close_before = self._parse_time(
            config.get('leverage_close_before', '18:00')
        )
        self.check_dividends = config.get('check_dividends', True)
        self.max_overnight_positions = config.get('max_overnight_positions', 5)
        self.holidays = self._load_holidays()

    def _parse_time(self, time_str: str) -> time:
        """Конвертация строки времени в объект time"""
        return datetime.strptime(time_str, '%H:%M').time()

    def _load_holidays(self) -> List[datetime]:
        """Загрузка списка праздников (можно заменить на API)"""
        # В реальной реализации следует использовать API календаря
        return [
            datetime(2023, 1, 1).date(),
            datetime(2023, 1, 2).date(),
            # ... другие праздники
        ]

    async def check_overnight_actions(self, 
                                    positions: Dict[str, Dict],
                                    is_leveraged: bool = False) -> List[OvernightDecision]:
        """
        Определение необходимых действий перед закрытием торговой сессии
        
        Args:
            positions: Словарь текущих позиций
            is_leveraged: Флаг маржинальной торговли
            
        Returns:
            List[OvernightDecision]: Список решений по позициям
        """
        decisions = []
        now = datetime.now(self.tz)
        
        # Проверка на предстоящие выходные или праздники
        is_pre_holiday = self._is_pre_holiday(now)
        
        for ticker, pos in positions.items():
            # Для маржинальных позиций - обязательное закрытие
            if is_leveraged:
                decisions.append(OvernightDecision(
                    ticker=ticker,
                    action=OvernightAction.CLOSE,
                    quantity=abs(pos['quantity']),
                    reason="leverage_overnight_risk"
                ))
                continue
                
            # Проверка дивидендов для акций
            if self.check_dividends:
                dividend_check = await self._check_dividend_risk(ticker, now.date())
                if dividend_check:
                    decisions.append(OvernendDecision(
                        ticker=ticker,
                        action=OvernightAction.CLOSE,
                        quantity=pos['quantity'],
                        reason="dividend_risk",
                        details=dividend_check
                    ))
                    continue
                    
            # Проверка корпоративных событий
            corp_action = await self._check_corporate_actions(ticker, now.date())
            if corp_action:
                decisions.append(OvernightDecision(
                    ticker=ticker,
                    action=OvernightAction.ADJUST,
                    quantity=pos['quantity'],
                    reason=corp_action['type'],
                    details=corp_action
                ))
                continue
                
            # Стандартное overnight решение
            if is_pre_holiday or len(positions) > self.max_overnight_positions:
                action = OvernightAction.ADJUST
                quantity = int(pos['quantity'] * 0.5)  # Уменьшаем позицию наполовину
                reason = "pre_holiday" if is_pre_holiday else "too_many_positions"
            else:
                action = OvernightAction.HOLD
                quantity = None
                reason = None
                
            decisions.append(OvernightDecision(
                ticker=ticker,
                action=action,
                quantity=quantity,
                reason=reason
            ))
            
        return decisions

    def _is_pre_holiday(self, dt: datetime) -> bool:
        """Проверка, является ли дата предпраздничной"""
        next_day = dt.date() + timedelta(days=1)
        return next_day in self.holidays

    async def _check_dividend_risk(self, 
                                 ticker: str, 
                                 date: datetime.date) -> Optional[Dict]:
        """
        Проверка дивидендных рисков (заглушка - в реальности использовать API)
        
        Returns:
            Dict: Информация о дивидендах или None
        """
        # В реальной реализации следует использовать API дивидендов
        # Например: MOEX ISS или Tinkoff Corporate Actions
        return None

    async def _check_corporate_actions(self, 
                                     ticker: str, 
                                     date: datetime.date) -> Optional[Dict]:
        """
        Проверка корпоративных событий (сплиты, делисты и т.д.)
        
        Returns:
            Dict: Информация о событии или None
        """
        # В реальной реализации следует использовать API корп. действий
        return None

    def is_overnight_time(self, current_time: Optional[datetime] = None) -> bool:
        """Проверка, находится ли текущее время в overnight-периоде"""
        if not current_time:
            current_time = datetime.now(self.tz)
        
        close_time = datetime.combine(current_time.date(), self.close_before)
        open_time = datetime.combine(current_time.date() + timedelta(days=1), time(9, 50))
        
        return current_time >= close_time or current_time < open_time

    def time_until_close(self, current_time: Optional[datetime] = None) -> timedelta:
        """Оставшееся время до закрытия сессии"""
        if not current_time:
            current_time = datetime.now(self.tz)
            
        close_time = datetime.combine(current_time.date(), self.close_before)
        return close_time - current_time

    async def execute_overnight_actions(self,
                                      executor,
                                      decisions: List[OvernightDecision]) -> Dict:
        """
        Исполнение решений по overnight-позициям
        
        Args:
            executor: Объект для исполнения торговых операций
            decisions: Список решений от check_overnight_actions
            
        Returns:
            Dict: Результаты исполнения
        """
        results = {}
        for decision in decisions:
            try:
                if decision.action == OvernightAction.CLOSE:
                    if decision.quantity > 0:
                        action = 'sell'
                    else:
                        action = 'buy'
                        
                    result = await executor.execute_order(
                        ticker=decision.ticker,
                        action=action,
                        quantity=abs(decision.quantity),
                        reason=decision.reason
                    )
                    results[decision.ticker] = result
                    
                elif decision.action == OvernightAction.ADJUST:
                    # Закрываем часть позиции
                    close_qty = decision.quantity
                    current_qty = abs(decision.details.get('current_quantity', 0))
                    
                    if close_qty < current_qty:
                        if decision.details.get('quantity', 0) > 0:
                            action = 'sell'
                        else:
                            action = 'buy'
                            
                        result = await executor.execute_order(
                            ticker=decision.ticker,
                            action=action,
                            quantity=close_qty,
                            reason=decision.reason
                        )
                        results[decision.ticker] = result
                        
            except Exception as e:
                logger.error(f"Failed to execute overnight action for {decision.ticker}: {str(e)}")
                results[decision.ticker] = {'error': str(e)}
                
        return results

    async def prepare_market_open(self,
                                executor,
                                portfolio: Dict) -> Dict:
        """
        Подготовка к открытию рынка (проверка overnight-рисков)
        
        Args:
            executor: Объект для исполнения торговых операций
            portfolio: Текущий портфель
            
        Returns:
            Dict: Результаты проверки
        """
        # Здесь может быть проверка гэпов, новостей и т.д.
        return {'status': 'completed'}