import gettext
from pathlib import Path
from typing import Dict
from fastapi import Request

from classes.logger.logger import Logger
from classes.logger.logger_types import LoggerType


class GettextTranslator:
    """Улучшенный переводчик с поддержкой UI переводов"""

    def __init__(self, domain: str = "messages", locale_dir: str = "l10n", default_lang: str = "en"):
        self.domain = domain
        self.locale_dir = Path(locale_dir)
        self.default_lang = default_lang
        self.translations = {}
        self.ui_translations = {}  # Кэш для UI переводов
        self.plugin_translations = {}  # Кэш для переводов плагинов

    def set_language(self, lang: str) -> str:
        """Установка языка по умолчанию"""
        self.default_lang = lang
        return self.default_lang

    def get_default_lang(self):
        return self.default_lang

    def get_current_language(self, request: Request = None, accept_language: str = None) -> str:
        """
        Определение языка из запроса с fallback на default

        Args:
            request: FastAPI Request объект
            accept_language: Заголовок Accept-Language

        Returns:
            Код языка (например, 'en', 'ru')
        """
        if accept_language:
            lang = accept_language.split(',')[0].split('-')[0].lower()
        elif request and request.headers.get('accept-language'):
            lang = request.headers.get('accept-language').split(',')[0].split('-')[0].lower()
        else:
            lang = self.default_lang

        # Проверяем доступность языка
        available_langs = self.get_available_languages()
        return lang if lang in available_langs else self.default_lang

    def get_translation(self, lang: str) -> gettext.NullTranslations:
        """Получение объекта перевода для языка"""
        if lang not in self.translations:
            try:
                translation = gettext.translation(
                    self.domain,
                    localedir=str(self.locale_dir),
                    languages=[lang],
                    fallback=True
                )
                self.translations[lang] = translation
            except FileNotFoundError:
                self.translations[lang] = gettext.NullTranslations()

        return self.translations[lang]

    def _load_ui_translations(self, lang: str) -> Dict[str, str]:
        """Загрузка UI переводов из PO файла"""
        if lang in self.ui_translations:
            return self.ui_translations[lang]

        ui_translations = {}
        try:
            import polib
            po_file_path = self.locale_dir / lang / "LC_MESSAGES" / "ui.po"
            if po_file_path.exists():
                po = polib.pofile(str(po_file_path))
                for entry in po:
                    if entry.msgstr:  # Только переведенные строки
                        ui_translations[entry.msgid] = entry.msgstr
        except ImportError:
            # Fallback: используем gettext если polib не установлен
            ui_translation = gettext.translation(
                "ui",
                localedir=str(self.locale_dir),
                languages=[lang],
                fallback=True
            )
            # К сожалению, gettext не предоставляет простого способа получить все переводы
            pass

        self.ui_translations[lang] = ui_translations
        return ui_translations

    def get_ui_translations_json(self, lang: str = None) -> Dict[str, str]:
        """
        Получение всех UI переводов в формате JSON

        Returns:
            Словарь с переводами для фронтенда
        """
        lang = lang or self.default_lang
        return self._load_ui_translations(lang)

    def _(self, message: str, lang: str = None, **kwargs) -> str:
        """Основная функция перевода (для Python кода)"""
        lang = lang or self.default_lang
        translation = self.get_translation(lang)
        translated = translation.gettext(message)

        if kwargs:
            try:
                return translated.format(**kwargs)
            except (KeyError, ValueError):
                return translated
        return translated

    def ui(self, key: str, lang: str = None, **kwargs) -> str:
        """
        Перевод для UI элементов

        Args:
            key: Ключ перевода из UI PO файла
            lang: Язык перевода
            **kwargs: Параметры для подстановки

        Returns:
            Переведенная строка или ключ если перевод не найден
        """
        lang = lang or self.default_lang
        ui_translations = self._load_ui_translations(lang)

        translated = ui_translations.get(key, key)  # Fallback to key if not found

        if kwargs:
            try:
                return translated.format(**kwargs)
            except (KeyError, ValueError):
                return translated
        return translated

    def ngettext(self, singular: str, plural: str, count: int, lang: str = None, **kwargs) -> str:
        """Плюрализация"""
        lang = lang or self.default_lang
        translation = self.get_translation(lang)

        translated = translation.ngettext(singular, plural, count)

        if kwargs:
            try:
                return translated.format(**kwargs)
            except (KeyError, ValueError):
                return translated
        return translated

    def get_available_languages(self) -> list:
        """Получение списка доступных языков"""
        languages = []
        for item in self.locale_dir.iterdir():
            if item.is_dir() and item.name != "templates":
                languages.append({
                    "key": item.name,
                    "selected": self.default_lang == item.name
                })
        return languages

    # Добавляем в класс GettextTranslator

    def add_plugin_translations(self, plugin_name: str, plugin_locale_dir: Path):
        """Добавление переводов плагина в общую систему"""
        try:
            # Компилируем MO файлы если нужно
            # self._compile_plugin_translations(plugin_locale_dir, plugin_name)

            # Создаем отдельный домен для плагина
            domain = f"messages"

            # Загружаем переводы плагина
            for lang_dir in plugin_locale_dir.iterdir():
                if lang_dir.is_dir() and lang_dir.name != "templates":
                    lang = lang_dir.name

                    try:
                        plugin_translation = gettext.translation(
                            domain,
                            localedir=str(plugin_locale_dir),
                            languages=[lang],
                            fallback=True
                        )

                        # Сохраняем в отдельном кэше плагинов
                        if lang not in self.plugin_translations:
                            self.plugin_translations[lang] = {}
                        self.plugin_translations[lang][plugin_name] = plugin_translation

                    except FileNotFoundError:
                        # Переводы для этого языка не найдены - игнорируем
                        pass

            Logger.info(f"Translations for plugin {plugin_name} loaded", LoggerType.PLUGINS)

        except Exception as e:
            Logger.err(f"Error loading translations for plugin {plugin_name}: {str(e)}", LoggerType.PLUGINS)

    def _compile_plugin_translations(self, plugin_locale_dir: Path, plugin_name: str):
        """Компиляция PO в MO файлы для плагина"""
        try:
            import polib

            for lang_dir in plugin_locale_dir.iterdir():
                if lang_dir.is_dir():
                    lc_messages_dir = lang_dir / "LC_MESSAGES"
                    po_file = lc_messages_dir / f"messages.po"
                    mo_file = lc_messages_dir / f"messages.mo"

                    if po_file.exists() and (not mo_file.exists() or po_file.stat().st_mtime > mo_file.stat().st_mtime):
                        po = polib.pofile(str(po_file))
                        po.save_as_mofile(str(mo_file))

        except ImportError:
            # polib не установлен - пропускаем компиляцию
            pass
        except Exception as e:
            Logger.err(f"Error compiling plugin translations: {str(e)}", LoggerType.PLUGINS)

    def get_plugin_translation(self, message: str, plugin_name: str, lang: str = None) -> str:
        """Получение перевода для плагина"""
        # Используем переданный язык или default_lang
        lang = lang or self.default_lang

        # Сначала проверяем переводы плагина
        if (lang in self.plugin_translations and
                plugin_name in self.plugin_translations[lang]):
            plugin_translation = self.plugin_translations[lang][plugin_name]
            translated = plugin_translation.gettext(message)
            if translated != message:  # Если нашли перевод в плагине
                return translated
            else:
                print(f"DEBUG: No plugin translation found for '{message}'")
        else:
            print(f"DEBUG: No plugin translations for lang '{lang}' or plugin '{plugin_name}'")

        # Fallback к основным переводам
        main_translation = self.get_translation(lang)
        main_translated = main_translation.gettext(message)
        print(f"DEBUG: Main translation: '{main_translated}'")

        return main_translated


# Глобальный экземпляр
translator = GettextTranslator()


# Удобные alias функций
def _(message: str, lang: str = None, **kwargs) -> str:
    return translator._(message, lang, **kwargs)


def ui(key: str, lang: str = None, **kwargs) -> str:
    return translator.ui(key, lang, **kwargs)


def ngettext(singular: str, plural: str, count: int, lang: str = None, **kwargs) -> str:
    return translator.ngettext(singular, plural, count, lang, **kwargs)


def plugin_translate(plugin_name: str, message: str, **kwargs) -> str:
    """Функция перевода для использования в плагинах"""
    translated = translator.get_plugin_translation(
        message=message,
        plugin_name=plugin_name
    )

    if kwargs:
        try:
            return translated.format(**kwargs)
        except (KeyError, ValueError):
            return translated
    return translated
