import asyncio
from typing import Dict, List, Optional, Union
import logging
from datetime import datetime
import aiohttp
from dataclasses import asdict
import json

from src.trading import (
    Order,
    ExecutionReport,
    OrderStatus,
    OrderType,
    BrokerType,
    TradeError
)
from src.data.data_handler import DataHandler

logger = logging.getLogger(__name__)

class TradeExecutor:
    """Исполнитель торговых операций с поддержкой мультиброкерского API"""

    def __init__(self, config: Dict, data_handler: DataHandler):
        self.config = config
        self.data_handler = data_handler
        self.broker_type = BrokerType(config['api_source'].split('_')[-1].upper())
        self.session = None
        self._order_counter = 0
        self._active_orders: Dict[str, Order] = {}

    async def __aenter__(self):
        self.session = aiohttp.ClientSession(
            headers=self._get_auth_headers(),
            timeout=aiohttp.ClientTimeout(total=10)
        )
        return self

    async def __aexit__(self, exc_type, exc, tb):
        if self.session:
            await self.session.close()
        self._active_orders.clear()

    def _get_auth_headers(self) -> Dict:
        """Получение заголовков авторизации для API"""
        if self.broker_type == BrokerType.TINKOFF:
            token = self.config['api_settings']['tinkoff']['token']
            return {
                'Authorization': f'Bearer {token}',
                'Content-Type': 'application/json'
            }
        return {}

    async def execute_order(self, order: Order) -> ExecutionReport:
        """
        Основной метод исполнения ордера
        
        Args:
            order: Торговый ордер
            
        Returns:
            ExecutionReport: Отчет об исполнении
            
        Raises:
            TradeError: В случае ошибки исполнения
        """
        try:
            # Валидация ордера
            if not self._validate_order(order):
                raise TradeError("Invalid order parameters")

            # Регистрация ордера
            self._register_order(order)

            # Исполнение в зависимости от типа брокера
            if self.broker_type == BrokerType.TINKOFF:
                report = await self._execute_tinkoff_order(order)
            elif self.broker_type == BrokerType.MOEX:
                report = await self._execute_moex_order(order)
            else:
                raise TradeError(f"Unsupported broker: {self.broker_type}")

            # Обновление статуса ордера
            self._update_order_status(report)

            logger.info(f"Order executed: {order.order_id} {order.ticker} "
                       f"{order.order_type.name} {order.quantity}@{order.price}")
            return report

        except Exception as e:
            logger.error(f"Order execution failed: {str(e)}")
            self._update_order_status(OrderStatus.FAILED)
            raise TradeError(f"Execution failed: {str(e)}")

    async def _execute_tinkoff_order(self, order: Order) -> ExecutionReport:
        """Исполнение ордера через Tinkoff API"""
        url = "https://invest-public-api.tinkoff.ru/rest/tinkoff.public.invest.api.contract.v1.OrdersService/PostOrder"
        
        payload = {
            "figi": await self.data_handler.get_figi(order.ticker),
            "quantity": order.quantity,
            "price": self._apply_slippage(order.price),
            "direction": "ORDER_DIRECTION_BUY" if order.order_type == OrderType.BUY else "ORDER_DIRECTION_SELL",
            "accountId": self.config['api_settings']['tinkoff']['account_id'],
            "orderType": "ORDER_TYPE_LIMIT",  # Можно добавить другие типы
            "orderId": order.order_id
        }

        async with self.session.post(url, json=payload) as resp:
            if resp.status != 200:
                error = await resp.text()
                raise TradeError(f"Tinkoff API error: {error}")

            data = await resp.json()
            return ExecutionReport(
                order_id=order.order_id,
                execution_time=datetime.now(),
                filled_quantity=data['executedOrderQuantity'],
                fill_price=data['executedOrderPrice'],
                commission=data['commission'],
                remaining_quantity=data['requestedLots'] - data['executedLots']
            )

    async def _execute_moex_order(self, order: Order) -> ExecutionReport:
        """Исполнение ордера через MOEX API (имитация)"""
        # В реальной реализации нужно использовать MOEX ISS API
        await asyncio.sleep(0.1)  # Имитация задержки
        
        return ExecutionReport(
            order_id=order.order_id,
            execution_time=datetime.now(),
            filled_quantity=order.quantity,
            fill_price=order.price,
            commission=0.0,
            remaining_quantity=0
        )

    def _register_order(self, order: Order):
        """Регистрация нового ордера в системе"""
        if not order.order_id:
            order.order_id = self._generate_order_id()
        order.status = OrderStatus.PENDING
        self._active_orders[order.order_id] = order

    def _generate_order_id(self) -> str:
        """Генерация уникального ID ордера"""
        self._order_counter += 1
        return f"{datetime.now().strftime('%Y%m%d')}_{self._order_counter}"

    def _update_order_status(self, report: ExecutionReport):
        """Обновление статуса ордера на основе отчета"""
        order = self._active_orders.get(report.order_id)
        if not order:
            return

        if report.remaining_quantity == 0:
            order.status = OrderStatus.FILLED
        elif report.filled_quantity > 0:
            order.status = OrderStatus.PARTIALLY_FILLED
        else:
            order.status = OrderStatus.REJECTED

        order.filled_quantity = report.filled_quantity
        order.avg_fill_price = report.fill_price

    def _apply_slippage(self, price: float) -> float:
        """Применение проскальзывания к цене"""
        slippage = self.config.get('slippage', 0.001)
        return price * (1 + slippage)

    def _validate_order(self, order: Order) -> bool:
        """Проверка валидности ордера"""
        if order.quantity <= 0:
            return False
        if order.price <= 0:
            return False
        if order.ticker not in self.config['tickers']:
            return False
        return True

    async def cancel_order(self, order_id: str) -> bool:
        """Отмена активного ордера"""
        if order_id not in self._active_orders:
            return False

        order = self._active_orders[order_id]
        if order.status not in [OrderStatus.PENDING, OrderStatus.PARTIALLY_FILLED]:
            return False

        try:
            if self.broker_type == BrokerType.TINKOFF:
                url = "https://invest-public-api.tinkoff.ru/rest/tinkoff.public.invest.api.contract.v1.OrdersService/CancelOrder"
                payload = {
                    "accountId": self.config['api_settings']['tinkoff']['account_id'],
                    "orderId": order_id
                }
                async with self.session.post(url, json=payload) as resp:
                    if resp.status != 200:
                        return False

            order.status = OrderStatus.CANCELLED
            return True

        except Exception as e:
            logger.error(f"Order cancellation failed: {str(e)}")
            return False

    async def get_order_status(self, order_id: str) -> Optional[Order]:
        """Получение текущего статуса ордера"""
        return self._active_orders.get(order_id)

    async def close_all_positions(self) -> List[ExecutionReport]:
        """Закрытие всех активных позиций"""
        reports = []
        for order in self._active_orders.values():
            if order.status in [OrderStatus.PENDING, OrderStatus.PARTIALLY_FILLED]:
                try:
                    report = await self.execute_order(Order(
                        order_id=f"close_{order.order_id}",
                        ticker=order.ticker,
                        order_type=OrderType.SELL if order.order_type == OrderType.BUY else OrderType.BUY,
                        price=await self.data_handler.get_last_price(order.ticker),
                        quantity=order.quantity - order.filled_quantity,
                        timestamp=datetime.now()
                    ))
                    reports.append(report)
                except TradeError as e:
                    logger.error(f"Failed to close position {order.ticker}: {str(e)}")
        return reports