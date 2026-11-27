"""설계속도별 데이터셋(JSON + 경간 spandata.xlsx) 로더

표준 데이터셋은 항상 소스 폴더의 config/ 에서만 읽는다 (PC마다 c:/temp 등 외부 경로에
남아 있는 이전 버전 파일과 혼동되지 않도록). 사용자 정의(커스텀) 데이터셋만 사용자가
경로를 직접 지정한다.
"""
import json
import os
import sys

import pandas as pd

SUPPORTED_SPEEDS = (150, 250, 350)


def get_config_dir() -> str:
    """소스(또는 실행 파일) 폴더의 config/ 경로"""
    if getattr(sys, 'frozen', False):  # PyInstaller 등으로 빌드된 실행 파일
        base = os.path.dirname(sys.executable)
    else:
        base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(base, 'config')


def get_standard_dataset_paths(designspeed: int) -> tuple[str, str]:
    """설계속도별 표준 데이터셋 (json, spandata.xlsx) 경로"""
    if designspeed not in SUPPORTED_SPEEDS:
        raise ValueError(f'지원하지 않는 속도 모드입니다. {designspeed} (지원: {SUPPORTED_SPEEDS})')
    config_dir = get_config_dir()
    return (os.path.join(config_dir, f'railway_{designspeed}.JSON'),
            os.path.join(config_dir, f'spandata_{designspeed}.xlsx'))


def load_dataset(designspeed, iscustommode, custom_json=None, custom_spandata=None):
    """데이터셋 로드

    :param designspeed: 설계속도 (표준 모드에서 사용)
    :param iscustommode: True 면 custom_json / custom_spandata 를 사용
    :param custom_json: 커스텀 데이터셋 JSON 경로 (커스텀 모드 필수)
    :param custom_spandata: 커스텀 경간 xlsx 경로 (커스텀 모드 필수)
    """
    if iscustommode:
        if not custom_json or not custom_spandata:
            raise ValueError('커스텀 모드에서는 데이터셋 JSON 과 spandata xlsx 경로를 직접 지정해야 합니다.')
        filename, xlsxname = custom_json, custom_spandata
    else:
        filename, xlsxname = get_standard_dataset_paths(int(designspeed))

    for path in (filename, xlsxname):
        if not os.path.isfile(path):
            raise FileNotFoundError(f'데이터셋 파일이 없습니다: {path}')

    with open(filename, "r", encoding="utf-8") as f:
        base_data = json.load(f)

    # 모든 시트를 읽어서 구조화: 각 시트별로 {길이: 인덱스}
    sheets = pd.read_excel(xlsxname, sheet_name=None)
    base_data['span_data'] = {name: dict(zip(df['길이'], df['인덱스'])) for name, df in sheets.items()}

    # 오류 메시지에서 어떤 파일이 로드됐는지 알 수 있도록 기록
    base_data['_source'] = {'json': filename, 'spandata': xlsxname}
    return base_data
