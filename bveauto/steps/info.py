# bveauto/steps/info.py
from ..context import BuildContext
from ..core.alignment.coord.loader import load_coord_data
from ..core.alignment.curve.loader import load_curve_data
from ..core.alignment.profile.loader import load_pitch_data
from ..core.structure.loader import load_structure_data
from ..decorators import log_errors
from ..steps.base import Step


class InfoStep(Step):
    name = "#0. 기본 정보 로드"
    requires_loaded = False

    @log_errors("#0. 기본 정보 로드", reraise=True)
    def execute(self, ctx: BuildContext, log):
        log(f"설계속도={ctx.designspeed}km/h, 선로구분={ctx.alignment_type}, 선로수={ctx.linecount}")

        ctx.curve_info = load_curve_data() or None
        ctx.pitch_info = load_pitch_data() or None
        ctx.bve_coord = load_coord_data() or None
        ctx.structure_list = load_structure_data() or None

        if not ctx.curve_info:
            raise RuntimeError("곡선 정보 로드 실패")
        if not ctx.structure_list:
            raise RuntimeError("구조물 정보 로드 실패")

        ctx.start_block = ctx.curve_info[0][0]
        ctx.last_block = ctx.curve_info[-1][0]
        log(f"시작 측점: {ctx.start_block}, 끝 측점: {ctx.last_block}")
        log(f"파정: {ctx.brokenchain}, freeobj offset: {ctx.offset}")