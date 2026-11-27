"""데이터셋 편집 — 설계 데이터셋(JSON) + 경간표(spandata xlsx) 조회·수정·검사·저장 (GUI 없이 동작)

데이터셋 = JSON(전주·브래킷·전선 인덱스와 오프셋 등) + 경간표 xlsx(시트별 경간 길이 → 전선 오브젝트 인덱스).
표준 데이터셋(소스 폴더 config/)은 덮어쓰지 않는다. 편집 결과는 커스텀 데이터셋으로 저장하고,
GUI 에서 커스텀 모드로 지정해 사용한다.

검사(validate):
    1) 같은 설계속도의 표준 데이터셋(없으면 250)과 비교: 빠진 키, 형식이 다른 값(숫자 자리에 문자 등)
    2) 실제 처리 코드(bveauto.xref.decats.datasetGetter)가 쓰는 조회를 구조물별로 직접 실행
    3) 경간표: 필요한 시트, 길이·인덱스 열, 정수 값, 중복 길이
오류가 있으면 저장하지 않는다 (그 데이터셋으로 실행하면 처리 중 실패하므로).
"""
import copy
import json
import os
from dataclasses import dataclass

import pandas as pd

from bveauto.xref.decats.dataset.dataset_getter import DatasetGetter
from bveauto.xref.decats.dataset.dataset_manager import SUPPORTED_SPEEDS, get_config_dir, get_standard_dataset_paths

STRUCTURES = ('토공', '교량', '터널')
SPAN_SHEETS = ('토공전차선', '터널전차선', '급전선', '보호선', '무효용전차선', '무효용조가선')
SPAN_REQUIRED_COLUMNS = ('길이', '인덱스')
DERIVED_KEYS = ('span_data', '_source')   # load_bveauto.xref.decats.dataset 이 붙이는 값 (JSON 에 저장하지 않음)
KEY_TEXT = {'design': '설계', 'mast': '전주', 'bracket': '브래킷', 'feeder': '급전선 설비', 'spreader': '평행틀',
            'wire': '전선', 'airjoint': '에어조인트', 'airsection': '에어섹션'}


@dataclass
class Problem:
    level: str      # 'error' | 'warning'
    where: str      # 경로 (예: 'mast.gauge.토공') 또는 '경간표:시트'
    message: str


# ── 경로 ────────────────────────────────────────────
def path_text(path):
    return '.'.join(str(p) for p in path)


def get_at(data, path):
    node = data
    for key in path:
        node = node[key]
    return node


def leaves(data, prefix=()):
    """(경로, 값) — 딕셔너리가 아닌 값 전부 (리스트·null 포함)"""
    if isinstance(data, dict):
        for k, v in data.items():
            yield from leaves(v, prefix + (k,))
    else:
        yield prefix, data


def _kind(value):
    if value is None:
        return 'null'
    if isinstance(value, bool):
        return 'bool'
    if isinstance(value, (int, float)):
        return 'number'
    if isinstance(value, str):
        return 'text'
    if isinstance(value, list):
        return 'list'
    return 'dict'


def parse_value(text, current):
    """입력 문자열을 현재 값 형식에 맞게 변환. 'null' 또는 빈 값은 None (인덱스 없음)"""
    text = '' if text is None else str(text).strip()
    if text.lower() in ('', 'null', 'none'):
        return None
    if isinstance(current, bool):
        if text.lower() in ('true', '1', '예'):
            return True
        if text.lower() in ('false', '0', '아니오'):
            return False
        raise ValueError(f"참/거짓 값이어야 합니다: {text}")
    if isinstance(current, list) or text.startswith('['):
        try:
            value = json.loads(text)
        except json.JSONDecodeError:
            raise ValueError(f"목록은 JSON 형식으로 입력하세요 (예: [1, 2]): {text}") from None
        if not isinstance(value, list):
            raise ValueError(f"목록이어야 합니다: {text}")
        return value
    if isinstance(current, str):
        return text
    # 숫자 또는 null 자리: 정수면 정수, 아니면 실수, 숫자가 아니면 문자
    try:
        return int(text)
    except ValueError:
        pass
    try:
        return float(text)
    except ValueError:
        if current is None or isinstance(current, (int, float)):
            raise ValueError(f"숫자(또는 비우기=null)를 입력하세요: {text}") from None
        return text


