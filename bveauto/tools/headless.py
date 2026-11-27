"""GUI 없이 OpenBveAutoSolution 파이프라인 자동 배치 실행 (CLI)

사용 예:
    python -m tools.headless --config tests/regression_cases/case.json --out out/run1
    python -m tools.headless --base-source c:/temp --route D:/BVE/Route --obj D:/BVE/Object \
        --speed 180 --linecount 2 --out out/run2
    python -m tools.headless --config case.json --step "#2. 곡선레일" --out out/step_only
"""
from __future__ import annotations

import argparse
import json
import re
import sys
import time
from pathlib import Path
from typing import Callable

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from bveauto.config import DEFAULT_PATHS, PathConfig  # noqa: E402
from bveauto.context import BuildContext  # noqa: E402
from bveauto.runner import SolutionRunner  # noqa: E402

DEFAULTS = {
    "speed": 150,
    "linecount": 1,
    "offset": 0.0,
    "brokenchain": 0.0,
    "iscustommode": False,
    "base_source": str(DEFAULT_PATHS.base_source),
    "route": str(DEFAULT_PATHS.route),
    "obj": str(DEFAULT_PATHS.obj),
}

PATH_KEYS = ("base_source", "route", "obj")
ERROR_PATTERN = re.compile(r"에러|오류|Error|error|실패")


def load_config(path: str | Path) -> dict:
    """case.json 로드 및 상대경로를 case.json 위치 기준으로 정규화"""
    cfg_path = Path(path).resolve()
    with open(cfg_path, encoding="utf-8") as f:
        cfg = json.load(f)

    base_dir = cfg_path.parent
    for key in PATH_KEYS:
        if cfg.get(key):
            cfg[key] = str((base_dir / cfg[key]).resolve())
    return cfg


def build_runner(cfg: dict, log_fn: Callable[[str], None]) -> SolutionRunner:
    """설정 딕셔너리로부터 BuildContext 및 SolutionRunner 구성"""
    cfg = {**DEFAULTS, **cfg}
    paths = PathConfig(
        base_source=Path(cfg["base_source"]),
        route=Path(cfg["route"]),
        obj=Path(cfg["obj"]),
    )
    ctx = BuildContext(
        designspeed=int(cfg["speed"]),
        linecount=int(cfg["linecount"]),
        offset=float(cfg["offset"]),
        brokenchain=float(cfg["brokenchain"]),
        iscustommode=bool(cfg["iscustommode"]),
        paths=paths,
    )
    return SolutionRunner(ctx=ctx, log=log_fn)


def run(
    cfg: dict,
    out_dir: str | Path,
    step_name: str | None = None,
    quiet: bool = True,
) -> dict:
    """파이프라인 전체 또는 특정 단계 실행 후 summary.json 및 run.log 저장"""
    out_path = Path(out_dir)
    out_path.mkdir(parents=True, exist_ok=True)

    logs: list[str] = []

    def log_handler(msg: str) -> None:
        logs.append(msg)
        if not quiet:
            print(msg)

    runner = build_runner(cfg, log_handler)

    t0 = time.time()
    if step_name:
        runner.run_step(step_name)
    else:
        runner.run_all()
    elapsed = round(time.time() - t0, 2)

    errors = [line for line in logs if ERROR_PATTERN.search(line)]
    summary = {
        "speed": runner.ctx.designspeed,
        "linecount": runner.ctx.linecount,
        "alignment_type": runner.ctx.alignment_type,
        "step": step_name or "ALL",
        "elapsed_sec": elapsed,
        "error_count": len(errors),
        "errors": errors,
        "paths": {
            "base_source": str(runner.ctx.paths.base_source),
            "route": str(runner.ctx.paths.route),
            "obj": str(runner.ctx.paths.obj),
        },
    }

    with open(out_path / "run.log", "w", encoding="utf-8") as f:
        f.write("\n".join(logs) + "\n")

    with open(out_path / "summary.json", "w", encoding="utf-8") as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)

    return summary


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="OpenBveAutoSolution 헤드리스 배치 실행기")
    ap.add_argument("--config", help="case.json 설정 파일 경로")
    ap.add_argument("--base-source", help="입력 소스 폴더 경로 (선형, 구조물 등)")
    ap.add_argument("--route", help="BVE Route 출력 폴더 경로")
    ap.add_argument("--obj", help="BVE Object 출력 폴더 경로")
    ap.add_argument("--speed", type=int, help="설계속도 (km/h)")
    ap.add_argument("--linecount", type=int, help="선로 수 (1: 단선, 2: 복선)")
    ap.add_argument("--offset", type=float, help="선로 중심 간격 / 오프셋 (m)")
    ap.add_argument("--brokenchain", type=float, help="파정 (m)")
    ap.add_argument("--custom", action="store_true", help="커스텀 모드 활성화")
    ap.add_argument("--step", help="특정 단계만 단독 실행할 경우 단계명 (예: '#2. 곡선레일')")
    ap.add_argument("--out", default="out/headless", help="실행 로그 및 summary.json 저장 폴더")
    ap.add_argument("--verbose", action="store_true", help="처리 로그를 터미널에 실시간 출력")
    args = ap.parse_args(argv)

    cfg = load_config(args.config) if args.config else {}

    cli_overrides = {
        "base_source": args.base_source,
        "route": args.route,
        "obj": args.obj,
        "speed": args.speed,
        "linecount": args.linecount,
        "offset": args.offset,
        "brokenchain": args.brokenchain,
    }
    for k, v in cli_overrides.items():
        if v is not None:
            cfg[k] = v
    if args.custom:
        cfg["iscustommode"] = True

    summary = run(cfg, out_dir=args.out, step_name=args.step, quiet=not args.verbose)

    print(f"[완료] 모드: {summary['alignment_type']} ({summary['speed']}km/h) | 소요시간: {summary['elapsed_sec']}초")
    print(f"오류 {summary['error_count']}건 → 결과 요약: {args.out}/summary.json")
    for err in summary["errors"][:10]:
        print("  !", err)

    return 1 if summary["error_count"] > 0 else 0


if __name__ == "__main__":
    sys.exit(main())
