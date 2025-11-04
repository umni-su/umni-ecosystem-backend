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

import time
from starlette.exceptions import HTTPException

from classes.l10n.l10n import _
from classes.logger.logger import Logger
from classes.logger.logger_types import LoggerType
from classes.rules.rules_store import rules_triggers_store
from database.session import write_session
from entities.camera_area import CameraAreaEntity
from entities.device import DeviceEntity
from entities.rule_entity import RuleEntity, RuleNode, RuleEdge
from entities.sensor_entity import SensorEntity
from models.camera_area_model import CameraAreaBaseModel
from models.pagination_model import PageParams, PaginatedResponse
from models.rule_condition_models import RuleConditionEntitiesParams
from models.rule_model import (
    RuleCreate,
    RuleNodeTypes,
    RuleNodeTypeKeys,
    RuleNodeData, NodePosition,
    RuleGraphUpdate,
    RuleEntityType,
    RuleNodeFlow,
    RuleNodeEl,
    RuleNodeModel,
    RuleModel,
    NodeDataWithList, NodeVisualize
)
from models.sensor_model import SensorModelWithDevice
from models.ui_models import UiListItem
from repositories.area_repository import CameraAreaRepository
from repositories.base_repository import BaseRepository
from sqlmodel import select, delete, col

from repositories.device_repository import DeviceRepository
from repositories.sensor_repository import SensorRepository


