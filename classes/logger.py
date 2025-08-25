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

import uvicorn.logging as u_logging
import logging

FORMAT: str = "%(levelprefix)s %(asctime)s [%(threadName)s]  [%(name)s]  %(message)s"

logger = logging.getLogger("logger")
logger.setLevel(logging.DEBUG)
console_handler = logging.StreamHandler()
console_handler.setLevel(logging.DEBUG)
formatter = u_logging.DefaultFormatter(FORMAT, datefmt="%Y-%m-%d %H:%M:%S")
console_handler.setFormatter(formatter)
logger.addHandler(console_handler)


class Logger:
    @staticmethod
    def info(msg: str):
        logger.info(msg)

    @staticmethod
    def warn(msg: str):
        logger.warning(msg)

    @staticmethod
    def err(msg: str | Exception):
        logger.error(msg)

    @staticmethod
    def debug(msg: str):
        logger.debug(msg)
