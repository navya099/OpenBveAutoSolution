"""전주 상세 편집 — 전주 구성품(기둥·기초·밴드·브래킷·피팅·장비) 조회·수정·추가·삭제 (GUI 없이 동작)

구성품 키:
    'mast'                 기둥            'base'          기초
    'acc:{i}'              기둥 부속(밴드)   'eq:{i}'        장비 (급전선설비, 평행틀 등)
    'br:{i}'               브래킷           'br:{i}/fit:{j}' 브래킷의 피팅
    'twin/mast' 'twin/base' 'twin/acc:{i}' 'twin/eq:{i}'  복주 두 번째 전주의 기둥·기초·부속·장비
    (복주 브래킷은 'br:{i}' 그대로, BracketDATA.on_twin 으로 앞/뒤 전주 구분)
흐름방지장치·봉강지선은 흐름방지 처리기가 재계산마다 다시 만들므로 읽기 전용이다.

오브젝트 이름 ↔ 인덱스는 인덱스 라이브러리(runner.idxlib)로 맞춘다. 이름만 주면 인덱스를 찾고,
인덱스만 주면 이름을 찾는다. 라이브러리에 없으면 ValueError (인덱스 None 으로 저장되지 않도록).

편집 함수는 전주 데이터만 바꾼다. 호출 측에서 rebuild(runner) 후 MODEL_CHANGED 로 화면을 갱신한다.
건식게이지 변경은 게이지 위치(x = ±게이지)에 있던 구성품만 새 게이지로 옮기고 나머지 편집은 유지한다.
'자동 구성으로 되돌리기'는 그 전주의 구성품을 자동 배치 규칙으로 다시 만든다.
"""
from dataclasses import dataclass

from bveauto.xref.decats.core.airjoint.airjoint_processor import AirJointProcessor
from bveauto.xref.decats.core.airsection.airsection_processor import AirSectionProcessor
from bveauto.xref.decats.core.bracket.bracket_data import BracketDATA
from bveauto.xref.decats.core.bracket.fitting_data import FittingDATA
from bveauto.xref.decats.core.equipment.equipment_data import EquipmentDATA
from bveauto.xref.decats.core.mast.base.mast_base import MastBase
from bveauto.xref.decats.core.mast.mast_accessory.mast_accessory import MastAccessory
from bveauto.xref.decats.core.pole.normal_section_processor import NormalSectionProcessor
from bveauto.xref.decats.core.pole.pole_geometry import place_on_alignment, track_lists
from bveauto.xref.decats.core.pole.tunnel_section_processor import TunnelSectionProcessor
from bveauto.xref.decats.enums.component_role import ComponentRole, infer_role, known_indices
from bveauto.xref.decats.enums.section_type import AIRSECTION_SINGLE, SectionType

READ_ONLY_EQUIPMENT_TYPES = ('흐름방지장치', '봉강지선')
KIND_TEXT = {'mast': '기둥', 'base': '기초', 'acc': '밴드/부속', 'br': '브래킷', 'fit': '피팅', 'eq': '장비'}
ADDABLE_KINDS = ('br', 'fit', 'eq', 'acc')


@dataclass
class ComponentRow:
    key: str
    kind: str            # 'mast' | 'base' | 'acc' | 'br' | 'fit' | 'eq'
    name: str
    index: int | None
    offset: tuple
    rotation: float
    detail: str          # 장비 종류 등
    editable: bool
    parent: str | None = None   # 피팅의 브래킷 키
    role: str = ''              # 구성품 역할 (bveauto.xref.decats.enums.component_role)
    spec: str = ''              # 형식·위치 (I/O, L/R …)

    @property
    def role_text(self):
        return f'{self.role} {self.spec}'.strip() if self.role else ''


# ── 조회 ────────────────────────────────────────────
def _name_of(obj):
    return getattr(obj, 'bracket_name', None) or getattr(obj, 'name', None) or getattr(obj, 'label', '') or ''


TWIN = 'twin/'   # 복주 두 번째 전주 구성품 키 접두어
TWIN_TEXT = ('앞 전주', '뒤 전주')


def _role(obj):
    return {'role': str(getattr(obj, 'role', '') or ''), 'spec': str(getattr(obj, 'spec', '') or '')}