# ── 문서 ────────────────────────────────────────────
class DatasetDocument:
    def __init__(self, data, spans, json_path=None, xlsx_path=None):
        self.data = {k: v for k, v in data.items() if k not in DERIVED_KEYS}
        self.spans = {name: df.copy() for name, df in spans.items()}
        self.json_path = json_path
        self.xlsx_path = xlsx_path
        self.template, self.template_spans, self.template_speed = _load_template(self.data)
        self.dirty = False

    # 만들기
    @classmethod
    def load(cls, json_path, xlsx_path):
        with open(json_path, encoding='utf-8') as f:
            data = json.load(f)
        spans = pd.read_excel(xlsx_path, sheet_name=None)
        return cls(data, spans, json_path, xlsx_path)

    @classmethod
    def from_standard(cls, speed):
        return cls.load(*get_standard_dataset_paths(int(speed)))

    @property
    def is_standard(self):
        """표준 데이터셋(config/) 파일인지 — 덮어쓰기 금지"""
        cfg = os.path.normcase(os.path.abspath(get_config_dir()))
        return any(p and os.path.normcase(os.path.dirname(os.path.abspath(p))) == cfg
                   for p in (self.json_path, self.xlsx_path))

    # 조회·수정
    def get(self, path):
        return get_at(self.data, path)

    def set(self, path, text):
        """값 수정 (입력 문자열 → 현재 값 형식). 반환: 새 값"""
        path = tuple(path)
        parent = get_at(self.data, path[:-1])
        if not isinstance(parent, dict) or path[-1] not in parent:
            raise KeyError(f'없는 항목입니다: {path_text(path)}')
        if isinstance(parent[path[-1]], dict):
            raise ValueError('하위 항목이 있는 묶음은 값을 직접 바꿀 수 없습니다. 하위 항목을 수정하세요.')
        value = parse_value(text, parent[path[-1]])
        parent[path[-1]] = value
        self.dirty = True
        return value

    def add_key(self, path, key, text=''):
        """묶음(딕셔너리)에 항목 추가 (예: 추가 밴드·추가 전선 오프셋)"""
        parent = get_at(self.data, tuple(path))
        key = str(key).strip()
        if not isinstance(parent, dict):
            raise ValueError('값 항목에는 하위 항목을 추가할 수 없습니다.')
        if not key:
            raise ValueError('항목 이름을 입력하세요.')
        if key in parent:
            raise ValueError(f'이미 있는 항목입니다: {key}')
        parent[key] = parse_value(text, None) if text not in ('{}',) else {}
        self.dirty = True

    def remove_key(self, path):
        path = tuple(path)
        if self.template is not None and _exists(self.template, path):
            raise ValueError(f'{path_text(path)} 는 표준 데이터셋에 있는 필수 항목이라 삭제할 수 없습니다.')
        parent = get_at(self.data, path[:-1])
        del parent[path[-1]]
        self.dirty = True

    def template_value(self, path):
        """같은 설계속도 표준 데이터셋의 값 (없으면 None, 존재 여부는 두 번째 값)"""
        if self.template is None or not _exists(self.template, path):
            return None, False
        return get_at(self.template, path), True

    def reset_to_template(self, path):
        value, ok = self.template_value(path)
        if not ok:
            raise ValueError(f'표준 데이터셋에 {path_text(path)} 가 없습니다.')
        get_at(self.data, tuple(path)[:-1])[path[-1]] = copy.deepcopy(value)
        self.dirty = True

    def changed_paths(self):
        """표준 데이터셋과 값이 다른 경로"""
        if self.template is None:
            return set()
        out = set()
        for path, value in leaves(self.data):
            tval, ok = self.template_value(path)
            if not ok or tval != value:
                out.add(path)
        return out

    # 경간표
    def set_span_cell(self, sheet, row, column, text):
        df = self.spans[sheet]
        current = df.at[row, column]
        if column in SPAN_REQUIRED_COLUMNS or pd.api.types.is_integer_dtype(df[column].dtype):
            try:
                value = int(str(text).strip())
            except ValueError:
                raise ValueError(f'{column} 은(는) 정수로 입력하세요: {text}') from None
        elif pd.api.types.is_float_dtype(df[column].dtype):
            value = float(text)
        else:
            value = str(text)
        if current != value:
            df.at[row, column] = value
            self.dirty = True

    def add_span_row(self, sheet, values=None):
        df = self.spans[sheet]
        row = dict(values or {})
        if not row and len(df):
            row = df.iloc[-1].to_dict()
            row['길이'] = int(df['길이'].max()) + 1
        self.spans[sheet] = pd.concat([df, pd.DataFrame([row])], ignore_index=True)
        self.dirty = True
        return len(self.spans[sheet]) - 1

    def remove_span_row(self, sheet, row):
        self.spans[sheet] = self.spans[sheet].drop(index=row).reset_index(drop=True)
        self.dirty = True

    # 검사
    def to_dataset(self):
        """load_bveauto.xref.decats.dataset 과 같은 형식 (span_data 포함)"""
        ds = copy.deepcopy(self.data)
        ds['span_data'] = {name: dict(zip(df['길이'], df['인덱스'])) for name, df in self.spans.items()
                           if all(c in df.columns for c in SPAN_REQUIRED_COLUMNS)}
        ds['_source'] = {'json': self.json_path, 'spandata': self.xlsx_path}
        return ds

    def validate(self):
        problems = []
        if self.template is not None:
            for path, tval in leaves(self.template):
                if not _exists(self.data, path):
                    problems.append(Problem('error', path_text(path), '필수 항목이 없습니다 (표준 데이터셋에 있음).'))
                    continue
                value = self.get(path)
                if tval is not None and value is not None and _kind(tval) != _kind(value):
                    problems.append(Problem('error', path_text(path),
                                            f'형식이 다릅니다: 표준 {_kind(tval)}, 현재 {_kind(value)} ({value!r})'))
        problems += _probe(self.to_bveauto.xref.decats.dataset())
        problems += _check_spans(self.spans, self.template_spans)
        if self.template is not None and self.template_speed != _speed(self.data):
            problems.insert(0, Problem('warning', 'design.speed',
                                       f'설계속도 {_speed(self.data)} 의 표준 데이터셋이 없어 '
                                       f'{self.template_speed}km/h 표준과 비교했습니다.'))
        return problems

    def errors(self):
        return [p for p in self.validate() if p.level == 'error']

    # 저장
    def save(self, json_path=None, xlsx_path=None):
        """커스텀 데이터셋으로 저장. 표준(config/) 덮어쓰기 금지, 검사 오류가 있으면 저장 안 함"""
        json_path = json_path or self.json_path
        xlsx_path = xlsx_path or self.xlsx_path
        if not json_path or not xlsx_path:
            raise ValueError('저장할 JSON·경간표 경로를 지정하세요.')
        cfg = os.path.normcase(os.path.abspath(get_config_dir()))
        for p in (json_path, xlsx_path):
            if os.path.normcase(os.path.dirname(os.path.abspath(p))) == cfg:
                raise ValueError('표준 데이터셋(config/)은 덮어쓸 수 없습니다. 다른 위치에 커스텀으로 저장하세요.')
        errors = self.errors()
        if errors:
            raise ValueError('검사 오류가 있어 저장하지 않았습니다:\n' +
                             '\n'.join(f'- {p.where}: {p.message}' for p in errors[:10]))
        os.makedirs(os.path.dirname(os.path.abspath(json_path)), exist_ok=True)
        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump(self.data, f, ensure_ascii=False, indent=2)
        with pd.ExcelWriter(xlsx_path) as w:
            for name, df in self.spans.items():
                df.to_excel(w, sheet_name=name, index=False)
        self.json_path, self.xlsx_path = json_path, xlsx_path
        self.dirty = False
        return json_path, xlsx_path


