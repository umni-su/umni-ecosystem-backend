from enum import StrEnum
from typing import List, Dict, Set, LiteralString
from pydantic import BaseModel, Field

from classes.logger.logger import Logger
from classes.logger.logger_types import LoggerType
from models.rule_model import NodeDataWithList, NodeVisualize, RuleNodeTypeKeys


# Pydantic модель для хранения информации о триггере
class RuleTriggerModel(BaseModel):
    rule_id: int
    ids: List[int] = Field(default_factory=list())


# Модель для хранения идентификаторов с привязкой к rule_id
class EntityIdsCollection:
    def __init__(self):
        self._rules: Dict[int, Set[int]] = {}  # {rule_id: set(entity_ids)}

    def add(self, rule_id: int, entity_id: int) -> None:
        if rule_id not in self._rules:
            self._rules[rule_id] = set()
        self._rules[rule_id].add(entity_id)

    def remove(self, rule_id: int, entity_id: int) -> bool:
        if rule_id in self._rules and entity_id in self._rules[rule_id]:
            self._rules[rule_id].remove(entity_id)
            # Если после удаления set пустой, удаляем rule_id
            if not self._rules[rule_id]:
                del self._rules[rule_id]
            return True
        return False

    def exists(self, entity_id: int) -> bool:
        """Проверяет существование entity_id в любом rule_id"""
        for rule_entities in self._rules.values():
            if entity_id in rule_entities:
                return True
        return False

    def find(self, entity_id: int) -> List[RuleTriggerModel]:
        """Находит все rule_id, где есть entity_id"""
        result = []
        for rule_id, entities in self._rules.items():
            if entity_id in entities:
                result.append(RuleTriggerModel(rule_id=rule_id, ids=list(entities)))
        return result

    def get_all(self) -> List[RuleTriggerModel]:
        """Возвращает все rule_id с их entity_ids"""
        return [
            RuleTriggerModel(rule_id=rule_id, ids=sorted(list(entities)))
            for rule_id, entities in self._rules.items()
        ]

    def get_rule_ids_for_entity(self, entity_id: int) -> List[int]:
        """Возвращает список rule_id для конкретного entity_id"""
        return [
            rule_id for rule_id, entities in self._rules.items()
            if entity_id in entities
        ]

    def reload(self, rule_models: List[RuleTriggerModel]) -> None:
        """Полная перезагрузка данных"""
        self._rules.clear()
        for rule_model in rule_models:
            for entity_id in rule_model.ids:
                self.add(rule_model.rule_id, entity_id)

    def __len__(self) -> int:
        return sum(len(entities) for entities in self._rules.values())

    def __repr__(self) -> str:
        return f"EntityIdsCollection(rules={len(self._rules)}, total_entities={len(self)})"


# Модель для хранения триггеров
class RuleTriggersStore:
    def __init__(self, nodes: List["NodeVisualize"] = None):
        self._storage: Dict[RuleNodeTypeKeys, EntityIdsCollection] = {}
        if nodes:
            self.reread(nodes)

    def reread(self, nodes: List['NodeVisualize']) -> None:
        """Полностью переинициализирует хранилище из списка NodeVisualize"""
        self._storage.clear()

        # Фильтруем только trigger-ноды
        trigger_nodes = [node for node in nodes if node.type == 'trigger']

        for node in trigger_nodes:
            try:
                key_str = node.key
                rule_id = node.rule_id

                # Получаем IDs из options
                ids = self._parse_ids_from_options(node.data)

                # Конвертируем строковый ключ в enum
                key = self._get_key_enum(key_str)
                if key and ids:
                    if key not in self._storage:
                        self._storage[key] = EntityIdsCollection()

                    # Добавляем все ids для этого rule_id
                    for entity_id in ids:
                        self._storage[key].add(rule_id, entity_id)

            except Exception as e:
                Logger.err(f"Error processing node {node.id}: {e}", LoggerType.RULES)
                continue

    def _parse_ids_from_options(self, data: "NodeDataWithList") -> List[int]:
        """Парсит IDs из NodeDataWithList"""
        try:
            ids = data.options.ids
            if isinstance(ids, list):
                return [int(id) for id in ids if str(id).isdigit()]
        except:
            pass
        return []

    def _get_key_enum(self, key_str: str) -> LiteralString | None:
        """Конвертирует строку в enum ключ"""
        for key in RuleNodeTypeKeys:
            if key == key_str:
                return key
        return None

    def find(self, key: RuleNodeTypeKeys) -> EntityIdsCollection:
        """Возвращает коллекцию идентификаторов для ключа"""
        return self._storage.get(key, EntityIdsCollection())

    def has(self, key: RuleNodeTypeKeys) -> bool:
        """Проверяет наличие ключа в хранилище"""
        return key in self._storage

    def add_entity(self, key: RuleNodeTypeKeys, rule_id: int, entity_id: int) -> None:
        """Добавляет entity_id для указанного ключа и rule_id"""
        if key not in self._storage:
            self._storage[key] = EntityIdsCollection()
        self._storage[key].add(rule_id, entity_id)

    def remove_entity(self, key: RuleNodeTypeKeys, rule_id: int, entity_id: int) -> bool:
        """Удаляет entity_id для указанного ключа и rule_id"""
        if key in self._storage:
            return self._storage[key].remove(rule_id, entity_id)
        return False

    def get_all_keys(self) -> List[RuleNodeTypeKeys]:
        """Возвращает все ключи в хранилище"""
        return list(self._storage.keys())

    def __repr__(self) -> str:
        return f"RuleTriggersStore(keys={list(self._storage.keys())})"


rules_triggers_store = RuleTriggersStore()
