from pathlib import Path
import pytest
from bveauto.config import PathConfig
from bveauto.context import BuildContext
from bveauto.core.alignment.curve.curvedata import CurveData, CurveDirection
from bveauto.steps.curve import CurveStep


def test_curve_step_execute_with_real_context(tmp_path: Path) -> None:
    """실제 BuildContext를 사용한 CurveStep 실행 및 파일 생성 검증"""
    # 1. 실제 BuildContext 생성 및 출력 경로(route)만 임시 폴더(tmp_path)로 설정
    ctx = BuildContext(
        designspeed=150,
        paths=PathConfig(base_source=tmp_path, route=tmp_path, obj=tmp_path),
    )
    ctx.curve_info.add(CurveData(station=0.0, radius=0, direction=CurveDirection.TANGENT, cant=0.0))
    ctx.curve_info.add(CurveData(station=25.0, radius=600, direction=CurveDirection.RIGHT, cant=0.1))

    logs: list[str] = []
    step = CurveStep()

    # 2. 실행
    step.execute(ctx, logs.append)

    # 3. 검증
    freeobj_files = list(tmp_path.glob("freeobj_*.txt"))
    railtype_files = list(tmp_path.glob("railtype_*.txt"))

    assert len(logs) == 4
    assert "----- #2. 곡선레일 시작 -----" in logs[0]
    assert "FreeObj 저장:" in logs[1]
    assert "RailType 저장:" in logs[2]
    assert "#2. 곡선레일 완료" in logs[3]