def _mast_rows(mast, prefix='', detail=''):
    rows = []
    if mast is None:
        return rows
    rows.append(ComponentRow(f'{prefix}mast', 'mast', mast.name, mast.index, tuple(_xy(mast.offset)), mast.rotation,
                             detail, True, **_role(mast)))
    if mast.base is not None:
        b = mast.base
        rows.append(ComponentRow(f'{prefix}base', 'base', b.name, b.index, tuple(_xy(b.offset)), b.rotation, detail,
                                 True, **_role(b)))
    for i, acc in enumerate(mast.accessories or []):
        rows.append(ComponentRow(f'{prefix}acc:{i}', 'acc', acc.name, acc.index, tuple(_xy(acc.offset)), acc.rotation,
                                 detail, True, **_role(acc)))
    return rows


def components(pole):
    """전주 구성품 목록 (표시 순서: 기둥, 기초, 부속, 브래킷(+피팅), 장비, 복주 두 번째 전주의 기둥·장비)"""
    twin = getattr(pole, 'twin', None)
    rows = _mast_rows(pole.mast, detail=TWIN_TEXT[0] if twin else '')
    for i, br in enumerate(pole.brackets):
        key = f'br:{i}'
        detail = str(br.bracket_type or '')
        if twin is not None:
            detail = f'{detail} ({TWIN_TEXT[1] if getattr(br, "on_twin", False) else TWIN_TEXT[0]})'.strip()
        rows.append(ComponentRow(key, 'br', br.bracket_name, br.index, tuple(_xy(br.offset)), br.rotation,
                                 detail, True, **_role(br)))
        for j, fit in enumerate(br.fittings):
            rows.append(ComponentRow(f'{key}/fit:{j}', 'fit', fit.label, fit.index, tuple(_xy(fit.offset)),
                                     fit.rotation, '', True, parent=key, **_role(fit)))
    for i, eq in enumerate(pole.equipments):
        rows.append(ComponentRow(f'eq:{i}', 'eq', eq.name, eq.index, tuple(_xy(eq.offset)), eq.rotation, eq.type,
                                 eq.type not in READ_ONLY_EQUIPMENT_TYPES, **_role(eq)))
    if twin is not None:
        rows += _mast_rows(twin.mast, TWIN, TWIN_TEXT[1])
        for i, eq in enumerate(twin.equipments):
            rows.append(ComponentRow(f'{TWIN}eq:{i}', 'eq', eq.name, eq.index, tuple(_xy(eq.offset)), eq.rotation,
                                     f'{eq.type} ({TWIN_TEXT[1]})', eq.type not in READ_ONLY_EQUIPMENT_TYPES,
                                     **_role(eq)))
    return rows


def _xy(offset):
    """구버전 데이터에서 offset 이 숫자 하나로 저장된 경우 보정 (기둥 offset=gauge 버그)"""
    if isinstance(offset, (int, float)):
        return (float(offset), 0.0)
    return tuple(offset)


def _holder(pole, key):
    """키 → (기둥·장비를 가진 객체(전주 또는 복주 두 번째 전주), 접두어를 뗀 키)"""
    if key.startswith(TWIN):
        if getattr(pole, 'twin', None) is None:
            raise KeyError(key)
        return pole.twin, key[len(TWIN):]
    return pole, key


def _get(pole, key):
    """키 → 구성품 객체"""
    holder, key = _holder(pole, key)
    if holder is not pole:
        if key == 'mast':
            return holder.mast
        if key == 'base':
            return holder.mast.base if holder.mast else None
        kind, _, rest = key.partition(':')
        if kind == 'acc':
            return (holder.mast.accessories or [])[int(rest)]
        if kind == 'eq':
            return holder.equipments[int(rest)]
        raise KeyError(key)
    if key == 'mast':
        return pole.mast
    if key == 'base':
        return pole.mast.base if pole.mast else None
    kind, _, rest = key.partition(':')
    if kind == 'acc':
        return (pole.mast.accessories or [])[int(rest)]
    if kind == 'eq':
        return pole.equipments[int(rest)]
    if kind == 'br':
        if '/fit:' in rest:
            b, f = rest.split('/fit:')
            return pole.brackets[int(b)].fittings[int(f)]
        return pole.brackets[int(rest)]
    raise KeyError(key)


# ── 이름 ↔ 인덱스 ──────────────────────────────────────
def resolve(idxlib, name=None, index=None):
    """(이름, 인덱스). 하나만 주면 라이브러리에서 나머지를 찾는다. 찾지 못하면 ValueError"""
    name = (str(name).strip() if name is not None else '').removesuffix('.csv').removesuffix('.CSV')
    if index is not None and str(index).strip() != '':
        index = int(index)
        if not name:
            found = idxlib.get_name(index)
            if found is None:
                raise ValueError(f'인덱스 {index} 가 인덱스 라이브러리에 없습니다.')
            name = found
        return name, index
    if not name:
        raise ValueError('오브젝트 이름이나 인덱스를 입력하세요.')
    found = idxlib.get_index(name)
    if found is None:
        raise ValueError(f"'{name}' 이(가) 인덱스 라이브러리에 없습니다. 인덱스를 직접 입력하세요.")
    return name, int(found)


