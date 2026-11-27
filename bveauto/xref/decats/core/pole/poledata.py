import uuid
from dataclasses import dataclass, field

from bveauto.xref.decats.core.bracket.bracket_data import BracketDATA
from bveauto.xref.decats.core.equipment.equipment_data import EquipmentDATA
from bveauto.xref.decats.core.mast.mastdata import Mast
from bveauto.xref.decats.enums.section_type import FlowStop, SectionType


def new_pole_uid() -> str:
    return uuid.uuid4().hex


@dataclass
class TwinPole:
    """복주(複柱): 한 지지점에 선 두 번째 전주. 주 전주는 측점 − spacing/2, 이 전주는 측점 + spacing/2 에 선다.
    브래킷은 PoleDATA.brackets 에 함께 두고 BracketDATA.on_twin 으로 어느 전주에 달렸는지 구분한다."""
    spacing: float
    mast: Mast | None = None
    equipments: list[EquipmentDATA] = field(default_factory=list)


@dataclass
class PoleDATA:
    post_number: str
    pos: int
    next_pos: int
    span: int
    gauge: float
    next_gauge: float
    structure: str
    next_structure: str
    radius: float
    cant: float
    pitch: float
    section: SectionType | None   # None = 일반개소
    z: float
    next_z: float
    mast: Mast | None
    brackets: list[BracketDATA] = field(default_factory=list)
    equipments: list[EquipmentDATA] = field(default_factory=list)
    base_type: str = ''
    next_base_type: str = ''
    coord: tuple[float, float] = (0, 0)
    track: str = None  # 추가: 트랙 구분 (main / sub)
    side: int = None  # 추가: 좌/우 구분 -1,1
    next_side: int = None
    # 흐름방지장치 위치 (구간과 별개). 흐름방지가 붙어도 section(일반개소/에어조인트 등)은 그대로 유지된다
    flowstop: FlowStop | None = None
    # 전주 고유 ID: 전주가 이동/재계산돼도 유지. 경간(Span) = (앞 전주 uid, 뒤 전주 uid)
    uid: str = field(default_factory=new_pole_uid)
    # 복주 에어조인트의 두 번째 전주 (없으면 None)
    twin: TwinPole | None = None

    @property
    def station_offsets(self):
        """(주 전주, 두 번째 전주) 측점 보정값. 복주가 아니면 (0, None)"""
        if self.twin is None:
            return 0, None
        half = self.twin.spacing / 2
        return -half, half


# ── 이웃 전주 값: 저장하지 않고 다음 전주에서 바로 읽음 ─────────────────────
# 예전에는 next_* 를 다음 전주 값으로 복사해 두고 편집 때마다 다시 복사해야 했다 (빠뜨리면 값이 어긋남:
# 토공→터널 경간 next_gauge 부호 버그). 이제 PoleUpdator 가 다음 전주를 잇고(link_next), 아래 속성은 이은 전주의
# 현재 값을 그대로 돌려준다. 잇지 않은 전주(레일 단절 직전, 마지막 전주)는 생성 때 넣은 값(측점 기준)을 쓴다.
NEIGHBOR_FIELDS = {
    'next_pos': lambda pole, nxt: nxt.pos,
    'span': lambda pole, nxt: nxt.pos - pole.pos,
    'next_gauge': lambda pole, nxt: nxt.gauge,
    'next_structure': lambda pole, nxt: nxt.structure,
    'next_z': lambda pole, nxt: nxt.z,
    'next_base_type': lambda pole, nxt: nxt.base_type,
    'next_side': lambda pole, nxt: nxt.side,
}


def _neighbor_property(name, compute):
    def getter(self):
        nxt = self.__dict__.get('_next')
        if nxt is not None:
            return compute(self, nxt)
        unlinked = self.__dict__.get('_unlinked')
        if unlinked is not None and name in unlinked:
            return unlinked[name]
        return self.__dict__.get(name)          # 구버전 .dat: 값이 인스턴스에 그대로 저장돼 있음

    def setter(self, value):
        """생성자·구버전 코드가 넣는 값 = 잇지 않았을 때 쓰는 값"""
        self.__dict__.setdefault('_unlinked', {})[name] = value

    return property(getter, setter, doc=f'{name}: 이은 다음 전주에서 계산 (잇지 않았으면 생성 때 값)')


for _name, _compute in NEIGHBOR_FIELDS.items():
    setattr(PoleDATA, _name, _neighbor_property(_name, _compute))


def _link_next(self, other):
    """다음 전주 잇기 (None = 잇지 않음). PoleUpdator 만 부른다"""
    self.__dict__['_next'] = other


def _next_pole(self):
    """이은 다음 전주 (없으면 None)"""
    return self.__dict__.get('_next')


def _getstate(self):
    """저장(.dat)·복사 때 다음 전주 연결은 빼고 저장 (긴 연결 사슬은 pickle 재귀 한도를 넘음).
    불러온 뒤 normalize/rebuild 가 다시 잇는다"""
    state = dict(self.__dict__)
    state.pop('_next', None)
    return state


PoleDATA.link_next = _link_next
PoleDATA.next_pole = property(_next_pole)
PoleDATA.__getstate__ = _getstate
