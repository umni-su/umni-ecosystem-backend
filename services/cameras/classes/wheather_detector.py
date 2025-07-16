from enum import Enum

import cv2
import numpy as np


class WeatherCondition(Enum):
    """Типы погодных условий"""
    CLEAR = 0  # Ясная погода
    RAIN = 1  # Дождь
    SNOW = 2  # Снег
    STRONG_WIND = 3  # Сильный ветер
    FOG = 4  # Туман


class DayNightDetector:
    """Детектор времени суток (день/ночь)"""

    @staticmethod
    def is_night(frame: np.ndarray, threshold: float = 0.3) -> bool:
        """
        Определяет, ночь ли сейчас на изображении

        Args:
            frame: Входной кадр видео
            threshold: Порог яркости (0-1), ниже которого считается ночью

        Returns:
            bool: True если ночь, False если день
        """
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        avg_brightness = np.mean(gray) / 255  # Нормализуем к 0-1
        return avg_brightness < threshold


class WeatherDetector:
    """Детектор погодных условий по изображению"""

    @staticmethod
    def detect_weather(frame: np.ndarray) -> WeatherCondition:
        """
        Определяет текущие погодные условия

        Args:
            frame: Входной кадр видео

        Returns:
            WeatherCondition: Текущее погодное условие
        """
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

        # 1. Детекция дождя/снега по текстуре изображения
        edges = cv2.Canny(gray, 50, 150)
        edge_density = np.sum(edges) / (frame.shape[0] * frame.shape[1])

        if edge_density > 0.2:  # Высокая плотность краев - возможен дождь/снег
            # Анализ гистограммы для различия дождя и снега
            hist = cv2.calcHist([gray], [0], None, [256], [0, 256])
            white_pixels = np.sum(hist[200:]) / np.sum(hist)

            if white_pixels > 0.3:
                return WeatherCondition.SNOW
            else:
                return WeatherCondition.RAIN

        # 2. Детекция тумана по контрасту
        contrast = gray.std()
        if contrast < 25:  # Низкий контраст - возможен туман
            return WeatherCondition.FOG

        # 3. Детекция ветра требует анализа нескольких кадров (реализуется отдельно)

        return WeatherCondition.CLEAR