def search(idxlib, keyword, limit=200):
    """인덱스 라이브러리에서 이름 검색 → [(이름, 인덱스)]"""
    keyword = (keyword or '').strip()
    if not keyword or idxlib is None:
        return []
    df = idxlib.search(keyword)
    return [(str(r['파일명']), int(r['인덱스'])) for _, r in df.head(limit).iterrows()]


# ── 수정 ────────────────────────────────────────────
def set_component(runner, pole, key, name=None, index=None, offset=None, rotation=None):
    """구성품 이름/인덱스·위치·회전 수정. 값 검증 후에만 바꾼다"""
    obj = _get(pole, key)
    if obj is None:
        raise ValueError(f'{key} 구성품이 없습니다.')
    if isinstance(obj, EquipmentDATA) and obj.type in READ_ONLY_EQUIPMENT_TYPES:
        raise ValueError(f'{obj.type} 는 흐름방지 처리에서 자동으로 만들어져 직접 수정할 수 없습니다.')
    new_name, new_index = None, None
    if name is not None or index is not None:
        new_name, new_index = resolve(runner.idxlib, name, index)
    new_offset = None if offset is None else (float(offset[0]), float(offset[1]))
    new_rotation = None if rotation is None else float(rotation)

    if new_name is not None:
        obj.index = new_index
        if isinstance(obj, BracketDATA):
            obj.bracket_name = new_name
        elif isinstance(obj, FittingDATA):
            obj.label = new_name
        else:
            obj.name = new_name
    if new_offset is not None:
        obj.offset = new_offset
    if new_rotation is not None:
        obj.rotation = new_rotation


def add_component(runner, pole, kind, name=None, index=None, offset=(0.0, 0.0), rotation=0.0,
                  parent=None, equipment_type='기타장비'):
    """구성품 추가. 반환: 새 구성품 키"""
    if kind not in ADDABLE_KINDS:
        raise ValueError(f'추가할 수 없는 종류입니다: {kind}')
    name, index = resolve(runner.idxlib, name, index)
    offset = (float(offset[0]), float(offset[1]))
    rotation = float(rotation)
    on_twin = parent is not None and parent.startswith(TWIN.rstrip('/')) and getattr(pole, 'twin', None) is not None
    if kind == 'br':
        bracket = BracketDATA(bracket_type=pole.base_type, index=index, offset=offset, rotation=rotation,
                              bracket_name=name, on_twin=on_twin)
        bracket.role, bracket.spec = infer_role('br', bracket)
        pole.brackets.append(bracket)
        return f'br:{len(pole.brackets) - 1}'
    if kind == 'fit':
        if not parent or not parent.startswith('br:') or '/fit:' in parent:
            raise ValueError('피팅을 추가할 브래킷을 선택하세요.')
        br = _get(pole, parent)
        fitting = FittingDATA(index=index, offset=offset, rotation=rotation, label=name)
        fitting.role, fitting.spec = infer_role('fit', fitting, known_indices(runner.dataprocessor)
                                                if getattr(runner, 'dataprocessor', None) is not None else None)
        br.fittings.append(fitting)
        return f'{parent}/fit:{len(br.fittings) - 1}'
    holder, prefix = pole, ''
    if parent is not None and parent.startswith(TWIN.rstrip('/')):   # 'twin' 또는 'twin/...' : 복주 두 번째 전주
        if getattr(pole, 'twin', None) is None:
            raise ValueError('복주 전주가 아닙니다.')
        holder, prefix = pole.twin, TWIN
    if kind == 'eq':
        if equipment_type in READ_ONLY_EQUIPMENT_TYPES:
            raise ValueError(f'{equipment_type} 는 흐름방지장치 추가 기능으로 설치하세요.')
        equipment = EquipmentDATA(name=name, index=index, offset=offset, rotation=rotation,
                                  type=equipment_type or '기타장비')
        equipment.role, equipment.spec = infer_role('eq', equipment)
        holder.equipments.append(equipment)
        return f'{prefix}eq:{len(holder.equipments) - 1}'
    # acc
    if holder.mast is None:
        raise ValueError('기둥이 없는 전주에는 부속을 추가할 수 없습니다.')
    if holder.mast.accessories is None:
        holder.mast.accessories = []
    accessory = MastAccessory(name=name, index=index, offset=offset, rotation=rotation)
    accessory.role, accessory.spec = infer_role('acc', accessory)
    holder.mast.accessories.append(accessory)
    return f'{prefix}acc:{len(holder.mast.accessories) - 1}'


