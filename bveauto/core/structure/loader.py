import logging
from tkinter import filedialog

from bveauto.core.structure.structuredata import StructureCollection, StructureData, StructureType

logger = logging.getLogger(__name__)

def validate_structure_row(
        name,
        start_station,
        end_station,
        row_index: int
) -> None:
    """구조물 행 데이터 검증"""

    try:
        start_station = float(start_station)
        end_station = float(end_station)
    except ValueError:
        msg = f"{row_index}행: 측점은 숫자여야 합니다."
        logger.error(msg)
        raise ValueError(msg)


    if not name:
        msg = f"{row_index}행: 구조물명이 비어 있습니다."
        logger.error(msg)
        raise ValueError(msg)

    if start_station < 0:
        msg = f"{row_index}행: 시작측점은 0 이상이어야 합니다."
        logger.error(msg)
        raise ValueError(msg)


    if end_station < start_station:
        msg = f"{row_index}행: 끝측점이 시작측점보다 작습니다."
        logger.error(msg)
        raise ValueError(msg)

def read_file() -> str | None:
    file_path = filedialog.askopenfilename(defaultextension=".xlsx",
                                           filetypes=[
                                               ("xlsx files", "*.xlsx"),
                                               ("All files", "*.*")
                                           ])

    if not file_path:
        logger.error("파일을 선택하지 않았습니다.")
        return None
    logger.info(f'현재 선택된 파일 : {file_path}')
    return file_path

def create_structure_data(
        name,
        start_station,
        end_station,
        structure_type: StructureType,
        row_index: int
) -> StructureData:
    validate_structure_row(
        name,
        start_station,
        end_station,
        row_index
    )

    return StructureData(
        name=str(name),
        start_station=float(start_station),
        end_station=float(end_station),
        structure_type=structure_type
    )

def load_structure_sheet(
        df,
        name_col: str,
        start_col: str,
        end_col: str,
        structure_type: StructureType,
        collection: StructureCollection
):
    for idx, row in df.iterrows():
        collection.add(
            create_structure_data(
                row[name_col],
                row[start_col],
                row[end_col],
                structure_type,
                idx + 1
            )
        )

def load_structure_data() -> StructureCollection | None:
    """xlsx 파일을 읽고 교량과 터널 정보를 반환하는 함수"""
    file_path = read_file()
    if not file_path:
        logger.error('read_file is empty')
        return None
    try:
    # xlsx 파일 읽기
        import pandas as pd
    except ImportError:
        raise ImportError('pandas 모듈 임포트에 실패했습니다.')
    try:
        df_bridge = pd.read_excel(file_path, sheet_name='교량', header=None)
        df_tunnel = pd.read_excel(file_path, sheet_name='터널', header=None)

        # 열 개수 확인
        logger.debug(f'터널 구조물 행 개수, 열 개수:  {df_tunnel.shape}')  # (행 개수, 열 개수)
        logger.debug(f'터널 구조물 데이터 검증:  {df_tunnel.head()}')  # 데이터 확인

        if not df_bridge.empty:
            # 첫 번째 행을 열 제목으로 설정
            df_bridge.columns = ['br_NAME', 'br_START_STA', 'br_END_STA', 'br_LENGTH']
        if not df_tunnel.empty:
            df_tunnel.columns = ['tn_NAME', 'tn_START_STA', 'tn_END_STA', 'tn_LENGTH']
        if df_bridge.empty and df_tunnel.empty:
            logger.info('구조물이 비었습니다.')
            return None

        # 교량 구간과 터널 구간 정보
        sc = StructureCollection()
        load_structure_sheet(
            df_bridge,
            'br_NAME',
            'br_START_STA',
            'br_END_STA',
            StructureType.BRIDGE,
            sc
        )

        load_structure_sheet(
            df_tunnel,
            'tn_NAME',
            'tn_START_STA',
            'tn_END_STA',
            StructureType.TUNNEL,
            sc
        )
    except Exception:
        logger.exception('구조물데이터 생성중 예외가 발생했습니다.')
        return None
    logger.info(f'{len(sc)}개의 구조물을 읽었습니다.')
    logger.info(f'교량: {sc.total_bridge_count()}개')
    logger.info(f'터널: {sc.total_tunnel_count()}개')
    return sc
