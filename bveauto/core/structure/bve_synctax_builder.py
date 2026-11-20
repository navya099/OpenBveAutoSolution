from bveauto.core.structure.helper import get_obj_index, get_earthwork_embank_index
from bveauto.core.structure.structuredata import StructureCollection, StructureType
from bveauto.utils import get_block_index


def create_wall_syntax(idx, mode="start"):
    """
    벽체(wall) 구문 생성 함수
    :param idx: 벽체 인덱스 (교량/터널 구분)
    :param mode: "start" 또는 "end"
    :return: 문자열 구문
    """
    if mode == "start":
        return f".wall 0;-1;{idx};\n"
    elif mode == "end":
        return f".wallend 0;\n"
    return ""

def create_dike_syntax(e_idx, line_count, designspeed=None, mode="start"):
    if mode == "start":
        if designspeed == 150:
            return f".dike 0;-1;{e_idx};,.dike 1;-1;{e_idx}\n"
        else:
            return f".dike 0;-1;{e_idx};\n"
    elif mode == "end":
        if line_count == 1:
            return f".dikeend 0;\n"
        else:
            return ".dikeend 0;,.dikeend 1;\n"
    return ""

def create_network_data(
    structure_list: StructureCollection,
    designspeed: float,
    line_count: int,
) -> list[str]:
    result: list[str] = []
    e_idx, br_idx, tn_idx = get_obj_index(designspeed, line_count)
    idx_E, idx_tns, idx_tne = get_earthwork_embank_index(designspeed, line_count)

    # 시점부 토공
    result.append(create_dike_syntax(e_idx, line_count, designspeed, mode="start"))

    # 교량 처리
    for structure in structure_list.find_by_type(StructureType.BRIDGE):
        name = structure.name
        start = get_block_index(structure.start_station)
        end = get_block_index(structure.end_station)

        br_start_data = (
            f",;{name}\n"
            f"{start}\n"
            f"{create_wall_syntax(br_idx, mode='start')}"
            f"{create_dike_syntax(e_idx, line_count, designspeed, mode='end')}\n"
            f'.freeobj 0;{idx_E};0;0;'
        )

        br_end_data = (
            f"{end}\n"
            f"{create_wall_syntax(br_idx, mode='end')}"
            f"{create_dike_syntax(e_idx, line_count, designspeed, mode='start')}"
            f'.freeobj 0;{idx_E};0;0;180;\n'
        )

        result.append(br_start_data)
        result.append(br_end_data)

    # 터널 처리
    for structure in structure_list.find_by_type(StructureType.TUNNEL):
        name = structure.name
        start = get_block_index(structure.start_station)
        end = get_block_index(structure.end_station)

        tn_start_data = (
            f",;{name}\n"
            f"{start}\n"
            f"{create_wall_syntax(tn_idx, mode='start')}"
            f"{create_dike_syntax(e_idx, line_count, designspeed, mode='end')}\n"
            f".freeobj 0;{idx_tns};\n"
        )

        tn_end_data = (
            f"{end}\n"
            f"{create_wall_syntax(tn_idx, mode='end')}"
            f"{create_dike_syntax(e_idx, line_count, designspeed, mode='start')}"
            f".freeobj {0 if line_count == 1 else 1};{idx_tne};0;0;180;\n"
        )

        result.append(tn_start_data)
        result.append(tn_end_data)

    return result