def remove_component(pole, key):
    """구성품 삭제 (기둥은 삭제 불가, 기초는 없음으로)"""
    obj = _get(pole, key)
    holder, key = _holder(pole, key)
    if key == 'mast':
        raise ValueError('기둥은 삭제할 수 없습니다. 다른 기둥으로 바꾸세요.')
    if key == 'base':
        if holder.mast is not None:
            holder.mast.base = None
        return
    if isinstance(obj, EquipmentDATA) and obj.type in READ_ONLY_EQUIPMENT_TYPES:
        raise ValueError(f'{obj.type} 는 흐름방지장치 삭제 기능으로 제거하세요.')
    kind, _, rest = key.partition(':')
    if kind == 'acc':
        holder.mast.accessories.pop(int(rest))
    elif kind == 'eq':
        holder.equipments.pop(int(rest))
    elif '/fit:' in rest:
        b, f = rest.split('/fit:')
        pole.brackets[int(b)].fittings.pop(int(f))
    else:
        pole.brackets.pop(int(rest))


def set_base(runner, pole, name=None, index=None, twin=False):
    """기초 지정 (없던 기초도 추가). twin=True: 복주 두 번째 전주의 기초"""
    holder = pole
    if twin:
        if getattr(pole, 'twin', None) is None:
            raise ValueError('복주 전주가 아닙니다.')
        holder = pole.twin
    if holder.mast is None:
        raise ValueError('기둥이 없는 전주입니다.')
    name, index = resolve(runner.idxlib, name, index)
    if holder.mast.base is None:
        holder.mast.base = MastBase(name=name, index=index, offset=(_xy(holder.mast.offset)[0], 0.0),
                                    rotation=holder.mast.rotation, role=ComponentRole.FOUNDATION)
    else:
        holder.mast.base.name, holder.mast.base.index = name, index


def component_pole(pole, key):
    """구성품이 달린 전주: 0 = 주(앞) 전주, 1 = 복주 두 번째(뒤) 전주"""
    if key.startswith(TWIN):
        return 1
    if key.startswith('br:') and getattr(pole, 'twin', None) is not None:
        b = int(key.split(':')[1].split('/')[0])
        return 1 if getattr(pole.brackets[b], 'on_twin', False) else 0
    return 0


# ── 자동 구성 재생성 (건식게이지 변경, 되돌리기) ─────────────────
def regenerate(runner, pole, alignment):
    """전주 구성품을 현재 구간·구조물·건식게이지로 자동 배치 규칙에 따라 다시 만든다 (수동 편집 내용은 사라짐)"""
    section = SectionType.parse(pole.section)
    # 구간 종류 등록표에서 이 전주가 속한 구간의 처리 방식 사용 (새 에어조인트 타입 등)
    from bveauto.xref.decats.core.section_edit import kind_of_pole
    kind = kind_of_pole(runner, pole) if section is not None else None
    pole.brackets, pole.mast, pole.equipments = [], None, []
    pole.twin = None
    if section is None:
        processor = TunnelSectionProcessor if pole.structure == '터널' else NormalSectionProcessor
        processor.process(pole, runner.dataprocessor, runner.idxlib)
    elif kind is not None and kind.processor is not None:
        kind.processor(runner, pole, alignment)
    elif section.is_airjoint:
        AirJointProcessor.process(pole, alignment, runner.dataprocessor, runner.idxlib)
    else:
        mode = 'single' if section in AIRSECTION_SINGLE else 'double'
        AirSectionProcessor.process(pole, alignment, runner.dataprocessor, runner.idxlib, mode=mode)


GAUGE_ANGLE_EQUIPMENT_TYPES = ('장력장치',)  # 회전각이 게이지로 계산되는 장비


