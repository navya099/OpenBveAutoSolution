"""전주의 선형 값(좌표·계획고·곡선 반경·캔트·구배) — 측점·건식게이지와 선형으로 계산하는 단일 함수

PoleDATA.coord / z / radius / cant / pitch 는 측점에서 언제든 다시 계산할 수 있는 값이다.
전주를 만들 때·옮길 때·게이지를 바꿀 때·재계산(rebuild) 때 모두 place_on_alignment 하나로 계산해
값이 서로 어긋나지 않게 한다 (예전에는 곳마다 따로 계산했고, 이동은 상선도 본선 곡선표를 썼음).
구조물(structure)은 구성품(기둥·브래킷 종류)을 정하는 입력이라 여기서 바꾸지 않는다 (이동 때 pole_edit 가 처리).
"""
from bveauto.xref.decats.core.alignment.alignment import as_alignment
from bveauto.xref.decats.core.alignment.define_funtion import iscurve, isslope


def track_lists(runner, track):
    """(곡선표, 구배표) — 트랙별 표가 있으면 그것, 없으면 본선 표 (구버전 runner)"""
    curves = (getattr(runner, 'curve_list_by_track', None) or {}).get(track)
    pitches = (getattr(runner, 'pitchlist_by_track', None) or {}).get(track)
    return (runner.curvelist if curves is None else curves), (runner.pitchlist if pitches is None else pitches)


def place_on_alignment(pole, alignment, curve_list, pitch_list):
    """측점·건식게이지로 좌표·계획고·곡선 반경·캔트·구배 계산"""
    al = as_alignment(alignment)
    pole.z = al.elevation(pole.pos)
    _, pole.radius, pole.cant = iscurve(pole.pos, curve_list)
    _, pole.pitch = isslope(pole.pos, pitch_list)
    pole.coord = al.offset_point(pole.pos, pole.gauge)


def place_track(runner, track, alignment):
    """트랙 전주 전체의 선형 값 다시 계산"""
    curves, pitches = track_lists(runner, track)
    al = as_alignment(alignment)
    for pole in runner.poledata.get(track, []):
        place_on_alignment(pole, al, curves, pitches)
