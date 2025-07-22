from enum import Enum

import cv2
import numpy as np
from datetime import datetime
from collections import deque
from typing import List, Optional, Dict, Callable, Any

from numpy import ndarray
from pydantic import BaseModel, Field, field_validator, ConfigDict

from classes.logger import Logger
from entities.camera import CameraEntity
from entities.camera_area import CameraAreaEntity


class ROIEventType(Enum):
    MOTION_START = 1
    MOTION_END = 2
    ROI_DETECT_START = 3
    ROI_DETECT_END = 4


class ROISettings(BaseModel):
    """
    Настройки детекции для ROI
    Attributes:
        enabled (bool): Включена ли детекция
        sensitivity (float): Чувствительность (0.1-5.0), где 0.1 - максимальная чувствительность, 5.0 - минимальная
        min_area (int): Минимальная площадь контура
        min_aspect_ratio (float): Минимальное соотношение сторон
        max_aspect_ratio (float): Максимальное соотношение сторон
    """
    enabled: bool = True
    sensitivity: float = Field(1.4, ge=0.1, le=5.0)
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
    options: ROISettings | None = Field(default_factory=ROISettings)

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
    event: ROIEventType
    camera: CameraEntity
    timestamp: datetime
    frame: ndarray
    original: ndarray
    model_config = ConfigDict(arbitrary_types_allowed=True)


class ROIDetectionEvent(ROIEvent):
    roi: ROI
    changes: list[dict]


