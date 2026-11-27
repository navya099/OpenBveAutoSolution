from bveauto.xref.decats.core.base_runner import BaseRunner
from bveauto.xref.decats.core.equipment.anticreepingdevice.anticreeping_device_processor import AnticreepingDeviceProcessor
from bveauto.xref.decats.core.pole.pole_processor import PoleProcessor
from bveauto.xref.decats.core.wire.wire_processor import WireProcessor
from bveauto.xref.decats.enums.section_type import AIRJOINT_DOUBLE_POLE_SEQUENCE
from bveauto.xref.decats.utils.comom_util import distribute_pole_spacing_flexible, define_airjoint_section

class AutoRunner(BaseRunner):
    def __init__(self):
        super().__init__()

    def run(self):
        """전체 작업을 관리하는 메인 함수"""
        self.base_info_load()
        self.apply_dataset_options()
        self.pole_positions = distribute_pole_spacing_flexible(self.start_station, self.end_station, curvelist=self.curvelist,structure_list=self.structure_list, design_speed=self.designspeed)
        self.create_dictionary_by_track()

        tags = AIRJOINT_DOUBLE_POLE_SEQUENCE if getattr(self, 'airjoint_type', 'single') == 'double_pole' else None
        self.airjoint_list = define_airjoint_section(self.pole_positions, airjoint_span=1600, tags=tags)
        self.pole_processor = PoleProcessor()

        self.poledata = self.pole_processor.process_pole_multitrack(
            self.positions_by_track, self.structure_list_by_track, self.curve_list_by_track, self.pitchlist_by_track,
            self.dataprocessor, self.airjoint_list, self.alignment_by_track, self.idxlib,
            self.track_mode, self.track_direction,tunnel_direction=self.tunnel_direction
        )

        self.wire_processor = WireProcessor(self.dataprocessor, self.alignment_by_track, self.poledata, self.curvelist)
        self.wire_data = self.wire_processor.process_to_wire()
        self.pole_errors = list(self.pole_processor.errors)
        self.wire_errors = list(self.wire_processor.errors)

        #추가설비(흐름방지장치)
        self.anticreeping_pr = AnticreepingDeviceProcessor(self.poledata, self.wire_data, self.airjoint_list, self.wire_processor)
        self.anticreeping_pr.idxlib = self.idxlib   # 흐름방지장치·봉강지선 오브젝트 이름
        self.anticreeping_pr.process()

        # 최종 출력
        main_count = len(self.poledata.get("main", []))
        sub_count = len(self.poledata.get("sub", []))
        if self.track_mode == "single":
            self.log(f"전주 개수: 본선={main_count}개")
        else:
            self.log(f"전주 개수: 본선={main_count}개, 상선={sub_count}개")
        self.log(f"마지막 전주 위치: {self.positions_by_track['main'][-1]}m (종점: {int(self.end_station)}m)")
        errors = self.processing_errors()
        if errors:
            self.log(f'⚠️ 처리 오류 {len(errors)}건 — 아래 전주·전선이 출력에서 빠졌습니다:')
            for message in errors:
                self.log(f'  {message}')
        self.log('모든 작업 완료')