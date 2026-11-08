# bveauto/steps/transmission.py
from ..context import BuildContext
from ..decorators import log_errors
from ..steps.base import Step

class TransmissionStep(Step):
    name = "#5. 통신"

    @log_errors("#5. 통신")
    def execute(self, ctx: BuildContext, log):
        result = create_transmisson_data(ctx.structure_list)
        create_txt(ctx.paths.route / '통신.txt', result)