class RulesRepository(BaseRepository):
    @classmethod
    def get_rules(cls):
        with write_session() as sess:
            try:
                rules = sess.exec(
                    select(RuleEntity)
                ).all()
                return [
                    RuleModel.model_validate(
                        rule.to_dict(
                            include_relationships=True
                        )
                    )
                    for rule in rules
                ]
            except Exception as e:
                Logger.err(str(e), LoggerType.APP)

    @classmethod
    def get_rule(cls, rule_id: int):
        with write_session() as sess:
            try:
                rule = sess.get(RuleEntity, rule_id)
                if not rule:
                    raise HTTPException(status_code=404, detail="Rule not found")
                return RuleModel.model_validate(
                    rule.to_dict(
                        include_relationships=True
                    )
                )
            except Exception as e:
                Logger.err(str(e), LoggerType.APP)

    @classmethod
    def delete_rule(cls, rule_id: int) -> bool:
        with write_session() as sess:
            try:
                sess.exec(delete(RuleEdge).where(col(RuleEdge.rule_id) == rule_id))
                sess.exec(delete(RuleNode).where(col(RuleNode.rule_id) == rule_id))
                rule = sess.get(RuleEntity, rule_id)
                if not rule:
                    raise HTTPException(status_code=404, detail=_("Rule not found"))
                sess.delete(rule)
                return True
            except Exception as e:
                Logger.err(str(e), LoggerType.APP)
                return False

    @classmethod
    def add_rule(cls, rule_data: RuleCreate):
        with write_session() as sess:
            try:
                db_rule = RuleEntity.model_validate(rule_data)
                sess.add(db_rule)
                sess.commit()
                sess.refresh(db_rule)
                # Добавляем стартовый узел
                start_node = RuleNode(
                    id=time.time(),
                    type=RuleNodeTypes.START,
                    position=NodePosition(
                        x=50,
                        y=50
                    ).model_dump(),
                    rule_id=db_rule.id,
                    key=RuleNodeTypeKeys.RULE_START,
                    data=RuleNodeData(
                        options={},
                        flow=RuleNodeFlow(
                            el=RuleNodeEl(
                                type=RuleNodeTypes.START
                            )
                        )
                    ).model_dump()
                )
                sess.add(start_node)
                sess.commit()
                sess.refresh(db_rule)

                return RuleModel.model_validate(
                    db_rule.to_dict(
                        include_relationships=True
                    )
                )
            except Exception as e:
                Logger.err(str(e), LoggerType.APP)

    @classmethod
    def update_rule_graph(
            cls,
            rule_id: int,
            graph_data: RuleGraphUpdate
    ):
        print(123)
        with write_session() as session:
            try:
                # Удаляем старые узлы и связи
                session.exec(delete(RuleEdge).where(col(RuleEdge.rule_id) == rule_id))
                session.exec(delete(RuleNode).where(col(RuleNode.rule_id) == rule_id))

                # Добавляем новые узлы
                for node in graph_data.nodes:
                    if node.key == RuleNodeTypeKeys.ACTION_WEBHOOK:
                        print(node.data.model_dump(), node_data.model_dump_json(), "\r\n")
                    node_data = NodeDataWithList(**node.data.model_dump())

                    # Определяем entity_type и entity_id
                    entity_type, entity_id = None, None
                    if node.type == RuleNodeTypes.ENTITY:
                        if node_data.flow.el.key in (
                                RuleNodeTypeKeys.DEVICES_CHANGES
                        ):
                            entity_type = RuleEntityType.DEVICE
                        elif node_data.flow.el.key in (
                                RuleNodeTypeKeys.MOTION_END,
                                RuleNodeTypeKeys.MOTION_START
                        ):
                            entity_type = RuleEntityType.CAMERA
                        elif node_data.flow.el.key in (
                                RuleNodeTypeKeys.SENSORS_CHANGES
                        ):
                            entity_type = RuleEntityType.SENSOR
                        entity_id = node_data.options.get("entity_id")
                    db_node = RuleNode(
                        id=node.id,
                        type=node.type,
                        position=node.position.model_dump(),
                        rule_id=rule_id,
                        data=node_data.model_dump(),
                        key=node_data.flow.el.key,
                        entity_id=entity_id,
                        entity_type=entity_type
                    )
                    session.add(db_node)
                session.commit()

                # Добавляем новые связи
                for edge in graph_data.edges:
                    db_edge = RuleEdge(
                        id=edge.id,
                        source=edge.source,
                        target=edge.target,
                        source_handle=edge.source_handle,
                        target_handle=edge.target_handle,
                        rule_id=rule_id
                    )
                    session.add(db_edge)
                session.commit()
                rule = session.get(RuleEntity, rule_id)

                orm_triggers: list[RuleNode] = session.exec(
                    select(RuleNode).where(RuleNode.type == RuleNodeTypes.TRIGGER.value)
                ).all()
                triggers = [
                    NodeVisualize.model_validate(
                        t.to_dict()
                    ) for t in orm_triggers
                ]
                rules_triggers_store.reread(triggers)

                return RuleModel.model_validate(
                    rule.to_dict(
                        include_relationships=True
                    )
                )
            except Exception as e:
                Logger.err(str(e), LoggerType.APP)

    @classmethod
    def get_node(cls, node_id: str):
        with write_session() as sess:
            try:
                node = sess.get(RuleNode, node_id)
                if not node:
                    raise HTTPException(status_code=404, detail="Node not found")
                return RuleNodeModel.model_validate(
                    node.model_dump()
                )
            except Exception as e:
                Logger.err(str(e), LoggerType.APP)

    @classmethod
    def get_node_entities_by_trigger(cls, trigger: str | None, params: PageParams):
        with write_session() as sess:
            try:
                if trigger is None:
                    return []
                res = []
                _items = []
                trigger = RuleNodeTypeKeys(trigger)
                if trigger in (
                        RuleNodeTypeKeys.MOTION_START,
                        RuleNodeTypeKeys.MOTION_END
                ):
                    # cameras = CameraRepository.get_cameras()
                    res = CameraAreaRepository.find_paginated(
                        session=sess,
                        page_params=params,
                        search_term=params.term,
                        search_fields=[
                            CameraAreaEntity.name
                        ]
                    )
                    all_areas: list[CameraAreaBaseModel] = res.items
                    for area in all_areas:
                        _items.append(
                            UiListItem(
                                id=area.id,
                                name=area.name,
                                icon='mdi-texture-box',
                                color=area.color
                            )
                        )

                elif trigger == RuleNodeTypeKeys.DEVICES_CHANGES:
                    res = DeviceRepository.find_paginated(
                        session=sess,
                        page_params=params,
                        search_term=params.term,
                        search_fields=[
                            DeviceEntity.name,
                            DeviceEntity.description,
                            DeviceEntity.title
                        ]
                    )
                    for device in res.items:
                        _items.append(
                            UiListItem(
                                id=device.id,
                                name=device.name,
                                description=device.title,
                                icon='mdi-chip',
                            )
                        )
                elif trigger == RuleNodeTypeKeys.SENSORS_CHANGES:

                    res = SensorRepository.find_paginated(
                        session=sess,
                        page_params=params,
                        search_term=params.term,
                        search_fields=[
                            SensorEntity.name,
                            SensorEntity.visible_name,
                            SensorEntity.identifier
                        ]
                    )
                    ar: list[SensorModelWithDevice] = res.items
                    for sensor in ar:
                        _items.append(
                            UiListItem(
                                id=sensor.id,
                                name=sensor.identifier,
                                description=sensor.name,
                                icon='mdi-chip',
                            )
                        )

                return PaginatedResponse(
                    items=_items,
                    total=res.total,
                    page=res.page,
                    size=res.size,
                    pages=res.pages,
                )
            except Exception as e:
                Logger.err(str(e), LoggerType.APP)

    @classmethod
    def get_node_entities_by_node(cls, node_id: str):
        try:
            node = cls.get_node(node_id)
            if node:
                trigger = node.data.flow.el.key
                ids = node.data.options.get("ids")
                res = []
                if ids is not None:
                    with write_session() as sess:
                        try:
                            if trigger in (
                                    RuleNodeTypeKeys.MOTION_START,
                                    RuleNodeTypeKeys.MOTION_END
                            ):
                                areas = sess.exec(
                                    select(CameraAreaEntity).where(
                                        col(CameraAreaEntity.id).in_(ids)
                                    )
                                ).all()
                                for area in areas:
                                    res.append(
                                        UiListItem(
                                            id=area.id,
                                            name=area.name,
                                            icon='mdi-texture-box',
                                            color=area.color
                                        )
                                    )
                            elif trigger == RuleNodeTypeKeys.DEVICES_CHANGES:
                                devices = sess.exec(
                                    select(DeviceEntity).where(
                                        col(DeviceEntity.id).in_(ids)
                                    )
                                ).all()
                                for device in devices:
                                    res.append(
                                        UiListItem(
                                            id=device.id,
                                            name=device.name,
                                            description=device.title,
                                            icon='mdi-chip',
                                        )
                                    )
                        except Exception as e:
                            Logger.err(str(e), LoggerType.APP)

                return [UiListItem.model_validate(item) for item in res]

            raise HTTPException(status_code=404, detail="Node not found")
        except Exception as e:
            Logger.err(str(e), LoggerType.APP)

    @classmethod
    def get_rule_condition_entities(cls, params: RuleConditionEntitiesParams):
        return params
