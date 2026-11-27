"""전주 데이터 변경 후 파생 데이터(전주 연결, 전선, 흐름방지장치) 재계산 — 단일 진입점

편집 동작(전주 이동/추가/삭제/값 수정, 에어조인트·에어섹션 추가/삭제, 엑셀 로드 등)은
runner.poledata 만 고친 뒤 rebuild(runner) 를 한 번 부른다. 화면 갱신은 호출 측에서
MODEL_CHANGED 이벤트로 알린다 (event/events.py).
"""
from bveauto.xref.decats.core.equipment.anticreepingdevice.anticreeping_device_processor import AnticreepingDeviceProcessor
from bveauto.xref.decats.core.pole.pole_updator import PoleUpdator
from bveauto.xref.decats.core.pole.poledata import new_pole_uid
from bveauto.xref.decats.core.wire import wire_overrides
from bveauto.xref.decats.core.wire.wire_processor import WireProcessor
from bveauto.xref.decats.enums.section_type import FlowStop, SectionType


def alignment_for(runner, track):
    """트랙 선형 (main: 본선, sub: 상선)"""
    if runner.alignment_by_track and runner.alignment_by_track.get(track) is not None:
        return runner.alignment_by_track[track]
    return runner.polyline_with_sta if track == 'main' else runner.offset_line_with_25


def normalize(runner):
    """구버전 데이터(.dat) 보정: 전주 uid·flowstop 필드 추가, 구간 문자열 → SectionType,
    section 에 들어 있던 흐름방지 위치 → flowstop. 여러 번 호출해도 안전."""
    from bveauto.xref.decats.enums.component_role import fill_roles, known_indices
    known = known_indices(runner.dataprocessor) if getattr(runner, 'dataprocessor', None) is not None else {}
    for poles in (runner.poledata or {}).values():
        for pole in poles:
            fill_roles(pole, known)   # 구버전 .dat: 구성품 역할 추정
            if not getattr(pole, 'uid', None):
                pole.uid = new_pole_uid()
            flowstop = FlowStop.parse(getattr(pole, 'flowstop', None))
            legacy_flowstop = FlowStop.parse(pole.section)
            if legacy_flowstop is not None:
                flowstop = flowstop or legacy_flowstop
                pole.section = None
            pole.flowstop = flowstop
            pole.section = SectionType.parse(pole.section)
            _repair_mast_offset(runner, pole)
    if not hasattr(runner, 'wire_overrides') or runner.wire_overrides is None:
        runner.wire_overrides = {}
    _normalize_alignments(runner)
    # 다음 전주 연결은 저장되지 않으므로(.dat) 불러온 뒤 다시 잇는다
    for track, poles in (runner.poledata or {}).items():
        PoleUpdator.update_all(poles, alignment_for(runner, track))


def _normalize_alignments(runner):
    """구버전 .dat: 선형이 [(측점, x, y, z)] 리스트로 저장된 경우 Alignment 로 변환 (본선·상선·트랙별 사전이 같은 객체 유지)"""
    from bveauto.xref.decats.core.alignment.alignment import Alignment
    main = getattr(runner, 'polyline_with_sta', None)
    if main is None:
        return
    converted = {}

    def convert(points):
        if points is None or isinstance(points, Alignment):
            return points
        if id(points) not in converted:
            if isinstance(main, Alignment) and points is not main:
                converted[id(points)] = main.derived(points)   # 상선: 본선 곡선·구배 공유
            else:
                converted[id(points)] = Alignment.from_points(points, getattr(runner, 'curvelist', None),
                                                              getattr(runner, 'pitchlist', None))
        return converted[id(points)]

    runner.polyline_with_sta = main = convert(main)
    runner.offset_line_with_25 = convert(getattr(runner, 'offset_line_with_25', None))
    by_track = getattr(runner, 'alignment_by_track', None)
    if by_track:
        for track, points in list(by_track.items()):
            by_track[track] = convert(points)
    if getattr(runner, 'alignment', None) is None:
        runner.alignment = main


def _repair_mast_offset(runner, pole):
    """이전 전주 조립기 버그로 기둥 offset 이 숫자 하나(게이지)로 저장된 경우 (x, y) 로 복구
    (숫자 하나면 CSV 출력에서 그 전주의 기둥·밴드·기초·브래킷 줄이 빠졌음)"""
    mast = getattr(pole, 'mast', None)
    if mast is None or not isinstance(mast.offset, (int, float)):
        return
    y = 0
    if getattr(runner, 'dataprocessor', None) is not None:
        from bveauto.xref.decats.core.mast.mast_builder import MASTBuilder
        try:
            y = MASTBuilder.get_yoffset(runner.dataprocessor, pole.structure)
        except Exception:
            y = 0
    mast.offset = (mast.offset, y)  # 자동 생성과 같은 값 형식 유지 (CSV 표기 동일)


def rebuild(runner):
    """runner.poledata 기준으로 전주 연결 → 전선 → 흐름방지장치를 처음부터 다시 계산"""
    if not runner.poledata:
        return
    normalize(runner)
    # 1) 선형 값(좌표·계획고·곡선·구배)을 측점에서 다시 계산하고, 인접 전주를 이음 (next_* 는 이은 전주에서 계산).
    #    레일 단절 구간은 잇지 않음
    from bveauto.xref.decats.core.pole.pole_geometry import place_track
    for track, poles in runner.poledata.items():
        place_track(runner, track, alignment_for(runner, track))
        PoleUpdator.update_all(poles, alignment_for(runner, track))

    # 2) 전선 재생성
    runner.wire_processor = WireProcessor(runner.dataprocessor, runner.alignment_by_track,
                                          runner.poledata, runner.curvelist)
    runner.wire_data = runner.wire_processor.process_to_wire()
    runner.wire_errors = list(runner.wire_processor.errors)

    # 2-1) 전선 상세 편집 내용(경간 단위) 다시 적용. 흐름방지선이 편집된 전차선 기준으로 만들어지도록 흐름방지보다 먼저
    applied, pruned = wire_overrides.apply(runner, alignment_for)
    if applied or pruned:
        runner.log(f"전선 편집 내용 적용: 전선 {applied}개" + (f", 삭제된 전주 경간 {pruned}개 정리" if pruned else ""))

    # 3) 흐름방지장치: 사용자 추가/삭제 요청은 유지하고, 현재 배치에서 다시 계산
    anticreeping = getattr(runner, 'anticreeping_pr', None)
    if anticreeping is None:
        anticreeping = AnticreepingDeviceProcessor(runner.poledata, runner.wire_data,
                                                   runner.airjoint_list, runner.wire_processor)
        runner.anticreeping_pr = anticreeping
    anticreeping.set_data(runner.poledata, runner.wire_data, runner.wire_processor)
    anticreeping.idxlib = getattr(runner, 'idxlib', None)
    anticreeping.process()
