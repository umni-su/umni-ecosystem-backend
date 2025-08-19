from typing import Annotated

from fastapi import APIRouter, Depends

from classes.auth.auth import Auth
from database.database import write_session
from entities.rule_entity import RuleEntity
from models.rule_model import (
    RuleCreate,
    RuleGraphUpdate,
    RuleModel
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
        rule: list[RuleEntity] = Depends(RulesRepository.get_rule)
):
    return rule


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
