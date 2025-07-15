import cv2
import numpy as np
from datetime import datetime
from collections import deque
from typing import List, Optional, Dict
from pydantic import BaseModel, Field, field_validator

from classes.logger import Logger
from entities.camera import CameraEntity


class ROISettings(BaseModel):
    """
    Настройки детекции для ROI
    Attributes:
        enabled (bool): Включена ли детекция
        sensitivity (float): Чувствительность (0.1-5.0)
        min_area (int): Минимальная площадь контура
        min_aspect_ratio (float): Минимальное соотношение сторон
        max_aspect_ratio (float): Максимальное соотношение сторон
    """
    enabled: bool = True
    sensitivity: float = Field(1.0, ge=0.1, le=5.0)
    min_area: int = Field(100, gt=0)
    min_aspect_ratio: float = Field(0.5, gt=0)
    max_aspect_ratio: float = Field(2.0, gt=0)

    @classmethod
    @field_validator('max_aspect_ratio')
    def validate_aspect_ratios(cls, v, values):
        if 'min_aspect_ratio' in values and v < values['min_aspect_ratio']:
            raise ValueError("max_aspect_ratio must be >= min_aspect_ratio")
        return v


class ROI(BaseModel):
    """
    Область интереса (Region of Interest)
    Attributes:
        id (int): Уникальный идентификатор
        name (str): Название области
        points (List[List[int]]): Список точек [[x1,y1], [x2,y2], ...]
        color (str): Цвет в HEX формате (#RRGGBBAA)
        camera_id (int): ID камеры
        settings (ROISettings): Настройки детекции
    """
    id: int
    name: str
    points: List[List[int]]
    color: str = "#29B3A85A"
    camera_id: int = 0
    settings: ROISettings = Field(default_factory=ROISettings)

    @classmethod
    @field_validator('points')
    def validate_points(cls, v):
        if len(v) < 3:
            raise ValueError("ROI must have at least 3 points")
        return v

    @classmethod
    @field_validator('color')
    def validate_color(cls, v):
        if not v.startswith("#") or len(v) not in (7, 9):
            raise ValueError("Color must be in HEX format (#RRGGBB or #RRGGBBAA)")
        return v

    def get_mask(self, width: int, height: int) -> np.ndarray:
        """Генерация маски для ROI"""
        mask = np.zeros((height, width), dtype=np.uint8)
        pts = np.array(self.points, np.int32).reshape((-1, 1, 2))
        cv2.fillPoly(mask, [pts], 255)
        return mask

    @property
    def bgr_color(self) -> tuple:
        """Конвертация HEX цвета в BGR"""
        hex_color = self.color.lstrip("#")
        rgba = tuple(int(hex_color[i:i + 2], 16) for i in (0, 2, 4, 6))
        return (rgba[2], rgba[1], rgba[0])


class ROIEvent(BaseModel):
    roi: ROI
    camera: CameraEntity
    changes: list[dict]
    timestamp: datetime
    # results.append({
    #     "roi_id": roi.id,
    #     "roi_name": roi.name,
    #     "changes": changes,
    #     "timestamp": datetime.now().isoformat()
    # })


