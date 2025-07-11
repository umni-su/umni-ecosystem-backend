from fastapi import APIRouter

notifications = APIRouter(
    prefix='/notifications',
    tags=['notifications']
)


@notifications.get('')
def het_notifications():
    pass
