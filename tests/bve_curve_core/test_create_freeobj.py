import pytest
from bveauto.core.alignment.curve.curvedata import CurveCollection, CurveData, CurveDirection
from bveauto.core.structure.structuredata import StructureCollection, StructureData, StructureType  # 실제 경로 확인
from bveauto.xref.bve_curve_core import (
    create_freeobj,
    FreeObjPoint,
    _DEFAULT_VALUES,
)


@pytest.fixture
def sample_structures() -> StructureCollection:
    """0~30m: 토공, 40~60m: 교량, 70~90m: 터널"""
    sc = StructureCollection()
    sc.add(StructureData(name="제1교량", start_station=40.0, end_station=60.0, structure_type=StructureType.BRIDGE))
    sc.add(StructureData(name="제1터널", start_station=70.0, end_station=90.0, structure_type=StructureType.TUNNEL))
    return sc


@pytest.fixture
def sample_curves() -> CurveCollection:
    """0m: 직선(TANGENT), 25m/50m/75m: 우곡선(RIGHT)"""
    cc = CurveCollection()
    cc.add(CurveData(station=0.0, radius=0, direction=CurveDirection.TANGENT, cant=0.0))
    cc.add(CurveData(station=25.0, radius=600, direction=CurveDirection.RIGHT, cant=0.1))
    cc.add(CurveData(station=50.0, radius=600, direction=CurveDirection.RIGHT, cant=0.1))
    cc.add(CurveData(station=75.0, radius=600, direction=CurveDirection.RIGHT, cant=0.1))
    return cc


@pytest.mark.parametrize(
    "line_type, expected_straight, expected_earth, expected_bridge, expected_tunnel",
    [
        ("일반철도", 499, 449, 449, 473),
        ("도시철도", 499, 228, 228, 473),
        ("고속철도", 499, 656, 656, 658),
    ],
)
def test_create_freeobj_by_line_type(
    sample_structures: StructureCollection,
    sample_curves: CurveCollection,
    line_type: str,
    expected_straight: int,
    expected_earth: int,
    expected_bridge: int,
    expected_tunnel: int,
) -> None:
    """노선별(일반/도시/고속) 및 구조물별(토공/교량/터널) FreeObj 인덱스 매핑 검증"""
    index_dict = _DEFAULT_VALUES[line_type]

    points = [
        FreeObjPoint(sta=0.0, x=0.0, y=0.0, z=0.0),    # 직선 (TANGENT)
        FreeObjPoint(sta=25.0, x=0.1, y=0.0, z=5.0),   # 토공 + 곡선 (블록 시작점)
        FreeObjPoint(sta=30.0, x=0.15, y=0.0, z=6.0),  # 토공 + 곡선 (25m 블록 내부 5m 점)
        FreeObjPoint(sta=50.0, x=0.2, y=0.0, z=10.0),  # 교량 + 곡선
        FreeObjPoint(sta=75.0, x=0.3, y=0.0, z=15.0),  # 터널 + 곡선
    ]

    result = create_freeobj(points, sample_structures, sample_curves, index_dict)

    assert result[0] == f"0.0,.freeobj 0;{expected_straight};0.0;0;0.0;0;0.0\n"
    assert result[1] == f"25.0,.freeobj 0;{expected_earth};0.1;0;0.0;0;5.0\n"
    assert result[2] == f"30.0,.freeobj 0;{expected_earth};0.15;0;0.0;0;6.0\n"
    assert result[3] == f"50.0,.freeobj 0;{expected_bridge};0.2;0;0.0;0;10.0\n"
    assert result[4] == f"75.0,.freeobj 0;{expected_tunnel};0.3;0;0.0;0;15.0\n"
