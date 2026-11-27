# bveauto/steps/pole.py (이식 어댑터 뼈대)
import os
from datetime import datetime
from pathlib import Path
from ..context import BuildContext
from ..core.electric_system.index_util import _find_index_file, load_index_library
from ..decorators import log_errors
from ..steps.base import Step
from ..xref.decats.bve.bvecsv import BVECSV
from ..xref.decats.core.runner import AutoRunner
from ..xref.decats.dataset.dataset_getter import DatasetGetter
from ..xref.decats.dataset.dataset_manager import load_dataset
from ..xref.decats.index_libmgr import IndexLibrary
import pandas as pd
import re




class PoleStep(Step):
    name = "#3. 전차선"

    @log_errors("#3. 전차선")
    def execute(self, ctx: BuildContext, log):
        r = AutoRunner()
        import pandas as pd
        idx_file = _find_index_file(ctx)
        r.idxlib = load_index_library(idx_file)
        if idx_file:
            log(f"인덱스 라이브러리 로드: {idx_file.name}")
        # 1. BuildContext의 경로 및 선형/구조물 파일 연결
        base_dir = ctx.paths.base_source
        alignment = base_dir / "bve_alignment.txt"
        if alignment.is_file():
            r.alignment_file_path = str(alignment)
        else:
            r.coord_file_path = str(base_dir / "bve_coordinates.txt")
            r.curve_file_path = str(base_dir / "curve_info.txt")
            r.pitch_file_path = str(base_dir / "pitch_info.txt")

        # 구조물 엑셀 파일 탐색
        xlsx_files = [f for f in sorted(base_dir.glob("*.xlsx")) if not f.name.startswith("~$")]
        if xlsx_files:
            r.structure_file_path = str(xlsx_files[0])

        # 2. 설계속도, 선로수, 측점 등 파라미터 매핑
        r.designspeed = ctx.designspeed
        r.track_mode = "double" if ctx.linecount >= 2 else "single"
        r.start_station = ctx.start_block
        r.end_station = ctx.last_block
        r.brokenchain = ctx.brokenchain
        r.iscustommode = int(ctx.iscustommode)
        r.dataprocessor = DatasetGetter(load_dataset(r.designspeed, bool(ctx.iscustommode), None, None))

        if r.track_mode == "double":
            r.track_direction.update(main=-1, sub=1)
            r.track_distance = ctx.offset if ctx.offset > 0 else 4.3
            r.tunnel_direction.update(main=1, sub=-1)
        else:
            r.track_direction["main"] = -1
            r.tunnel_direction["main"] = -1

        # 3. 전차선 계산 실행
        r.run()

        # 4. BVE 구문 파일 저장
        out_dir = ctx.paths.route
        out_dir.mkdir(parents=True, exist_ok=True)
        stamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        for track, idx in (("main", 0), ("sub", 1)):
            if track not in r.poledata:
                continue
            csv = BVECSV(r.poledata[track], r.wire_data[track], track_index=idx)
            pole_lines, wire_lines = csv.create_pole_csv(), csv.create_wire_csv()

            pole_path = out_dir / f"{track}_pole_{stamp}.txt"
            wire_path = out_dir / f"{track}_wire_{stamp}.txt"
            pole_path.write_writelines(pole_lines) if hasattr(pole_path, "write_writelines") else pole_path.write_text("".join(pole_lines), encoding="utf-8")
            wire_path.write_writelines(wire_lines) if hasattr(wire_path, "write_writelines") else wire_path.write_text("".join(wire_lines), encoding="utf-8")
            log(f"[{track}] 전주/전선 저장 완료: {pole_path.name}, {wire_path.name}")