def set_gauge(runner, pole, gauge, alignment):
    """건식게이지 변경: 전주 좌표 갱신 + 게이지를 따르는 구성품의 x 이동 (편집 내용 유지).

    자동 배치에서 기둥·기초·밴드·급전선설비·장력장치·지선·평행틀 등은 x = 게이지(반대편 설비는 −게이지)에 놓인다.
    x 가 ±이전 게이지인 구성품만 ±새 게이지로 옮기고 이름·인덱스·높이·회전·추가한 구성품은 그대로 둔다.
    반환: (옮긴 구성품 수, 안내 문구 목록)
    """
    gauge = float(gauge)
    if gauge == 0:
        raise ValueError('건식게이지는 0 이 될 수 없습니다.')
    if (gauge < 0) != (pole.gauge < 0):
        raise ValueError('건식게이지 부호(전주 좌/우)는 바꿀 수 없습니다. 값의 크기만 바꾸세요.')
    old = float(pole.gauge)
    moved = 0
    for r in components(pole):
        x, y = r.offset
        if abs(x - old) < 1e-9:
            new_x = gauge
        elif abs(x + old) < 1e-9:
            new_x = -gauge
        else:
            continue
        obj = _get(pole, r.key)
        obj.offset = (new_x, y)
        moved += 1
    pole.gauge = gauge
    place_on_alignment(pole, alignment, *track_lists(runner, pole.track))

    notices = []
    if any(e.type in GAUGE_ANGLE_EQUIPMENT_TYPES for e in pole.equipments):
        notices.append('장력장치 회전각은 게이지로 계산된 값이라 이전 값 그대로입니다. '
                       '정확히 맞추려면 "자동 구성으로 되돌리기"를 쓰세요.')
    return moved, notices


# ── 전주 기본 속성 (표 셀 편집·배치도 이동) ───────────────────
BASE_TYPES = ('I', 'O', 'F')


def _track_poles(runner, pole):
    poles = runner.poledata.get(pole.track, [])
    idx = next((i for i, p in enumerate(poles) if p is pole), None)
    if idx is None:
        raise ValueError(f'{pole.post_number}: 전주 목록에 없는 전주입니다.')
    return poles, idx


def rename(runner, pole, post_number):
    """전주번호 변경 (같은 트랙에서 중복 불가)"""
    post_number = str(post_number).strip()
    if not post_number:
        raise ValueError('전주번호를 입력하세요.')
    poles, _ = _track_poles(runner, pole)
    if any(p is not pole and p.post_number == post_number for p in poles):
        raise ValueError(f'같은 트랙에 전주번호 {post_number} 가 이미 있습니다.')
    pole.post_number = post_number


def _check_span(runner, span, structure, label):
    try:
        runner.dataprocessor.get_contact_wire_span(span, structure)
    except ValueError:
        raise ValueError(f'{label} 경간 {span:g}m 가 {structure} 경간표에 없습니다.') from None


def move_pole(runner, pole, new_pos, alignment):
    """전주 측점 이동. 앞뒤 전주 사이, 앞뒤 경간이 경간표에 있어야 함, 일반개소만.
    좌표·고도·곡선·구배·구조물을 새 위치로 갱신하고 구성품 편집은 유지한다.
    구조물(토공/교량/터널)이 바뀌면 그 구조물의 건식게이지로 구성품을 자동 재생성한다.
    반환: 안내 문구 목록"""
    from bveauto.xref.decats.core.alignment.alignment import as_alignment
    from bveauto.xref.decats.core.structure.define_structure import isbridge_tunnel

    new_pos = float(new_pos)
    new_pos = int(new_pos) if new_pos.is_integer() else new_pos
    if pole.section is not None:
        raise ValueError(f'{pole.post_number}: {pole.section} 전주는 이동할 수 없습니다 (일반개소만 이동 가능).')
    poles, idx = _track_poles(runner, pole)
    prev_pole = poles[idx - 1] if idx > 0 else None
    next_pole = poles[idx + 1] if idx + 1 < len(poles) else None
    if prev_pole is not None and new_pos <= prev_pole.pos:
        raise ValueError(f'앞 전주({prev_pole.post_number}, {prev_pole.pos}m)보다 뒤여야 합니다.')
    if next_pole is not None and new_pos >= next_pole.pos:
        raise ValueError(f'뒤 전주({next_pole.post_number}, {next_pole.pos}m)보다 앞이어야 합니다.')
    al = as_alignment(alignment)
    if not (al.start <= new_pos <= al.end):
        raise ValueError(f'선형 범위({al.start:g}~{al.end:g}m) 밖입니다.')
    new_structure = isbridge_tunnel(new_pos, runner.structure_list)
    if prev_pole is not None and prev_pole.next_pos == pole.pos:
        _check_span(runner, new_pos - prev_pole.pos, prev_pole.structure, '앞')
    if next_pole is not None and pole.next_pos == next_pole.pos:
        _check_span(runner, next_pole.pos - new_pos, new_structure, '뒤')

    # 검증 통과 → 반영
    notices = []
    old_structure = pole.structure
    pole.pos = new_pos
    pole.structure = new_structure
    curves, pitches = track_lists(runner, pole.track)
    if new_structure != old_structure:
        sign = -1 if pole.gauge < 0 else 1
        pole.gauge = runner.dataprocessor.get_pole_gauge(new_structure) * sign
        regenerate(runner, pole, al)
        notices.append(f'구조물이 {old_structure} → {new_structure} 로 바뀌어 건식게이지({pole.gauge})와 '
                       '구성품을 자동으로 다시 만들었습니다.')
    place_on_alignment(pole, al, curves, pitches)   # 좌표·계획고·곡선·구배 (게이지가 바뀐 뒤)
    # 앞뒤 전주와의 연결(next_pos·span 등)을 바로 맞춤 (전체 재계산 전에도 데이터가 일관되도록)
    from bveauto.xref.decats.core.pole.pole_updator import PoleUpdator
    PoleUpdator.update_all(poles, al)   # 트랙 전체를 다시 이음 (일부만 넘기면 끝 전주 연결이 끊김)
    if prev_pole is not None and prev_pole.next_pos == pole.pos:
        notices += filter(None, [span_limit_notice(runner, prev_pole.pos, pole.pos, '앞')])
    if next_pole is not None and pole.next_pos == next_pole.pos:
        notices += filter(None, [span_limit_notice(runner, pole.pos, next_pole.pos, '뒤')])
    return notices


