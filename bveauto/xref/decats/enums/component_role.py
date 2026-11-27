"""전주 구성품 역할 — BVE 오브젝트 이름과 별개로 '무엇인지'를 기록 (도면 표기·물량표·다른 출력용)

구성품(Mast·MastBase·MastAccessory·BracketDATA·FittingDATA·EquipmentDATA)마다
    role: ComponentRole 값 (무엇인지)
    spec: 형식·위치 등 세부 (브래킷 I/O, 곡선당김금구 L/R, 기둥 P10/P12/H250, 조가선 지지금구 무효인상용 …)
자동 배치가 만들 때 기록하고, 구버전 데이터·사용자가 추가한 구성품은 infer_role 로 이름·종류에서 추정한다.
"""
from bveauto.xref.decats.enums.section_type import _StrEnum


class ComponentRole(_StrEnum):
    # 기둥
    MAST = '기둥'
    HANGER = '하수강'                    # 터널 하수강(기둥 대신 / 브래킷을 다는 H형강)
    FOUNDATION = '기초'
    BAND_BRACKET = '가동브래킷용밴드'
    BAND_ARM = '완철용밴드'
    BAND = '기타밴드'
    # 브래킷
    BRACKET = '가동브래킷'               # 일반 개소 (spec I/O)
    BRACKET_F = 'F형브래킷'              # 무효선 인상 (에어조인트·에어섹션)
    BRACKET_AJ = 'AJ형브래킷'            # 평행 개소 (spec I/O)
    # 금구
    FIT_CW = '전차선지지금구'
    FIT_MW = '조가선지지금구'            # spec 무효인상용/에어조인트용
    FIT_STEADY = '곡선당김금구'          # spec L/R
    # 설비
    FEEDER = '급전선설비'
    SPREADER = '평행틀'
    TENSION = '장력장치'
    DEAD_END = '인류장치'
    GUY = '지선'
    ANTICREEP = '흐름방지장치'
    ANTICREEP_GUY = '봉강지선'
    OTHER = '기타'


# 설비 종류(EquipmentDATA.type) ↔ 역할
EQUIPMENT_TYPE_ROLE = {
    '급전선설비': ComponentRole.FEEDER, '평행틀': ComponentRole.SPREADER, '장력장치': ComponentRole.TENSION,
    '지선설비': ComponentRole.GUY, '인류장치': ComponentRole.DEAD_END, '흐름방지장치': ComponentRole.ANTICREEP,
    '봉강지선': ComponentRole.ANTICREEP_GUY,
}


def known_indices(dataprocessor):
    """데이터셋에서 인덱스로 알 수 있는 역할 {구성품 종류: {인덱스: (역할, spec)}}
    (이름이 인덱스 라이브러리에 없을 때 추정용: 금구, 밴드, 기둥/하수강)"""
    fits, accs = {}, {}
    try:
        cw, mw, steady = dataprocessor.get_fittings()
    except Exception:  # noqa: BLE001 - 데이터셋이 없거나 형식이 다름
        cw, mw, steady = None, None, None
    if isinstance(steady, dict):
        for sides in steady.values():
            for side, idx in (sides or {}).items():
                fits.setdefault(idx, (ComponentRole.FIT_STEADY, side))
    if isinstance(mw, dict):
        keys = {}
        for key, idx in mw.items():
            keys.setdefault(idx, []).append(key)
        for idx, names in keys.items():   # 같은 오브젝트를 여러 용도에 쓰면 용도(spec)는 정하지 않음
            fits.setdefault(idx, (ComponentRole.FIT_MW, names[0] if len(names) == 1 else ''))
    if cw is not None:
        fits.setdefault(cw, (ComponentRole.FIT_CW, ''))
    try:
        bands = dataprocessor.bveauto.xref.decats.dataset['mast']['band']['index']
    except Exception:  # noqa: BLE001
        bands = {}
    roles = {'가동브래킷용': ComponentRole.BAND_BRACKET, '완철용': ComponentRole.BAND_ARM}
    for band_type, by_size in (bands or {}).items():
        role = roles.get(band_type, ComponentRole.BAND)
        for value in (by_size or {}).values():
            for spec, idx in (value.items() if isinstance(value, dict) else [('', value)]):
                accs.setdefault(idx, (role, spec if role != ComponentRole.BAND else band_type))
    masts = {}
    try:
        mast_index = dataprocessor.bveauto.xref.decats.dataset['mast']['index']
    except Exception:  # noqa: BLE001
        mast_index = {}
    for by_structure in (mast_index or {}).values():           # 일반개소·평행개소 → 구조물별 기둥 인덱스
        for structure, idx in (by_structure or {}).items():
            if structure == '터널':
                masts[idx] = (ComponentRole.HANGER, '')
                fits.setdefault(idx, (ComponentRole.HANGER, ''))   # 터널 평행 개소: 브래킷에 단 하수강
            else:
                masts.setdefault(idx, (ComponentRole.MAST, ''))
    return {'fit': fits, 'acc': accs, 'mast': masts}


