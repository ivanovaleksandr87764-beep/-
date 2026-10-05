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

# Проверяем токен у Telegram, пока он не окажется рабочим
while true; do
  if [ ! -f .env ]; then
    read -r -p "Вставь токен бота из @BotFather и нажми Enter: " TOKEN </dev/tty
    TOKEN="$(echo "$TOKEN" | tr -d '[:space:]')"
    echo "BOT_TOKEN=$TOKEN" > .env
  fi
  set -a; . ./.env; set +a
  ME="$(curl -s "https://api.telegram.org/bot$BOT_TOKEN/getMe")"
  if echo "$ME" | grep -q '"ok":true'; then
    NAME="$(echo "$ME" | sed -n 's/.*"username":"\([^"]*\)".*/\1/p')"
    echo "Токен рабочий, бот @$NAME"
    break
  fi
  echo "❌ Telegram не принял этот токен. Возьми свежий в @BotFather (/mybots → бот → API Token) и вставь ещё раз."
  rm -f .env
done

if [ ! -d venv ]; then
  echo "Ставлю библиотеки (один раз, около минуты)..."
  python3 -m venv venv
fi
./venv/bin/pip install -q -r requirements.txt --disable-pip-version-check

echo ""
echo "✅ Бот запущен. Пока это окно открыто, бот работает."
echo "Мак не уснёт, пока бот включён. Остановить: Ctrl+C."
caffeinate -i ./venv/bin/python bot.py