def span_limit_notice(runner, start_pos, end_pos, label=''):
    """경간이 설계 최대 경간(설계속도·곡선 반경·터널, 경간이 걸치는 시작·안쪽 블록·끝 중 엄격한 값)을 넘으면
    안내 문구, 아니면 None. 경간표에 있는 경간이면 전선은 만들어지므로 거부하지 않고 알리기만 한다."""
    from bveauto.xref.decats.utils.comom_util import get_max_span_between
    speed = getattr(runner, 'designspeed', None)
    try:
        limit = get_max_span_between(start_pos, end_pos, speed, runner.curvelist, runner.structure_list)
    except ValueError:
        return None  # 최대 경간 기준이 없는 설계속도
    span = end_pos - start_pos
    if span <= limit:
        return None
    return (f'{label + " " if label else ""}경간 {span:g}m 가 설계 최대 경간 {limit}m 를 넘습니다 '
            f'(설계속도 {speed}km/h, 곡선 반경·터널 기준).')


def _section_containing(runner, track, pos, inclusive=True):
    """pos 가 걸치는 에어조인트·에어섹션 구간 (inclusive=False 면 구간 시작·끝 전주 사이 안쪽만). 없으면 None"""
    from bveauto.xref.decats.core.section_edit import find_sections
    for inst in find_sections(runner, track):
        if inst.kind is not None and inst.kind.category == 'flowstop':
            continue
        lo, hi = inst.start_pos, inst.end_pos
        if (lo <= pos <= hi) if inclusive else (lo < pos < hi):
            return inst
    return None