def infer_role(kind, obj, known=None):
    """역할이 없는 구성품(구버전 데이터·사용자 추가)의 (역할, spec) 추정.
    kind: 'mast' | 'base' | 'acc' | 'br' | 'fit' | 'eq' (bveauto.xref.decats.core.pole.pole_edit 구성품 종류)
    known: known_indices(데이터셋) — 금구는 인덱스로 먼저 찾고, 없으면 이름으로"""
    table = (known or {}).get(kind) or {}
    if getattr(obj, 'index', None) in table:
        return table[obj.index]
    name = str(getattr(obj, 'name', None) or getattr(obj, 'bracket_name', None) or getattr(obj, 'label', None) or '')
    if kind == 'mast':
        return (ComponentRole.HANGER if '하수강' in name else ComponentRole.MAST), ''
    if kind == 'base':
        return ComponentRole.FOUNDATION, ''
    if kind == 'acc':
        if '가동브래킷' in name:
            return ComponentRole.BAND_BRACKET, ''
        if '완철' in name:
            return ComponentRole.BAND_ARM, ''
        return ComponentRole.BAND, ''
    if kind == 'br':
        bracket_type = str(getattr(obj, 'bracket_type', '') or '')
        if bracket_type == 'F':
            return ComponentRole.BRACKET_F, ''
        if bracket_type == 'AJ':
            upper = name.upper()
            return ComponentRole.BRACKET_AJ, ('O' if upper.endswith('-O') or '_O' in upper else 'I')
        return ComponentRole.BRACKET, bracket_type
    if kind == 'fit':
        if '곡선당김' in name:
            return ComponentRole.FIT_STEADY, ('R' if name.rstrip().endswith('R') else 'L')
        if '조가선' in name:
            return ComponentRole.FIT_MW, ('에어조인트용' if '에어조인트' in name else '무효인상용' if '무효' in name else '')
        if '전차선' in name:
            return ComponentRole.FIT_CW, ''
        if '하수강' in name:
            return ComponentRole.HANGER, ''
        return ComponentRole.OTHER, ''
    if kind == 'eq':
        return EQUIPMENT_TYPE_ROLE.get(getattr(obj, 'type', ''), ComponentRole.OTHER), ''
    return ComponentRole.OTHER, ''


def iter_components(pole):
    """전주 구성품 [(kind, 객체)] — 기둥·기초·밴드·설비 (복주 두 번째 전주 포함), 브래킷·금구"""
    out = []
    for holder in [pole] + ([pole.twin] if getattr(pole, 'twin', None) is not None else []):
        mast = holder.mast
        if mast is not None:
            out.append(('mast', mast))
            if mast.base is not None:
                out.append(('base', mast.base))
            out += [('acc', a) for a in mast.accessories or [] if a is not None]
        out += [('eq', e) for e in holder.equipments or [] if e is not None]
    for bracket in pole.brackets or []:
        out.append(('br', bracket))
        out += [('fit', f) for f in bracket.fittings or [] if f is not None]
    return out


def fill_roles(pole, known=None):
    """역할이 비어 있는 구성품에 추정 역할 기록 (구버전 데이터). 채운 개수"""
    filled = 0
    for kind, obj in iter_components(pole):
        if not getattr(obj, 'role', ''):
            obj.role, spec = infer_role(kind, obj, known)
            if not getattr(obj, 'spec', ''):
                obj.spec = spec
            filled += 1
    return filled
