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
        items: list[StorageModel] = Depends(StorageRepository.get_storages)
):
    return items


@storages.post('')
def add_storage(
        user: Annotated[UserResponseOut, Depends(Auth.get_current_active_user)],
        model: StorageModelBase = Depends(StorageRepository.add_storage)
):
    return model


@storages.put('/{id}')
def update_storage(
        user: Annotated[UserResponseOut, Depends(Auth.get_current_active_user)],
        model: StorageModelBase = Depends(StorageRepository.update_storage)
):
    return model


@storages.delete('/{storage_id}', response_model=SuccessResponse)
def update_storage(
        user: Annotated[UserResponseOut, Depends(Auth.get_current_active_user)],
        res: SuccessResponse = Depends(StorageRepository.delete_storage)
):
    return res
