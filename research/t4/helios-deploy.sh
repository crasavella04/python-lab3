#!/bin/sh
# Единственная команда, доступная ключу деплоя на Helios (forced command).
#
# Установка на Helios:
#   mkdir -p ~/bin && cp helios-deploy.sh ~/bin/deploy-python-lab3 && chmod 700 ~/bin/deploy-python-lab3
# В ~/.ssh/authorized_keys строку ключа деплоя дополнить ограничениями (одной строкой):
#   restrict,command="$HOME/bin/deploy-python-lab3" ssh-ed25519 AAAA... github-actions
# ($HOME в authorized_keys не раскрывается — указать полный путь, например /home/s564180/bin/...)
#
# Что это даёт: с украденным ключом можно только заменить сайт python-lab3.
# Нельзя получить shell, читать другие файлы, пробросить порты или агент (restrict).
# Команда, которую присылает клиент, игнорируется: сервер всегда выполняет этот скрипт,
# который читает tar.gz из stdin.
set -eu

DEST="$HOME/public_html/python-lab3"
NEW="$DEST.new.$$"
OLD="$DEST.old.$$"
MAX_BYTES=104857600   # 100 МБ распакованного архива — защита от заполнения квоты

cleanup() { rm -rf "$NEW"; }
trap cleanup EXIT

mkdir -p "$NEW"
# Распаковка во временный каталог: недокачанный архив не испортит работающий сайт
tar -xzf - -C "$NEW"

# Отказ, если в архиве ссылки (могут указывать за пределы каталога) или слишком много данных
if find "$NEW" -type l | grep -q .; then
    echo "deploy: в архиве есть символические ссылки, отказ" >&2
    exit 1
fi
size=$(du -sk "$NEW" | cut -f1)
if [ $((size * 1024)) -gt "$MAX_BYTES" ]; then
    echo "deploy: архив больше лимита ($size КБ), отказ" >&2
    exit 1
fi
[ -f "$NEW/index.html" ] || { echo "deploy: нет index.html, отказ" >&2; exit 1; }

chmod -R a+rX "$NEW"
# Подмена каталога двумя переименованиями: сайт не бывает наполовину обновлённым
[ -d "$DEST" ] && mv "$DEST" "$OLD"
mv "$NEW" "$DEST"
rm -rf "$OLD"
echo "deploy: ok"
