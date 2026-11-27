# bveauto/steps/curve.py
from ..context import BuildContext
from ..decorators import log_errors
from ..steps.base import Step
from ..xref.bve_curve_core import generate_bve_texts, save_lines
from datetime import datetime

class CurveStep(Step):
    name = "#2. 곡선레일"

    @log_errors("#2. 곡선레일")
    def execute(self, ctx: BuildContext, log):

        result = generate_bve_texts(
            curveinfo=ctx.curve_info,
            structure_data=ctx.structure_list,
            alignment_type=ctx.alignment_type,
            filter_zero_offsets=True,  # 필요 없으면 생략 가능
        )

        out_path = ctx.paths.route
        out_path.mkdir(parents=True, exist_ok=True)

        stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        freeobj_path = save_lines(result.freeobj_lines, out_path / f"freeobj_{stamp}.txt")
        log(f"FreeObj 저장: {freeobj_path}")

        railtype_path = save_lines(result.railtype_lines, out_path / f"railtype_{stamp}.txt")
        log(f"RailType 저장: {railtype_path}")