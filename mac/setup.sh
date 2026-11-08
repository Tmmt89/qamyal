#!/bin/bash
# Qamyal для macOS: подготовка при первом запуске и после обновления. Запускает сама Qamyal.app
# (Contents/Resources/setup.sh <папка payload>), пользователь Терминала не видит: ход — строками
# «STEP <проценты> <текст>» в stdout, ошибка — «FAIL <текст>»; подробности — в ~/Qamyal/setup.log.
# Ставит программу из приложения в ~/Qamyal, качает uv, Python 3.11 и базовые библиотеки (~100 МБ).
# Распознавание, Whisper и Claude Code пользователь качает сам в Настройках → «Модели и дополнения».
set -uo pipefail

SRC="$1"
ROOT="$HOME/Qamyal"
UV_VERSION="0.12.15"
mkdir -p "$ROOT"
LOG="$ROOT/setup.log"
echo "=== $(date) ===" >>"$LOG"
rm -f "$ROOT/.setup-error"
step() { echo "STEP $1 $2"; echo "$2" >>"$LOG"; }
# текст ошибки — ещё и в файл: окно показывает его, даже если последняя строка stdout не успела дойти
die() { echo "FAIL $1"; echo "$1" >"$ROOT/.setup-error"; echo "ОШИБКА: $1" >>"$LOG"; exit 1; }

[[ "$(uname -m)" == "arm64" ]] || die "Qamyal работает только на Mac с процессором Apple (M1 и новее)."
free_gb=$(df -g "$HOME" | awk 'NR==2 {print $4}')
(( free_gb >= 3 )) || die "Мало места на диске: свободно $free_gb ГБ. Освободите хотя бы 3 ГБ и откройте Qamyal снова."

step 5 "Копирую программу"
mkdir -p "$ROOT/app/mac" "$ROOT/models" "$ROOT/mac" "$ROOT/bin"
{
  rsync -a --delete --exclude '__pycache__' --exclude 'settings.json' --exclude 'editor_cwd' --exclude 'mac/' \
        "$SRC/app/" "$ROOT/app/" &&
  rsync -a "$SRC/mac/" "$ROOT/mac/" &&
  rsync -a --delete "$SRC/gigaam/" "$ROOT/gigaam/" &&
  cp -f "$SRC/bin/QamyalAudioTap" "$ROOT/app/mac/QamyalAudioTap" &&
  cp -f "$SRC/bin/QamyalCallScout" "$ROOT/app/mac/QamyalCallScout" &&
  cp -f "$SRC/bin/QamyalScreen" "$ROOT/app/mac/QamyalScreen" &&
  chmod +x "$ROOT/app/mac/QamyalAudioTap" "$ROOT/app/mac/QamyalCallScout" "$ROOT/app/mac/QamyalScreen"
} >>"$LOG" 2>&1 || die "Не получилось скопировать программу в $ROOT."
# файлы пришли из скачанного образа: снимаем метку «из интернета», иначе macOS не даст запустить помощника звука
xattr -dr com.apple.quarantine "$ROOT" 2>/dev/null

UV="$ROOT/bin/uv"
if [[ "$("$UV" --version 2>/dev/null | awk '{print $2}')" != "$UV_VERSION" ]]; then
  step 15 "Скачиваю установщик Python"
  tmp="$(mktemp -d)"
  curl -fsSL --retry 3 --retry-all-errors --max-time 300 -o "$tmp/uv.tar.gz" \
       "https://github.com/astral-sh/uv/releases/download/$UV_VERSION/uv-aarch64-apple-darwin.tar.gz" >>"$LOG" 2>&1 \
    || die "Нет связи с интернетом. Подключитесь к сети и нажмите «Повторить»."
  tar -xzf "$tmp/uv.tar.gz" -C "$tmp" && cp -f "$tmp/uv-aarch64-apple-darwin/uv" "$UV" && chmod +x "$UV" \
    || die "Не получилось распаковать установщик Python."
  rm -rf "$tmp"
fi

step 35 "Скачиваю Python 3.11"
"$UV" venv --python 3.11 --allow-existing "$ROOT/.venv" >>"$LOG" 2>&1 \
  || die "Python не скачался — проверьте интернет и нажмите «Повторить»."

step 60 "Ставлю библиотеки программы"
"$UV" pip install --python "$ROOT/.venv/bin/python" -r "$ROOT/mac/requirements-mac.txt" >>"$LOG" 2>&1 \
  || die "Библиотеки не поставились — проверьте интернет и нажмите «Повторить»."

if [[ ! -f "$ROOT/app/settings.json" ]]; then
  # имя спросит само окно программы; итог делает Claude Code, если он уже есть на этом Mac
  editor="none"
  for c in "$HOME/.local/bin/claude" /opt/homebrew/bin/claude /usr/local/bin/claude; do
    [[ -x "$c" ]] && { editor="claude"; break; }
  done
  printf '{\n  "user_name": "",\n  "editor": "%s"\n}\n' "$editor" >"$ROOT/app/settings.json"
fi

step 100 "Готово"
