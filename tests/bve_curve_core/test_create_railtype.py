import pytest
from bveauto.core.alignment.curve.curvedata import CurveCollection, CurveData, CurveDirection
from bveauto.core.structure.structuredata import StructureCollection, StructureData, StructureType
from bveauto.xref.bve_curve_core import create_railtype, _DEFAULT_VALUES


@pytest.fixture
def sample_structures() -> StructureCollection:
    """0~30m: 토공, 40~60m: 교량, 70~110m: 터널"""
    sc = StructureCollection()
    sc.add(StructureData(name="제1교량", start_station=40.0, end_station=60.0, structure_type=StructureType.BRIDGE))
    sc.add(StructureData(name="제1터널", start_station=70.0, end_station=110.0, structure_type=StructureType.TUNNEL))
    return sc


@pytest.fixture
def sample_curves() -> CurveCollection:
    """직선(토공/교량/터널) + 곡선(터널 내부 포함) 조합 데이터"""
    cc = CurveCollection()
    cc.add(CurveData(station=0.0, radius=0, direction=CurveDirection.TANGENT, cant=0.0))     # 직선 + 토공
    cc.add(CurveData(station=50.0, radius=0, direction=CurveDirection.TANGENT, cant=0.0))    # 직선 + 교량
    cc.add(CurveData(station=75.0, radius=0, direction=CurveDirection.TANGENT, cant=0.0))    # 직선 + 터널
    cc.add(CurveData(station=100.0, radius=600, direction=CurveDirection.RIGHT, cant=0.1))   # 곡선 + 터널 (곡선 우선)
    return cc


@pytest.mark.parametrize(
    "line_type, expected_earth, expected_bridge, expected_tunnel, expected_curve",
    [
        ("일반철도", 9, 9, 25, 4),
        ("도시철도", 9, 9, 25, 4),
        ("고속철도", 7, 7, 114, 4),
    ],
)
def test_create_railtype_by_line_type(
    sample_structures: StructureCollection,
    sample_curves: CurveCollection,
    line_type: str,
    expected_earth: int,
    expected_bridge: int,
    expected_tunnel: int,
    expected_curve: int,
) -> None:
    """노선별(일반/도시/고속) 직선(토공/교량/터널) 및 곡선 RailType 구문 생성 검증"""
    index_dict = _DEFAULT_VALUES[line_type]

    result = create_railtype(sample_curves, sample_structures, index_dict)

    assert len(result) == 4
    assert result[0] == f"0.0,.railtype 0;{expected_earth};\n"
    assert result[1] == f"50.0,.railtype 0;{expected_bridge};\n"
    assert result[2] == f"75.0,.railtype 0;{expected_tunnel};\n"
    assert result[3] == f"100.0,.railtype 0;{expected_curve};\n"


def test_create_railtype_empty(sample_structures: StructureCollection) -> None:
    """빈 CurveCollection 입력 시 빈 리스트 반환 검증"""
    empty_curves = CurveCollection()
    result = create_railtype(empty_curves, sample_structures, _DEFAULT_VALUES["일반철도"])
    assert result == []
