import logging
from pathlib import Path
from tkinter import filedialog

from bveauto.core.alignment.coord.coorddata import CoordData, CoordCollection

logger = logging.getLogger(__name__)

def read_file() -> str | None:
    file_path = filedialog.askopenfilename(defaultextension=".txt",
                                           filetypes=[("txt files", "bve_coordinates.txt"), ("All files", "*.*")])

    if not file_path:
        logger.error("파일을 선택하지 않았습니다.")
        return None
    logger.info(f'현재 선택된 파일 : {file_path}')
    return file_path


def load_coord_data(base_dir: str | Path | None = None) -> CoordCollection | None:
    if base_dir is not None:
        target = Path(base_dir) / "bve_coordinates.txt"
        if not target.is_file():
            logger.error(f"파일을 찾을 수 없습니다: {target}")
            raise FileNotFoundError(f"좌표 파일이 존재하지 않습니다: {target}")
        file_path = str(target)
    else:
        file_path = read_file()

    if not file_path:
        logger.error("read_file is empty")
        raise ValueError("입력 데이터가 비어있습니다.")
    try:
        cs = CoordCollection()

        with open(file_path, 'r', encoding='utf-8') as file:
            for line in file:
                x, y, z = map(float, line.strip().split(','))

                cd = CoordData(
                    x=x,
                    y=y,
                    z=z
                )

                cs.add(cd)

    except Exception:
        logger.exception('좌표데이터 생성중 예외가 발생했습니다.')
        return None
    logger.info(f'{len(cs)}개의 좌표를 읽었습니다.')
    return cs
