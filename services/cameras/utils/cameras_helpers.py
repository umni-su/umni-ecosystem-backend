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

import os
import cv2
import imutils
import numpy as np


def get_no_signal_frame(width: int):
    try:
        frame = cv2.imread(os.path.abspath('static/images/no-signal.jpg'))
        return imutils.resize(frame, width=width)
    except Exception as e:
        frame = np.zeros((width, width / 2, 1), dtype="uint8")
    return frame
