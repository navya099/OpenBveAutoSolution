"""전선 상세 편집 — 경간(Span) 단위 편집 내용 보관·적용 (GUI 없이 동작)

경간 = 연속한 두 전주. 키는 (트랙, 앞 전주 uid, 뒤 전주 uid) 로, 전주가 이동해도 유지된다 (PoleDATA.uid).
편집 내용은 전선 지지점(시작점·끝점의 x 이격거리, 높이)과 전선 추가/삭제이며, 각도(평면·종단)는
적용할 때 현재 선형·전주 위치로 다시 계산한다. 그래서 전주를 옮겨도 편집은 유지되고 각도는 새 위치에 맞는다.

저장 형식 (runner.wire_overrides, .dat 에 함께 저장):
    {("main", 앞 uid, 뒤 uid): {
        "전차선#0":   {"offset": [x, y], "end_point": [x, y]},     # 자동 생성 전선의 지지점 수정
        "__removed__": {"급전선#0": {"label": "급전선", "index": 1236}},   # 자동 생성 전선 삭제
        "__added__":   {"added:1a2b": {"label": .., "index": .., "offset": [..], "end_point": [..]}},
    }}
전선 키: 자동 생성 전선 = "라벨#같은 라벨 안에서의 순번", 사용자 추가 전선 = "added:ID".

편집 흐름: 아래 set_wire / add_wire / remove_wire / reset_* 로 편집 내용을 바꾼 뒤 rebuild(runner) 를 부르면
apply() 가 재생성된 wire_data 에 반영한다. 경간이 없어지면 미적용, 삭제된 전주의 경간 편집은 정리된다.
"""
import uuid
from dataclasses import dataclass

from bveauto.xref.decats.core.wire.common_processor import CommonWireProcessor
from bveauto.xref.decats.core.wire.singlewire import SingleWire
from bveauto.xref.decats.utils.math_util import change_permile_to_degree

REMOVED = '__removed__'
ADDED = '__added__'
READ_ONLY_LABELS = ('흐름방지선',)  # 흐름방지장치 처리기가 전선 편집 뒤에 다시 만듦


@dataclass
class WireRow:
    """편집기 표시용 전선 한 줄"""
    key: str
    label: str
    index: int
    offset: tuple
    end_point: tuple
    adjusted_angle: float | None
    topdown_angle: float | None
    status: str          # 'auto' | 'edited' | 'added' | 'removed'
    editable: bool


@dataclass
class SpanInfo:
    track: str
    pole: object
    next_pole: object
    wires: list          # [WireRow]

    @property
    def pos(self):
        return self.pole.pos

    @property
    def next_pos(self):
        return self.next_pole.pos


# ── 경간·전선 키 ─────────────────────────────────────
def wire_keys(wires):
    """[(전선키, SingleWire), ...] — 사용자 추가 전선은 edit_key 속성의 키를 쓴다"""
    seen = {}
    out = []
    for w in wires:
        key = getattr(w, 'edit_key', None)
        if key is None:
            k = seen.get(w.label, 0)
            seen[w.label] = k + 1
            key = f"{w.label}#{k}"
        out.append((key, w))
    return out


def span_key(track, pole, next_pole):
    return (track, pole.uid, next_pole.uid)


def spans_by_pos(poles):
    """{앞 전주 pos: (앞 전주, 뒤 전주)} — 실제로 이어진(next_pos 가 다음 전주) 경간만"""
    return {pole.pos: (pole, nxt) for pole, nxt in zip(poles, poles[1:]) if pole.next_pos == nxt.pos}


def _overrides(runner):
    if getattr(runner, 'wire_overrides', None) is None:
        runner.wire_overrides = {}
    return runner.wire_overrides


def _span(runner, track, pos):
    spans = spans_by_pos(runner.poledata.get(track, []))
    if pos not in spans:
        raise ValueError(f'{track} {pos} 에서 시작하는 경간이 없습니다.')
    return spans[pos]


def _wire_data(runner, track, pos):
    return next((w for w in runner.wire_data.get(track, []) if w.pos == pos), None)


def _is_editable(w):
    return w.label not in READ_ONLY_LABELS and w.station is None


