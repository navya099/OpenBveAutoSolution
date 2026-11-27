"""실제로 선 전주 단위 — 복주 에어조인트는 지지점(PoleDATA) 1개에 전주 2개

화면(테이블·배치도)과 CSV 주석에서 복주 전주를 앞/뒤로 따로 다루기 위한 보조 함수 (GUI 없이 동작).
    단주:  1-39D            측점 = pos
    복주:  1-39D-F (앞 전주) 측점 = pos − 간격/2
           1-39D-B (뒤 전주) 측점 = pos + 간격/2
편집 데이터(PoleDATA)는 그대로 지지점 하나이고, which 로 앞(0)/뒤(1) 전주를 구분한다.
"""
from dataclasses import dataclass

FRONT, REAR = 0, 1
SUFFIX = {FRONT: 'F', REAR: 'B'}
SIDE_TEXT = {FRONT: '앞 전주', REAR: '뒤 전주'}


@dataclass(frozen=True)
class PoleUnit:
    pole: object             # PoleDATA
    which: int | None        # None = 단주, FRONT/REAR = 복주 앞/뒤 전주

    @property
    def label(self):
        return unit_label(self.pole, self.which)

    @property
    def station(self):
        front, rear = self.pole.station_offsets
        offset = rear if self.which == REAR else front
        return _clean(self.pole.pos + offset)

    def coord(self, alignment):
        """평면 좌표 (지지점이면 PoleDATA.coord, 복주 전주면 자기 측점의 게이지 위치)"""
        if self.which is None:
            return tuple(self.pole.coord)
        from bveauto.xref.decats.core.alignment.alignment import as_alignment
        return tuple(as_alignment(alignment).offset_point(self.station, self.pole.gauge))

    @property
    def key(self):
        """테이블 행 식별자"""
        return f'{self.pole.uid}|{"" if self.which is None else self.which}'


def _clean(value):
    value = round(float(value), 6)
    return int(value) if value.is_integer() else value


def units(pole):
    """지지점 → 실제 전주 목록 (단주 1개, 복주 앞·뒤 2개)"""
    if getattr(pole, 'twin', None) is None:
        return [PoleUnit(pole, None)]
    return [PoleUnit(pole, FRONT), PoleUnit(pole, REAR)]


def track_units(poles):
    return [u for pole in poles for u in units(pole)]


def unit_label(pole, which):
    """전주번호 표시: 복주면 '-F'(앞) / '-B'(뒤)"""
    if which is None or getattr(pole, 'twin', None) is None:
        return pole.post_number
    return f'{pole.post_number}-{SUFFIX[which]}'


def find_unit(poles, key):
    """행 식별자 → PoleUnit (없으면 None)"""
    uid, _, which = key.partition('|')
    pole = next((p for p in poles if p.uid == uid), None)
    if pole is None:
        return None
    which = int(which) if which != '' else None
    if which is not None and getattr(pole, 'twin', None) is None:
        which = None   # 복주가 일반 전주로 바뀐 뒤
    return PoleUnit(pole, which)


def bracket_stations(pole):
    """브래킷별 측점 보정값 [(브래킷, dpos)] — BVE CSV 와 도면이 같은 규칙을 쓴다.
    복주: 달린 전주 위치(∓간격/2). 단주 평행 개소: 브래킷 2개를 ±0.528m(에어조인트 중간주는 ±0.8m).
    구간 시작·끝 전주(에어조인트 1·5호주, 에어섹션 AS1_1·AS1_5·AS2_4)는 첫 브래킷만. 일반 전주는 모두 측점에."""
    from bveauto.xref.decats.enums.section_type import SectionType, section_role
    brackets = list(pole.brackets or [])
    if getattr(pole, 'twin', None) is not None:
        front, rear = pole.station_offsets
        return [(b, rear if getattr(b, 'on_twin', False) else front) for b in brackets]
    role = section_role(pole.section)
    if role in (SectionType.AJ_START, SectionType.AJ_END, SectionType.AS1_1, SectionType.AS1_5, SectionType.AS2_4):
        return [(brackets[0], 0)] if brackets else []
    if role == SectionType.AJ_MIDDLE:
        return list(zip(brackets, (-0.8, 0.8)))
    if role in (SectionType.AJ_2, SectionType.AJ_4, SectionType.AS1_2, SectionType.AS1_3, SectionType.AS1_4_S,
                SectionType.AS1_4_D, SectionType.AS2_1, SectionType.AS2_2, SectionType.AS2_3):
        return list(zip(brackets, (-0.528, 0.528)))
    return [(b, 0) for b in brackets]
