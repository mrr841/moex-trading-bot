import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Tuple
import logging
from pathlib import Path
import json
import seaborn as sns
from matplotlib.ticker import FuncFormatter

logger = logging.getLogger(__name__)

plt.style.use('seaborn-v0_8')
sns.set_palette("husl")

class ReportGenerator:
    """Генератор торговых отчетов и аналитики"""

    def __init__(self, reports_dir: str = "reports"):
        self.reports_dir = Path(reports_dir)
        self.reports_dir.mkdir(exist_ok=True)
        self._init_template_engine()

    def _init_template_engine(self):
        """Инициализация шаблонов отчетов"""
        self.templates = {
            'trade': self._load_template('trade_report'),
            'performance': self._load_template('performance_report'),
            'risk': self._load_template('risk_report')
        }

    def _load_template(self, template_name: str) -> Dict:
        """Загрузка шаблона отчета"""
        template_path = Path(__file__).parent / 'templates' / f'{template_name}.json'
        try:
            with open(template_path) as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Failed to load template {template_name}: {str(e)}")
            return {}

    def generate_trade_report(self, 
                            trades: List[Dict],
                            report_type: str = 'detailed') -> Dict:
        """
        Генерация отчета по сделкам
        
        Args:
            trades: Список сделок
            report_type: Тип отчета ('detailed' или 'summary')
            
        Returns:
            Dict: Отчет в формате {metrics: {}, charts: []}
        """
        if not trades:
            return {'error': 'No trades data provided'}

        df = self._prepare_trades_dataframe(trades)
        report = {
            'metrics': self._calculate_trade_metrics(df),
            'charts': [],
            'trades': df.to_dict('records')
        }

        # Генерация графиков для детального отчета
        if report_type == 'detailed':
            report['charts'] = [
                self._create_pnl_chart(df),
                self._create_trades_distribution_chart(df),
                self._create_daily_performance_chart(df)
            ]

        return report

    def _prepare_trades_dataframe(self, trades: List[Dict]) -> pd.DataFrame:
        """Подготовка DataFrame из списка сделок"""
        df = pd.DataFrame(trades)
        
        # Конвертация временных меток
        df['entry_time'] = pd.to_datetime(df['entry_time'])
        df['exit_time'] = pd.to_datetime(df['exit_time'])
        
        # Расчет длительности сделок
        df['duration'] = (df['exit_time'] - df['entry_time']).dt.total_seconds() / 60
        
        # Расчет PnL
        df['pnl'] = df['exit_price'] - df['entry_price']
        df['pnl_pct'] = df['pnl'] / df['entry_price'] * 100
        
        # Маркировка прибыльных/убыточных сделок
        df['is_profitable'] = df['pnl'] > 0
        
        return df

    def _calculate_trade_metrics(self, df: pd.DataFrame) -> Dict:
        """Расчет ключевых метрик"""
        total_trades = len(df)
        profitable_trades = df['is_profitable'].sum()
        
        return {
            'total_trades': total_trades,
            'win_rate': profitable_trades / total_trades if total_trades > 0 else 0,
            'avg_pnl': df['pnl'].mean(),
            'median_pnl': df['pnl'].median(),
            'max_profit': df['pnl'].max(),
            'max_loss': df['pnl'].min(),
            'profit_factor': abs(df[df['is_profitable']]['pnl'].sum() / 
                            df[~df['is_profitable']]['pnl'].sum()) if total_trades > 0 else 0,
            'avg_trade_duration': df['duration'].mean()
        }

    def _create_pnl_chart(self, df: pd.DataFrame) -> Dict:
        """График кумулятивного PnL"""
        df = df.sort_values('exit_time')
        df['cumulative_pnl'] = df['pnl'].cumsum()
        
        fig, ax = plt.subplots(figsize=(12, 6))
        ax.plot(df['exit_time'], df['cumulative_pnl'], label='Cumulative PnL')
        ax.set_title('Cumulative Profit/Loss')
        ax.set_xlabel('Date')
        ax.set_ylabel('PnL')
        ax.grid(True)
        ax.legend()
        
        chart_path = self._save_chart(fig, 'cumulative_pnl')
        plt.close(fig)
        
        return {
            'type': 'line',
            'title': 'Cumulative PnL',
            'path': chart_path
        }

    def generate_performance_analytics(self, 
                                     portfolio_history: Dict,
                                     benchmark: Optional[Dict] = None) -> Dict:
        """
        Анализ эффективности портфеля
        
        Args:
            portfolio_history: История изменения портфеля
            benchmark: Данные бенчмарка (например, IMOEX)
            
        Returns:
            Dict: Отчет с метриками и графиками
        """
        df = pd.DataFrame(portfolio_history)
        df['date'] = pd.to_datetime(df['date'])
        df.set_index('date', inplace=True)
        
        # Расчет дневной доходности
        df['daily_return'] = df['value'].pct_change()
        
        report = {
            'metrics': self._calculate_performance_metrics(df),
            'charts': [
                self._create_equity_curve_chart(df, benchmark),
                self._create_drawdown_chart(df),
                self._create_returns_distribution_chart(df)
            ]
        }
        
        return report

    def _calculate_performance_metrics(self, df: pd.DataFrame) -> Dict:
        """Расчет метрик эффективности"""
        total_return = (df['value'].iloc[-1] / df['value'].iloc[0] - 1) * 100
        daily_returns = df['daily_return'].dropna()
        
        return {
            'total_return': total_return,
            'annualized_return': self._annualize_returns(daily_returns),
            'annualized_volatility': daily_returns.std() * np.sqrt(252),
            'sharpe_ratio': self._calculate_sharpe(daily_returns),
            'max_drawdown': self._calculate_max_drawdown(df['value']),
            'calmar_ratio': self._calculate_calmar_ratio(daily_returns, df['value'])
        }

    def _annualize_returns(self, daily_returns: pd.Series) -> float:
        """Годовая доходность"""
        if len(daily_returns) < 2:
            return 0
        return ((1 + daily_returns.mean()) ** 252 - 1) * 100

    def _calculate_sharpe(self, daily_returns: pd.Series) -> float:
        """Коэффициент Шарпа"""
        if len(daily_returns) < 2 or daily_returns.std() == 0:
            return 0
        return (daily_returns.mean() / daily_returns.std()) * np.sqrt(252)

    def _save_chart(self, fig, name: str) -> str:
        """Сохранение графика в файл"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        chart_path = self.reports_dir / f"{name}_{timestamp}.png"
        fig.savefig(chart_path, bbox_inches='tight')
        return str(chart_path)

    def save_report(self, report: Dict, report_name: str) -> str:
        """Сохранение отчета в JSON"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        report_path = self.reports_dir / f"{report_name}_{timestamp}.json"
        
        with open(report_path, 'w') as f:
            json.dump(report, f, indent=2)
            
        return str(report_path)

# Функции модуля для прямого вызова
def generate_trade_report(trades: List[Dict], report_type: str = 'detailed') -> Dict:
    """Генерация отчета по сделкам (фасадная функция)"""
    return ReportGenerator().generate_trade_report(trades, report_type)

def generate_performance_analytics(portfolio_history: Dict, benchmark: Dict = None) -> Dict:
    """Анализ эффективности портфеля (фасадная функция)"""
    return ReportGenerator().generate_performance_analytics(portfolio_history, benchmark)

def create_backtest_visualization(backtest_results: Dict) -> Dict:
    """Визуализация результатов бэктеста"""
    # Реализация аналогична generate_performance_analytics
    pass

def prepare_daily_summary(portfolio: Dict, trades: List[Dict]) -> Dict:
    """Подготовка ежедневного отчета"""
    # Краткая сводка за день
    pass