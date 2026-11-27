from dataclasses import dataclass, field

from bveauto.xref.decats.core.bracket.fitting_data import FittingDATA


@dataclass
class BracketDATA:
    bracket_type: str
    index: int
    offset: tuple[float, float] = (0, 0)
    rotation: float = 0.0
    bracket_name: str = ""
    stagger: float = 0.0
    fittings: list[FittingDATA] = field(default_factory=list)
    on_twin: bool = False   # 복주: 두 번째 전주(PoleDATA.twin)에 달린 브래킷
    role: str = ''          # 역할 (bveauto.xref.decats.enums.component_role.ComponentRole)
    spec: str = ''          # 형식·위치 등 세부 (I/O, L/R, P10 …)