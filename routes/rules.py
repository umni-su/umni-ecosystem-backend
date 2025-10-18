#  Copyright (C) 2025 Mikhail Sazanov
#  #
#  This program is free software: you can redistribute it and/or modify
#  it under the terms of the GNU Affero General Public License as published
#  by the Free Software Foundation, either version 3 of the License, or
#  (at your option) any later version.
#  #
#  This program is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU Affero General Public License for more details.
#  #
#  You should have received a copy of the GNU Affero General Public License
#  along with this program.  If not, see <https://www.gnu.org/licenses/>.

from typing import Annotated
from fastapi import APIRouter, Depends, HTTPException

from classes.auth.auth import Auth
from classes.rules.rule_conditions import RuleConditionsList, RuleConditionKey
from classes.rules.rule_executor import RuleExecutor
from database.session import write_session
from entities.camera import CameraEntity
from entities.device import DeviceEntity
from entities.rule_entity import RuleEntity
from entities.sensor_entity import SensorEntity
from entities.storage import StorageEntity
from models.camera_model import CameraModelWithRelations
from models.device_model_relations import DeviceModelWithRelations
from models.pagination_model import PaginatedResponse, PageParams
from models.rule_condition_models import RuleConditionEntitiesParams
from models.rule_model import (
    RuleCreate,
    RuleGraphUpdate,
    RuleModel,
    RuleNodeModel
)
from models.sensor_model import SensorModelWithDevice
from models.storage_model import StorageModel
from models.ui_models import UiListItem
from repositories.camera_repository import CameraRepository
from repositories.device_repository import DeviceRepository
from repositories.rules_repository import RulesRepository
from repositories.sensor_repository import SensorRepository
from repositories.storage_repository import StorageRepository
from responses.user import UserResponseOut
from services.rule.rule_service import RuleService

rules = APIRouter(
    prefix="/rules",
    tags=["rules"]
)


def get_db():
    with write_session() as session:
        yield session


@rules.get("", response_model=list[RuleModel])
def get_rules(
        user: Annotated[UserResponseOut, Depends(Auth.get_current_active_user)],
):
    all_rules = RulesRepository.get_rules()
    return all_rules


@rules.get("/{rule_id}", response_model=RuleModel)
def get_rule(
        rule_id: int,
        user: Annotated[UserResponseOut, Depends(Auth.get_current_active_user)],
):
    rule: RuleEntity = RulesRepository.get_rule(rule_id)
    rule_data = {
        "id": rule.id,
        "name": rule.name,
        "description": rule.description,
        "enabled": rule.enabled,
        "priority": rule.priority,
        "nodes": [node.model_dump() for node in rule.nodes],
        "edges": [edge.model_dump() for edge in rule.edges]
    }
    _rule = RuleModel.model_validate(rule_data)
    # for index, node in enumerate(_rule.nodes):
    #     _rule.nodes[index].data.options.items = RulesRepository.get_node_entities_by_node(
    #         node.id
    #     )
    return _rule


@rules.post("", response_model=RuleModel)
def create_rule(
        user: Annotated[UserResponseOut, Depends(Auth.get_current_active_user)],
        rule_data: RuleCreate,
):
    rule: RuleModel = RulesRepository.add_rule(rule_data)
    return rule


@rules.put("/{rule_id}/graph", response_model=RuleModel)
def update_rule_graph(
        user: Annotated[UserResponseOut, Depends(Auth.get_current_active_user)],
        rule_id: int,
        graph_data: RuleGraphUpdate,

):
    rule: RuleModel = RulesRepository.update_rule_graph(rule_id, graph_data)
    return rule


def start_rule(rule: RuleModel):
    rule_executor = RuleExecutor(rule, True)
    rule_executor.execute()


@rules.get("/{rule_id}/execute", response_model=RuleModel)
def execute_rule(
        user: Annotated[UserResponseOut, Depends(Auth.get_current_active_user)],
        rule_id: int
):
    try:
        rule = RulesRepository.get_rule(rule_id)
        if rule:
            RuleService.task_manager.submit(
                func=start_rule,
                rule=rule
            )
            return rule
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@rules.get("/nodes/{node_id}", response_model=RuleNodeModel)
def get_node(
        user: Annotated[UserResponseOut, Depends(Auth.get_current_active_user)],
        node: RuleNodeModel = Depends(RulesRepository.get_node)
):
    return node


@rules.post("/nodes/{node_id}/list")
def get_node(
        params: PageParams,
        node_id: str,
        user: Annotated[UserResponseOut, Depends(Auth.get_current_active_user)],
):
    node: RuleNodeModel = RulesRepository.get_node(node_id)
    _list = RulesRepository.get_node_entities_by_trigger(node.data.flow.el.key, params)
    return _list


@rules.get("/conditions/list")
def get_rules_conditions(
        user: Annotated[UserResponseOut, Depends(Auth.get_current_active_user)],
):
    return RuleConditionsList().conditions


@rules.post("/conditions/entities")
def get_rules_condition_entities(
        params: RuleConditionEntitiesParams,
        user: Annotated[UserResponseOut, Depends(Auth.get_current_active_user)],
):
    data = []
    with write_session() as sess:
        if params.condition == RuleConditionKey.AVAILABILITY_DEVICE:
            items = DeviceRepository.find_paginated(
                session=sess,
                page_params=params,
                search_term=params.term,
                search_fields=[
                    DeviceEntity.name,
                    DeviceEntity.title
                ]
            )
            res: list[DeviceModelWithRelations] = items.items
            final_items = [
                UiListItem(
                    id=item.id,
                    name=item.name,
                    description=item.title,
                    icon='mdi-chip'
                ) for item in res]
        elif params.condition == RuleConditionKey.AVAILABILITY_CAMERA:
            items = CameraRepository.find_paginated(
                session=sess,
                page_params=params,
                search_term=params.term,
                search_fields=[
                    CameraEntity.name,
                    CameraEntity.ip
                ]
            )
            res: list[CameraModelWithRelations] = items.items
            final_items = [
                UiListItem(
                    id=item.id,
                    name=item.name,
                    description=item.ip,
                    icon='mdi-texture-box'
                ) for item in res]
        elif params.condition in [
            RuleConditionKey.AVAILABILITY_SENSOR,
            RuleConditionKey.IS_SENSOR_VALUE
        ]:
            items = SensorRepository.find_paginated(
                session=sess,
                page_params=params,
                search_term=params.term,
                search_fields=[
                    SensorEntity.name,
                    SensorEntity.identifier,
                    SensorEntity.visible_name
                ]
            )
            res: list[SensorModelWithDevice] = items.items
            final_items = [
                UiListItem(
                    id=item.id,
                    name=item.identifier,
                    description=item.name,
                    icon='mdi-thermometer'
                ) for item in
                res]
        elif params.condition in [
            RuleConditionKey.IS_STORAGE_SIZE
        ]:
            items = StorageRepository.find_paginated(
                session=sess,
                page_params=params,
                search_term=params.term,
                search_fields=[
                    StorageEntity.name,
                    StorageEntity.path
                ]
            )
            res: list[StorageModel] = items.items
            final_items = [
                UiListItem(
                    id=item.id,
                    name=item.name,
                    description=item.path,
                    icon='mdi-harddisk'
                ) for item in
                res]

        return PaginatedResponse(
            items=final_items,
            total=items.total,
            page=items.page,
            size=items.size,
            pages=items.pages,
        )
