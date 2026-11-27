# tests/test_runner.py
import pytest

from bveauto.context import BuildContext
from bveauto.pipeline import Pipeline
from bveauto.runner import SolutionRunner, build_default_pipeline


class DummyStep:
    def __init__(self, name: str):
        self.name = name
        self.called_with = []

    def run(self, ctx: BuildContext, log):
        self.called_with.append((ctx.designspeed, ctx.linecount))


def test_configure_updates_context_and_logs():
    logs = []
    runner = SolutionRunner(pipeline=Pipeline([], logs.append), log=logs.append)

    ctx = runner.configure("200", "2")

    assert ctx.designspeed == 200
    assert ctx.linecount == 2
    assert "속도=200, 선로수=2" in logs[-1]


def test_configure_raises_on_invalid_input():
    runner = SolutionRunner(pipeline=Pipeline([], lambda _: None))

    with pytest.raises(ValueError, match="설계속도"):
        runner.configure("abc", "1")


def test_run_step_with_mock_pipeline():
    step0 = DummyStep("#0. 기본 정보 로드")
    step1 = DummyStep("#1. 교량")
    logs = []
    pipeline = Pipeline([step0, step1], logs.append)

    runner = SolutionRunner(pipeline=pipeline, log=logs.append)
    runner.run_step("#1. 교량", designspeed=180, linecount=2)

    assert step0.called_with == []
    assert step1.called_with == [(180, 2)]


def test_default_pipeline_integration():
    # 실제 스텝 전체를 GUI 없이 실행하는 통합 테스트
    logs = []
    pipeline = build_default_pipeline(log=logs.append)
    runner = SolutionRunner(pipeline=pipeline, log=logs.append)

    runner.configure(150, 1)
    runner.run_step("#0. 기본 정보 로드")
    # runner.run_all()