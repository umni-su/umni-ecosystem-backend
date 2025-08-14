from fastapi import APIRouter, Depends

from config.dependencies import get_ecosystem
from responses.init import InitResponse

initialize = APIRouter(
    prefix='/init',
    tags=['init']
)


@initialize.get('', response_model=InitResponse)
def init(
        ecosystem=Depends(get_ecosystem)
):
    success = ecosystem.installed
    return InitResponse(success=success)
