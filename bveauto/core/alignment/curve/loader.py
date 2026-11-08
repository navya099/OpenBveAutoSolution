import logging
from tkinter import filedialog

import pandas as pd

from bveauto.core.alignment.curve.curvedata import CurveData, CurveCollection, CurveDirection

logger = logging.getLogger(__name__)

def read_file() -> str | None:
    file_path = filedialog.askopenfilename(defaultextension=".txt",
                                           filetypes=[("txt files", "curve_info.txt"), ("All files", "*.*")])

    if not file_path:
        logger.error("파일을 선택하지 않았습니다.")
        return None
    logger.info(f'현재 선택된 파일 : {file_path}')
    return file_path


def load_curve_data() -> CurveCollection | None:
    file_path = read_file()
    if not file_path:
        logger.error('read_file is empty')
        raise ValueError('입력 데이터가 비어있습니다.')
    try:
        # 텍스트 파일(.txt) 읽기
        df_curve = pd.read_csv(file_path, sep=",", header=None, names=['sta', 'radius', 'cant'])

        # 곡선 구간 정보 저장
        cs = CurveCollection()
        for _, row in df_curve.iterrows():
            radius_raw = float(row['radius'])

            if radius_raw > 0:
                direction = CurveDirection.LEFT
            elif radius_raw < 0:
                direction = CurveDirection.RIGHT
            else:
                direction = CurveDirection.TANGENT

            cd = CurveData(
                station=float(row['sta']),
                radius=abs(radius_raw),
                cant=float(row['cant']),
                direction=direction
            )
            cs.add(cd)
    except Exception:
        logger.exception('곡선데이터 생성중 예외가 발생했습니다.')
        return None
    cs.sort()
    return cs
