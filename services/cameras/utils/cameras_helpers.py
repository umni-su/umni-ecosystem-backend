import os
import cv2
import imutils
import numpy as np


def get_no_signal_frame(width: int):
    try:
        frame = cv2.imread(os.path.abspath('static/images/no-signal.jpg'))
        return imutils.resize(frame, width=width)
    except Exception:
        frame = np.zeros((width, width / 2, 1), dtype="uint8")
    return frame
