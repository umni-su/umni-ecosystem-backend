import time
from starlette.exceptions import HTTPException

from database.database import write_session
from entities.camera_area import CameraAreaEntity
from entities.device import Device
from entities.rule_entity import RuleEntity, RuleNode, RuleEdge
from models.rule_model import (
    RuleCreate,
    RuleNodeTypes,
    RuleNodeTypeKeys,
    RuleNodeData, NodePosition,
    RuleGraphUpdate,
    RuleEntityType, RuleNodeListItem, RuleNodeFlow, RuleNodeEl, RuleNodeModel
)
from repositories.base_repository import BaseRepository
from sqlmodel import select, delete, col

from repositories.camera_repository import CameraRepository
from repositories.device_repository import DeviceRepository


class RulesRepository(BaseRepository):
    @classmethod
    def get_rules(cls):
        with write_session() as sess:
            return sess.exec(
                select(RuleEntity)
            ).all()

    @classmethod
    def get_rule(cls, rule_id: int):
        with write_session() as sess:
            rule = sess.get(RuleEntity, rule_id)
            if not rule:
                raise HTTPException(status_code=404, detail="Rule not found")
            return rule

    @classmethod
    def add_rule(cls, rule_data: RuleCreate):
        with write_session() as sess:
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

            return db_rule

    @classmethod
    def update_rule_graph(
            cls,
            rule_id: int,
            graph_data: RuleGraphUpdate
    ):
        with write_session() as session:
            # Удаляем старые узлы и связи
            session.exec(delete(RuleEdge).where(col(RuleEdge.rule_id) == rule_id))
            session.exec(delete(RuleNode).where(col(RuleNode.rule_id) == rule_id))

            # Добавляем новые узлы
            for node in graph_data.nodes:
                node_data = RuleNodeData(**node.data.model_dump())

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
            return session.get(RuleEntity, rule_id)

    @classmethod
    def get_node(cls, node_id: str):
        with write_session() as sess:
            node = sess.get(RuleNode, node_id)
            if not node:
                raise HTTPException(status_code=404, detail="Node not found")
            return RuleNodeModel.model_validate(node.model_dump())

    @classmethod
    def get_node_entities_by_trigger(cls, trigger: str | None):
        if trigger is None:
            return []
        res = []
        trigger = RuleNodeTypeKeys(trigger)
        if trigger in (
                RuleNodeTypeKeys.MOTION_START,
                RuleNodeTypeKeys.MOTION_END
        ):
            cameras = CameraRepository.get_cameras()
            for camera in cameras:
                for area in camera.areas:
                    res.append(
                        RuleNodeListItem(
                            id=area.id,
                            name=area.name,
                            icon='mdi-texture-box',
                            color=area.color
                        )
                    )
        if trigger == RuleNodeTypeKeys.DEVICES_CHANGES:
            devices = DeviceRepository.get_devices()
            for device in devices:
                res.append(
                    RuleNodeListItem(
                        id=device.id,
                        name=device.name,
                        description=device.title,
                        icon='mdi-chip',
                    )
                )
        return res

    @classmethod
    def get_node_entities_by_node(cls, node_id: str):
        node = cls.get_node(node_id)
        if node:
            trigger = node.data.flow.el.key
            ids = node.data.options.get("ids")
            res = []
            if ids is not None:
                with write_session() as sess:
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
                                RuleNodeListItem(
                                    id=area.id,
                                    name=area.name,
                                    icon='mdi-texture-box',
                                    color=area.color
                                )
                            )
                    elif trigger == RuleNodeTypeKeys.DEVICES_CHANGES:
                        devices = sess.exec(
                            select(Device).where(
                                col(Device.id).in_(ids)
                            )
                        ).all()
                        for device in devices:
                            res.append(
                                RuleNodeListItem(
                                    id=device.id,
                                    name=device.name,
                                    description=device.title,
                                    icon='mdi-chip',
                                )
                            )

            return [RuleNodeListItem.model_validate(item) for item in res]

        raise HTTPException(status_code=404, detail="Node not found")
