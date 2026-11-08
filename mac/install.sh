#!/bin/bash
# Qamyal для macOS: установка и обновление. Запуск из папки комплекта:  bash mac/install.sh
# Повторный запуск безопасен: обновляет программу, записи и настройки не трогает.
#
# Комплект (папка, собранная на Windows скриптом mac/make_kit.ps1):
#   app/     — программа (тот же код, что и в Windows)
#   mac/     — этот скрипт, оболочка окна и помощник звука на Swift, иконка
#   gigaam/  — исходники GigaAM (ставятся в Python)
#   models/  — GigaAM и разметка голосов (Whisper скачивается здесь)
set -euo pipefail

KIT="$(cd "$(dirname "$0")/.." && pwd)"
ROOT="${QAMYAL_ROOT:-$HOME/Qamyal}"
APPDIR="$HOME/Applications/Qamyal.app"
TARGET="arm64-apple-macos14.2"
step() { printf '\n\033[1m%s\033[0m\n' "$*"; }

step "1/7 Проверка системы"
[[ "$(uname -m)" == "arm64" ]] || { echo "Нужен Mac на Apple Silicon (M1–M4)."; exit 1; }
ver="$(sw_vers -productVersion)"; major="${ver%%.*}"; rest="${ver#*.}"; minor="${rest%%.*}"
if (( major < 14 || (major == 14 && minor < 2) )); then
  echo "Нужна macOS 14.2 или новее (сейчас $ver): только с ней можно записывать звук собеседников."; exit 1
fi
if ! xcode-select -p >/dev/null 2>&1; then
  xcode-select --install || true
  echo "Установите «Инструменты командной строки» в открывшемся окне и запустите install.sh ещё раз."; exit 1
fi
echo "macOS $ver, Apple Silicon — подходит"

step "2/7 Файлы программы → $ROOT"
mkdir -p "$ROOT"
if [[ "$KIT" != "$ROOT" ]]; then
  rsync -a --delete --exclude '__pycache__' --exclude 'settings.json' --exclude 'editor_cwd' \
        --exclude 'mac/' "$KIT/app/" "$ROOT/app/"
  rsync -a "$KIT/mac/" "$ROOT/mac/"
  if [[ -d "$KIT/models" ]]; then rsync -a "$KIT/models/" "$ROOT/models/"; fi
fi

step "3/7 Python 3.11 и библиотеки"
UV="$(command -v uv || true)"
if [[ -z "$UV" && -x "$HOME/.local/bin/uv" ]]; then UV="$HOME/.local/bin/uv"; fi
if [[ -z "$UV" ]]; then
  echo "Ставлю uv (менеджер Python от Astral)…"
  curl -LsSf https://astral.sh/uv/install.sh | sh
  UV="$HOME/.local/bin/uv"
fi
"$UV" venv --python 3.11 --allow-existing "$ROOT/.venv"
"$UV" pip install --python "$ROOT/.venv/bin/python" -r "$ROOT/mac/requirements-mac.txt" -r "$ROOT/mac/requirements-speech.txt"
"$UV" pip install --python "$ROOT/.venv/bin/python" "$KIT/gigaam"

step "4/7 Модели распознавания (в первый раз — около 2 ГБ)"
"$ROOT/.venv/bin/python" "$ROOT/mac/download_models.py" "$ROOT"

step "5/7 Помощник записи звука компьютера"
mkdir -p "$ROOT/app/mac"
swiftc -O -target "$TARGET" "$ROOT/mac/QamyalAudioTap.swift" -o "$ROOT/app/mac/QamyalAudioTap"
codesign --force --sign - "$ROOT/app/mac/QamyalAudioTap"
swiftc -O -target "$TARGET" "$ROOT/mac/QamyalCallScout.swift" -o "$ROOT/app/mac/QamyalCallScout"
codesign --force --sign - "$ROOT/app/mac/QamyalCallScout"
swiftc -O -target "$TARGET" "$ROOT/mac/QamyalScreen.swift" -o "$ROOT/app/mac/QamyalScreen" -framework AppKit -framework AVFoundation -framework CoreMedia -framework ScreenCaptureKit   # запись экрана и рамка
codesign --force --sign - "$ROOT/app/mac/QamyalScreen"

step "6/7 Приложение Qamyal.app"
BUILD="$(mktemp -d)"
A="$BUILD/Qamyal.app"
mkdir -p "$A/Contents/MacOS" "$A/Contents/Resources"
swiftc -O -target "$TARGET" "$ROOT/mac/QamyalApp.swift" -o "$A/Contents/MacOS/Qamyal" -framework Cocoa -framework WebKit

ICONSET="$BUILD/qamyal.iconset"
mkdir "$ICONSET"
for s in 16 32 128 256 512; do
  sips -z "$s" "$s" "$ROOT/mac/qamyal-1024.png" --out "$ICONSET/icon_${s}x${s}.png" >/dev/null
  sips -z "$((s * 2))" "$((s * 2))" "$ROOT/mac/qamyal-1024.png" --out "$ICONSET/icon_${s}x${s}@2x.png" >/dev/null
done
iconutil -c icns "$ICONSET" -o "$A/Contents/Resources/qamyal.icns"

cat > "$A/Contents/Info.plist" <<EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>CFBundleName</key><string>Qamyal</string>
  <key>CFBundleDisplayName</key><string>Qamyal</string>
  <key>CFBundleIdentifier</key><string>app.qamyal</string>
  <key>CFBundleExecutable</key><string>Qamyal</string>
  <key>CFBundleIconFile</key><string>qamyal</string>
  <key>CFBundlePackageType</key><string>APPL</string>
  <key>CFBundleShortVersionString</key><string>1.0</string>
  <key>CFBundleVersion</key><string>1</string>
  <key>LSMinimumSystemVersion</key><string>14.2</string>
  <key>LSApplicationCategoryType</key><string>public.app-category.productivity</string>
  <key>NSHighResolutionCapable</key><true/>
  <key>NSPrincipalClass</key><string>NSApplication</string>
  <key>NSMicrophoneUsageDescription</key><string>Qamyal записывает разговор с микрофона.</string>
  <key>NSAudioCaptureUsageDescription</key><string>Qamyal записывает голоса собеседников в созвонах — звук, который играет компьютер.</string>
  <key>NSAppTransportSecurity</key><dict><key>NSAllowsLocalNetworking</key><true/></dict>
  <key>QamyalRoot</key><string>$ROOT</string>
</dict>
</plist>
EOF
codesign --force --deep --sign - "$A"
mkdir -p "$HOME/Applications"
rm -rf "$APPDIR"
mv "$A" "$APPDIR"
rm -rf "$BUILD"

step "7/7 Готово"
echo "Программа: $APPDIR (перетащите её в Dock)."
echo "Данные: $ROOT/Записи. При первой записи macOS спросит доступ к микрофону и к записи системного звука."
open "$APPDIR"
