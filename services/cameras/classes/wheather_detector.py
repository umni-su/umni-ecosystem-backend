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
    def is_indoor(frame: np.ndarray) -> bool:
        """
        Определяет, находится ли камера в помещении
        по анализу особенностей изображения
        """
        # 1. Проверка по наличию потолка/стен (геометрия)
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        edges = cv2.Canny(gray, 50, 150)
        lines = cv2.HoughLinesP(edges, 1, np.pi / 180, threshold=50,
                                minLineLength=100, maxLineGap=10)

        if lines is not None and len(lines) > 5:  # Много линий - вероятно помещение
            return True

        # 2. Проверка по цветовому балансу (искусственное освещение)
        hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
        avg_saturation = np.mean(hsv[:, :, 1])
        if avg_saturation < 40:  # Низкая насыщенность - искусственный свет
            return True

        return False

    @staticmethod
    def detect_weather(frame: np.ndarray) -> WeatherCondition:
        """Улучшенный алгоритм определения погоды"""
        # Сначала проверяем, не в помещении ли мы
        if WeatherDetector.is_indoor(frame):
            return WeatherCondition.CLEAR

        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

        # 1. Проверка на снег по яркости и текстуре
        bright_pixels = np.sum(gray > 200) / gray.size
        if bright_pixels > 0.3:
            edges = cv2.Canny(gray, 50, 150)
            edge_density = np.sum(edges) / edges.size
            if edge_density > 0.15:  # Снег имеет высокую плотность мелких деталей
                return WeatherCondition.SNOW

        # 2. Проверка на дождь
        # Дождь создает вертикальные линии
        sobel_y = cv2.Sobel(gray, cv2.CV_64F, 0, 1, ksize=3)
        sobel_y = np.abs(sobel_y)
        vertical_lines = np.sum(sobel_y > 50) / sobel_y.size

        if vertical_lines > 0.1:  # Много вертикальных градиентов
            # Дополнительная проверка на динамику (нужна история кадров)
            return WeatherCondition.RAIN

        # 3. Проверка на туман по контрасту
        contrast = gray.std()
        if contrast < 25 and bright_pixels < 0.1:  # Низкий контраст + нет пересветов
            return WeatherCondition.FOG

        return WeatherCondition.CLEAR
