import random
from ..context import BuildContext
from ..core.signal.signal_builder import save_signal_data, build
from ..decorators import log_errors
from ..steps.base import Step

class SignalStep(Step):
    name = "#4. 신호"

    @log_errors("#4. 신호")
    def execute(self, ctx: BuildContext, log) -> None:
        # 1200~1800m 사이의 랜덤 폐색 간격 후보 4개 생성
        block_length = [random.randint(1200, 1800) for _ in range(4)]

        start_km = ctx.start_block // 1000
        end_km = ctx.last_block // 1000


        spans, pole_positions = build(
            start_km, end_km, block_length
        )

        # 데이터 저장
        out_dir = ctx.paths.route
        out_dir.mkdir(parents=True, exist_ok=True)
        signal_path = out_dir / "신호.txt"

        # save_signal_data가 str 경로를 기대할 수 있으므로 str() 변환 전달
        save_signal_data(pole_positions, ctx.structure_list, str(signal_path))

        log(f"신호 저장: {signal_path}")
        log(f"신호기 개수: {len(pole_positions)}")
        log(f"폐색간격 최소: {min(block_length)}m, 최대: {max(block_length)}m")
