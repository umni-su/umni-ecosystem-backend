from fastapi import APIRouter

from classes.ecosystem import Ecosystem
from responses.init import InitResponse

initialize = APIRouter(
    prefix='/init',
    tags=['init']
)


@initialize.get('', response_model=InitResponse)
def init():
    success = Ecosystem.installed
    return InitResponse(success=success)
