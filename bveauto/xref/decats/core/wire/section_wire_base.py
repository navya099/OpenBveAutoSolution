"""에어조인트·에어섹션 전선 공통 (본선·무효선·장간애자 생성 도우미)

평행 개소는 시점 쪽(시점·F 시점·중간1)과 끝 쪽(중간2·끝·F 끝) 오프셋이 선로 양쪽으로 갈린다.
하위 클래스는 OFFSET_GETTER(데이터셋 오프셋 표)와 PREFIX(AJ형/AS형)만 정한다.
"""
from bveauto.xref.decats.core.insulator.insulator_data import InsulatorData
from bveauto.xref.decats.core.wire.common_processor import CommonWireProcessor
from bveauto.xref.decats.utils.comom_util import initialrize_tenstion_device


class SectionWireProcessor:
    OFFSET_GETTER = None    # 'get_airjoint_offset' | 'get_airsection_offset'
    PREFIX = None           # 'AJ형' | 'AS형'

    def __init__(self, compros: CommonWireProcessor, datap, al):
        self.common = compros
        self.datap = datap
        self.al = al

    # ── 공통 ────────────────────────────────────────
    def _offset(self, name):
        """데이터셋 오프셋 (x, y)"""
        value = getattr(self.datap, self.OFFSET_GETTER)(name)
        return value.get('x'), value.get('y')

    def _signed_offsets(self, pole, start_sign):
        """방향에 맞춘 x 오프셋과 F형 높이. 시점 쪽(시점·F 시점·중간1)에 start_sign, 끝 쪽(중간2·끝·F 끝)에 반대 부호"""
        end_sign = -start_sign
        p = self.PREFIX
        f_start_x, f_start_y = self._offset('F형_시점')
        return dict(
            start=self._offset(f'{p}_시점')[0] * start_sign,
            f_start=f_start_x * start_sign,
            middle1=self._offset(f'{p}_중간1')[0] * start_sign,
            middle2=self._offset(f'{p}_중간2')[0] * end_sign,
            end=self._offset(f'{p}_끝')[0] * end_sign,
            f_end=self._offset('F형_끝')[0] * end_sign,
            f_y=f_start_y,
        )

    def _heights(self, pole, next_pole):
        """(시작 전차선, 끝 전차선, 시작 가고, 끝 가고)"""
        d = self.datap
        return (d.get_contact_wire_height(pole.structure), d.get_contact_wire_height(next_pole.structure),
                d.get_system_height(pole.structure), d.get_system_height(next_pole.structure))

    def _wire(self, wire, index, pole, start, end, pitch_angle, label, station=None):
        w = self.common.run(self.al, index, station if station is not None else pole.pos, pole.next_pos,
                            pole.z, pole.next_z, start, end, pitch_angle, label=label)
        if station is not None:
            w.station = station
        wire.add_wire(w)

    def _insulators(self, wire, pole, dpos, x, mw_height, cw_height):
        """장간애자 (조가선·전차선 높이에 하나씩)"""
        index = self.datap.get_equipment_index('장간애자')
        for height in (mw_height, cw_height):
            wire.add_insulator(InsulatorData(pos=pole.pos + dpos, index=index, type='장간애자N-a',
                                             offset=(x, height), yaw=0, pitch=0, roll=0))

    def _rising_from_tension(self, wire, pole, pitch_angle, imw_index, icw_index, end_x, h):
        """장력장치에서 출발해 다음 전주 end_x 로 오르는 무효 조가선·전차선 (기점 측점이 앞당겨짐)"""
        scw, ecw, ssys, esys = h['heights']
        _, _, th1, th2, parallel_d, sta2 = initialrize_tenstion_device(
            pole.pos, pole.gauge, pole.span, scw, ssys, h['f_y'])
        self._wire(wire, imw_index, pole, (parallel_d, th2), (end_x, ecw + esys), pitch_angle, '무효조가선',
                   station=sta2)
        self._wire(wire, icw_index, pole, (parallel_d, th1), (end_x, ecw + h['f_y']), pitch_angle, '무효전차선',
                   station=sta2)

    def _falling_to_tension(self, wire, pole, pitch_angle, cut, start_x, h, **tension):
        """start_x 에서 다음 전주 장력장치(다음 전주 게이지)로 내려가는 무효 조가선·전차선"""
        scw, _, ssys, _ = h['heights']
        imw_index = self.datap.get_inactive_mw_span(pole.span - cut)
        icw_index = self.datap.get_inactive_cw_span(pole.span - cut)
        _, _, th1, th2, _, _ = initialrize_tenstion_device(pole.pos, pole.gauge, pole.span, scw, ssys, h['f_y'],
                                                          **tension)
        self._wire(wire, imw_index, pole, (start_x, scw + ssys), (pole.next_gauge, th2), pitch_angle, '무효조가선')
        self._wire(wire, icw_index, pole, (start_x, scw + h['f_y']), (pole.next_gauge, th1), pitch_angle,
                   '무효전차선')

    # ── 공통 전주 처리 ───────────────────────────────
    def wires_parallel_in(self, pole, next_pole, wire, cw_index, pitch_angle, o, insulators):
        """본선 시점 → 중간2, 무효선 F 시점 → 중간1 (+ 장간애자)"""
        scw, ecw, ssys, esys = self._heights(pole, next_pole)
        self._wire(wire, cw_index, pole, (o['start'], scw), (o['middle2'], ecw), pitch_angle, '본선전차선')
        inactive = self.datap.get_inactive_mw_span(pole.span)  # 이전 코드 그대로 전차선도 조가선 인덱스
        self._wire(wire, inactive, pole, (o['f_start'], scw + ssys), (o['middle1'], ecw + esys), pitch_angle,
                   '무효조가선')
        self._wire(wire, inactive, pole, (o['f_start'], scw + o['f_y']), (o['middle1'], ecw), pitch_angle,
                   '무효전차선')
        if insulators:
            self._insulators(wire, pole, +2, o['f_start'], scw + ssys, scw + o['f_y'])

    def wires_crossing(self, pole, next_pole, wire, cw_index, pitch_angle, o):
        """가운데: 본선 → 무효선 상승 (중간2 → F 끝), 무효선 → 본선 (중간1 → 끝)"""
        scw, ecw, ssys, esys = self._heights(pole, next_pole)
        inactive = self.datap.get_inactive_mw_span(pole.span)  # 이전 코드 그대로 전차선도 조가선 인덱스
        self._wire(wire, inactive, pole, (o['middle2'], scw), (o['f_end'], ecw + o['f_y']), pitch_angle,
                   '무효전차선')
        self._wire(wire, inactive, pole, (o['middle2'], scw + ssys), (o['f_end'], ecw + esys), pitch_angle,
                   '무효조가선')
        self._wire(wire, cw_index, pole, (o['middle1'], scw), (o['end'], ecw), pitch_angle, '무효->본선전차선')

    def wires_start(self, pole, next_pole, wire, cw_index, pitch_angle, o):
        """구간 시작 전주: 본선 → 시점, 장력장치에서 F 시점으로 오르는 무효선"""
        h = dict(heights=self._heights(pole, next_pole), f_y=o['f_y'])
        scw, ecw, _, _ = h['heights']
        self._wire(wire, cw_index, pole, (pole.brackets[0].stagger, scw), (o['start'], ecw), pitch_angle,
                   '본선전차선')
        self._rising_from_tension(wire, pole, pitch_angle, self.datap.get_inactive_mw_span(pole.span - 7),
                                  self.datap.get_inactive_cw_span(pole.span - 7), o['f_start'], h)

    def wires_end(self, pole, next_pole, wire, cw_index, pitch_angle):
        """구간 끝 전주: 본선 (브래킷 편위 → 다음 전주 편위)"""
        scw, ecw, _, _ = self._heights(pole, next_pole)
        self._wire(wire, cw_index, pole, (pole.brackets[0].stagger, scw), (next_pole.brackets[0].stagger, ecw),
                   pitch_angle, '본선전차선')
