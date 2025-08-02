from enum import Enum
from typing import Optional, Dict, List
from collections import deque
from pydantic import BaseModel, Field
import cv2
import numpy as np


# --- Pydantic модели ---
class WeatherCondition(str, Enum):
    CLEAR = "clear"
    RAIN = "rain"
    SNOW = "snow"
    STRONG_WIND = "strong_wind"
    FOG = "fog"
    CLOUDY = "cloudy"
    INDOOR = "indoor"


class DetectionResult(BaseModel):
    weather: WeatherCondition = Field(..., description="Тип погодных условий")
    is_night: bool = Field(..., description="Ночное время суток")
    is_indoor: bool = Field(..., description="Находится ли камера в помещении")
    confidence: float = Field(..., ge=0, le=1, description="Уверенность предсказания")
    metrics: Dict[str, float] = Field(default_factory=dict, description="Детальные метрики анализа")


# --- Основной класс ---
class WeatherDetector:
    """Комплексный детектор погодных условий с поддержкой мультикамерности"""

    def __init__(self, camera_id: str, history_size: int = 5):
        """
        Args:
            camera_id: Уникальный идентификатор камеры
            history_size: Размер буфера кадров для анализа (0 - только текущий кадр)
        """
        self.camera_id = camera_id
        self.history_size = history_size
        self.frame_history = deque(maxlen=history_size) if history_size > 0 else None
        self.prev_frame: Optional[np.ndarray] = None

    def process_frame(self, frame: np.ndarray, use_history: bool = True) -> DetectionResult:
        """
        Основной метод обработки кадра

        Args:
            frame: Входной кадр в формате BGR
            use_history: Использовать историю кадров для анализа

        Returns:
            DetectionResult: Результаты детекции
        """
        # Сохраняем кадр в историю (если нужно)
        if self.frame_history is not None:
            self.frame_history.append(frame.copy())

        # Определяем помещение/улицу
        is_indoor = self._detect_indoor(frame)

        # Анализируем погоду
        if is_indoor:
            weather = WeatherCondition.INDOOR
            confidence = 1.0
            metrics = {}
        else:
            if use_history and self.frame_history and len(self.frame_history) == self.history_size:
                weather, confidence, metrics = self._analyze_frame_sequence()
            else:
                weather, confidence, metrics = self._analyze_single_frame(frame)

        # Определение времени суток
        is_night = self._detect_night(frame)

        return DetectionResult(
            weather=weather,
            is_night=is_night,
            is_indoor=is_indoor,
            confidence=confidence,
            metrics=metrics
        )

    def _detect_indoor(self, frame: np.ndarray) -> bool:
        """Улучшенное определение нахождения в помещении"""
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)

        # 1. Анализ резкости (Laplacian variance)
        laplacian_var = cv2.Laplacian(gray, cv2.CV_64F).var()

        # 2. Цветовой баланс (искусственный свет)
        saturation = np.mean(hsv[:, :, 1])
        value = np.mean(hsv[:, :, 2])

        # 3. Геометрические структуры (стены, потолки)
        edges = cv2.Canny(gray, 50, 150)
        lines = cv2.HoughLinesP(edges, 1, np.pi / 180, threshold=50,
                                minLineLength=50, maxLineGap=10)

        # 4. Детекция "природных" элементов (небо, деревья)
        blue_ratio = np.mean(frame[:, :, 0]) / (np.mean(frame[:, :, 1]) + 1e-5)
        green_dominance = np.mean(frame[:, :, 1]) / (np.mean(frame[:, :, 0]) + 1e-5)

        # Критерии для улицы (переопределяют indoor)
        outdoor_indicators = 0
        if blue_ratio > 1.3:  # Много синего (небо)
            outdoor_indicators += 0.4
        if green_dominance > 1.2:  # Много зелени (растительность)
            outdoor_indicators += 0.3
        if laplacian_var < 100:  # Низкая резкость (атмосферные явления)
            outdoor_indicators += 0.3

        # Если явные признаки улицы - сразу возвращаем False
        if outdoor_indicators >= 0.7:
            return False

        # Критерии для помещения
        indoor_score = 0
        if laplacian_var > 300:  # Очень высокая резкость
            indoor_score += 0.4
        if saturation < 40 and value > 120:  # Искусственное освещение
            indoor_score += 0.3
        if lines is not None and len(lines) > 15:  # Много прямых линий
            indoor_score += 0.3

        return indoor_score > 0.7

    def _detect_night(self, frame: np.ndarray) -> bool:
        """Определение ночного времени"""
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        avg_brightness = np.mean(gray) / 255
        return avg_brightness < 0.35

    def _analyze_single_frame(self, frame: np.ndarray) -> (WeatherCondition, float, dict):
        """Анализ одного кадра"""
        metrics = self._extract_frame_metrics(frame)
        return self._decide_weather_condition(metrics)

    def _analyze_frame_sequence(self) -> (WeatherCondition, float, dict):
        """Анализ последовательности кадров"""
        metrics_list = [self._extract_frame_metrics(f) for f in self.frame_history]

        # Усредняем метрики по всем кадрам
        avg_metrics = {}
        for key in metrics_list[0].keys():
            avg_metrics[key] = np.mean([m[key] for m in metrics_list])

        return self._decide_weather_condition(avg_metrics)

    def _extract_frame_metrics(self, frame: np.ndarray) -> dict:
        """Извлечение всех метрик из кадра"""
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)

        metrics = {
            'brightness': np.mean(gray) / 255,
            'contrast': gray.std() / 255,
            'blue_hist': self._calc_blue_histogram(frame),
            'rain_drops': self._detect_rain_drops(frame),
            'snow_coverage': self._detect_snow(gray),
            'motion': self._detect_motion(frame),
            'edge_density': self._calc_edge_density(gray),
            'weather_artifacts': self._detect_weather_artifacts(frame)
        }

        return metrics

    def _detect_weather_artifacts(self, frame: np.ndarray) -> float:
        """Обнаружение артефактов погоды (дождь/снег)"""
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        edges = cv2.Canny(gray, 50, 150)
        return np.sum(edges > 0) / edges.size

    def _decide_weather_condition(self, metrics: dict) -> (WeatherCondition, float, dict):
        """Логика принятия решения о погоде"""
        # Приоритетная детекция особых условий
        # Если обнаружены погодные артефакты - точно не помещение
        if metrics.get('weather_artifacts', 0) > 0.2:
            metrics['is_indoor_override'] = False
        if metrics['rain_drops'] > 0.1:
            return WeatherCondition.RAIN, metrics['rain_drops'], metrics
        elif metrics['snow_coverage'] > 0.3:
            return WeatherCondition.SNOW, metrics['snow_coverage'], metrics
        elif metrics['motion'] > 0.2 and metrics['edge_density'] > 0.1:
            return WeatherCondition.STRONG_WIND, metrics['motion'], metrics
        elif metrics['blue_hist'] > 0.25:
            return WeatherCondition.CLOUDY, metrics['blue_hist'], metrics
        elif metrics['contrast'] < 0.1:
            return WeatherCondition.FOG, 1 - metrics['contrast'], metrics

        return WeatherCondition.CLEAR, 1.0, metrics

    def _calc_blue_histogram(self, frame: np.ndarray) -> float:
        """Анализ облачности по гистограмме синего канала"""
        blue = frame[:, :, 0]
        hist = cv2.calcHist([blue], [0], None, [256], [0, 256])
        hist = hist / hist.sum()  # Нормализация
        return float(np.sum(hist[150:]))  # Яркие синие тона

    def _detect_rain_drops(self, frame: np.ndarray) -> float:
        """Улучшенная детекция дождя с защитой от ложных срабатываний"""
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

        # 1. Предварительная фильтрация (убираем шум)
        blurred = cv2.GaussianBlur(gray, (5, 5), 0)

        # 2. Детекция специфичных для дождя паттернов
        sobel_y = cv2.Sobel(blurred, cv2.CV_64F, 0, 1, ksize=3)
        sobel_y = np.abs(sobel_y)
        vertical_density = np.sum(sobel_y > 25) / sobel_y.size

        # 3. Поиск круглых объектов (капли)
        circles = cv2.HoughCircles(blurred, cv2.HOUGH_GRADIENT, dp=1,
                                   minDist=30, param1=150, param2=20,
                                   minRadius=2, maxRadius=8)

        # 4. Анализ динамики (для видео)
        motion_factor = self._get_motion_factor(frame)

        # Комбинированный score
        rain_score = 0
        if vertical_density > 0.15:  # Вертикальные линии
            rain_score += vertical_density * 0.6
        if circles is not None:  # Круглые объекты
            rain_score += min(0.4, len(circles[0]) / 500)
        if motion_factor > 0.1:  # Движение капель
            rain_score *= 1.2

        return min(rain_score, 1.0)

    def _get_motion_factor(self, frame: np.ndarray) -> float:
        """Анализ движения между кадрами"""
        if self.prev_frame is None:
            self.prev_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            return 0.0

        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        flow = cv2.calcOpticalFlowFarneback(
            self.prev_frame, gray, None, 0.5, 3, 15, 3, 5, 1.2, 0)

        self.prev_frame = gray
        magnitude = np.sqrt(flow[..., 0] ** 2 + flow[..., 1] ** 2)
        return float(np.mean(magnitude))

    def _detect_snow(self, gray: np.ndarray) -> float:
        """Детекция снега"""
        bright_pixels = np.sum(gray > 200) / gray.size
        edges = cv2.Canny(gray, 50, 150)
        edge_density = np.sum(edges) / edges.size
        return bright_pixels * edge_density

    def _calc_edge_density(self, gray: np.ndarray) -> float:
        """Вычисление плотности границ"""
        edges = cv2.Canny(gray, 50, 150)
        return np.sum(edges > 0) / edges.size

    def _detect_motion(self, frame: np.ndarray) -> float:
        """Детекция движения между кадрами"""
        if self.prev_frame is None:
            self.prev_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            return 0.0

        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        flow = cv2.calcOpticalFlowFarneback(
            self.prev_frame, gray, None, 0.5, 3, 15, 3, 5, 1.2, 0)

        motion = np.sqrt(flow[..., 0] ** 2 + flow[..., 1] ** 2).mean()
        self.prev_frame = gray

        return float(motion)
