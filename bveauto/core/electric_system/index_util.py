from pathlib import Path
import pandas as pd
import re
import os

from bveauto.context import BuildContext
from bveauto.xref.decats.index_libmgr import IndexLibrary


def _find_index_file(ctx: BuildContext) -> Path | None:
    """base_source 또는 route 폴더에서 인덱스 라이브러리 파일 자동 탐색"""
    # 1. BuildContext에 명시적 경로가 있다면 우선 사용 (선택 확장)
    explicit = getattr(ctx, "idxlib_path", None)
    if explicit and Path(explicit).is_file():
        return Path(explicit)

    # 2. base_source 및 route 폴더에서 지정된 후보 파일명 탐색
    candidates = [
        ctx.paths.base_source / "index_lib.csv",
        ctx.paths.base_source / "idxlib.csv",
        ctx.paths.base_source / "freeobj_list.txt",
        ctx.paths.route / "freeobj_list.txt",
    ]
    for cand in candidates:
        if cand.is_file():
            return cand
    return None


def load_index_library(path):
    """인덱스 라이브러리: CSV(인덱스,파일명,경로) 또는 BVE '.freeobj(N) 경로' 목록"""
    if not path:


        return IndexLibrary(pd.DataFrame(columns=['인덱스', '파일명', '경로']))
    # 수정 후 (Path 객체의 확장자 비교)
    if Path(path).suffix.lower() == '.csv':
        return IndexLibrary(pd.read_csv(path))
    rows = []
    with open(path, encoding='utf-8', errors='replace') as f:
        for line in f:

            m = re.match(r'\s*\.freeobj\((\d+)\)\s*(.+?)\s*$', line, re.I)
            if m:
                obj_path = m.group(2)
                name = os.path.splitext(os.path.basename(obj_path.replace('\\', '/')))[0]
                rows.append({'인덱스': int(m.group(1)), '파일명': name, '경로': obj_path})
    return IndexLibrary(pd.DataFrame(rows, columns=['인덱스', '파일명', '경로']))