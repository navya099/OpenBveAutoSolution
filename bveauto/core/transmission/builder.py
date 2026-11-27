from __future__ import annotations

from pathlib import Path
from bveauto.core.structure.structuredata import StructureCollection, StructureType


def create_transmission_data(structure_list: StructureCollection) -> list[str]:
    """교량 및 터널 시점/종점의 통신 설비(누설동축케이블/안테나/레일엔드 등) BVE 구문 생성."""
    result: list[str] = []

    # 1. 교량 구간 통신 구문
    for br in structure_list.find_by_type(StructureType.BRIDGE):
        result.append(f",;{br.name} (통신-교량)\n")
        result.append(
            f"{br.start_station},.FREEOBJ 0;237;,.FREEOBJ 0;237;6.58;,"
            f".FREEOBJ 0;239;,.FREEOBJ 0;240;,.RAILEND 100;,.RAILEND 101;\n"
        )
        result.append(
            f"{br.end_station},.FREEOBJ 0;237;0;0;180;,.FREEOBJ 0;237;-6.58;0;180;,"
            f".FREEOBJ 0;241;,.FREEOBJ 0;242;,.RAIL 100;0;0;76;,.RAIL 101;0;0;77;\n"
        )

    # 2. 터널 구간 통신 구문
    for tn in structure_list.find_by_type(StructureType.TUNNEL):
        result.append(f",;{tn.name} (통신-터널)\n")
        result.append(
            f"{tn.start_station},.FREEOBJ 0;238;,.FREEOBJ 0;238;6.41;,"
            f".RAILEND 100;,.RAILEND 101;\n"
        )
        result.append(
            f"{tn.end_station},.FREEOBJ 0;238;-6.58;0;180;,.FREEOBJ 0;238;0;0;180;,"
            f".RAIL 100;0;0;76;,.RAIL 101;0;0;77;\n"
        )

    return result


def save_transmission_data(lines: list[str], filename: str | Path) -> Path:
    """통신 구문 리스트를 파일로 저장."""
    out_path = Path(filename)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text("".join(lines), encoding="utf-8")
    return out_path
