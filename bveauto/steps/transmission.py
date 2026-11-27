from ..context import BuildContext
from ..core.transmission.builder import create_transmission_data, save_transmission_data
from ..decorators import log_errors
from ..steps.base import Step


class TransmissionStep(Step):
    name = "#5. 통신"

    @log_errors("#5. 통신")
    def execute(self, ctx: BuildContext, log) -> None:
        lines = create_transmission_data(ctx.structure_list)

        out_path = ctx.paths.route / "통신.txt"
        save_transmission_data(lines, out_path)

        log(f"통신 저장: {out_path} ({len(lines)}줄)")
