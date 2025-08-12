import numpy as np
import pandas as pd
from typing import Dict, List, Optional, Tuple, Union
import logging
from dataclasses import dataclass
from enum import Enum, auto
from datetime import datetime

logger = logging.getLogger(__name__)

class RiskLevel(Enum):
    """Уровни риска для управления торговлей"""
    LOW = auto()        # Низкий риск (нормальные условия)
    MODERATE = auto()   # Умеренный риск (повышенная волатильность)
    HIGH = auto()       # Высокий риск (критические условия)
    EXTREME = auto()    # Экстремальный риск (рыночные потрясения)

@dataclass
class PositionRisk:
    """Данные о риске позиции"""
    ticker: str
    entry_price: float
    current_price: float
    volume: int
    risk_score: float
    stop_loss: Optional[float] = None
    take_profit: Optional[float] = None
    last_updated: datetime = datetime.now()

class PositionSizer:
    """Калькулятор размера позиции с учетом риска"""
    
    def __init__(self, risk_per_trade: float = 0.01):
        """
        :param risk_per_trade: процент риска на одну сделку (1% по умолчанию)
        """
        self.risk_per_trade = risk_per_trade
    
    def calculate(self, capital: float, entry_price: float, stop_loss: float) -> Tuple[int, float]:
        """
        Расчет размера позиции
        
        :param capital: доступный капитал
        :param entry_price: цена входа
        :param stop_loss: цена стоп-лосса
        :return: (размер позиции, фактический риск)
        """
        risk_per_share = abs(entry_price - stop_loss)
        if risk_per_share <= 0:
            return 0, 0.0
            
        position_size = int((capital * self.risk_per_trade) / risk_per_share)
        actual_risk = (position_size * risk_per_share) / capital
        return position_size, actual_risk

class MaxDrawdownCalculator:
    """Калькулятор максимальной просадки"""
    
    def __init__(self, max_allowed_drawdown: float = 0.05):
        """
        :param max_allowed_drawdown: максимально допустимая просадка (5% по умолчанию)
        """
        self.max_drawdown = max_allowed_drawdown
        self.peak_value = 0.0
        self.current_drawdown = 0.0
    
    def update(self, current_value: float) -> bool:
        """
        Обновление состояния просадки
        
        :param current_value: текущее значение капитала/портфеля
        :return: True если превышен лимит просадки
        """
        if current_value > self.peak_value:
            self.peak_value = current_value
            self.current_drawdown = 0.0
        else:
            self.current_drawdown = (self.peak_value - current_value) / self.peak_value
            
        return self.current_drawdown > self.max_drawdown

class LeverageController:
    """Контроллер кредитного плеча"""
    
    def __init__(self, max_leverage: int = 3):
        """
        :param max_leverage: максимальное допустимое плечо (3x по умолчанию)
        """
        self.max_leverage = max_leverage
    
    def validate(self, positions: Dict[str, Dict], capital: float) -> bool:
        """
        Проверка соблюдения лимитов плеча
        
        :param positions: текущие позиции
        :param capital: доступный капитал
        :return: True если лимиты не превышены
        """
        total_exposure = sum(abs(p['volume'] * p['price']) for p in positions.values())
        leverage = total_exposure / capital
        if leverage > self.max_leverage:
            logger.warning(f"Leverage {leverage:.2f}x exceeds max allowed {self.max_leverage}x")
            return False
        return True

