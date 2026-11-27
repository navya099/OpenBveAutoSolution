from bveauto.xref.decats.core.airjoint.airjoint_processor import AirJointProcessor
from bveauto.xref.decats.core.airjoint.aj_checker import check_isairjoint
from bveauto.xref.decats.core.alignment.rail_alignment import is_span_visible
from bveauto.xref.decats.core.alignment.define_funtion import iscurve, isslope
from bveauto.xref.decats.core.pole.normal_section_processor import NormalSectionProcessor
from bveauto.xref.decats.core.pole.poledata import PoleDATA
from bveauto.xref.decats.core.pole.tunnel_section_processor import TunnelSectionProcessor
from bveauto.xref.decats.core.structure.define_structure import isbridge_tunnel
from bveauto.xref.decats.utils.comom_util import generate_postnumbers, find_post_number
from bveauto.xref.decats.core.alignment.alignment import as_alignment

class PoleProcessor:
    def __init__(self):
        self.poles = []
        # 전주 생성에 실패해 빠진 전주 목록 ("[트랙] 측점m: 오류") → runner.pole_errors 로 화면에 알림
        self.errors = []

    def _process_single_track(self, positions, structure_list, curve_list, pitchlist,
                              dataprocessor, airjoint_list, polyline_with_sta, idxlib,
                              track_name="main", side=-1, tunnel_direction=1):
        """단일 트랙 처리 함수"""
        alignment = as_alignment(polyline_with_sta)
        post_number_lst = generate_postnumbers(positions)
        poles = []

        for i in range(len(positions) - 1):
            pos, next_pos = positions[i], positions[i + 1]
            if not is_span_visible(polyline_with_sta, pos, next_pos):
                continue  # 레일이 그려지지 않는 경간 (RailEnd 이후 등)
            try:
                currentspan = next_pos - pos
                current_structure = isbridge_tunnel(pos, structure_list)
                next_structure = isbridge_tunnel(next_pos, structure_list)
                current_curve, R, c = iscurve(pos, curve_list)
                current_slope, pitch = isslope(pos, pitchlist)
                z = alignment.elevation(pos)
                next_z = alignment.elevation(next_pos)
                current_airjoint = check_isairjoint(pos, airjoint_list)
                post_number = find_post_number(post_number_lst, pos)

                gauge = dataprocessor.get_pole_gauge(current_structure)
                next_gauge = dataprocessor.get_pole_gauge(next_structure)
                if current_structure == '터널':
                    poleside = tunnel_direction
                else:
                    poleside = side
                if next_structure == '터널':
                    nextside  = tunnel_direction
                else:
                    nextside  = side
                if nextside == -1:
                    next_gauge *= -1  # 다음 전주 방향 기준 (토공→터널 등 방향이 바뀌는 경간)
                if poleside == -1:
                    gauge *= -1
                    current_type = 'I' if i % 2 == 1 else 'O'
                    next_type = 'O' if current_type == 'I' else 'I'

                else:
                    current_type = 'O' if i % 2 == 1 else 'I'
                    next_type = 'I' if current_type == 'O' else 'O'
                if track_name == 'main':
                    if poleside == -1:
                        post_number = f'{post_number}D'
                    else:
                        post_number = f'{post_number}U'
                else:
                    if poleside == -1:
                        post_number = f'{post_number}D'
                    else:
                        post_number = f'{post_number}U'
                pos_coord_with_offset = alignment.offset_point(pos, gauge)

                pole = PoleDATA(
                    pos=pos,
                    next_pos=next_pos,
                    span=currentspan,
                    gauge=gauge,
                    next_gauge=next_gauge,
                    structure=current_structure,
                    next_structure=next_structure,
                    radius=R,
                    cant=c,
                    pitch=pitch,
                    section=current_airjoint,
                    post_number=post_number,
                    brackets=[],
                    mast=None,
                    equipments=[],
                    z=z,
                    next_z=next_z,
                    base_type=current_type,
                    next_base_type=next_type,
                    coord=pos_coord_with_offset,
                    track=track_name,  # 추가
                    side=poleside,
                    next_side=nextside # 추가
                )
                if current_airjoint is None:
                    if pole.structure == '터널':
                        TunnelSectionProcessor.process(pole, dataprocessor, idxlib)
                    else:
                        NormalSectionProcessor.process(pole, dataprocessor, idxlib)
                else:
                    AirJointProcessor.process(pole, polyline_with_sta, dataprocessor, idxlib)

                poles.append(pole)
            except Exception as e:
                message = f"[{track_name}] {positions[i]}m 전주 생성 실패 (전주가 빠짐): {e}"
                self.errors.append(message)
                print(f"[{track_name}] process_pole 실행 중 에러 발생: {e}")
        return poles

    def process_pole_multitrack(self, positions_by_track, structure_list_by_track,
                                curve_list_by_track, pitchlist_by_track,
                                dataprocessor, airjoint_list, polyline_with_sta,
                                idxlib, track_mode="single", track_direction=None, tunnel_direction=None):
        """단일/이중 트랙 모두 지원"""
        results = {}
        if track_mode == "single":
            results["main"] = self._process_single_track(
                positions_by_track["main"],
                structure_list_by_track["main"],
                curve_list_by_track["main"],
                pitchlist_by_track["main"],
                dataprocessor, airjoint_list, polyline_with_sta['main'], idxlib,
                track_name="main", side=track_direction['main'], tunnel_direction=tunnel_direction['main']
            )
        else:  # double track
            results["main"] = self._process_single_track(
                positions_by_track["main"],
                structure_list_by_track["main"],
                curve_list_by_track["main"],
                pitchlist_by_track["main"],
                dataprocessor, airjoint_list, polyline_with_sta['main'], idxlib,
                track_name="main", side=track_direction['main'], tunnel_direction=tunnel_direction['main']
            )
            results["sub"] = self._process_single_track(
                positions_by_track["sub"],
                structure_list_by_track["sub"],
                curve_list_by_track["sub"],
                pitchlist_by_track["sub"],
                dataprocessor, airjoint_list, polyline_with_sta['sub'], idxlib,
                track_name="sub", side=track_direction['sub'], tunnel_direction=tunnel_direction['sub']
            )
        return results