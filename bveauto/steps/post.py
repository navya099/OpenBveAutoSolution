from ..context import BuildContext
from ..decorators import log_errors
from ..steps.base import Step
from ..xref.post.controller.mainrunner import MainRunner
from ..xref.post.controller.state import AppState

POST_TYPES = ("거리표", "곡선표", "기울기표")

# 구조물별 선로제표 기본 배치 오프셋 (x절댓값, y높이)
DEFAULT_POST_OFFSET = {
    "토공": (3.0, 0.0),
    "교량": (3.0, 0.0),
    "터널": (2.5, 1.5),
}


class PostStep(Step):
    name = "#6. 선로제표"

    @log_errors("#6. 선로제표")
    def execute(self, ctx: BuildContext, log) -> None:
        base_dir = ctx.paths.base_source
        xlsx_files = [f for f in sorted(base_dir.glob("*.xlsx")) if not f.name.startswith("~$")]

        state = AppState()
        state.start_station = ctx.start_block
        state.end_station = ctx.last_block
        state.brokenchain = ctx.brokenchain
        state.isbrokenchain = ctx.brokenchain != 0.0
        state.alignment_type = ctx.alignment_type

        state.base_source_directory = str(base_dir)
        state.structure_excel_path = str(xlsx_files[0]) if xlsx_files else ""
        # 선로제표는 CSV/PNG 오브젝트 파일과 txt 구문을 함께 생성하므로 obj 또는 route 경로 지정
        state.target_directory = str(ctx.paths.obj)
        state.work_directory = str(ctx.paths.obj)
        state.offset = DEFAULT_POST_OFFSET.copy()

        # 트랙 모드 및 방향/인덱스 설정
        if ctx.linecount >= 2:
            state.track_mode = "double"
            state.track_distance = ctx.offset if ctx.offset > 0 else 4.3
            state.track_direction = {"main": -1, "sub": 1}
            state.track_index = {"main": 0, "sub": 1}
        else:
            state.track_mode = "single"
            state.track_distance = 0.0
            state.track_direction = {"main": -1}
            state.track_index = {"main": 0}

        info_file_map = {
            "거리표": str(base_dir / "curve_info.txt"),
            "곡선표": str(base_dir / "curve_info.txt"),
            "기울기표": str(base_dir / "pitch_info.txt"),
        }

        for post_type in POST_TYPES:
            state.posttype = post_type
            state.info_path = info_file_map[post_type]
            log(f"선로제표 생성 중: {post_type}")
            runner = MainRunner(
                state=state,
                logger=log,
                generator_type=post_type,
            )
            runner.run()