class RiskManager:
    """Комплексная система управления рисками торгового бота"""

    def __init__(self, config: Dict):
        """
        :param config: конфигурация риск-менеджмента
        """
        self.config = config
        self.risk_level = RiskLevel.LOW
        self.portfolio_risk = 0.0
        self.daily_loss_limit = config.get('daily_loss_limit', 0.02)  # 2% по умолчанию
        self.position_risks: Dict[str, PositionRisk] = {}
        
        # Подкомпоненты
        self.position_sizer = PositionSizer(config.get('position_risk', 0.01))
        self.drawdown_calculator = MaxDrawdownCalculator(config.get('max_drawdown', 0.05))
        self.leverage_controller = LeverageController(config.get('max_leverage', 3))

    def calculate_position_size(self, 
                             capital: float, 
                             entry_price: float, 
                             stop_loss: float) -> Tuple[int, float]:
        """
        Расчет оптимального размера позиции с учетом риска
        """
        return self.position_sizer.calculate(capital, entry_price, stop_loss)

    def validate_signal(self, 
                      signal: Dict, 
                      current_positions: Dict) -> bool:
        """
        Проверка торгового сигнала на соответствие риск-параметрам
        """
        # Проверка максимального количества позиций
        max_positions = self.config.get('max_active_positions', 5)
        if len(current_positions) >= max_positions:
            logger.warning(f"Max positions limit reached: {max_positions}")
            return False

        # Проверка плеча
        if not self.leverage_controller.validate(current_positions, signal.get('capital', 1)):
            return False

        # Проверка стоп-лосса
        if not self._validate_stop_loss(signal):
            return False

        return True

    def _validate_stop_loss(self, signal: Dict) -> bool:
        """Проверка корректности стоп-лосса"""
        if 'stop_loss' not in signal:
            if self.config.get('stop_loss_required', True):
                logger.warning("Stop loss is required but not provided")
                return False
            return True

        price = signal['price']
        stop_loss = signal['stop_loss']
        max_loss_pct = self.config.get('max_loss_pct', 0.05)  # 5% по умолчанию

        # Проверка логики стоп-лосса
        if (signal['action'] == 'buy' and stop_loss >= price) or \
           (signal['action'] == 'sell' and stop_loss <= price):
            logger.warning(f"Invalid stop loss {stop_loss} for {signal['action']} at {price}")
            return False

        # Проверка размера стоп-лосса
        loss_pct = abs(price - stop_loss) / price
        if loss_pct > max_loss_pct:
            logger.warning(f"Stop loss {loss_pct:.2%} exceeds max allowed {max_loss_pct:.2%}")
            return False

        return True

    def update_risk_level(self, 
                        portfolio_value: float, 
                        drawdown: float, 
                        volatility: float):
        """
        Обновление уровня риска на основе рыночных условий
        """
        # Расчет комплексного показателя риска
        risk_score = 0.4 * drawdown + 0.6 * volatility
        self.portfolio_risk = risk_score
        
        # Определение уровня риска
        if risk_score < 0.02:
            self.risk_level = RiskLevel.LOW
        elif risk_score < 0.05:
            self.risk_level = RiskLevel.MODERATE
        elif risk_score < 0.1:
            self.risk_level = RiskLevel.HIGH
        else:
            self.risk_level = RiskLevel.EXTREME
            
        logger.info(f"Updated risk level: {self.risk_level.name} (score: {risk_score:.4f})")

    def check_daily_loss(self, 
                       initial_balance: float, 
                       current_balance: float) -> bool:
        """
        Проверка превышения дневного лимита убытков
        """
        loss_pct = (initial_balance - current_balance) / initial_balance
        if loss_pct > self.daily_loss_limit:
            logger.critical(f"Daily loss limit exceeded: {loss_pct:.2%} > {self.daily_loss_limit:.2%}")
            return True
        return False

    def adjust_for_overnight(self, 
                           positions: Dict, 
                           is_leveraged: bool = False) -> List[Dict]:
        """
        Генерация корректирующих ордеров для ночного периода
        """
        adjustments = []
        for ticker, pos in positions.items():
            if is_leveraged:
                # Полное закрытие маржинальных позиций
                adjustments.append({
                    'ticker': ticker,
                    'action': 'sell' if pos['volume'] > 0 else 'buy',
                    'volume': abs(pos['volume']),
                    'reason': 'overnight_leverage_close'
                })
            elif self.risk_level in [RiskLevel.HIGH, RiskLevel.EXTREME]:
                # Частичное закрытие при высоком риске
                close_pct = 0.5 if self.risk_level == RiskLevel.HIGH else 0.8
                close_volume = int(pos['volume'] * close_pct)
                if close_volume > 0:
                    adjustments.append({
                        'ticker': ticker,
                        'action': 'sell',
                        'volume': close_volume,
                        'reason': f'risk_reduction_{self.risk_level.name.lower()}'
                    })
        
        return adjustments

    def calculate_trailing_stop(self, 
                              ticker: str, 
                              current_price: float, 
                              peak_price: float) -> Optional[float]:
        """
        Расчет динамического трейлинг-стопа
        """
        if ticker not in self.position_risks:
            return None
            
        position = self.position_risks[ticker]
        trail_pct = self.config.get('trailing_stop_pct', 0.02)  # 2% по умолчанию
        
        # Расчет нового стоп-лосса
        if position.volume > 0:  # Для длинных позиций
            new_stop = peak_price * (1 - trail_pct)
            if position.stop_loss is None or new_stop > position.stop_loss:
                return new_stop
        else:  # Для коротких позиций
            new_stop = peak_price * (1 + trail_pct)
            if position.stop_loss is None or new_stop < position.stop_loss:
                return new_stop
        
        return position.stop_loss

    def update_position_risk(self, 
                           ticker: str, 
                           entry_price: float, 
                           current_price: float, 
                           volume: int):
        """Обновление метрик риска для позиции"""
        risk_score = abs(current_price - entry_price) / entry_price * np.sign(volume)
        self.position_risks[ticker] = PositionRisk(
            ticker=ticker,
            entry_price=entry_price,
            current_price=current_price,
            volume=volume,
            risk_score=risk_score,
            last_updated=datetime.now()
        )

    def get_risk_report(self) -> Dict:
        """Генерация отчета о текущих рисках"""
        return {
            'risk_level': self.risk_level.name,
            'portfolio_risk': round(self.portfolio_risk, 4),
            'current_drawdown': round(self.drawdown_calculator.current_drawdown, 4),
            'positions_at_risk': [
                {k: v for k, v in pos.__dict__.items() if k != 'last_updated'}
                for pos in self.position_risks.values() 
                if abs(pos.risk_score) > 0.03  # Позиции с риском > 3%
            ]
        }