# ── 조회 ────────────────────────────────────────────
def span_info(runner, track, pos):
    """경간의 전선 목록 (삭제한 자동 전선도 'removed' 로 포함). 경간이 없으면 None"""
    spans = spans_by_pos(runner.poledata.get(track, []))
    if pos not in spans:
        return None
    pole, nxt = spans[pos]
    edits = _overrides(runner).get(span_key(track, pole, nxt), {})
    rows = []
    wd = _wire_data(runner, track, pos)
    for key, w in wire_keys(wd.wires if wd else []):
        if key.startswith('added:'):
            status = 'added'
        else:
            status = 'edited' if key in edits else 'auto'
        rows.append(WireRow(key, w.label, w.index, tuple(w.offset), tuple(w.end_point),
                            w.adjusted_angle, w.topdown_angle, status, _is_editable(w)))
    for key, spec in edits.get(REMOVED, {}).items():
        rows.append(WireRow(key, spec['label'], spec['index'], (), (), None, None, 'removed', False))
    return SpanInfo(track, pole, nxt, rows)


# ── 편집 ────────────────────────────────────────────
def set_wire(runner, track, pos, key, start, end, link_neighbors=True):
    """전선 지지점 수정 (start/end = 시작점·끝점 (x 이격, 높이)).
    link_neighbors 면 같은 전선의 앞 경간 끝점·뒤 경간 시작점도 맞춘다. 반환: 수정한 경간들의 앞 전주 pos"""
    pole, nxt = _span(runner, track, pos)
    offset, end_point = tuple(map(float, start)), tuple(map(float, end))
    edits = _overrides(runner).setdefault(span_key(track, pole, nxt), {})
    current = {k: w for k, w in wire_keys(_wire_data(runner, track, pos).wires)}
    if key not in current:
        raise ValueError(f'전선 {key} 가 이 경간에 없습니다.')
    if not _is_editable(current[key]):
        raise ValueError(f'{current[key].label} 은(는) 자동 계산 전선이라 직접 수정할 수 없습니다.')
    old_offset, old_end = tuple(current[key].offset), tuple(current[key].end_point)

    if key.startswith('added:'):
        edits[ADDED][key].update(offset=list(offset), end_point=list(end_point))
        return [pos]
    edits[key] = {'offset': list(offset), 'end_point': list(end_point)}
    changed = [pos]
    if not link_neighbors:
        return changed
    if end_point != old_end:  # 뒤 경간 시작점
        neighbor = _neighbor_wire(runner, track, nxt.pos, key)
        if neighbor:
            _set_auto_edit(runner, track, nxt.pos, key, offset=end_point, end_point=tuple(neighbor.end_point))
            changed.append(nxt.pos)
    if offset != old_offset:  # 앞 경간 끝점
        prev = next((p for p, (_, n) in spans_by_pos(runner.poledata[track]).items() if n is pole), None)
        neighbor = _neighbor_wire(runner, track, prev, key) if prev is not None else None
        if neighbor:
            _set_auto_edit(runner, track, prev, key, offset=tuple(neighbor.offset), end_point=offset)
            changed.append(prev)
    return changed


def _neighbor_wire(runner, track, pos, key):
    if pos is None:
        return None
    wd = _wire_data(runner, track, pos)
    if wd is None:
        return None
    w = dict(wire_keys(wd.wires)).get(key)
    return w if w is not None and _is_editable(w) else None


def _set_auto_edit(runner, track, pos, key, offset, end_point):
    pole, nxt = _span(runner, track, pos)
    _overrides(runner).setdefault(span_key(track, pole, nxt), {})[key] = {
        'offset': list(map(float, offset)), 'end_point': list(map(float, end_point))}


def add_wire(runner, track, pos, label, index, start, end):
    """경간에 전선 추가 (start/end = 시작점·끝점 (x 이격, 높이)). 반환: 새 전선 키"""
    pole, nxt = _span(runner, track, pos)
    key = f"added:{uuid.uuid4().hex[:8]}"
    edits = _overrides(runner).setdefault(span_key(track, pole, nxt), {})
    edits.setdefault(ADDED, {})[key] = {'label': str(label), 'index': int(index),
                                        'offset': list(map(float, start)), 'end_point': list(map(float, end))}
    return key


