import time

from database.database import write_session
from entities.rule_entity import RuleEntity, RuleNode, RuleEdge
from models.rule_model import RuleCreate, RuleNodeTypes, RuleNodeTypeKeys, RuleNodeData, NodePosition, RuleGraphUpdate, \
    RuleEntityType
from repositories.base_repository import BaseRepository
from sqlmodel import select, delete


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
            return sess.get(RuleEntity, rule_id)

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
                    flow={"el": {"type": "start"}}
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
            session.exec(delete(RuleEdge).where(RuleEdge.rule_id == rule_id))
            session.exec(delete(RuleNode).where(RuleNode.rule_id == rule_id))

            # Добавляем новые узлы
            for node in graph_data.nodes:
                node_data = RuleNodeData(**node.data.model_dump())

                # Определяем entity_type и entity_id
                entity_type, entity_id = None, None
                if node.type == RuleNodeTypes.ENTITY:
                    if node_data.flow["el"]["key"] in (
                            RuleNodeTypeKeys.DEVICES_CHANGES
                    ):
                        entity_type = RuleEntityType.DEVICE
                    elif node_data.flow["el"]["key"] in (
                            RuleNodeTypeKeys.MOTION_END,
                            RuleNodeTypeKeys.MOTION_START
                    ):
                        entity_type = RuleEntityType.CAMERA
                    elif node_data.flow["el"]["key"] in (
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
                    key=node_data.flow["el"]["key"],
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
                    source_handle=edge.sourceHandle,
                    target_handle=edge.targetHandle,
                    rule_id=rule_id
                )
                session.add(db_edge)
            session.commit()
            return session.get(RuleEntity, rule_id)
