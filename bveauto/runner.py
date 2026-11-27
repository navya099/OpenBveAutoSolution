# bveauto/runner.py
from __future__ import annotations

from typing import Callable

from .context import BuildContext
from .pipeline import Pipeline
from .steps import (
    BridgeStep,
    CurveStep,
    InfoStep,
    PoleStep,
    PostStep,
    SignalStep,
    TransmissionStep,
)

LogFn = Callable[[str], None]
DEFAULT_INFO_STEP = "#0. 기본 정보 로드"


def _noop_log(_msg: str) -> None:
    pass


def build_default_pipeline(log: LogFn | None = None) -> Pipeline:
    """기본 실행 파이프라인을 생성한다."""
    return Pipeline(
        [
            InfoStep(),
            BridgeStep(),
            CurveStep(),
            PoleStep(),
            SignalStep(),
            PostStep(),
            TransmissionStep(),
        ],
        log or _noop_log,
    )


def parse_int(value: int | str, field_name: str) -> int:
    """정수 입력값을 검증/파싱한다."""
    if isinstance(value, bool):
        raise ValueError(f"{field_name}에는 정수를 입력하세요: {value!r}")
    try:
        return int(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{field_name}에 숫자를 입력하세요: {value!r}") from exc


class SolutionRunner:
    """GUI와 무관하게 파이프라인 설정 및 실행을 제어하는 코어 러너."""

    def __init__(
        self,
        ctx: BuildContext | None = None,
        pipeline: Pipeline | None = None,
        log: LogFn | None = None,
    ) -> None:
        self.log: LogFn = log or _noop_log
        self.ctx: BuildContext = ctx if ctx is not None else BuildContext()
        self.pipeline: Pipeline = (
            pipeline if pipeline is not None else build_default_pipeline(self.log)
        )

    def step_names(self) -> list[str]:
        return list(self.pipeline.names())

    def configure(self, designspeed: int | str, linecount: int | str) -> BuildContext:
        """입력값을 검증하고 BuildContext에 반영한다."""
        speed = parse_int(designspeed, "설계속도")
        lines = parse_int(linecount, "선로갯수")
        self.ctx.designspeed = speed
        self.ctx.linecount = lines
        self.log(f"입력 반영: 속도={self.ctx.designspeed}, 선로수={self.ctx.linecount}")
        return self.ctx

    def run_all(
        self,
        designspeed: int | str | None = None,
        linecount: int | str | None = None,
    ) -> BuildContext:
        """전체 파이프라인을 실행한다."""
        if designspeed is not None or linecount is not None:
            self.configure(
                designspeed if designspeed is not None else self.ctx.designspeed,
                linecount if linecount is not None else self.ctx.linecount,
            )
        self.pipeline.run(self.ctx)
        return self.ctx

    def run_step(
        self,
        step_name: str,
        designspeed: int | str | None = None,
        linecount: int | str | None = None,
    ) -> BuildContext:
        """지정한 단일 스텝만 실행한다."""
        if designspeed is not None or linecount is not None:
            self.configure(
                designspeed if designspeed is not None else self.ctx.designspeed,
                linecount if linecount is not None else self.ctx.linecount,
            )
        self.pipeline.run_single(self.ctx, step_name)
        return self.ctx