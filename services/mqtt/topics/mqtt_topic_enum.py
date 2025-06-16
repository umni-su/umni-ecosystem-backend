from enum import StrEnum


class MqttTopicEnum(StrEnum):
    REGISTER = 'register'
    CNF_DIO = 'cnf/dio'
    CNF_OW = 'cnf/ow'
    CNF_RF433 = 'cnf/rf'
    CNF_AI = 'cnf/ai'
    OW = 'ow'
    RF433 = 'rf'
    AI = 'ai'
    NTC = 'ntc'
    INP = 'inp'
    REL = 'rel'