# ── 내부 ────────────────────────────────────────────
def _exists(data, path):
    node = data
    for key in path:
        if not isinstance(node, dict) or key not in node:
            return False
        node = node[key]
    return True


def _speed(data):
    try:
        return int(data['design']['speed'])
    except (KeyError, TypeError, ValueError):
        return None


def _load_template(data):
    speed = _speed(data)
    template_speed = speed if speed in SUPPORTED_SPEEDS else 250
    json_path, xlsx_path = get_standard_dataset_paths(template_speed)
    try:
        with open(json_path, encoding='utf-8') as f:
            template = json.load(f)
        template_spans = pd.read_excel(xlsx_path, sheet_name=None)
    except OSError:
        return None, None, None
    return template, template_spans, template_speed


def _probe(ds):
    """실제 처리 코드가 쓰는 조회를 구조물별로 실행해 실패를 찾는다"""
    g = DatasetGetter(ds)
    problems = []

    def call(where, fn, *args, level='error', allow_none=True):
        try:
            value = fn(*args)
        except Exception as e:  # noqa: BLE001 - 어떤 조회 실패든 문제로 보고
            problems.append(Problem(level, where, f'조회 실패: {e}'))
            return
        if value is None and not allow_none:
            problems.append(Problem(level, where, '값이 비어 있습니다.'))

    call('design.speed', g.get_design_speed, allow_none=False)
    call('bracket.fitting', g.get_fittings)
    call('airjoint.bracket_height', g.get_airjoint_f_bracket_height, allow_none=False)
    call('airjoint.double_pole', g.get_double_pole_settings)  # 복주 에어조인트 (없으면 기본값)
    for name in g.EQUIPMENT_DEFAULTS:
        call(f'equipment.{name}', g.get_equipment_index, name, allow_none=False)
    for key in ('F형_시점', 'AJ형_시점', 'AJ형_중간1', 'AJ형_중간2', 'AJ형_끝', 'F형_끝'):
        call(f'airjoint.offset.{key}', g.get_airjoint_offset, key, allow_none=False)
    for s in STRUCTURES:
        call(f'mast.gauge.{s}', g.get_pole_gauge, s, allow_none=False)
        call(f'mast.index.일반개소.{s}', g.get_mast_index, s, None)
        call(f'mast.index.평행개소.{s}', g.get_mast_index, s, 'section')
        call(f'mast.foundation.{s}', g.get_post_base, s)
        call(f'feeder.{s}', g.get_feeder_insulator_idx, s)
        call(f'spreader.{s}', g.get_spreader_idx, s, '1m')
        call(f'wire.offset.CW.{s}', g.get_contact_wire_height, s, allow_none=False)
        call(f'wire.system_height.{s}', g.get_system_height, s, allow_none=False)
        call(f'wire.offset.AF.{s}', g.get_af_offset, s)
        call(f'wire.offset.FPW.{s}', g.get_fpw_offset, s)
        for kind in ('일반개소', '에어조인트', 'F브래킷'):
            for base in ('I', 'O'):
                call(f'bracket.index.{kind}.{s}.{base}', g.get_bracket_codes, kind, s, base)
        for base in ('I', 'O'):  # 에어섹션은 에어섹션을 쓸 때만 필요
            call(f'bracket.index.에어섹션.{s}.{base}', g.get_bracket_codes, '에어섹션', s, base, level='warning')
    if 'airsection' in ds:
        call('airsection.bracket_height', g.get_airsection_f_bracket_height, level='warning')
    return problems


def _check_spans(spans, template_spans):
    problems = []
    required = list(template_spans) if template_spans else list(SPAN_SHEETS)
    for name in required:
        if name not in spans:
            problems.append(Problem('error', f'경간표:{name}', '시트가 없습니다.'))
    for name, df in spans.items():
        where = f'경간표:{name}'
        missing = [c for c in SPAN_REQUIRED_COLUMNS if c not in df.columns]
        if missing:
            problems.append(Problem('error', where, f'열이 없습니다: {missing}'))
            continue
        for col in SPAN_REQUIRED_COLUMNS:
            bad = df[col][pd.to_numeric(df[col], errors='coerce').isna()]
            if len(bad):
                problems.append(Problem('error', where, f'{col} 에 숫자가 아닌 값이 있습니다 ({len(bad)}행, 예: {bad.iloc[0]!r}).'))
        dup = df['길이'][df['길이'].duplicated()]
        if len(dup):
            problems.append(Problem('error', where, f'같은 길이가 여러 번 있습니다: {sorted(set(dup.tolist()))[:5]}'))
    return problems
