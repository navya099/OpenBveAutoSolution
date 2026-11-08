import logging
from tkinter import filedialog

import pandas as pd
from bveauto.core.alignment.profile.profiledata import ProfileCollection, ProfileData

logger = logging.getLogger(__name__)

def read_file() -> str | None:
    file_path = filedialog.askopenfilename(defaultextension=".txt",
                                           filetypes=[("txt files", "pitch_info.txt"), ("All files", "*.*")])

    if not file_path:
        logger.error("파일을 선택하지 않았습니다.")
        return None
    logger.info(f'현재 선택된 파일 : {file_path}')
    return file_path





def load_pitch_data() -> ProfileCollection | None:
    file_path = read_file()
    if not file_path:
        logger.error('read_file is empty')
        raise ValueError('입력 데이터가 비어있습니다.')
    try:
        # 텍스트 파일(.txt) 읽기
        df_grade = pd.read_csv(file_path, sep=",", header=None, names=['sta', 'grade'])

        # 구배 구간 정보 저장
        ps = ProfileCollection()
        for _, row in df_grade.iterrows():

            profile = ProfileData(
                station=float(row['sta']),
                grade=float(row['grade'])
                )
            ps.add(profile)
    except Exception:
        logger.exception('구배데이터 생성중 예외가 발생했습니다.')
        return None
    return ps
