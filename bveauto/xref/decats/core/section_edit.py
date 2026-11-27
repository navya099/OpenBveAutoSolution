"""구간 편집 — 에어조인트·에어섹션·흐름방지 구간 조회·추가·삭제 (GUI 없이 동작)

구간 = 연속한 여러 전주를 묶는 설비 단위.
    에어조인트: 인류구간(장력 구간) 구분용. 2경간 단주(전주 5개) / 2경간 복주(지지점 5개, 전주 8개)
    에어섹션:   변전소(SS·SP 등) 위상 구분용. 단일(전주 5개) / 이중(전주 8개)
    흐름방지:   장력 구간 가운데의 흐름방지장치 (전주 3개)

구간 종류는 SECTION_KINDS 등록표로 관리한다. 새 에어조인트 타입(예: 3경간)을 지원하려면
SectionType 에 전주별 구간 값을 추가하고 register_kind() 로 등록하면 된다 (처리 방식이 다르면 processor 지정).
기존 구간은 전주 구간 값의 순서가 등록된 종류와 일치하는지로 찾는다.

기준 전주는 모든 종류에서 '구간 시작 전주'. 편집 함수는 전주 데이터만 바꾸고, 호출 측에서 rebuild 한다.
"""
from dataclasses import dataclass, field
from typing import Callable

from bveauto.xref.decats.core.airjoint.airjoint_processor import AirJointProcessor
from bveauto.xref.decats.core.airsection.airsection_processor import AirSectionProcessor
from bveauto.xref.decats.enums.section_type import (AIRJOINT_DOUBLE_POLE_SEQUENCE, AIRJOINT_SEQUENCE, AIRSECTION_DOUBLE,
                                AIRSECTION_SINGLE, FlowStop, SectionType)

CATEGORY_TEXT = {'airjoint': '에어조인트', 'airsection': '에어섹션', 'flowstop': '흐름방지'}


# ── 구간 종류 등록표 ─────────────────────────────────
@dataclass(frozen=True)
class SectionKind:
    id: str
    label: str                    # 화면 표시 이름
    category: str                 # 'airjoint' | 'airsection' | 'flowstop'
    purpose: str                  # 용도 설명
    sequence: tuple               # 전주별 구간 값 (시작 전주부터)
    processor: Callable | None = field(default=None, compare=False)  # (runner, pole, alignment) → 구성품 생성

    @property
    def n_poles(self):
        return len(self.sequence)


def _airjoint_processor(runner, pole, alignment):
    if hasattr(runner, 'apply_dataset_options'):
        runner.apply_dataset_options()  # 실행 설정의 복주 쌍 전주 간격·급전선설비
    AirJointProcessor.process(pole, alignment, runner.dataprocessor, runner.idxlib)


def _airsection_processor(mode):
    def process(runner, pole, alignment):
        AirSectionProcessor.process(pole, alignment, runner.dataprocessor, runner.idxlib, mode=mode)
    return process


SECTION_KINDS = {}


def register_kind(kind: SectionKind):
    """구간 종류 등록 (새 에어조인트 타입 등). 같은 순서를 쓰는 종류가 이미 있으면 거부"""
    for other in SECTION_KINDS.values():
        if other.sequence == kind.sequence and other.id != kind.id:
            raise ValueError(f'{kind.id}: {other.id} 와 전주 구간 순서가 같아 구분할 수 없습니다.')
    SECTION_KINDS[kind.id] = kind
    return kind


register_kind(SectionKind('airjoint_2span', '에어조인트 (2경간, 전주 5개)', 'airjoint',
                          '인류구간(장력 구간) 구분', AIRJOINT_SEQUENCE, _airjoint_processor))
register_kind(SectionKind('airjoint_2span_double_pole', '복주 에어조인트 (2경간, 지지점 5개·전주 8개)', 'airjoint',
                          '인류구간(장력 구간) 구분 — 2·3·4호주에 전주 2개(브래킷 1개씩), 레거시 방식',
                          AIRJOINT_DOUBLE_POLE_SEQUENCE, _airjoint_processor))
register_kind(SectionKind('airsection_single', '에어섹션 단일 (전주 5개)', 'airsection',
                          '변전소(SS·SP 등) 위상 구분', AIRSECTION_SINGLE, _airsection_processor('single')))
register_kind(SectionKind('airsection_double', '에어섹션 이중 (전주 8개)', 'airsection',
                          '변전소(SS·SP 등) 위상 구분', AIRSECTION_DOUBLE, _airsection_processor('double')))
register_kind(SectionKind('flowstop', '흐름방지 (전주 3개)', 'flowstop',
                          '장력 구간 가운데 흐름방지장치', (FlowStop.START, FlowStop.MIDDLE, FlowStop.END)))


# ── 조회 ────────────────────────────────────────────
@dataclass
class SectionInstance:
    kind: SectionKind | None      # None = 불완전 구간 (순서가 깨진 구간 값)
    track: str
    poles: list

    @property
    def start_pos(self):
        return self.poles[0].pos

    @property
    def end_pos(self):
        return self.poles[-1].pos

    @property
    def label(self):
        return self.kind.label if self.kind else '불완전 구간 (구간 값 순서 불일치)'


def _linked(poles):
    """연속 전주가 실제로 이어져 있는지 (레일 단절 등으로 끊기지 않음)"""
    return all(a.next_pos == b.pos for a, b in zip(poles, poles[1:]))


def _section_kinds():
    """에어조인트·에어섹션 종류 (긴 것 먼저 → 접두가 같은 단일/이중도 정확히 구분)"""
    return sorted((k for k in SECTION_KINDS.values() if k.category != 'flowstop'), key=lambda k: -k.n_poles)


