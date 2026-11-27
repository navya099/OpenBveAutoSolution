from dataclasses import dataclass

from bveauto.xref.decats.core.mast.base.mast_base import MastBase
from bveauto.xref.decats.core.mast.mast_accessory.mast_accessory import MastAccessory


@dataclass
class Mast:
    name: str
    index: int
    offset: tuple[float, float]
    rotation: float = 0.0
    base: MastBase | None = None
    accessories: list[MastAccessory] = None
    role: str = ''          # 역할 (bveauto.xref.decats.enums.component_role.ComponentRole)
    spec: str = ''          # 형식·위치 등 세부 (I/O, L/R, P10 …)
