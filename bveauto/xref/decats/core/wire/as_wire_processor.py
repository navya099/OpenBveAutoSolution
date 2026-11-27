"""에어섹션 구간 전선 (본선·무효선·장간애자)

에어섹션 = 1구간(AS1_1 ~ AS1_5, 단일 에어섹션은 여기까지) + 이중 에어섹션의 2구간(AS2_1 ~ AS2_4).
2구간은 1구간과 좌우가 반대라 오프셋 부호만 뒤집힌다 (_signed_offsets 의 second).

전주별 처리:
    AS1_1        본선 → AS 시점, 장력장치에서 오르는 무효선
    AS1_2 AS2_1  본선 (AS 시점 → 중간2), 무효선 (F 시점 → 중간1), 장간애자
    AS1_3 AS2_2  본선 → 무효선 상승 (중간2 → F 끝), 무효선 → 본선 (중간1 → AS 끝)
    AS1_4_D      본선 (AS 끝 유지), 1구간 무효선 → 장력장치, 2구간 장력장치에서 오르는 무효선
    AS1_4_S      본선 (AS 끝 → 다음 전주), 무효선 → 장력장치, 장간애자
    AS2_3        AS1_4_S 와 같고 장력장치 길이·높이만 다름
    AS1_5 AS2_4  본선 (일반 개소처럼 브래킷 편위)
"""
from bveauto.xref.decats.core.wire.section_wire_base import SectionWireProcessor
from bveauto.xref.decats.enums.section_type import SectionType

# 무효선이 장력장치로 내려가는 구간의 장력장치 길이·높이 (AS1_4_D 1구간, AS2_3)
SHORT_TENSION = dict(tension_device_length=4, cw_height=5.638094, mw_height=6.237956)


class AirSectionWireProcessor(SectionWireProcessor):
    OFFSET_GETTER = 'get_airsection_offset'
    PREFIX = 'AS형'

    def _section_offsets(self, pole, second=False):
        """1구간: 시점 쪽 부호 = −side, 2구간(second): +side (좌우 반대)"""
        return self._signed_offsets(pole, pole.side if second else -pole.side)

    def run(self, pole, next_pole, wire, pitch_angle, offset, cw_index):
        section = pole.section
        if section == SectionType.AS1_1:
            self.wires_start(pole, next_pole, wire, cw_index, pitch_angle, self._section_offsets(pole))
        elif section in (SectionType.AS1_2, SectionType.AS2_1):
            o = self._section_offsets(pole, second=section == SectionType.AS2_1)
            self.wires_parallel_in(pole, next_pole, wire, cw_index, pitch_angle, o, insulators=True)
        elif section in (SectionType.AS1_3, SectionType.AS2_2):
            o = self._section_offsets(pole, second=section == SectionType.AS2_2)
            self.wires_crossing(pole, next_pole, wire, cw_index, pitch_angle, o)
        elif section == SectionType.AS1_4_D:
            self.process_double_middle(pole, next_pole, wire, cw_index, pitch_angle)
        elif section == SectionType.AS1_4_S:
            self.process_parallel_out(pole, next_pole, wire, cw_index, pitch_angle, second=False, cut=7)
        elif section == SectionType.AS2_3:
            self.process_parallel_out(pole, next_pole, wire, cw_index, pitch_angle, second=True, cut=4,
                                      **SHORT_TENSION)
        elif section in (SectionType.AS1_5, SectionType.AS2_4):
            self.wires_end(pole, next_pole, wire, cw_index, pitch_angle)

    def process_double_middle(self, pole, next_pole, wire, cw_index, pitch_angle):
        """AS1_4_D (이중 에어섹션 가운데): 본선 AS 끝 유지, 1구간 무효선 → 장력장치,
        2구간 무효선이 장력장치에서 오름 (2구간 F 시점은 1구간 기준 좌표에서 좌측일 때만 반전)"""
        o = self._section_offsets(pole)
        h = dict(heights=self._heights(pole, next_pole), f_y=o['f_y'])
        scw, ecw, _, _ = h['heights']
        self._wire(wire, cw_index, pole, (o['end'], scw), (o['end'], ecw), pitch_angle, '본선전차선')
        self._falling_to_tension(wire, pole, pitch_angle, 4, o['f_end'], h, **SHORT_TENSION)
        second_f_start = o['f_start'] * (-1 if pole.side == -1 else 1)
        self._rising_from_tension(wire, pole, pitch_angle, self.datap.get_inactive_mw_span(pole.span - 6),
                                  self.datap.get_inactive_cw_span(pole.span - 6), second_f_start, h)

    def process_parallel_out(self, pole, next_pole, wire, cw_index, pitch_angle, second, cut, **tension):
        """AS1_4_S / AS2_3: 본선 AS 끝 → 다음 전주 편위, 무효선 F 끝 → 장력장치, 장간애자"""
        o = self._section_offsets(pole, second)
        h = dict(heights=self._heights(pole, next_pole), f_y=o['f_y'])
        scw, ecw, ssys, _ = h['heights']
        self._wire(wire, cw_index, pole, (o['end'], scw), (next_pole.brackets[0].stagger, ecw), pitch_angle,
                   '본선전차선')
        self._falling_to_tension(wire, pole, pitch_angle, cut, o['f_end'], h, **tension)
        self._insulators(wire, pole, -2, o['f_end'], scw + ssys, scw + o['f_y'])
