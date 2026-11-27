from bveauto.xref.decats.core.structure.define_structure import apply_brokenchain_to_structure
import os

from bveauto.xref.decats.core.alignment.alignment import BLOCK, Alignment
from bveauto.xref.decats.file_io.filemanager import load_structure_data
from bveauto.xref.decats.core.alignment.rail_alignment import parse_rail_info, build_rail_alignment, visible_ranges

class BaseRunner:
    def __init__(self):
        self.polyline = None
        self.coord_file_path = None
        self.pitch_file_path = None
        self.curve_file_path = None
        self.structure_file_path = None
        self.alignment_by_track = None
        self.pitchlist_by_track = None
        self.curve_list_by_track = None
        self.structure_list_by_track = None
        self.positions_by_track = None
        self.anticreeping_pr = None
        self.polesaver_sub = None
        self.polesaver_main = None
        self.wire_path_sub = None
        self.pole_path_sub = None
        self.pole_path_main = None
        self.wire_path_main = None
        self.offset_line_with_25 = None
        self.pole_positions = None
        self.idxlib = None
        self.airjoint_list = None
        self.pitchlist = None
        self.curvelist = None
        self.structure_list = None
        self.polyline_with_sta = None
        self.pole_processor = None
        self.wire_processor = None
        self.polesaver = None
        self.wire_path = None
        self.pole_path = None
        self.dataprocessor = None
        self.designspeed = 0
        self.iscustommode = False
        self.custom_dataset_json = None   # 커스텀 모드 데이터셋 경로 (표준은 config/ 고정)
        self.custom_spandata = None
        self.is_create_dxf = False
        self.track_mode = None
        self.track_direction: dict[str, int | None] = {'main': None, 'sub': None}
        self.track_distance = 0.0
        self.log_widget = None
        self.poledata = None
        self.wire_data = None
        self._cached_df = None
        self.start_station = 0.0
        self.end_station = 0.0
        self.brokenchain = 0.0
        self.tunnel_direction: dict[str, int | None] = {'main': None, 'sub': None}
        # 상선 선형을 BVEParser rail_info.txt 의 실제 레일 좌표로 만들 때 사용 (None 이면 일정 간격 오프셋)
        self.rail_info_file_path = None
        # 선형: BVEParser bve_alignment.txt 경로 (없으면 coord/curve/pitch 3개 파일 사용)
        self.alignment_file_path = None
        # 자동 배치 에어조인트 방식: 'single' = 단주(전주 1개에 브래킷 2개), 'double_pole' = 복주(2·3·4호주 전주 2개)
        self.airjoint_type = 'single'
        # 복주 쌍 전주 간격(m). None 이면 데이터셋 airjoint.double_pole.spacing
        self.double_pole_spacing = None
        # 복주 급전선설비: 'both' 두 전주 | 'front' 앞 전주만 | None 데이터셋 airjoint.double_pole.feeder
        self.double_pole_feeder = None
        # 처리 중 빠진 전주·전선 (오류 메시지). 화면에 경고로 알림 — 출력만 하고 넘어가지 않도록
        self.pole_errors = []    # 자동 배치 전주 생성 실패 (실행 때)
        self.wire_errors = []    # 전선 생성 실패 (실행·재계산 때마다 갱신)
        self.alignment = None
        self.sub_rail_key: int | None = None
        # 전선 상세 편집 내용 (경간 단위 지지점 수정·전선 추가/삭제): core/wire/wire_overrides.py 참고
        self.wire_overrides = {}

    def processing_errors(self):
        """빠진 전주·전선 오류 메시지 목록 (구버전 .dat 에는 속성이 없을 수 있음)"""
        return list(getattr(self, 'pole_errors', None) or []) + list(getattr(self, 'wire_errors', None) or [])

    def apply_dataset_options(self):
        """실행 설정 중 데이터셋 값을 덮어쓰는 항목을 데이터셋 겟터에 반영 (복주 쌍 전주 간격·급전선설비)"""
        if getattr(self, 'dataprocessor', None) is not None:
            self.dataprocessor.double_pole_spacing_override = getattr(self, 'double_pole_spacing', None)
            self.dataprocessor.double_pole_feeder_override = getattr(self, 'double_pole_feeder', None)

    def run(self):
        raise NotImplementedError("자식 클래스에서 구현하세요")

    def log(self, msg):
        if self.log_widget:
            self.log_widget.insert("end", msg + "\n")
            self.log_widget.see("end")
        else:
            print(msg)

    def safe_load(self, loader_func, file_path, success_msg, empty_msg, fail_msg):
        try:
            data = loader_func(file_path)
            if data:
                self.log(success_msg)
            else:
                self.log(empty_msg)
            return data
        except Exception as e:
            self.log(f"{fail_msg} {e}")
            raise

    def base_info_load(self):
        # 파일 읽기 및 데이터 처리
        # 구조물 정보 로드
        self.structure_list = self.safe_load(
            load_structure_data,
            self.structure_file_path,
            "구조물 정보가 성공적으로 로드되었습니다.",
            "구조물 정보가 비어 있습니다.",
            "구조물 정보 로드에 실패했습니다."
        )
        if self.structure_list:
            self.structure_list = apply_brokenchain_to_structure(
                self.structure_list, self.brokenchain
            )

        # 선형 로드: bve_alignment.txt(BVEParser) 하나로 좌표·곡선·구배. 없으면 기존 3개 파일
        self.alignment = self._load_alignment()
        self.curvelist = self.alignment.curvelist
        self.pitchlist = self.alignment.pitchlist
        self.polyline = self.alignment.coordinates

    def _load_alignment(self):
        alignment_path = getattr(self, 'alignment_file_path', None)
        try:
            if alignment_path:
                alignment = Alignment.from_bve_alignment(alignment_path)
                source = os.path.basename(alignment_path)
            else:
                missing = [p for p in (self.coord_file_path, self.curve_file_path, self.pitch_file_path)
                           if not p or not os.path.isfile(p)]
                if missing:
                    raise FileNotFoundError(f"선형 파일이 없습니다: {missing} (bve_alignment.txt 또는 "
                                            "bve_coordinates/curve_info/pitch_info.txt 필요)")
                alignment = Alignment.from_legacy_files(self.coord_file_path, self.curve_file_path,
                                                        self.pitch_file_path)
                source = '좌표·곡선·구배 3개 파일'
        except Exception as e:
            self.log(f"선형 정보 로드에 실패했습니다. {e}")
            raise
        if alignment.block != BLOCK:
            raise ValueError(f"블록 간격이 {alignment.block}m 입니다. 현재 {BLOCK}m 블록만 지원합니다.")
        self.log(f"선형 정보가 로드되었습니다 ({source}): {alignment.start:g} ~ {alignment.end:g}m, "
                 f"블록 {len(alignment)}개, 곡선 블록 {sum(1 for r, _ in alignment.curves.values() if r)}개")
        if not (alignment.start <= float(self.start_station) <= alignment.end):
            self.log(f"⚠️ 시점 {self.start_station}m 가 선형 범위({alignment.start:g}~{alignment.end:g}m) 밖입니다.")
        return alignment

    def _build_sub_alignment(self, fallback):
        """rail_info 가 지정되면 실제 레일 좌표로, 아니면 일정 간격 오프셋으로 상선 선형 생성"""
        # 구버전 pickle 로 불러온 runner 에는 속성이 없을 수 있음
        rail_key = getattr(self, 'sub_rail_key', None)
        path = getattr(self, 'rail_info_file_path', None)
        if rail_key is None:
            self.log(f"상선 선형: 일정 간격 오프셋 ({abs(self.track_distance)}m)")
            return fallback
        if not path:
            raise ValueError("상선 레일번호가 지정됐지만 rail_info 파일 경로가 없습니다.")
        rail_points, has_visibility = parse_rail_info(path, rail_key)
        alignment = build_rail_alignment(self.polyline_with_sta, rail_points, fallback,
                                         rail_key=rail_key, has_visibility=has_visibility)
        if not has_visibility:
            self.log(f"⚠️ rail_info 에 visible 열이 없습니다(구버전 파서). 레일 {rail_key} 를 전 구간 표시로 간주합니다.")
        else:
            ranges = visible_ranges(alignment)
            self.log(f"상선 선형: rail_info 레일 {rail_key}, 표시 구간 {ranges}")
        return alignment

    def create_dictionary_by_track(self):
        # 본선 선형 = Alignment ([(측점, x, y, z)] 리스트 + 측점별 곡선·구배)
        self.polyline_with_sta = self.alignment

        if self.track_mode == 'double':
            # BVE 레일 오프셋과 같은 방식: 각 블록 진행방향의 수직으로 오프셋 (측점·고도 유지)
            # 본선 전주가 좌측(-1)이면 상선은 우측(+x)
            side = 1 if self.track_direction['main'] == -1 else -1
            fallback = self.polyline_with_sta.offset(side * abs(self.track_distance))
            self.offset_line_with_25 = self._build_sub_alignment(fallback)

        ######트랙별 처리###### todo
        # 현재는 두 트랙이 동일하다고 가정(즉 pos와 모든 구조물을 공유함)
        # 선형만 별도로 존재(offset 적용)
        # 선형 오프셋

        self.positions_by_track = {
            "main": self.pole_positions,
            "sub": self.pole_positions  # double일 때만
        }
        self.structure_list_by_track = {
            "main": self.structure_list,
            "sub": self.structure_list
        }
        self.curve_list_by_track = {
            "main": self.curvelist,
            "sub": self.curvelist
        }
        self.pitchlist_by_track = {
            "main": self.pitchlist,
            "sub": self.pitchlist
        }
        self.alignment_by_track = {
            "main": self.polyline_with_sta,
            "sub": self.offset_line_with_25
        }