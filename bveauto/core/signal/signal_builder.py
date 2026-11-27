from pathlib import Path
from typing import Sequence

from bveauto.core.structure.structuredata import StructureCollection, StructureType
import random

def _get_structure_label(structure_list: StructureCollection, pos: float) -> str:
    """측점(pos)에 해당하는 구조물 명칭('교량' | '터널' | '토공') 반환."""
    struct = structure_list.find_by_station(pos)
    if struct is not None:
        if struct.structure_type == StructureType.BRIDGE:
            return "교량"
        if struct.structure_type == StructureType.TUNNEL:
            return "터널"
    return "토공"


def save_signal_data(
    pole_positions: Sequence[float],
    structure_list: StructureCollection,
    filename: str | Path = "신호.txt",
) -> Path:
    """신호기(하선/상선) 및 부속설비(발리스, LEU, 자동폐색유니트) BVE 구문 파일 저장."""
    pole_data = {
        "교량": {"signal_type": "5현시_교량용", "index": 44, "x-offset": -2.675},
        "터널": {"signal_type": "5현시_터널용", "index": 62, "x-offset": -2.54},
        "토공": {"signal_type": "5현시_토공용", "index": 44, "x-offset": -2.675},
    }
    device_data = {
        "LEU": (46,),
        "자동폐색유니트": (47,),
        "발리스": (45,),
    }

    out_path = Path(filename)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    with open(out_path, "w", encoding="utf-8") as f:
        for i, pos in enumerate(pole_positions):
            if i == 0:
                continue

            structure_type = _get_structure_label(structure_list, pos)
            signal_data = pole_data[structure_type]
            signal_type = signal_data["signal_type"]
            signal_index = signal_data["index"]
            x_offset = signal_data["x-offset"]

            f.write("\n,;폐색신호기\n")
            f.write(",;하선\n")
            f.write(f"{pos},.freeobj 0;{signal_index};{x_offset};;,;{signal_type}\n")

            f.write(",;상선\n")
            if structure_type == "터널":
                f.write(f"{pos},.freeobj 0;{signal_index};3;0;180;,;{signal_type}\n")
            else:
                f.write(f"{pos + 10},.freeobj 0;{signal_index};{x_offset};0;180;,;{signal_type}\n")

            if structure_type != "터널":
                f.write(",;발리스\n")
                f.write(f"{pos - 20},.freeobj 0;{device_data['발리스'][0]};0;;,;\n")
                f.write(f"{pos - 17},.freeobj 0;{device_data['발리스'][0]};0;;,;\n")

                f.write(",;LEU\n")
                f.write(f"{pos - 14},.freeobj 0;{device_data['LEU'][0]};0;0.3;,;\n")

                f.write(",;자동폐색유니트\n")
                f.write(f"{pos - 13},.freeobj 0;{device_data['자동폐색유니트'][0]};0;;,;\n")

    return out_path

def build(
    start_km: float,
    end_km: float,
    spans: Sequence[int] = (45, 50, 55, 60),
) -> tuple[list[int], list[int]]:
    """주어진 간격 후보(spans) 범위에서 간격을 균형 있게 배분하여 전체 구간을 채움."""
    start_m = int(start_km * 1000)
    end_m = int(end_km * 1000)

    if end_m <= start_m or not spans:
        return [], [start_m]

    positions: list[int] = [start_m]
    selected_spans: list[int] = []
    current_pos = start_m
    min_span = min(spans)

    while current_pos + min_span <= end_m:
        possible_spans = list(spans)

        random.shuffle(possible_spans)

        for span in possible_spans:
            if current_pos + span > end_m:
                continue

            current_pos += span
            positions.append(current_pos)
            selected_spans.append(span)
            break

    return selected_spans, positions