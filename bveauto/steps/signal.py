# bveauto/steps/signal.py
import random

from ..context import BuildContext
from ..decorators import log_errors
from ..steps.base import Step


class SignalStep(Step):
    name = "#4. 신호"

    @log_errors("#4. 신호")
    def execute(self, ctx: BuildContext, log):
        block_length = [random.randint(1200, 1800) for _ in range(4)]
        end_km = int(ctx.last_block // 1000)
        _, positions = distribute_pole_spacing_flexible(0, end_km, block_length)

        save_signal_data(positions, ctx.structure_list, ctx.paths.route / '신호.txt')

        log(f"신호기 {len(positions)}개, 폐색간격 {min(block_length)}~{max(block_length)}")