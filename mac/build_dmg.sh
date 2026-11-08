#!/bin/bash
# Собирает установочный образ Qamyal.dmg для других Mac (родные, близкие). Запускать на Mac Дэни,
# где есть Command Line Tools:
#   bash mac/build_dmg.sh [папка-комплекта] [куда положить dmg]
# Комплект — папка от mac/make_kit.ps1 (app/, mac/, gigaam/).
# Образ как у обычных программ: в окне Qamyal.app и ярлык «Программы» — перетащить и открыть.
# Программа едет внутри приложения (Contents/Resources/payload); при первом запуске приложение само
# ставит её в ~/Qamyal и качает Python (mac/setup.sh). Личного в образ не попадает:
# ни записей, ни голосов, ни settings.json, ни словаря.
set -euo pipefail

KIT="$(cd "${1:-$(dirname "$0")/..}" && pwd)"
OUT="${2:-$HOME/Desktop}"
TARGET="arm64-apple-macos14.2"
VERSION="$(date +%Y.%m.%d)"
BUILD="$(date +%Y%m%d%H%M)"            # по ней приложение понимает, что пора обновить ~/Qamyal
step() { printf '\n\033[1m%s\033[0m\n' "$*"; }

[[ -d "$KIT/app" && -d "$KIT/gigaam" ]] || { echo "Не похоже на комплект: $KIT"; exit 1; }

TMP="$(mktemp -d)"
STAGE="$TMP/Qamyal"
A="$STAGE/Qamyal.app"
R="$A/Contents/Resources"
P="$R/payload"
mkdir -p "$A/Contents/MacOS" "$P/bin" "$P/mac"

step "1/4 Программа внутри приложения"
rsync -a --exclude '__pycache__' --exclude 'settings.json' --exclude 'editor_cwd' --exclude '.ui-profile' \
      --exclude 'skype' --exclude 'scout' --exclude 'mac' "$KIT/app/" "$P/app/"
cp "$KIT/mac/requirements-mac.txt" "$KIT/mac/requirements-speech.txt" "$KIT/mac/update.sh" "$P/mac/"
rsync -a "$KIT/gigaam/" "$P/gigaam/"
cp "$KIT/mac/setup.sh" "$R/setup.sh"

step "2/4 Сборка Qamyal.app и помощника звука"
swiftc -O -target "$TARGET" "$KIT/mac/QamyalAudioTap.swift" -o "$P/bin/QamyalAudioTap"
codesign --force --sign - "$P/bin/QamyalAudioTap"
swiftc -O -target "$TARGET" "$KIT/mac/QamyalCallScout.swift" -o "$P/bin/QamyalCallScout"   # кто говорит в окнах Zoom, Teams…
codesign --force --sign - "$P/bin/QamyalCallScout"
swiftc -O -target "$TARGET" "$KIT/mac/QamyalScreen.swift" -o "$P/bin/QamyalScreen" -framework AppKit -framework AVFoundation -framework CoreMedia -framework ScreenCaptureKit   # запись экрана и рамка
codesign --force --sign - "$P/bin/QamyalScreen"
swiftc -O -target "$TARGET" "$KIT/mac/QamyalApp.swift" -o "$A/Contents/MacOS/Qamyal" -framework Cocoa -framework WebKit
ICONSET="$TMP/qamyal.iconset"
mkdir "$ICONSET"
for s in 16 32 128 256 512; do
  sips -z "$s" "$s" "$KIT/mac/qamyal-1024.png" --out "$ICONSET/icon_${s}x${s}.png" >/dev/null
  sips -z "$((s * 2))" "$((s * 2))" "$KIT/mac/qamyal-1024.png" --out "$ICONSET/icon_${s}x${s}@2x.png" >/dev/null
done
iconutil -c icns "$ICONSET" -o "$R/qamyal.icns"
# без ключа QamyalRoot: программа живёт в ~/Qamyal
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
  <key>CFBundleShortVersionString</key><string>$VERSION</string>
  <key>CFBundleVersion</key><string>$BUILD</string>
  <key>LSMinimumSystemVersion</key><string>14.2</string>
  <key>LSApplicationCategoryType</key><string>public.app-category.productivity</string>
  <key>NSHighResolutionCapable</key><true/>
  <key>NSPrincipalClass</key><string>NSApplication</string>
  <key>NSMicrophoneUsageDescription</key><string>Qamyal записывает разговор с микрофона.</string>
  <key>NSAudioCaptureUsageDescription</key><string>Qamyal записывает голоса собеседников в созвонах — звук, который играет компьютер.</string>
  <key>NSAppTransportSecurity</key><dict><key>NSAllowsLocalNetworking</key><true/></dict>
