import pytest
from bveauto.core.alignment.curve.curvedata import CurveCollection, CurveData, CurveDirection
from bveauto.xref.bve_curve_core import cal_mainlogic, FreeObjPoint, INCREMENT


@pytest.fixture
def straight_curve_collection() -> CurveCollection:
    """직선(radius=0) 2개 블록(0m, 25m) 데이터"""
    cl = CurveCollection()
    cl.add(CurveData(station=0, radius=0, direction=CurveDirection.TANGENT, cant=0.0))
    cl.add(CurveData(station=25, radius=0, direction=CurveDirection.TANGENT, cant=0.0))
    return cl


@pytest.fixture
def curved_collection() -> CurveCollection:
    """직선 -> 우곡선 -> 직선 전환이 포함된 데이터"""
    cl = CurveCollection()
    cl.add(CurveData(station=0, radius=0, direction=CurveDirection.TANGENT, cant=0.0))
    cl.add(CurveData(station=25, radius=600, direction=CurveDirection.RIGHT, cant=0.1))
    cl.add(CurveData(station=50, radius=0, direction=CurveDirection.TANGENT, cant=0.0))
    return cl


def test_cal_mainlogic_empty() -> None:
    """빈 컬렉션 입력 시 빈 리스트 반환 검증"""
    cl = CurveCollection()
    result = cal_mainlogic(cl)
    assert result == []


def test_cal_mainlogic_straight(straight_curve_collection: CurveCollection) -> None:
    """직선 구간: 블록당 INCREMENT개씩 총 2*INCREMENT개 생성 및 x, y가 0.0인지 검증"""
    result = cal_mainlogic(straight_curve_collection)

    assert len(result) == 2 * INCREMENT
    assert all(isinstance(pt, FreeObjPoint) for pt in result)

    # 직선 구간이므로 x, y 오프셋은 모두 0.0이어야 함
    for pt in result:
        assert pt.x == 0.0
        assert pt.y == 0.0

    # 측점(sta) 간격이 INCREMENT(5m)씩 증가하는지 검증
    expected_stas = [i * INCREMENT for i in range(2 * INCREMENT)]
    assert [pt.sta for pt in result] == expected_stas


def test_cal_mainlogic_with_curve(curved_collection: CurveCollection) -> None:
    """곡선 구간: radius != 0일 때 x, y 좌표가 계산되어 0이 아닌 값을 갖는지 검증"""
    result = cal_mainlogic(curved_collection)

    assert len(result) == 3 * INCREMENT

    # 첫 번째 블록(0~20m, 직선)은 x == 0.0
    straight_part = result[:INCREMENT]
    assert all(pt.x == 0.0 and pt.y == 0.0 for pt in straight_part)

    # 두 번째 블록(25~45m, 반경 600m 곡선)은 x 또는 y가 0.0이 아니어야 함
    curve_part = result[INCREMENT : 2 * INCREMENT]
    assert any(pt.x != 0.0 or pt.y != 0.0 for pt in curve_part)
