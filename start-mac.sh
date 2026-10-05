#!/bin/bash
# Запуск бота на Маке одной командой:
# bash <(curl -sL https://raw.githubusercontent.com/ivanovaleksandr87764-beep/-/main/start-mac.sh)
set -e
DIR="$HOME/ozarenie-bot"
mkdir -p "$DIR"
cd "$DIR"

echo "Скачиваю свежую версию бота..."
curl -sL https://github.com/ivanovaleksandr87764-beep/-/archive/refs/heads/main.zip -o bot.zip
unzip -qo bot.zip
cp -f -- --main/*.py --main/requirements.txt .
rm -rf -- bot.zip --main

if [ ! -d venv ]; then
  echo "Ставлю библиотеки (один раз, около минуты)..."
  python3 -m venv venv
fi
./venv/bin/pip install -q -r requirements.txt

if [ ! -f .env ]; then
  read -r -p "Вставь токен бота из @BotFather и нажми Enter: " TOKEN </dev/tty
  echo "BOT_TOKEN=$TOKEN" > .env
fi
set -a; . ./.env; set +a

echo ""
echo "✅ Бот запущен. Пока это окно открыто, бот работает."
echo "Мак не уснёт, пока бот включён. Остановить: Ctrl+C."
caffeinate -i ./venv/bin/python bot.py
