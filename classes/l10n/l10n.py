# Copyright (C) 2025 Mikhail Sazanov
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published
# by the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.

import gettext
from pathlib import Path

'''
Usage
translator.get_available_languages()
return {
        "message": _("Welcome to our application!", lang),
        "users_online": ngettext(
            "There is {count} user online", 
            "There are {count} users online", 
            5, lang, count=5
        ),
        "files": ngettext(
            "You have {count} file",
            "You have {count} files",
            1, lang, count=1
        )
    }
'''


class GettextTranslator:
    """Простой переводчик с gettext как в больших проектах"""

    def __init__(self, domain: str = "messages", locale_dir: str = "l10n", default_lang: str = "en"):
        self.domain = domain
        self.locale_dir = Path(locale_dir)
        self.default_lang = default_lang
        self.translations = {}

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

    def _(self, message: str, lang: str = None, **kwargs) -> str:
        """Основная функция перевода"""
        lang = lang or self.default_lang
        translation = self.get_translation(lang)
        translated = translation.gettext(message)

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
                languages.append(item.name)
        return languages


# Глобальный экземпляр
translator = GettextTranslator()


# Удобные alias функций
def _(message: str, lang: str = None, **kwargs) -> str:
    return translator._(message, lang, **kwargs)


def ngettext(singular: str, plural: str, count: int, lang: str = None, **kwargs) -> str:
    return translator.ngettext(singular, plural, count, lang, **kwargs)
