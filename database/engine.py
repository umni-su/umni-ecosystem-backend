#  Copyright (C) 2025 Mikhail Sazanov
#  #
#  This program is free software: you can redistribute it and/or modify
#  it under the terms of the GNU Affero General Public License as published
#  by the Free Software Foundation, either version 3 of the License, or
#  (at your option) any later version.
#  #
#  This program is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU Affero General Public License for more details.
#  #
#  You should have received a copy of the GNU Affero General Public License
#  along with this program.  If not, see <https://www.gnu.org/licenses/>.

from sqlmodel import create_engine
from config.settings import settings

SQLALCHEMY_ENGINE_OPTIONS = {
    "echo": False,
    "pool_pre_ping": True,
    "pool_recycle": 300,
    "pool_size": 20,
    "max_overflow": 10,
    "connect_args": {
        "connect_timeout": 10,
        "application_name": "umni-backend"
    }
}

# Создаем engine отдельно
engine = create_engine(str(settings.database_url), **SQLALCHEMY_ENGINE_OPTIONS)