def add_pole(runner, track, pos, post_number, gauge, base_type, alignment):
    """일반개소 전주 추가 (구간은 구간 편집기에서). 검증 후에만 추가.
    거부: 빈/중복 전주번호, 같은 측점 전주, 선형 범위 밖, 건식게이지 0, 기본 타입 오류,
          에어조인트·에어섹션 구간 안쪽, 앞뒤로 생기는 경간이 경간표에 없음.
    반환: (새 전주, 안내 문구 목록)"""
    from bveauto.xref.decats.core.alignment.alignment import as_alignment
    from bveauto.xref.decats.core.pole.manual_pole_processor import ManualPoleProcessor
    from bveauto.xref.decats.core.pole.pole_updator import PoleUpdator
    from bveauto.xref.decats.core.structure.define_structure import isbridge_tunnel

    poles = runner.poledata.setdefault(track, [])
    post_number = str(post_number).strip()
    pos = float(pos)
    pos = int(pos) if pos.is_integer() else pos
    gauge = float(gauge)
    base_type = str(base_type).strip().upper()
    if not post_number:
        raise ValueError('전주번호를 입력하세요.')
    if any(p.post_number == post_number for p in poles):
        raise ValueError(f'전주번호 {post_number} 가 이미 있습니다.')
    if any(float(p.pos) == float(pos) for p in poles):
        raise ValueError(f'{pos}m 에 이미 전주가 있습니다.')
    if gauge == 0:
        raise ValueError('건식게이지는 0 이 될 수 없습니다 (좌측 음수, 우측 양수).')
    if base_type not in BASE_TYPES:
        raise ValueError(f'기본 타입은 {", ".join(BASE_TYPES)} 중 하나입니다.')
    al = as_alignment(alignment)
    if not (al.start <= pos <= al.end):
        raise ValueError(f'선형 범위({al.start:g}~{al.end:g}m) 밖입니다.')
    inside = _section_containing(runner, track, pos, inclusive=False)
    if inside is not None:
        raise ValueError(f'{inside.label} 구간({inside.start_pos}~{inside.end_pos}m) 안에는 전주를 추가할 수 없습니다.')
    idx = next((i for i, p in enumerate(poles) if p.pos > pos), len(poles))
    prev_pole = poles[idx - 1] if idx > 0 else None
    next_pole = poles[idx] if idx < len(poles) else None
    new_structure = isbridge_tunnel(pos, runner.structure_list)
    # 새로 생기는 경간(앞 전주→새 전주, 새 전주→뒤 전주). 레일이 끊긴 사이에 넣으면 연결하지 않으므로 검사 생략
    linked = prev_pole is None or next_pole is None or prev_pole.next_pos == next_pole.pos
    if prev_pole is not None and linked:
        _check_span(runner, pos - prev_pole.pos, prev_pole.structure, '앞')
    if next_pole is not None and linked:
        _check_span(runner, next_pole.pos - pos, new_structure, '뒤')

    side = -1 if gauge < 0 else 1
    pole = ManualPoleProcessor.create_pole(al, runner.dataprocessor, runner.idxlib, runner.curvelist,
                                           runner.pitchlist, runner.structure_list, pos, post_number, gauge,
                                           None, base_type, track, side)
    place_on_alignment(pole, al, *track_lists(runner, track))   # 트랙 곡선·구배표로 (재계산과 같은 값)
    regenerate(runner, pole, al)   # 구조물(터널 등)에 맞는 자동 구성
    poles.insert(idx, pole)
    PoleUpdator.update_all(poles, al)   # 트랙 전체를 다시 이음 (일부만 넘기면 끝 전주 연결이 끊김)
    notices = []
    if prev_pole is not None:
        notices += filter(None, [span_limit_notice(runner, prev_pole.pos, pos, '앞')])
    if next_pole is not None:
        notices += filter(None, [span_limit_notice(runner, pos, next_pole.pos, '뒤')])
    return pole, notices


def delete_pole(runner, pole):
    """전주 삭제 (일반개소만). 앞뒤 전주가 이어지는 새 경간이 경간표에 있어야 함. 반환: 안내 문구 목록"""
    poles, idx = _track_poles(runner, pole)
    if pole.section is not None:
        raise ValueError(f'{pole.post_number}: {pole.section} 전주는 삭제할 수 없습니다. '
                         "'구간 편집'에서 구간을 삭제한 뒤 삭제하세요 (구간이 반쪽만 남음).")
    notices = []
    if 0 < idx < len(poles) - 1:
        prev_pole, next_pole = poles[idx - 1], poles[idx + 1]
        new_span = next_pole.pos - prev_pole.pos
        try:
            runner.dataprocessor.get_contact_wire_span(new_span, prev_pole.structure)
        except ValueError:
            raise ValueError(f'{pole.post_number}: 삭제하면 {prev_pole.post_number}~{next_pole.post_number} '
                             f'경간이 {new_span:g}m 가 되어 경간표에 없습니다.') from None
        notices += filter(None, [span_limit_notice(runner, prev_pole.pos, next_pole.pos,
                                                   f'{prev_pole.post_number}~{next_pole.post_number}')])
    del poles[idx]
    return notices


def set_base_type(runner, pole, base_type, alignment):
    """기본 타입(I/O/F) 변경 — 브래킷이 기본 타입으로 정해지므로 구성품을 자동 재생성"""
    base_type = str(base_type).strip().upper()
    if base_type not in BASE_TYPES:
        raise ValueError(f'기본 타입은 {", ".join(BASE_TYPES)} 중 하나입니다.')
    if pole.section is not None:
        raise ValueError(f'{pole.post_number}: {pole.section} 전주의 기본 타입은 바꿀 수 없습니다.')
    if base_type == pole.base_type:
        return []
    pole.base_type = base_type
    regenerate(runner, pole, alignment)
    return ['기본 타입이 바뀌어 구성품을 자동으로 다시 만들었습니다 (직접 편집한 구성품은 사라짐).']