class ROITracker:
    """
    Трекер областей интереса с детекцией движения

    Args:
        rois (List[ROI]): Список областей интереса

    Features:
        - Детекция движения в ROI
        - Защита от ложных срабатываний
        - Логирование событий
        - Визуализация
    """

    def __init__(self, camera: CameraEntity):
        self.camera = camera
        self.rois = [ROI.model_validate(item.model_dump()) for item in self.camera.areas] or []
        self.frame_history = deque(maxlen=5)
        self.frame_skip = 1
        self.frame_counter = 0

        # Состояние системы
        self.recording = False
        self.recording_start_time: Optional[datetime] = None
        self.last_movement_time: Dict[int, datetime / None] = {}
        self.active_movements: set[int] = set()

        # Параметры обработки
        self.threshold = 25
        self.blur_size = 3
        self.morph_size = 2
        self.recording_extension = 3

        # Защита от ложных срабатываний
        self.last_valid_frame = None
        self.frame_validity_threshold = 10
        self.consecutive_black_frames = 0
        self.max_black_frames = 5
        self.global_diff_threshold = 50
        self.min_solidity = 0.85

    def set_advanced_settings(self,
                              max_black_frames: int = 5,
                              brightness_thresh: int = 10,
                              global_diff_thresh: int = 50,
                              min_solidity: float = 0.85):
        """
        Настройка параметров защиты от ложных срабатываний

        Args:
            max_black_frames: Максимум черных кадров перед игнорированием
            brightness_thresh: Порог яркости для валидного кадра
            global_diff_thresh: Порог глобальных изменений
            min_solidity: Минимальная solidity контура
        """
        self.max_black_frames = max_black_frames
        self.frame_validity_threshold = brightness_thresh
        self.global_diff_threshold = global_diff_thresh
        self.min_solidity = min_solidity

    def is_frame_valid(self, frame: np.ndarray) -> bool:
        """
        Проверка валидности кадра
        Returns:
            bool: True если кадр пригоден для обработки
        """
        if frame is None or frame.size == 0:
            return False

        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        avg_brightness = np.mean(gray)

        if avg_brightness < self.frame_validity_threshold:
            self.consecutive_black_frames += 1
            if self.consecutive_black_frames > self.max_black_frames:
                return False
        else:
            self.consecutive_black_frames = 0
            self.last_valid_frame = frame.copy()

        return True

    def detect_changes(self, current_frame: np.ndarray) -> List[dict]:
        """
        Детекция изменений в ROI с защитой от артефактов

        Args:
            current_frame: Текущий кадр видео

        Returns:
            List[dict]: Список обнаруженных изменений
        """
        if not self.is_frame_valid(current_frame):
            if self.last_valid_frame is not None:
                current_frame = self.last_valid_frame
            else:
                return []

        gray = cv2.cvtColor(current_frame, cv2.COLOR_BGR2GRAY)

        if not self.frame_history:
            self.frame_history.append(gray)
            return []

        prev_gray = self.frame_history[-1]
        frame_diff = cv2.absdiff(gray, prev_gray)

        # Проверка на глобальные изменения
        global_diff = np.mean(frame_diff)
        if global_diff > self.global_diff_threshold:
            self.frame_history.clear()
            return []

        _, threshold = cv2.threshold(frame_diff, self.threshold, 255, cv2.THRESH_BINARY)

        if self.morph_size > 0:
            kernel = np.ones((self.morph_size, self.morph_size), np.uint8)
            threshold = cv2.morphologyEx(threshold, cv2.MORPH_OPEN, kernel)

        results = []
        current_movements = set()

        for roi in self.rois:
            if not roi.settings.enabled:
                continue

            mask = roi.get_mask(threshold.shape[1], threshold.shape[0])
            roi_diff = cv2.bitwise_and(threshold, mask)

            contours, _ = cv2.findContours(roi_diff, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            changes = self._process_contours(contours, roi.settings)

            if changes:
                if roi.id not in self.active_movements:
                    Logger.warn(f"[{self.camera.name}]🚨Движение НАЧАЛОСЬ в {roi.name} (ID: {roi.id})")
                    self.active_movements.add(roi.id)

                self.last_movement_time[roi.id] = datetime.now()
                current_movements.add(roi.id)
                results.append({
                    "roi_id": roi.id,
                    "roi_name": roi.name,
                    "changes": changes,
                    "timestamp": datetime.now().isoformat()
                })

            elif roi.id in self.active_movements:
                elapsed = (datetime.now() - self.last_movement_time[roi.id]).total_seconds()
                if elapsed > self.recording_extension:
                    Logger.warn(f"[{self.camera.name}]✅ Движение ЗАКОНЧИЛОСЬ в {roi.name} (ID: {roi.id})")
                    self.active_movements.remove(roi.id)

        self._update_recording_state(current_movements)
        return results

    def _process_contours(self, contours, settings) -> List[dict]:
        """Обработка и фильтрация контуров"""
        changes = []
        for contour in contours:
            area = cv2.contourArea(contour)
            if area < settings.min_area:
                continue

            x, y, w, h = cv2.boundingRect(contour)
            aspect_ratio = w / max(1, h)

            if not (settings.min_aspect_ratio <= aspect_ratio <= settings.max_aspect_ratio):
                continue

            solidity = self._calculate_solidity(contour)
            if solidity < self.min_solidity:
                continue

            changes.append({
                'bbox': (x, y, w, h),
                'area': area,
                'aspect_ratio': aspect_ratio,
                'solidity': solidity
            })
        return changes

    def _calculate_solidity(self, contour) -> float:
        """Вычисление solidity контура"""
        hull = cv2.convexHull(contour)
        hull_area = cv2.contourArea(hull)
        return float(cv2.contourArea(contour)) / hull_area if hull_area > 0 else 0

    def _update_recording_state(self, current_movements: set[int]) -> None:
        """Обновление состояния записи"""
        if not self.recording and current_movements:
            self.recording = True
            self.recording_start_time = datetime.now()
            active_names = [roi.name for roi in self.rois if roi.id in current_movements]
            Logger.warn(f"[{self.camera.name}]⏺️НАЧАЛО ЗАПИСИ! Активированы ROI: {active_names}")

        elif self.recording and not self.active_movements:
            duration = (datetime.now() - self.recording_start_time).total_seconds()
            Logger.warn(f"[{self.camera.name}]⏹️КОНЕЦ ЗАПИСИ! Длительность: {duration:.1f} сек")
            self.recording = False
            self.recording_start_time = None

    def draw_rois(self, frame: np.ndarray, changes: List[dict] = None) -> np.ndarray:
        """
        Отрисовка ROI и изменений на кадре

        Args:
            frame: Входной кадр
            changes: Список изменений для визуализации

        Returns:
            np.ndarray: Кадр с визуализацией
        """
        overlay = frame.copy()

        for roi in self.rois:
            pts = np.array(roi.points, np.int32)
            color = (0, 0, 255) if roi.id in self.active_movements else roi.bgr_color

            cv2.fillPoly(overlay, [pts], color)
            cv2.polylines(overlay, [pts], True, (0, 255, 0), 1)

            # status = "ACTIVE" if roi.id in self.active_movements else "READY"
            # cv2.putText(overlay, f"{roi.name} [{status}]",
            #             (pts[0][0], pts[0][1] - 10),
            #             cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)

        cv2.addWeighted(overlay, 0.3, frame, 0.7, 0, frame)

        if changes:
            for change in changes:
                for obj in change["changes"]:
                    x, y, w, h = obj["bbox"]
                    cv2.rectangle(frame, (x, y), (x + w, y + h), (0, 255, 255), 2)

        status_text = f"Recording: {'ON' if self.recording else 'OFF'}"
        cv2.putText(frame, status_text, (10, 20),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 1)

        return frame

    def get_roi(self, roi_id: int) -> Optional[ROI]:
        """Получение ROI по ID"""
        return next((r for r in self.rois if r.id == roi_id), None)

    def add_roi(self, roi: ROI) -> bool:
        """Добавление новой ROI"""
        if any(r.id == roi.id for r in self.rois):
            return False
        try:
            self.rois.append(ROI(**roi.model_dump()))
            self.last_movement_time[roi.id] = None
            return True
        except Exception as e:
            Logger.err(f"[{self.camera.name}] Ошибка валидации ROI: {e}")
            return False

    # Основные методы обновления ROI
    def update_roi(self, roi_id: int, new_data: ROI) -> bool:
        """Обновление ROI по ID с валидацией"""
        for i, roi in enumerate(self.rois):
            if roi.id == roi_id:
                try:
                    # Сохраняем текущее состояние активности
                    was_active = roi.id in self.active_movements

                    # Обновляем ROI с валидацией
                    self.rois[i] = ROI(**new_data.model_dump())

                    # Восстанавливаем состояние активности
                    if was_active:
                        self.active_movements.add(roi_id)
                    else:
                        self.active_movements.discard(roi_id)

                    return True
                except Exception as e:
                    Logger.err(f"[{self.camera.name}] Ошибка валидации ROI: {e}")
                    return False
        return False

    def update_all_rois(self, new_rois: List[ROI]) -> bool:
        """Полное обновление всех ROI с сохранением состояния"""
        try:
            # Сохраняем текущие активные ROI
            active_ids = self.active_movements.copy()

            # Валидируем новые ROI
            validated_rois = [ROI(**roi.model_dump()) for roi in new_rois]

            # Обновляем список ROI
            self.rois = validated_rois

            # Восстанавливаем активные ROI
            self.active_movements = {id for id in active_ids
                                     if any(r.id == id for r in self.rois)}

            return True
        except Exception as e:
            Logger.err(f"[{self.camera.name}] Ошибка валидации ROI: {e}")
            return False

    def remove_roi(self, roi_id: int) -> bool:
        """Удаление ROI"""
        for i, roi in enumerate(self.rois):
            if roi.id == roi_id:
                self.rois.pop(i)
                self.last_movement_time.pop(roi_id, None)
                self.active_movements.discard(roi_id)
                return True
        return False