class ROIRecordEvent(ROIEvent):
    rois: list[ROI] | None = None
    duration: float | None = None


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
        self.resized_frame = None
        self.original_frame = None
        self.rois = []
        self.camera = camera

        # self.rois = [ROI.model_validate(item.model_dump()) for item in self.camera.areas] or []
        self.frame_history = deque(maxlen=5)
        self.frame_skip = 1
        self.frame_counter = 0

        # Состояние системы
        self.recording = False
        self.triggered = False
        self.recording_start_time: Optional[datetime] = None
        self.last_movement_time: Dict[int, datetime / None] = {}
        self.active_movements: set[int] = set()

        # Параметры обработки
        self.threshold = 25
        self.blur_size = 3
        self.morph_size = 2
        self.recording_extension = 5

        # Защита от ложных срабатываний
        self.last_valid_frame = None
        self.frame_validity_threshold = 20
        self.consecutive_black_frames = 0
        self.max_black_frames = 5
        self.global_diff_threshold = 50
        self.min_solidity = 0.85

        self.frame_diff: Optional[np.ndarray] = None  # Добавляем для хранения diff между кадрам

        self._pending_movements: Dict[int, int] = {}  # Для отслеживания неподтвержденных движений
        self.movement_confirmation_frames = 2  # Количество кадров для подтверждения
        self.min_stable_movement_time = 0.5  # Минимальное время устойчивого движения (сек)

        # Callback функции
        self.on_motion_start: Optional[Callable[[ROIEvent], None]] = None
        self.on_motion_end: Optional[Callable[[ROIEvent], None]] = None
        self.on_recording_start: Optional[Callable[[ROIEvent], None]] = None
        self.on_recording_end: Optional[Callable[[ROIEvent], None]] = None

        self.update_all_rois(self.camera.areas)

    def set_callbacks(
            self,
            motion_start: Optional[Callable[[ROIDetectionEvent], None]] = None,
            motion_end: Optional[Callable[[ROIDetectionEvent], None]] = None,
            recording_start: Optional[Callable[[ROIRecordEvent], None]] = None,
            recording_end: Optional[Callable[[ROIRecordEvent], None]] = None
    ):
        """Установка callback-функций"""
        self.on_motion_start = motion_start
        self.on_motion_end = motion_end
        self.on_recording_start = recording_start
        self.on_recording_end = recording_end

    def _trigger_motion_start(self, roi_event: ROIDetectionEvent) -> None:
        """Вызывается при начале движения в ROI"""
        if self.on_motion_start:
            try:
                self.on_motion_start(roi_event)
            except Exception as e:
                Logger.err(f"Ошибка в callback on_motion_start: {e}")

    def _trigger_motion_end(self, roi_event: ROIDetectionEvent) -> None:
        """Вызывается при окончании движения в ROI"""
        if self.on_motion_end:
            try:
                self.on_motion_end(roi_event)
            except Exception as e:
                Logger.err(f"Ошибка в callback on_motion_end: {e}")

    def _trigger_recording_start(self, roi_event: ROIRecordEvent) -> None:
        """Вызывается при начале записи"""
        if self.on_recording_start:
            try:
                self.on_recording_start(roi_event)
            except Exception as e:
                Logger.err(f"Ошибка в callback on_recording_start: {e}")

    def _trigger_recording_end(self, roi_event: ROIRecordEvent) -> None:
        """Вызывается при окончании записи"""
        if self.on_recording_end:
            try:
                self.on_recording_end(roi_event)
            except Exception as e:
                Logger.err(f"Ошибка в callback on_recording_end: {e}")

    def reset_states(self):
        """Сброс всех состояний трекера"""
        self.active_movements.clear()
        self._pending_movements.clear()

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
        """Расширенная проверка валидности кадра с анализом стабильности"""
        if frame is None or frame.size == 0:
            return False

        try:
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            avg_brightness = np.mean(gray)
        except cv2.error as e:
            Logger.err(f"OpenCV error: {e}")
            return False

        # Проверка на черный/белый кадр
        if avg_brightness < self.frame_validity_threshold or avg_brightness > 250:
            self.consecutive_black_frames += 1
            if self.consecutive_black_frames > self.max_black_frames:
                return False
        else:
            self.consecutive_black_frames = 0

            # Дополнительная проверка на "замороженный" кадр
            if self.last_valid_frame is not None:
                diff = cv2.absdiff(gray, cv2.cvtColor(self.last_valid_frame, cv2.COLOR_BGR2GRAY))
                if np.mean(diff) < 1.0:  # Почти идентичные кадры
                    return False

            self.last_valid_frame = frame.copy()

        return True

    def set_original_frame(self, frame: np.ndarray):
        self.original_frame = frame.copy()

    def set_resized_frame(self, frame: np.ndarray):
        self.resized_frame = frame.copy()

    def detect_changes(self, current_frame: np.ndarray, original_frame: np.ndarray) -> List[ROIDetectionEvent]:
        """Улучшенная детекция с защитой от ложных срабатываний"""
        if not self.is_frame_valid(current_frame):
            return []

        self.set_original_frame(original_frame)
        self.set_resized_frame(current_frame)

        try:
            gray = cv2.cvtColor(current_frame, cv2.COLOR_BGR2GRAY)
            gray = cv2.GaussianBlur(gray, (self.blur_size, self.blur_size), 0)
        except cv2.error as e:
            Logger.err(f"OpenCV error in detect_changes: {e}")
            return []

        if not self.frame_history:
            self.frame_history.append(gray)
            return []

        # Анализ нескольких предыдущих кадров
        frame_diffs = []
        for prev_frame in self.frame_history:
            diff = cv2.absdiff(gray, prev_frame)
            frame_diffs.append(diff)

        # Комбинированная разница
        combined_diff = np.max(frame_diffs, axis=0)
        self.frame_diff = combined_diff  # Сохраняем для визуализации

        # Адаптивный порог
        _, threshold = cv2.threshold(combined_diff, self.threshold, 255, cv2.THRESH_BINARY)

        # Морфологические операции
        kernel = np.ones((self.morph_size, self.morph_size), np.uint8)
        threshold = cv2.morphologyEx(threshold, cv2.MORPH_OPEN, kernel)
        threshold = cv2.dilate(threshold, kernel, iterations=1)

        results = []
        current_movements = set()

        for roi in self.rois:
            if not roi.options.enabled:
                continue

            mask = roi.get_mask(threshold.shape[1], threshold.shape[0])
            roi_diff = cv2.bitwise_and(threshold, mask)

            # Фильтр по минимальной площади срабатывания
            if np.sum(roi_diff) < roi.options.min_area * 0.5:  # Эмпирический коэффициент
                continue

            contours, _ = cv2.findContours(roi_diff, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            changes = self._process_contours(contours, roi.options)

            if changes:
                # Дополнительная проверка устойчивости изменений
                if roi.id in self.active_movements or self._is_real_movement(changes, roi):
                    current_movements.add(roi.id)
                    results.append(
                        ROIDetectionEvent(
                            event=ROIEventType.ROI_DETECT_START,
                            roi=roi,
                            camera=self.camera,
                            changes=changes,
                            timestamp=datetime.now(),
                            frame=self.draw_rois(self.resized_frame),
                            original=self.original_frame
                        )
                    )

        self._update_movement_states(current_movements)
        self._update_recording_state(current_movements)
        self.frame_history.append(gray)
        return results

    def _is_real_movement(self, changes: List[dict], roi: ROI) -> bool:
        """Проверка что изменения соответствуют реальному движению"""
        total_area = sum(c['area'] for c in changes)

        # 1. Проверка по минимальной площади
        if total_area < roi.options.min_area:
            return False

        # 2. Проверка стабильности во времени
        if roi.id in self.last_movement_time:
            time_since_last = (datetime.now() - self.last_movement_time[roi.id]).total_seconds()
            if time_since_last < 0.5:  # Слишком частые срабатывания
                return False

        # 3. Проверка соотношения сигнал/шум
        mean_diffs = [c.get('mean_diff', 0) for c in changes]
        avg_diff = np.mean(mean_diffs) if mean_diffs else 0
        if avg_diff < self.threshold * roi.options.sensitivity:
            return False

        return True

    def _update_movement_states(self, current_movements: set[int]) -> None:
        """Обновление состояний движения с временными задержками"""
        now = datetime.now()

        # Обновление активных движений
        for roi_id in current_movements:
            self.last_movement_time[roi_id] = now
            if roi_id not in self.active_movements:
                # Требуется несколько последовательных обнаружений
                if roi_id in self._pending_movements:
                    self._pending_movements[roi_id] += 1
                    if self._pending_movements[roi_id] >= 2:  # 2 последовательных обнаружения
                        self.active_movements.add(roi_id)

                        if not self.triggered:
                            self.triggered = True

                        event = ROIDetectionEvent(
                            event=ROIEventType.MOTION_START,
                            roi=self.get_roi(roi_id),
                            camera=self.camera,
                            changes=[],
                            timestamp=now,
                            frame=self.draw_rois(self.resized_frame),
                            original=self.original_frame
                        )
                        self._trigger_motion_start(event)
                        Logger.info(f"🏃 [{self.camera.name}] Подтверждено движение в ROI {roi_id}")
                else:
                    self._pending_movements[roi_id] = 1
            else:
                self._pending_movements.pop(roi_id, None)

        # Очистка устаревших состояний
        for roi_id in list(self._pending_movements.keys()):
            if (now - self.last_movement_time.get(roi_id, now)).total_seconds() > 1.0:
                self._pending_movements.pop(roi_id, None)

        # Завершение движений
        for roi_id in list(self.active_movements):
            if roi_id not in current_movements:
                elapsed = (now - self.last_movement_time.get(roi_id, now)).total_seconds()
                if elapsed > self.recording_extension:
                    self.active_movements.remove(roi_id)

                    event = ROIDetectionEvent(
                        event=ROIEventType.MOTION_END,
                        roi=self.get_roi(roi_id),
                        camera=self.camera,
                        changes=[],
                        timestamp=now,
                        frame=self.draw_rois(self.resized_frame),
                        original=self.original_frame
                    )
                    self._trigger_motion_end(event)

                    Logger.info(f"🏃 [{self.camera.name}] Движение завершено в ROI {roi_id}")

    def _process_contours(self, contours, settings: ROISettings) -> List[dict]:
        """Обработка и фильтрация контуров с учетом чувствительности ROI"""
        changes = []

        # Рассчитываем динамический порог на основе чувствительности
        # Чем выше sensitivity, тем выше порог (меньше чувствительность)
        dynamic_threshold = int(self.threshold * settings.sensitivity)

        for contour in contours:
            area = cv2.contourArea(contour)
            if area < settings.min_area:
                continue

            # Дополнительная проверка на значимость изменения
            # Основанная на чувствительности
            contour_mask = np.zeros_like(self.frame_history[-1])
            cv2.drawContours(contour_mask, [contour], -1, 255, -1)
            mean_diff = cv2.mean(self.frame_diff, contour_mask)[0]

            if mean_diff < dynamic_threshold:
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
                'solidity': solidity,
                'mean_diff': mean_diff  # Добавляем информацию о значимости изменения
            })
        return changes

    def _calculate_solidity(self, contour) -> float:
        """Вычисление solidity контура"""
        hull = cv2.convexHull(contour)
        hull_area = cv2.contourArea(hull)
        return float(cv2.contourArea(contour)) / hull_area if hull_area > 0 else 0

    def _update_recording_state(self, current_movements: set[int]) -> None:
        """Обновление состояния записи"""

        now = datetime.now()

        if not self.recording and current_movements:
            if self.triggered:
                self.recording = True
                self.recording_start_time = datetime.now()
                active_names = [roi.name for roi in self.rois if roi.id in current_movements]
                rois = [roi for roi in self.rois if roi.id in current_movements]

                event = ROIRecordEvent(
                    event=ROIEventType.MOTION_START,
                    rois=rois,
                    camera=self.camera,
                    timestamp=now,
                    frame=self.resized_frame,
                    original=self.original_frame
                )
                self._trigger_recording_start(event)

                Logger.warn(f"[{self.camera.name}]🔴️ НАЧАЛО ЗАПИСИ! Активированы ROI: {active_names}")

        elif self.recording and not self.active_movements:
            if self.triggered:
                duration = (datetime.now() - self.recording_start_time).total_seconds()

                event = ROIRecordEvent(
                    event=ROIEventType.MOTION_START,
                    camera=self.camera,
                    timestamp=now,
                    duration=duration,
                    frame=self.resized_frame,
                    original=self.original_frame
                )
                self._trigger_recording_end(event)

                Logger.warn(f"⬛ [{self.camera.name}] ️КОНЕЦ ЗАПИСИ! Длительность: {duration:.1f} сек")
                self.recording = False
                self.recording_start_time = None
                self.triggered = False

    def draw_rois(self, frame: np.ndarray, changes: List[ROIDetectionEvent] = None,
                  roi_id: int | None = None) -> np.ndarray:
        """
        Отрисовка ROI и изменений на кадре

        Args:
            frame: Входной кадр
            changes: Список изменений для визуализации

        Returns:
            np.ndarray: Кадр с визуализацией
        """
        overlay = frame.copy()

        _exit = False

        for roi in self.rois:
            if _exit:
                continue
            if roi_id is not None:
                if roi.id == roi_id:
                    _exit = True
            pts = np.array(roi.points, np.int32)
            color = (0, 0, 255) if roi.id in self.active_movements else roi.bgr_color

            cv2.fillPoly(overlay, [pts], color)
            thickness = 3 if roi.id in self.active_movements else 1
            border = (0, 255, 255) if roi.id in self.active_movements else (0, 255, 0)
            cv2.polylines(overlay, [pts], True, border, thickness)

        cv2.addWeighted(overlay, 0.3, frame, 0.7, 0, frame)

        if changes:
            for change in changes:
                for obj in change.changes:
                    x, y, w, h = obj["bbox"]
                    cv2.rectangle(frame, (x, y), (x + w, y + h), (0, 255, 255), 2)

        # status_text = f"Recording: {'ON' if self.recording else 'OFF'}"
        # cv2.putText(frame, status_text, (10, 20),
        #             cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 1)

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

    def update_all_rois(self, new_rois: List[CameraAreaEntity]) -> bool:
        """Полное обновление всех ROI с сохранением состояния"""
        try:
            # Сохраняем текущие активные ROI
            active_ids = self.active_movements.copy()

            # Валидируем новые ROI
            # validated_rois = [ROI(**roi.model_dump()) for roi in new_rois]

            # Обновляем список ROI
            # self.rois = validated_rois

            self.rois = []
            for area in new_rois:
                roi = ROI(
                    id=area.id,
                    name=area.name,
                    points=area.points,
                    camera_id=area.camera_id,
                    color=area.color
                )
                if area.options is not None:
                    roi.options = ROISettings.model_validate(area.options)
                self.rois.append(roi)

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
