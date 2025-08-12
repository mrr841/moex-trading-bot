# Trading Bot for MOEX & Tinkoff

[![Python 3.9+](https://img.shields.io/badge/python-3.9%2B-blue)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)

Многофункциональный торговый бот для Московской биржи (MOEX) и Tinkoff Invest с поддержкой:
- Трендовых и контртрендовых стратегий
- Управления рисками
- Overnight-торговли
- Telegram-мониторинга

## 📌 Особенности

- **Поддержка API**: MOEX ISS и Tinkoff Invest API
- **Режимы работы**: Реальный/Песочница/Бэктест
- **Аналитика**: 15+ технических индикаторов
- **Риск-менеджмент**: Stop-Loss, Take-Profit, позиционный расчет
- **Уведомления**: Telegram-бот для алертов

## 🚀 Быстрый старт

### Предварительные требования
- Python 3.9+
- Tinkoff Invest API token
- Учетная запись MOEX ISS (для исторических данных)

### Установка
```bash
# Клонирование репозитория
git clone https://github.com/yourusername/trading-bot.git
cd trading-bot

# Создание виртуального окружения
python -m venv venv
source venv/bin/activate  # Linux/Mac
venv\Scripts\activate  # Windows

# Установка зависимостей
pip install -r requirements.txt

# Настройка конфигурации
cp config.example.json config.json
cp .env.example .env