#!/usr/bin/env bash
# ================================================================
#  JARVIS MAX — Build APK Release (Linux/macOS/Git Bash)
# ================================================================
set -e

echo ""
echo "  JarvisMax — Build APK Release"
echo "  =============================="
echo ""

# Vérifier Flutter
if ! command -v flutter &>/dev/null; then
    echo "[ERREUR] Flutter n'est pas installé ou pas dans le PATH."
    echo ""
    echo "  Pour installer : https://docs.flutter.dev/get-started/install"
    exit 1
fi

echo "[1/3] flutter pub get..."
flutter pub get

echo ""
echo "[2/3] flutter doctor..."
flutter doctor

echo ""
echo "[3/3] flutter build apk --release..."
flutter build apk --release --no-shrink

APK_PATH="build/app/outputs/flutter-apk/app-release.apk"
if [ -f "$APK_PATH" ]; then
    SIZE=$(du -h "$APK_PATH" | cut -f1)
    echo ""
    echo "================================================================"
    echo "  APK généré avec succès !"
    echo ""
    echo "  Chemin : $APK_PATH"
    echo "  Taille : $SIZE"
    echo "================================================================"
else
    echo "[ERREUR] APK introuvable."
    exit 1
fi
