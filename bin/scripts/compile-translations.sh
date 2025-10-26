#!/bin/bash
# compile-translations.sh

echo "🔨 Compiling translations..."

# Компилируем основные переводы
pybabel compile -d l10n -D messages

# Компилируем UI переводы
pybabel compile -d l10n -D ui

echo "✅ Translations compiled successfully!"