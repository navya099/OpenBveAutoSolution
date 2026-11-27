"""물량표 — 구성품 역할(bveauto.xref.decats.enums.component_role)로 전주 구성품·전선 수량 집계

    rows = bill_of_quantities(runner)          # [QuantityRow]
    write_bom_csv(rows, 'c:/temp/물량표.csv')  # 엑셀에서 열리는 UTF-8(BOM) CSV

구성품: (트랙, 분류, 역할, 형식, 오브젝트 이름, 인덱스) 별 개수
전선:   (트랙, '전선', 전선 이름, 구조물, 오브젝트 이름, 인덱스) 별 경간 수·총 길이(m, 경간 길이 합)
"""
import csv
from collections import defaultdict
from dataclasses import dataclass

from bveauto.xref.decats.enums.component_role import ComponentRole, iter_components

TRACK_NAME = {'main': '본선', 'sub': '상선'}
CATEGORY = {
    ComponentRole.MAST: '전주', ComponentRole.HANGER: '전주', ComponentRole.FOUNDATION: '전주',
    ComponentRole.BAND_BRACKET: '전주', ComponentRole.BAND_ARM: '전주', ComponentRole.BAND: '전주',
    ComponentRole.BRACKET: '브래킷', ComponentRole.BRACKET_F: '브래킷', ComponentRole.BRACKET_AJ: '브래킷',
    ComponentRole.FIT_CW: '금구', ComponentRole.FIT_MW: '금구', ComponentRole.FIT_STEADY: '금구',
}
ROLE_ORDER = {role: i for i, role in enumerate(ComponentRole)}


@dataclass
class QuantityRow:
    track: str
    category: str       # 전주 · 브래킷 · 금구 · 설비 · 전선
    role: str
    spec: str
    name: str
    index: int | None
    count: int
    length: float | None = None   # 전선 총 길이 (m)


def _name(obj):
    return str(getattr(obj, 'name', None) or getattr(obj, 'bracket_name', None) or getattr(obj, 'label', None) or '')


def bill_of_quantities(runner, include_wires=True):
    """전주 구성품·전선 물량 (트랙·분류·역할 순). 인덱스가 없는 자리(출력되지 않는 구성품)는 제외"""
    rows = []
    for track, poles in (runner.poledata or {}).items():
        counts = defaultdict(int)
        for pole in poles:
            for _, obj in iter_components(pole):
                if getattr(obj, 'index', None) is None or _name(obj).strip().lower() == 'null':
                    continue    # 인덱스 없는 자리, BVE 빈 오브젝트(null)
                role = getattr(obj, 'role', '') or ComponentRole.OTHER
                counts[(str(role), str(getattr(obj, 'spec', '') or ''), _name(obj), obj.index)] += 1
        track_name = TRACK_NAME.get(track, track)
        for (role, spec, name, index), n in counts.items():
            category = CATEGORY.get(ComponentRole.parse(role), '설비')
            rows.append(QuantityRow(track_name, category, role, spec, name, index, n))
        if include_wires:
            rows += _wire_rows(runner, track, track_name)
    order = {'전주': 0, '브래킷': 1, '금구': 2, '설비': 3, '전선': 4}
    rows.sort(key=lambda r: (r.track != '본선', r.track, order.get(r.category, 9),
                             ROLE_ORDER.get(ComponentRole.parse(r.role), 99), r.role, r.spec, r.name,
                             r.index if r.index is not None else -1))
    return rows


def _wire_rows(runner, track, track_name):
    poles = {p.pos: p for p in runner.poledata.get(track, [])}
    groups = defaultdict(lambda: [0, 0.0])
    for wd in (runner.wire_data or {}).get(track, []):
        pole = poles.get(wd.pos)
        if pole is None or pole.next_pos is None:
            continue
        for w in wd.wires:
            if w.index is None:
                continue
            start = w.station if w.station is not None else pole.pos
            key = (str(w.label), pole.structure, w.index)
            groups[key][0] += 1
            groups[key][1] += pole.next_pos - start
    lib = getattr(runner, 'idxlib', None)
    rows = []
    for (label, structure, index), (n, length) in groups.items():
        name = (lib.get_name(index) if lib is not None and hasattr(lib, 'get_name') else None) or ''
        rows.append(QuantityRow(track_name, '전선', label, structure, name, index, n, round(length, 3)))
    return rows


def write_bom_csv(rows, path):
    """물량표 CSV (엑셀용 UTF-8 BOM)"""
    with open(path, 'w', encoding='utf-8-sig', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(['트랙', '분류', '역할', '형식', '오브젝트', '인덱스', '수량', '길이(m)'])
        for r in rows:
            writer.writerow([r.track, r.category, r.role, r.spec, r.name, '' if r.index is None else r.index,
                             r.count, '' if r.length is None else r.length])
    return path
