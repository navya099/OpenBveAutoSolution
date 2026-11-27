# bveauto/steps/curve.py
from ..context import BuildContext
from ..decorators import log_errors
from ..steps.base import Step
from ..xref.bve_curve_core import generate_bve_texts


class CurveStep(Step):
    name = "#2. 곡선레일"

    @log_errors("#2. 곡선레일")
    def execute(self, ctx: BuildContext, log):

        result = generate_bve_texts(
            curveinfo=ctx.curve_info,
            structure_data=ctx.structure_list,
            alignment_type="고속철도",
            filter_zero_offsets=True,  # 필요 없으면 생략 가능
        )