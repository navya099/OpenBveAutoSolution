from dataclasses import dataclass


@dataclass
class MastBase:
    name: str
    index: int
    offset: tuple[float, float]
    rotation: float
    role: str = ''          # 역할 (bveauto.xref.decats.enums.component_role.ComponentRole)
    spec: str = ''          # 형식·위치 등 세부 (I/O, L/R, P10 …)