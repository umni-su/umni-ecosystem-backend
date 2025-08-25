from typing import Annotated

from fastapi import APIRouter, Depends

from classes.auth.auth import Auth
from models.storage_model import StorageModel, StorageModelBase
from repositories.storage_repository import StorageRepository
from responses.success import SuccessResponse
from responses.user import UserResponseOut

storages = APIRouter(
    prefix='/storages',
    tags=['storages']
)


@storages.get('', response_model=list[StorageModel])
def get_storages(
        user: Annotated[UserResponseOut, Depends(Auth.get_current_active_user)],

):
    items: list[StorageModel] = StorageRepository.get_storages()
    return items


@storages.post('')
def add_storage(
        user: Annotated[UserResponseOut, Depends(Auth.get_current_active_user)],
        model: StorageModelBase,
):
    storage: StorageModel = StorageRepository.add_storage(model)
    return storage


@storages.put('/{id}')
def update_storage(
        user: Annotated[UserResponseOut, Depends(Auth.get_current_active_user)],
        model: StorageModel,
):
    storage: StorageModel = StorageRepository.update_storage(model)
    return storage


@storages.delete('/{storage_id}', response_model=SuccessResponse)
def update_storage(
        storage_id: int,
        user: Annotated[UserResponseOut, Depends(Auth.get_current_active_user)],
):
    res: SuccessResponse = StorageRepository.delete_storage(storage_id)
    return res
