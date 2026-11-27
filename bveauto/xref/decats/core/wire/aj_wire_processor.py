"""에어조인트(2경간, 단주·복주) 전선 — 에어섹션 1구간과 같은 모양이고 오프셋 표(airjoint)와 좌우만 다름

    1호주(AJ_START)  본선 → AJ 시점, 장력장치에서 오르는 무효선
    2호주(AJ_2)      본선 (AJ 시점 → 중간2), 무효선 (F 시점 → 중간1)
    3호주(AJ_MIDDLE) 본선 → 무효선 상승, 무효선 → 본선
    4호주(AJ_4)      본선 (AJ 끝 → 다음 전주 편위), 무효선 → 장력장치
    5호주(AJ_END)    본선 (일반 개소처럼 브래킷 편위)
복주 에어조인트도 같은 위치 역할(section_role)이라 전선은 단주와 같다.
"""
from bveauto.xref.decats.core.wire.section_wire_base import SectionWireProcessor
from bveauto.xref.decats.enums.section_type import SectionType, section_role


class AirjointWireProcessor(SectionWireProcessor):
    OFFSET_GETTER = 'get_airjoint_offset'
    PREFIX = 'AJ형'

    def run(self, pole, next_pole, wire, pitch_angle, offset, cw_index):
        role = section_role(pole.section)
        o = self._signed_offsets(pole, pole.side)   # 시점 쪽 부호 = side
        if role == SectionType.AJ_START:
            self.wires_start(pole, next_pole, wire, cw_index, pitch_angle, o)
        elif role == SectionType.AJ_2:
            self.wires_parallel_in(pole, next_pole, wire, cw_index, pitch_angle, o, insulators=False)
        elif role == SectionType.AJ_MIDDLE:
            self.wires_crossing(pole, next_pole, wire, cw_index, pitch_angle, o)
        elif role == SectionType.AJ_4:
            h = dict(heights=self._heights(pole, next_pole), f_y=o['f_y'])
            scw, ecw, _, _ = h['heights']
            self._wire(wire, cw_index, pole, (o['end'], scw), (next_pole.brackets[0].stagger, ecw), pitch_angle,
                       '본선전차선')
            self._falling_to_tension(wire, pole, pitch_angle, 6, o['f_end'], h)
        elif role == SectionType.AJ_END:
            self.wires_end(pole, next_pole, wire, cw_index, pitch_angle)
