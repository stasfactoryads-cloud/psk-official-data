#!/usr/bin/env bash
# Создаёт приватный репозиторий на GitHub из папки psk-official-data и пушит первую версию.
# Запуск из папки psk-official-data:  bash setup_github.sh
# Нужно: git и gh (GitHub CLI), авторизованный через `gh auth login`.
set -euo pipefail

REPO_NAME="psk-official-data"
BRANCH="psk-official-data"

if ! command -v gh >/dev/null 2>&1; then
  echo "Не найден gh. Установите: brew install gh && gh auth login"; exit 1
fi
if ! gh auth status >/dev/null 2>&1; then
  echo "gh не авторизован. Выполните: gh auth login"; exit 1
fi

cd "$(dirname "$0")"

if [ ! -d .git ]; then
  git init -b main
fi

python3 build.py
git add -A
git commit -m "Initial structure: projects, build script, API output" || echo "Нет новых изменений для коммита"

if ! git remote get-url origin >/dev/null 2>&1; then
  gh repo create "$REPO_NAME" --private --source=. --remote=origin --push
else
  git push -u origin main
fi

git checkout -b "$BRANCH" 2>/dev/null || git checkout "$BRANCH"
git push -u origin "$BRANCH"

echo "Готово: $(gh repo view --json url -q .url) ветка $BRANCH"
