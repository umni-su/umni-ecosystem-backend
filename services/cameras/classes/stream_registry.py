from typing import List, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from entities.camera import CameraEntity
    from services.cameras.classes.camera_stream import CameraStream


class StreamRegistry:
    _streams: List["CameraStream"] = []

    @classmethod
    def add_stream(cls, stream: "CameraStream") -> None:
        cls._streams.append(stream)

    @classmethod
    def remove_stream(cls, stream: "CameraStream") -> None:
        cls._streams.remove(stream)

    @classmethod
    def find_by_camera(cls, camera: "CameraEntity") -> Optional["CameraStream"]:
        for stream in cls._streams:
            if stream.id == camera.id:
                return stream
        return None

    @classmethod
    def get_all_streams(cls) -> List["CameraStream"]:
        return cls._streams.copy()  # Возвращаем копию, чтобы избежать неконтролируемых изменений
