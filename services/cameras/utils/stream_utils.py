from typing import TYPE_CHECKING, Optional

if TYPE_CHECKING:
    from entities.camera import CameraEntity
    from services.cameras.classes.camera_stream import CameraStream


def find_stream_by_camera(streams: list["CameraStream"], camera: "CameraEntity") -> Optional["CameraStream"]:
    for stream in streams:
        if stream.id == camera.id:
            return stream
    return None