def remove_wire(runner, track, pos, key):
    """전선 삭제 (자동 생성 전선은 삭제 표시, 추가 전선은 제거)"""
    pole, nxt = _span(runner, track, pos)
    edits = _overrides(runner).setdefault(span_key(track, pole, nxt), {})
    if key.startswith('added:'):
        edits.get(ADDED, {}).pop(key, None)
    else:
        w = dict(wire_keys(_wire_data(runner, track, pos).wires)).get(key)
        if w is None:
            raise ValueError(f'전선 {key} 가 이 경간에 없습니다.')
        if not _is_editable(w):
            raise ValueError(f'{w.label} 은(는) 자동 계산 전선이라 삭제할 수 없습니다.')
        edits.pop(key, None)
        edits.setdefault(REMOVED, {})[key] = {'label': w.label, 'index': w.index}
    _drop_if_empty(runner, span_key(track, pole, nxt))


def reset_wire(runner, track, pos, key):
    """전선 하나를 자동값으로 (지지점 수정 취소, 삭제 취소, 추가 전선은 제거)"""
    pole, nxt = _span(runner, track, pos)
    skey = span_key(track, pole, nxt)
    edits = _overrides(runner).get(skey)
    if not edits:
        return
    edits.pop(key, None)
    edits.get(REMOVED, {}).pop(key, None)
    edits.get(ADDED, {}).pop(key, None)
    _drop_if_empty(runner, skey)


def reset_span(runner, track, pos):
    """경간의 모든 편집 취소"""
    pole, nxt = _span(runner, track, pos)
    _overrides(runner).pop(span_key(track, pole, nxt), None)


def clear(runner, track, positions):
    """여러 경간(앞 전주 pos)의 편집 취소. 취소한 경간 수"""
    overrides = _overrides(runner)
    spans = spans_by_pos(runner.poledata[track])
    n = 0
    for pos in positions:
        if pos in spans and overrides.pop(span_key(track, *spans[pos]), None) is not None:
            n += 1
    return n


def _drop_if_empty(runner, skey):
    edits = _overrides(runner).get(skey)
    if edits is None:
        return
    for k in (REMOVED, ADDED):
        if k in edits and not edits[k]:
            del edits[k]
    if not edits:
        del _overrides(runner)[skey]


# ── 재계산 시 적용 (bveauto.xref.decats.core.model_rebuilder.rebuild 에서 호출) ─────────────
def apply(runner, alignment_for):
    """재생성된 wire_data 에 편집 내용 적용 + 각도 재계산. (적용 전선 수, 정리한 경간 수)"""
    overrides = _overrides(runner)
    if not overrides:
        return 0, 0
    processor = CommonWireProcessor()
    applied = 0
    for track, wires in runner.wire_data.items():
        spans = spans_by_pos(runner.poledata[track])
        alignment = alignment_for(runner, track)
        for wire in wires:
            if wire.pos not in spans:
                continue
            pole, nxt = spans[wire.pos]
            edits = overrides.get(span_key(track, pole, nxt))
            if not edits:
                continue
            pitch_angle = change_permile_to_degree(pole.pitch)

            def recompute(w):
                new = processor.run(alignment, w.index, pole.pos, nxt.pos, pole.z, nxt.z,
                                    start=w.offset, end=w.end_point, pitch_angle=pitch_angle, label=w.label)
                w.adjusted_angle, w.topdown_angle = new.adjusted_angle, new.topdown_angle

            removed = edits.get(REMOVED, {})
            kept = []
            for key, w in wire_keys(wire.wires):
                if key in removed:
                    applied += 1
                    continue
                edit = edits.get(key)
                if edit is not None and _is_editable(w):
                    w.offset, w.end_point = tuple(edit['offset']), tuple(edit['end_point'])
                    recompute(w)
                    applied += 1
                if removed:
                    w.edit_key = key  # 앞 전선이 삭제돼도 '라벨#순번' 키가 밀리지 않도록 원래 키 고정
                kept.append(w)
            for key, spec in edits.get(ADDED, {}).items():
                w = SingleWire(index=spec['index'], offset=tuple(spec['offset']),
                               end_point=tuple(spec['end_point']), label=spec['label'])
                w.edit_key = key
                recompute(w)
                kept.append(w)
                applied += 1
            wire.wires = kept

    # 삭제된 전주가 낀 경간의 편집 정리
    live = {t: {p.uid for p in poles} for t, poles in runner.poledata.items()}
    stale = [k for k in overrides if k[0] not in live or k[1] not in live[k[0]] or k[2] not in live[k[0]]]
    for k in stale:
        del overrides[k]
    return applied, len(stale)