def load_pole_table(runner, sheets):
    """전주 배치표(엑셀 시트별 DataFrame: 전주번호·측점·기본타입·구간)로 트랙 전주를 통째로 바꾼다.

    - 시트 이름 = 트랙('main'/'sub'), 측점 순으로 정렬. 측점·전주번호 중복, 기본 타입 오류, 없는 트랙은 거부
    - 건식게이지: 구조물 게이지, 방향은 트랙 방향(터널은 터널 전주 방향)
    - 구간 전주는 그 구간 종류의 자동 구성(에어조인트·에어섹션 브래킷 등)으로 만든다 (이전: 모두 일반개소 구성품)
    - 구간 값 순서가 등록된 종류와 맞지 않으면 불완전 구간으로 안내 (불러오기는 진행)
    실패하면 runner.poledata 는 그대로. 반환: 안내 문구 목록"""
    from bveauto.xref.decats.core.alignment.alignment import as_alignment
    from bveauto.xref.decats.core.model_rebuilder import alignment_for
    from bveauto.xref.decats.core.pole.manual_pole_processor import ManualPoleProcessor
    from bveauto.xref.decats.core.pole.pole_updator import PoleUpdator
    from bveauto.xref.decats.core.section_edit import find_sections
    from bveauto.xref.decats.core.structure.define_structure import isbridge_tunnel
    from bveauto.xref.decats.enums.section_type import FlowStop

    required = ('전주번호', '측점', '기본타입', '구간')
    rows_by_track = {}
    for track, df in sheets.items():
        if track not in ('main', 'sub'):
            raise ValueError(f"시트 이름은 트랙 이름(main / sub)이어야 합니다: '{track}'")
        if track == 'sub' and getattr(runner, 'track_mode', None) != 'double':
            raise ValueError("단선 모드에서는 'sub' 시트를 불러올 수 없습니다.")
        missing = [c for c in required if c not in df.columns]
        if missing:
            raise ValueError(f"[{track}] 열이 없습니다: {', '.join(missing)}")
        rows = []
        for i, row in df.iterrows():
            where = f'[{track}] {i + 2}행'
            try:
                pos = float(row['측점'])
            except (TypeError, ValueError):
                raise ValueError(f"{where}: 측점이 숫자가 아닙니다: {row['측점']}") from None
            pos = int(pos) if pos.is_integer() else pos
            base_type = str(row['기본타입']).strip().upper()
            if base_type not in BASE_TYPES:
                raise ValueError(f"{where}: 기본 타입은 {', '.join(BASE_TYPES)} 중 하나입니다: {row['기본타입']}")
            raw_section = row['구간']
            section = SectionType.parse(raw_section)
            if section is None and FlowStop.parse(raw_section) is None and str(raw_section).strip() not in (
                    '', 'None', 'nan', '일반개소'):
                raise ValueError(f'{where}: 알 수 없는 구간 값입니다: {raw_section}')
            rows.append((pos, str(row['전주번호']).strip(), base_type, section))
        rows.sort(key=lambda r: float(r[0]))
        for kind, col in (('측점', 0), ('전주번호', 1)):
            seen = set()
            for r in rows:
                if r[col] in seen:
                    raise ValueError(f'[{track}] {kind} {r[col]} 이(가) 중복됩니다.')
                seen.add(r[col])
        rows_by_track[track] = rows

    backup = dict(runner.poledata or {})
    try:
        if runner.poledata is None:
            runner.poledata = {}
        for track, rows in rows_by_track.items():
            al = as_alignment(alignment_for(runner, track))
            poles = []
            for pos, post_number, base_type, section in rows:
                structure = isbridge_tunnel(pos, runner.structure_list)
                direction = (runner.tunnel_direction if structure == '터널' else runner.track_direction).get(track)
                side = -1 if direction == -1 else 1
                gauge = runner.dataprocessor.get_pole_gauge(structure) * side
                poles.append(ManualPoleProcessor.create_pole(al, runner.dataprocessor, runner.idxlib,
                                                             runner.curvelist, runner.pitchlist,
                                                             runner.structure_list, pos, post_number, gauge,
                                                             section, base_type, track, side))
            runner.poledata[track] = poles
            PoleUpdator.update_all(poles, al)
            for pole in poles:                      # 구간 종류에 맞는 구성 (앞뒤 전주 연결 뒤)
                regenerate(runner, pole, al)
    except Exception:
        runner.poledata = backup
        raise
    notices = []
    for track in rows_by_track:
        for inst in find_sections(runner, track):
            if inst.kind is None:
                notices.append(f'[{track}] 불완전 구간 {inst.start_pos}~{inst.end_pos}m: 구간 값 순서가 등록된 '
                               '종류와 맞지 않습니다 (구간 편집기에서 삭제 후 다시 추가하세요).')
    return notices
