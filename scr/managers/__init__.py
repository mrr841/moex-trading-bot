"""
Managers Module - ядро логики управления торговым ботом
"""

from .risk_manager import (
    RiskManager,
    PositionSizer,
    MaxDrawdownCalculator,
    LeverageController,
    RiskLevel,
    PositionRisk
)

from .strategy_manager import (
    StrategyManager,
    SignalGenerator
)

from .regime_detector import (
    MarketRegimeDetector,
    detect_trend,
    detect_volatility_regime,
    detect_liquidity_regime
)

from .overnight_manager import (
    OvernightManager,
    RolloverAnalyzer,
    DividendChecker,
    CorporateActionHandler
)

from enum import Enum, auto
import logging
from typing import Dict, Any

__all__ = [
    # Risk Management
    'RiskManager',
    'PositionSizer',
    'MaxDrawdownCalculator',
    'LeverageController',
    'RiskLevel',
    'PositionRisk',
    
    # Strategy
    'StrategyManager',
    'SignalGenerator',
    'StrategyBacktester',
    
    # Market Regimes
    'MarketRegimeDetector',
    'detect_trend',
    'detect_volatility_regime',
    'detect_liquidity_regime',
    
    # Overnight
    'OvernightManager',
    'RolloverAnalyzer',
    'DividendChecker',
    'CorporateActionHandler'
]

class ManagerType(Enum):
    RISK = auto()
    STRATEGY = auto()
    REGIME = auto()
    OVERNIGHT = auto()

__version__ = '1.2.0'

# Настройка логгера модуля
_logger = logging.getLogger(__name__)
_logger.info(f'Managers module v{__version__} initialized')

# Константы модуля
DEFAULT_THRESHOLDS = {
    'max_drawdown': 0.05,
    'daily_loss_limit': 0.02,
    'position_size': 0.1
}

def get_manager_config(manager_type: ManagerType) -> Dict[str, Any]:
    """Возвращает конфигурацию по умолчанию для каждого типа менеджера"""
    configs = {
        ManagerType.RISK: {
            'max_leverage': 3,
            'stop_loss_enabled': True,
            'trailing_stop': 0.01
        },
        ManagerType.STRATEGY: {
            'signal_expiry': '5m',
            'confirmations_required': 2
        },
        ManagerType.REGIME: {
            'volatility_window': 14,
            'trend_window': 21
        },
        ManagerType.OVERNIGHT: {
            'close_before': '18:40',
            'check_dividends': True
        }
    }
    return configs.get(manager_type, {})