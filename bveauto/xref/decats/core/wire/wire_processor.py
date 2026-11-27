from bveauto.xref.decats.core.wire.af_wire.af_processor import AFWireProcessor
from bveauto.xref.decats.core.wire.common_processor import CommonWireProcessor
from bveauto.xref.decats.core.wire.extra_wire.extra_wire_processor import ExtraWireProcessor
from bveauto.xref.decats.core.wire.fpw_wire.fpw_processor import FPWWireProcessor
from bveauto.xref.decats.core.wire.section_handler import WireSectionHandler
from bveauto.xref.decats.core.wire.wire_data import WireData
from bveauto.xref.decats.utils.math_util import change_permile_to_degree


class WireProcessor:
    def __init__(self, dataprocessor, polyline_by_track, poledata_by_track, curve_list):
        self.pro = dataprocessor
        self.polyline_by_track = polyline_by_track   # {"main": [...], "sub": [...]}
        self.poledata_by_track = poledata_by_track   # {"main": [...], "sub": [...]}
        self.com = CommonWireProcessor()
        self.afp = AFWireProcessor(self.pro)
        self.fpwp = FPWWireProcessor(self.pro)
        self.exp = ExtraWireProcessor(self.pro)
        self.curve_list = curve_list
        # 전선 생성에 실패해 빠진 경간 목록 ("[트랙] 측점m: 오류") → runner.wire_errors 로 화면에 알림
        self.errors = []

    def process_to_wire(self):
        results = {}
        self.errors = []
        for track_name, poles in self.poledata_by_track.items():
            wires = []
            wirehandler = WireSectionHandler(self.com, self.pro, self.polyline_by_track[track_name], self.curve_list)
            for i, pole in enumerate(poles[:-1]):
                try:
                    # 마지막 pole은 next_pole 없음 → 예외 처리
                    next_pole = poles[i + 1]
                    if next_pole.pos != pole.next_pos:
                        # 다음 전주가 이 전주의 경간 끝이 아님 → 레일 단절 구간이므로 전선 없음
                        continue
                    wire = WireData(pole.pos, pole.span, wires=[], track_name=track_name)
                    pitch_angle = change_permile_to_degree(pole.pitch)
                    # 본선/에어조인트 구간 전차선 처리
                    wirehandler.run(pole, next_pole, wire, pitch_angle)

                    # AF
                    wire.add_wire(self.afp.process(pole, self.polyline_by_track[track_name], pitch_angle))
                    # FPW
                    wire.add_wire(self.fpwp.process(pole, self.polyline_by_track[track_name], pitch_angle))
                    #EXTRA
                    isext = self.pro.get_extra_wire_dictionary()
                    if isext is not None:
                        wire.add_wire(self.exp.process(pole, self.polyline_by_track[track_name], pitch_angle))
                    wires.append(wire)
                except Exception as e:
                    self.errors.append(f"[{track_name}] {pole.pos}m 경간 전선 생성 실패 (전선이 빠짐): {e}")
                    print(f"[{track_name}] at {pole.pos} process_to_wire 실행 중 에러 발생: {e}")
                    continue
            results[track_name] = wires
        return results
