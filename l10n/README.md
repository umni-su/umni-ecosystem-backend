1. Установка зависимостей

```bash
# Установка Babel и Transifex CLI
pip install babel transifex-client
```

```bash
# Или добавить в requirements.txt
echo "babel>=2.9.0" > requirements.txt
echo "transifex-client>=0.14.0" >> requirements.txt
pip install -r requirements.txt
```

2. Создание структуры папок

```bash
# Создаем структуру каталогов

mkdir -p l10n/templates
mkdir -p l10n/ru/LC_MESSAGES
mkdir -p l10n/en/LC_MESSAGES

# Итоговая структура:

# project/
# └── l10n/
# ├── templates/
# ├── ru/
# │ └── LC_MESSAGES/
# └── en/
# └── LC_MESSAGES/
```

3. Извлечение строк из кода

```bash
# Извлекаем все строки из проекта в .pot файл

pybabel extract -o l10n/templates/messages.pot .

# Флаги для лучшего извлечения:

pybabel extract \
-F babel.cfg \ # Конфиг с настройками
-o l10n/templates/messages.pot \
--project="My App" \
--version="1.0.0" \
--copyright-holder="My Company" \
.
```

4. Создание конфига для Babel (опционально)

```ini
# babel.cfg
[python: **.py]
[jinja2: **/templates/**.html]
extensions = jinja2.ext.autoescape,jinja2.ext.with_
```

5. Инициализация языков

```bash
# Создаем PO файлы для каждого языка

pybabel init -i l10n/templates/messages.pot -d l10n -l en
pybabel init -i l10n/templates/messages.pot -d l10n -l ru

# После этого в l10n/en/LC_MESSAGES/ и l10n/ru/LC_MESSAGES/

# появятся messages.po файлы
```

6. Редактирование переводов
   Ручное редактирование PO файлов:

```po

# l10n/ru/LC_MESSAGES/messages.po

msgid "Welcome to our application!"
msgstr "Добро пожаловать в наше приложение!"

msgid "User profile"
msgstr "Профиль пользователя"

msgid "There is {count} user online"
msgid_plural "There are {count} users online"
msgstr[0] "Онлайн {count} пользователь"
msgstr[1] "Онлайн {count} пользователя"
msgstr[2] "Онлайн {count} пользователей"
```

7. Компиляция MO файлов

```bash
# Компилируем PO в MO файлы

pybabel compile -d l10n

# Компиляция конкретного языка

pybabel compile -d l10n -l ru
pybabel compile -d l10n -l en

# Принудительная компиляция (даже если переводы не завершены)

pybabel compile -d l10n -f
```

8. Обновление переводов при изменении кода

```bash
# Когда добавляете новые строки _("...") в код:

# 1. Обновляем .pot файл

pybabel extract -o l10n/templates/messages.pot .

# 2. Обновляем PO файлы

pybabel update -i l10n/templates/messages.pot -d l10n

# 3. Компилируем MO файлы

pybabel compile -d l10n
```