import gettext
from pathlib import Path
from typing import Dict
from fastapi import Request


class GettextTranslator:
    """Улучшенный переводчик с поддержкой UI переводов"""

    def __init__(self, domain: str = "messages", locale_dir: str = "l10n", default_lang: str = "en"):
        self.domain = domain
        self.locale_dir = Path(locale_dir)
        self.default_lang = default_lang
        self.translations = {}
        self.ui_translations = {}  # Кэш для UI переводов

    def set_language(self, lang: str) -> str:
        """Установка языка по умолчанию"""
        self.default_lang = lang
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


# Глобальный экземпляр
translator = GettextTranslator()


# Удобные alias функций
def _(message: str, lang: str = None, **kwargs) -> str:
    return translator._(message, lang, **kwargs)


def ui(key: str, lang: str = None, **kwargs) -> str:
    return translator.ui(key, lang, **kwargs)


def ngettext(singular: str, plural: str, count: int, lang: str = None, **kwargs) -> str:
    return translator.ngettext(singular, plural, count, lang, **kwargs)
