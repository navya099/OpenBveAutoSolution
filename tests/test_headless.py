import json
from pathlib import Path
from bveauto.tools.headless import load_config, build_runner, main


def test_load_config_resolves_relative_paths(tmp_path: Path) -> None:
    """case.json 내부의 상대경로가 case.json 기준 절대경로로 변환되는지 검증"""
    case_dir = tmp_path / "cases" / "case1"
    case_dir.mkdir(parents=True)
    cfg_file = case_dir / "case.json"

    cfg_file.write_text(
        json.dumps({"speed": 250, "base_source": "../../input", "route": "./out_route"}),
        encoding="utf-8",
    )

    loaded = load_config(cfg_file)
    assert loaded["speed"] == 250
    assert Path(loaded["base_source"]) == (tmp_path / "input").resolve()
    assert Path(loaded["route"]) == (case_dir / "out_route").resolve()


def test_build_runner_context_mapping(tmp_path: Path) -> None:
    """설정이 BuildContext에 정확히 매핑되는지 검증"""
    cfg = {
        "speed": 250,
        "linecount": 2,
        "offset": 4.3,
        "brokenchain": 10.5,
        "iscustommode": True,
        "base_source": str(tmp_path / "src"),
        "route": str(tmp_path / "route"),
        "obj": str(tmp_path / "obj"),
    }
    runner = build_runner(cfg, log_fn=lambda _: None)

    assert runner.ctx.designspeed == 250
    assert runner.ctx.linecount == 2
    assert runner.ctx.alignment_type == "준고속철도"
    assert runner.ctx.offset == 4.3
    assert runner.ctx.brokenchain == 10.5
    assert runner.ctx.iscustommode is True
    assert runner.ctx.paths.route == tmp_path / "route"
