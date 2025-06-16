from enum import Enum


class MqttSensorTypeEnum(Enum):
    RELAY = 1
    INPUT = 2
    NTC = 3
    OPENTHERM = 4
    RF433 = 5
    DS18B20 = 6
    AI = 7