def find_sections(runner, track=None):
    """트랙별 기존 구간 목록 (에어조인트·에어섹션·흐름방지·불완전 구간), 측점 순"""
    out = []
    for t, poles in (runner.poledata or {}).items():
        if track is not None and t != track:
            continue
        i = 0
        while i < len(poles):
            if poles[i].section is None:
                i += 1
                continue
            for kind in _section_kinds():
                group = poles[i:i + kind.n_poles]
                if (len(group) == kind.n_poles and tuple(p.section for p in group) == kind.sequence
                        and _linked(group)):
                    out.append(SectionInstance(kind, t, group))
                    i += kind.n_poles
                    break
            else:  # 어떤 종류와도 맞지 않는 구간 값 → 불완전 구간으로 묶음
                j = i
                while j < len(poles) and poles[j].section is not None:
                    j += 1
                out.append(SectionInstance(None, t, poles[i:j]))
                i = j
        flow = SECTION_KINDS['flowstop']
        for k in range(len(poles) - 2):
            group = poles[k:k + 3]
            if tuple(getattr(p, 'flowstop', None) for p in group) == flow.sequence:
                out.append(SectionInstance(flow, t, group))
    out.sort(key=lambda s: (s.track, s.start_pos))
    return out


# ── 추가 계획(미리보기·검증) ────────────────────────────
@dataclass
class AddPlan:
    kind: SectionKind
    track: str
    poles: list                   # 대상 전주 (시작 전주부터)
    problems: list                # 문제가 있으면 추가 불가

    @property
    def ok(self):
        return not self.problems

    @property
    def assignments(self):
        """[(전주, 현재 구간 표시, 새 구간 값)]"""
        return [(p, p.section or getattr(p, 'flowstop', None), tag) for p, tag in zip(self.poles, self.kind.sequence)]


def plan_add(runner, track, start_pos, kind_id):
    """start_pos 전주부터 kind 구간을 추가할 때 바뀌는 전주와 문제점"""
    kind = SECTION_KINDS[kind_id]
    poles = (runner.poledata or {}).get(track)
    if not poles:
        return AddPlan(kind, track, [], [f'{track} 트랙에 전주가 없습니다.'])
    idx = next((i for i, p in enumerate(poles) if p.pos == start_pos), None)
    if idx is None:
        return AddPlan(kind, track, [], [f'{start_pos}m 에 전주가 없습니다.'])
    group = poles[idx:idx + kind.n_poles]
    problems = []
    if len(group) < kind.n_poles:
        problems.append(f'시작 전주 뒤로 전주가 부족합니다 ({len(group)}/{kind.n_poles}개).')
    if not _linked(group):
        problems.append('대상 전주 사이에 끊긴 경간이 있습니다 (레일 단절 등).')
    if kind.category == 'flowstop':
        busy = [p for p in group if getattr(p, 'flowstop', None) is not None or p.section is not None]
        if busy:
            problems.append('흐름방지는 일반개소에만 설치할 수 있습니다: '
                            + ', '.join(f'{p.post_number}({p.section or p.flowstop})' for p in busy))
    else:
        busy = [p for p in group if p.section is not None]
        if busy:
            problems.append('이미 다른 구간에 속한 전주가 있습니다: '
                            + ', '.join(f'{p.post_number}({p.section})' for p in busy))
    return AddPlan(kind, track, group, problems)


def plan_add_tracks(runner, tracks, start_pos, kind_id):
    """여러 트랙에 같은 측점부터 추가할 때의 계획 목록"""
    return [plan_add(runner, t, start_pos, kind_id) for t in tracks]


# ── 적용 ────────────────────────────────────────────
def apply_add(runner, plan, alignment_for):
    """계획대로 구간 추가 (문제가 있으면 ValueError). 호출 측에서 rebuild"""
    if not plan.ok:
        raise ValueError('\n'.join(plan.problems))
    kind = plan.kind
    if kind.category == 'flowstop':
        start, mid, end = plan.poles
        runner.anticreeping_pr.add_manual_section(plan.track, start.pos, end.pos, mid.pos)
        return
    for pole, tag in zip(plan.poles, kind.sequence):
        pole.section = tag
        pole.flowstop = None
    alignment = alignment_for(runner, plan.track)
    for pole in plan.poles:
        pole.brackets, pole.mast, pole.equipments = [], None, []
        pole.twin = None
        kind.processor(runner, pole, alignment)


def remove(runner, instance, alignment_for):
    """구간 삭제: 전주를 일반개소로 되돌리고 구성품을 자동 재생성 (흐름방지는 장치 제거). 호출 측에서 rebuild"""
    from bveauto.xref.decats.core.pole import pole_edit
    if instance.kind is not None and instance.kind.category == 'flowstop':
        start, mid, end = instance.poles
        runner.anticreeping_pr.remove_manual_section(instance.track, start.pos, end.pos, mid.pos)
        return
    alignment = alignment_for(runner, instance.track)
    for pole in instance.poles:
        pole.section = None
        pole_edit.regenerate(runner, pole, alignment)


def kind_of_pole(runner, pole):
    """전주가 속한 구간 종류 (에어조인트·에어섹션). 없으면 None"""
    for inst in find_sections(runner, pole.track):
        if inst.kind is not None and inst.kind.category != 'flowstop' and any(p is pole for p in inst.poles):
            return inst.kind
    return None


def section_tag_label(tag):
    return str(tag) if tag else '일반개소'


__all__ = ['SECTION_KINDS', 'SectionKind', 'register_kind', 'SectionInstance', 'find_sections', 'AddPlan',
           'plan_add', 'plan_add_tracks', 'apply_add', 'remove', 'kind_of_pole', 'CATEGORY_TEXT',
           'SectionType']