</dict>
</plist>
EOF
codesign --force --deep --sign - "$A"

step "3/4 Окно образа: Qamyal → «Программы»"
mkdir "$STAGE/.background"
# инструкция «Если Qamyal не открывается» — в RTF: TextEdit не гадает с кодировкой, команду можно скопировать
textutil -convert rtf -inputencoding UTF-8 -font "Helvetica" -fontsize 14 "$KIT/mac/Если Qamyal не открывается.txt" \
         -output "$STAGE/Если Qamyal не открывается.rtf"
# фон рисуется здесь же, на Mac (шрифт SF Pro Rounded), обычный и Retina — в одном TIFF
swiftc -O "$KIT/mac/make_dmg_background.swift" -o "$TMP/bgtool" 2>/dev/null
"$TMP/bgtool" "$TMP/bg.png" "$TMP/bg@2x.png"
tiffutil -cathidpicheck "$TMP/bg.png" "$TMP/bg@2x.png" -out "$STAGE/.background/background.tiff" >/dev/null
mkdir -p "$OUT" && cp "$TMP/bg@2x.png" "$OUT/preview-background.png"      # посмотреть фон без Mac
RW="$TMP/rw.dmg"
# временное имя тома: если открыт прошлый образ «Qamyal», Finder перепутал бы диски
VOL="QamyalBuild$$"
hdiutil create -volname "$VOL" -srcfolder "$STAGE" -fs HFS+ -format UDRW -ov "$RW" >/dev/null
DEV="$(hdiutil attach -readwrite -noverify -noautoopen "$RW" | awk '/Apple_HFS/ {print $1}')"
MNT="/Volumes/$VOL"
# раскладка окна — через Finder; если macOS не дала управлять Finder, образ всё равно рабочий, просто без фона
sleep 2                                   # Finder замечает новый диск не сразу
cat > "$TMP/layout.applescript" <<'EOS'
on run argv
tell application "Finder"
  -- ярлык Finder, а не символьная ссылка: у ссылки macOS 26 рисует пустой пунктирный квадрат вместо папки
  make new alias file at (POSIX file (item 2 of argv) as alias) to (POSIX file "/Applications" as alias) ¬
    with properties {name:"Программы"}
  tell disk (item 1 of argv)
    open
    set current view of container window to icon view
    set toolbar visible of container window to false
    set statusbar visible of container window to false
    set the bounds of container window to {200, 90, 840, 598}
    set opts to the icon view options of container window
    set arrangement of opts to not arranged
    set icon size of opts to 112
    set text size of opts to 13
    set background picture of opts to file ".background:background.tiff"
    set position of item "Qamyal.app" of container window to {160, 180}
    set position of item "Программы" of container window to {480, 180}
    try
      set position of item "Если Qamyal не открывается.rtf" of container window to {535, 352}
      set extension hidden of item "Если Qamyal не открывается.rtf" of container window to true
    end try
    update without registering applications
    delay 1
    close
  end tell
end tell
end run
EOS
# на сервере сборки (GitHub) Finder может не ответить — ждём не больше 2 минут
osascript "$TMP/layout.applescript" "$VOL" "$MNT" &
LAYOUT=$!
( sleep 120; kill "$LAYOUT" 2>/dev/null ) &
WATCH=$!
wait "$LAYOUT" || echo "  (Finder не разложил значки — образ без фона, но рабочий)"
kill "$WATCH" 2>/dev/null || true
[[ -e "$MNT/Программы" ]] || ln -s /Applications "$MNT/Программы"     # без Finder — хотя бы ссылка на «Программы»
chflags hidden "$MNT/.background" 2>/dev/null || true
sync
diskutil rename "$DEV" "Qamyal" >/dev/null
hdiutil detach "$DEV" >/dev/null

step "4/4 Образ диска"
mkdir -p "$OUT"
DMG="$OUT/Qamyal-$VERSION.dmg"
rm -f "$DMG"
hdiutil convert "$RW" -format ULMO -o "$DMG" >/dev/null
rm -rf "$TMP"
# для обновления изнутри Qamyal (app/update.py): номер этой сборки и имя образа
printf '{"build": "%s", "version": "%s", "dmg": "%s"}\n' "$BUILD" "$VERSION" "$(basename "$DMG")" > "$OUT/latest.json"
echo "Готово: $DMG ($(du -h "$DMG" | cut -f1))"
