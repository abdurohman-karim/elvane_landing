#!/usr/bin/env bash
# Выкладка лендинга на elvane.cloud. Запускать на Mac из папки проекта:
#   ./deploy.sh            # хост по умолчанию — ssh elvane (root@79.132.143.211, ключ ~/.ssh/elvane_deploy)
#   ./deploy.sh user@host
# Сайт собирается здесь, на сервер едет только dist/. Повторный запуск = обновление.
# Nginx отдаёт файлы лендинга первыми, остальное (/v1, /c/…, /i/…) уходит в API —
# шаблон в elvane_backend/deploy/hestia/elvane.stpl.
set -euo pipefail

HOST="${1:-elvane}"
DOCROOT=/home/elvane/web/elvane.cloud/public_html
DIR="$DOCROOT/site"
URL=https://elvane.cloud/

cd "$(dirname "$0")"

echo ">>> Сборка"
[ -d node_modules ] || npm ci
npm run build

echo ">>> Выкладка в $HOST:$DIR"
# Сначала файлы с хешами в именах, потом index.html — пока идёт выкладка,
# старая страница не ссылается на уже удалённые файлы
ssh "$HOST" "mkdir -p '$DIR'"
rsync -rlz --exclude index.html dist/ "$HOST:$DIR/"
rsync -rlz --delete dist/ "$HOST:$DIR/"
ssh "$HOST" "chown -R elvane:elvane '$DIR' && find '$DIR' -type d -exec chmod 755 {} + && find '$DIR' -type f -exec chmod 644 {} +"

echo ">>> Проверка"
code=$(curl -s -o /dev/null -w '%{http_code}' "$URL")
if [ "$code" != 200 ] || ! curl -s "$URL" | grep -q '<div id="app">'; then
    echo "!!! $URL ответил $code или отдаёт не лендинг — проверьте шаблон nginx (deploy/hestia в elvane_backend)"
    exit 1
fi
curl -sf -o /dev/null "${URL}v1/health" || { echo "!!! API не отвечает на ${URL}v1/health"; exit 1; }
echo ">>> Готово: $URL"
