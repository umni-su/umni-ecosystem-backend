from typing import Annotated, Any, Dict

from fastapi import APIRouter, Depends, Body

from classes.auth.auth import Auth
from classes.rules.rule_executor import ExecutionResult, RuleExecutor
from database.database import write_session
from entities.rule_entity import RuleEntity
from models.rule_model import (
    RuleCreate,
    RuleGraphUpdate,
    RuleModel, RuleNodeModel, RuleNodeListItem, RuleNodeTypeKeys
)
from repositories.rules_repository import RulesRepository
from responses.user import UserResponseOut

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
        all_rules: list[RuleEntity] = Depends(RulesRepository.get_rules)
):
    return all_rules


@rules.get("/{rule_id}", response_model=RuleModel)
def get_rule(
        user: Annotated[UserResponseOut, Depends(Auth.get_current_active_user)],
        rule: RuleEntity = Depends(RulesRepository.get_rule)
):
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
    for index, node in enumerate(_rule.nodes):
        _rule.nodes[index].data.items = RulesRepository.get_node_entities_by_node(
            node.id
        )
    return _rule


@rules.post("", response_model=RuleModel)
def create_rule(
        user: Annotated[UserResponseOut, Depends(Auth.get_current_active_user)],
        rule_data: RuleCreate,
        rule: RuleModel = Depends(RulesRepository.add_rule)
):
    return rule


@rules.put("/{rule_id}/graph", response_model=RuleModel)
def update_rule_graph(
        user: Annotated[UserResponseOut, Depends(Auth.get_current_active_user)],
        rule_id: int,
        graph_data: RuleGraphUpdate,
        rule: RuleModel = Depends(RulesRepository.update_rule_graph)
):
    return rule


@rules.post("/{rule_id}/execute", response_model=ExecutionResult)
async def execute_rule(
        user: Annotated[UserResponseOut, Depends(Auth.get_current_active_user)],
        rule_id: int,
        trigger_data: Dict[str, Any] = Body(...),
        executor: RuleExecutor = Depends(RuleExecutor)
):
    """Выполняет правило и возвращает детальный результат"""
    return await executor.execute_rule(rule_id, trigger_data)


@rules.post("/{rule_id}/execute-from-start")
async def execute_from_start(
        user: Annotated[UserResponseOut, Depends(Auth.get_current_active_user)],
        rule_id: int,
        executor: RuleExecutor = Depends(RuleExecutor)
):
    """Выполняет правило с START ноды"""
    return await executor.execute_from_start(rule_id)


@rules.get("/nodes/{node_id}", response_model=RuleNodeModel)
def get_node(
        user: Annotated[UserResponseOut, Depends(Auth.get_current_active_user)],
        node: RuleNodeModel = Depends(RulesRepository.get_node)
):
    return node


@rules.get("/nodes/{node_id}/list", response_model=list[RuleNodeListItem])
def get_node(
        user: Annotated[UserResponseOut, Depends(Auth.get_current_active_user)],
        node: RuleNodeModel = Depends(RulesRepository.get_node),
):
    _list: list[RuleNodeListItem] = RulesRepository.get_node_entities_by_trigger(node.data.flow.el.key)
    return _list
