from pydantic import BaseModel


class NetUsageModel(BaseModel):
    bytes_sent: int
    bytes_received: int
    packets_sent: int
    packets_received: int
