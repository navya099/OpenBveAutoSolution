import pytest
from bveauto.core.alignment.curve.curvedata import CurveCollection, CurveData, CurveDirection
from bveauto.xref.bve_curve_core import cal_cant_5m, INCREMENT, M_TO_MM


@pytest.fixture
def right_curve_collection() -> CurveCollection:
    """우곡선(양수 반경): 직선 -> 완화곡선 진입 -> 원곡선 -> 완화곡선 진출 -> 직선"""
    cl = CurveCollection()
    cl.add(CurveData(station=0.0, radius=0, direction=CurveDirection.TANGENT, cant=0.0))
    # 25m -> 50m: 반경 1000 -> 600 (진입: SP-PC), 캔트 0.0 -> 0.10 증가
    cl.add(CurveData(station=25.0, radius=1000, direction=CurveDirection.RIGHT, cant=0.0))
    cl.add(CurveData(station=50.0, radius=600, direction=CurveDirection.RIGHT, cant=0.10))
    # 75m -> 100m: 반경 1000 -> 0 (진출: CP-PS), 캔트 0.10 -> 0.0 감소
    cl.add(CurveData(station=75.0, radius=1000, direction=CurveDirection.RIGHT, cant=0.10))
    cl.add(CurveData(station=100.0, radius=0, direction=CurveDirection.TANGENT, cant=0.0))
    return cl


@pytest.fixture
def left_curve_collection() -> CurveCollection:
    """좌곡선(음수 반경): 직선 -> 완화곡선 진입 -> 원곡선 -> 완화곡선 진출 -> 직선"""
    cl = CurveCollection()
    cl.add(CurveData(station=0.0, radius=0, direction=CurveDirection.TANGENT, cant=0.0))
    # 25m -> 50m: 반경 -1000 -> -600 (진입: SP-PC), 캔트 0.0 -> 0.10 증가
    cl.add(CurveData(station=25.0, radius=-1000, direction=CurveDirection.LEFT, cant=0.0))
    cl.add(CurveData(station=50.0, radius=-600, direction=CurveDirection.LEFT, cant=0.10))
    # 75m -> 100m: 반경 -1000 -> 0 (진출: CP-PS), 캔트 0.10 -> 0.0 감소
    cl.add(CurveData(station=75.0, radius=-1000, direction=CurveDirection.LEFT, cant=0.10))
    cl.add(CurveData(station=100.0, radius=0, direction=CurveDirection.TANGENT, cant=0.0))
    return cl


def test_cal_cant_5m_right_curve(right_curve_collection: CurveCollection) -> None:
    """우곡선(+1): 진입 시 양수(+), 원곡선 0.0, 진출 시 음수(-) 반환 검증"""
    expected_abs = (0.10 / INCREMENT) * M_TO_MM

    # 진입(SP-PC): +20.0
    assert cal_cant_5m(right_curve_collection, sta=25.0, direction_sign=1) == pytest.approx(expected_abs)
    # 원곡선(캔트 동일): 0.0
    assert cal_cant_5m(right_curve_collection, sta=50.0, direction_sign=1) == 0.0
    # 진출(CP-PS): -20.0
    assert cal_cant_5m(right_curve_collection, sta=75.0, direction_sign=1) == pytest.approx(-expected_abs)


def test_cal_cant_5m_left_curve(left_curve_collection: CurveCollection) -> None:
    """좌곡선(-1): 진입 시 음수(-), 원곡선 0.0, 진출 시 양수(+) 반환 검증"""
    expected_abs = (0.10 / INCREMENT) * M_TO_MM

    # 진입(SP-PC): -20.0
    assert cal_cant_5m(left_curve_collection, sta=25.0, direction_sign=-1) == pytest.approx(-expected_abs)
    # 원곡선(캔트 동일): 0.0
    assert cal_cant_5m(left_curve_collection, sta=50.0, direction_sign=-1) == 0.0
    # 진출(CP-PS): +20.0
    assert cal_cant_5m(left_curve_collection, sta=75.0, direction_sign=-1) == pytest.approx(expected_abs)


def test_cal_cant_5m_boundary(right_curve_collection: CurveCollection) -> None:
    """마지막 측점 및 존재하지 않는 측점 조회 시 0.0 반환"""
    assert cal_cant_5m(right_curve_collection, sta=100.0, direction_sign=1) == 0.0
    assert cal_cant_5m(right_curve_collection, sta=12.5, direction_sign=1) == 0.0
