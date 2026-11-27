"""선형(Alignment) — BVEParser 의 bve_alignment.txt 를 그대로 쓰는 선형 객체

bve_alignment.txt (BVEParser ApplyRouteData 출력, 블록마다 한 줄):
    측점,X,Y,Z,Bearing,Radius,Cant,Pitch,height
    - X, Y: 평면 좌표, Z: 레일 높이 (bve_coordinates.txt 와 같은 축)
    - Bearing: 진행 방위(라디안), Radius·Cant: 곡선 반경·캔트 (curve_info.txt 와 같음)
    - Pitch: 구배(비율, pitch_info.txt 와 같음), height: 블록 지반고 (참고용)
측점이 파일에 직접 들어 있으므로 노선이 0m 에서 시작하지 않아도 좌표·곡선·구배가 어긋나지 않는다.

Alignment 는 [(측점, x, y, z), ...] 리스트를 상속하고, 측점 기준 기하 계산을 모두 메서드로 갖는다:
    locate(보간 좌표·블록 시작점·방위), point, bearing, elevation, offset_point, wire_angle(전선 평면각), offset(평행 선형)
보간·고도 결과는 선형 객체마다 따로 캐시한다 (이전: 모듈 전역 캐시).
블록 간격이 일정하면 측점으로 구간 번호를 바로 계산한다 (이전: 조회마다 전체 점을 처음부터 탐색).
bveauto.xref.decats.utils.math_util 의 같은 이름 함수(interpolate_cached 등)는 이 메서드로 위임하는 호환용이다.
bve_alignment.txt 가 없으면 기존 3개 파일(bve_coordinates / curve_info / pitch_info)로도 만들 수 있다.
"""
import math
import os

from bveauto.xref.decats.utils.math_util import (calculate_bearing, calculate_destination_coordinates, calculate_height_at_new_distance,
                             calculate_offset_point)

BLOCK = 25
ALIGNMENT_FILE = 'bve_alignment.txt'
LEGACY_FILES = ('bve_coordinates.txt', 'curve_info.txt', 'pitch_info.txt')


class StationTable(list):
    """[(측점, 값...), ...] + 블록 측점 → 행 조회 (iscurve / isslope 가 리스트를 훑지 않도록)"""

    def __init__(self, rows=()):
        super().__init__(rows)
        self.by_station = {float(r[0]): r for r in self}

    def lookup(self, station):
        return self.by_station.get(float(station))


class Alignment(list):
    """[(측점, x, y, z), ...] + 측점별 곡선(반경, 캔트)·구배"""

    def __init__(self, points, curves=None, pitches=None, block=BLOCK, source=None):
        super().__init__(points)
        self.block = block
        self.source = source
        # 블록 측점 → (반경, 캔트) / 구배(비율)
        self.curves = dict(curves or {})
        self.pitches = dict(pitches or {})
        self._geometry_cache = {}

    # pickle(.dat) 에 캐시는 저장하지 않음
    def __getstate__(self):
        state = dict(self.__dict__)
        state.pop('_geometry_cache', None)
        return state

    def __setstate__(self, state):
        self.__dict__.update(state)
        self._geometry_cache = {}

    def _cache(self, name):
        caches = self.__dict__.setdefault('_geometry_cache', {})
        return caches.setdefault(name, {})

    def clear_cache(self):
        self.__dict__['_geometry_cache'] = {}

    # ── 만들기 ─────────────────────────────────────
    @classmethod
    def from_bve_alignment(cls, path):
        """BVEParser bve_alignment.txt 로 선형 생성"""
        points, curves, pitches = [], {}, {}
        with open(path, encoding='utf-8-sig') as f:
            for n, line in enumerate(f):
                line = line.strip()
                if not line:
                    continue
                cols = line.split(',')
                if n == 0 and not _is_number(cols[0]):
                    continue  # 머리글
                if len(cols) < 8:
                    raise ValueError(f'{path}:{n + 1} 열이 부족합니다 (측점,X,Y,Z,Bearing,Radius,Cant,Pitch 필요)')
                sta, x, y, z = (float(c) for c in cols[:4])
                points.append((sta, x, y, z))
                curves[sta] = (float(cols[5]), float(cols[6]))
                pitches[sta] = float(cols[7])
        if len(points) < 2:
            raise ValueError(f'{path}: 선형 점이 2개 이상 필요합니다.')
        block = points[1][0] - points[0][0]
        return cls(points, curves, pitches, block=block, source=path)

    @classmethod
    def from_legacy_files(cls, coord_path, curve_path, pitch_path, block=BLOCK):
        """기존 3개 파일로 선형 생성 (좌표 파일에는 측점이 없어 0m 부터 block 간격으로 가정)"""
        from bveauto.xref.decats.file_io.basedata_processor import parse_curve, parse_pitch, parse_polyline
        coords = parse_polyline(coord_path)
        points = [(i * block, x, y, z) for i, (x, y, z) in enumerate(coords)]
        curves = {float(s): (r, c) for s, r, c in parse_curve(curve_path)}
        pitches = {float(s): p for s, p in parse_pitch(pitch_path)}
        return cls(points, curves, pitches, block=block, source=coord_path)

    @classmethod
    def from_info_dir(cls, folder):
        """폴더에서 bve_alignment.txt 우선, 없으면 기존 3개 파일"""
        path = os.path.join(folder, ALIGNMENT_FILE)
        if os.path.isfile(path):
            return cls.from_bve_alignment(path)
        return cls.from_legacy_files(*(os.path.join(folder, f) for f in LEGACY_FILES))

    @classmethod
    def from_points(cls, points, curvelist=None, pitchlist=None):
        """[(측점, x, y, z)] 리스트(구버전 데이터)와 곡선·구배 목록으로 생성"""
        points = list(points)
        block = points[1][0] - points[0][0] if len(points) >= 2 else BLOCK
        curves = {float(s): (r, c) for s, r, c in (curvelist or [])}
        pitches = {float(s): p for s, p in (pitchlist or [])}
        return cls(points, curves, pitches, block=block)

    def derived(self, points):
        """같은 측점·곡선·구배를 쓰는 다른 선형 (상선 등)"""
        return Alignment(points, self.curves, self.pitches, block=self.block, source=self.source)

    def offset(self, distance):
        """진행방향 수직으로 distance 만큼 평행이동한 선형 (BVE Rail x 오프셋과 같은 방식, 우측 +).
        측점·고도·곡선·구배는 그대로"""
        return self.derived(offset_points(self, distance))

    # ── 범위 ──────────────────────────────────────
    @property
    def start(self):
        return self[0][0]

    @property
    def end(self):
        return self[-1][0]

    def block_of(self, station):
        """측점이 속한 블록 시작 측점"""
        return math.floor((station - self.start) / self.block + 0.001) * self.block + self.start

    # ── 측점별 기하 ─────────────────────────────────
    def _segment_index(self, station, include_upper):
        """station 이 속한 구간 번호. include_upper 면 구간 끝점도 그 구간에 포함 (앞 구간 우선, 고도 계산 규칙)"""
        n = len(self)
        if n < 2:
            raise ValueError('선형 점이 2개 이상 필요합니다.')
        i = int(math.floor((station - self[0][0]) / self.block)) if self.block else 0
        if include_upper and i > 0 and 0 < i < n and station == self[i][0]:
            i -= 1  # 예전 순차 탐색과 같이 경계 측점은 앞 구간에서 찾음
        i = min(max(i, 0), n - 2)
        if self._in_segment(i, station, include_upper):
            return i
        for k in range(n - 1):  # 블록 간격이 일정하지 않은 선형
            if self._in_segment(k, station, include_upper):
                return k
        raise ValueError(f"측점 {station} 이(가) 선형 범위({self[0][0]} ~ {self[-1][0]})를 벗어났습니다.")

    def _in_segment(self, i, station, include_upper):
        s1, s2 = self[i][0], self[i + 1][0]
        if include_upper:
            return s1 <= station <= s2
        return s1 <= station < s2 or (i == len(self) - 2 and station == s2)

    def locate(self, station):
        """((x, y, z) 보간 좌표, 블록 시작점 (x, y, z), 블록 방위(도)) — 캐시"""
        cache = self._cache('locate')
        if station not in cache:
            i = self._segment_index(station, include_upper=False)
            sta1, x1, y1, z1 = self[i]
            sta2, x2, y2, z2 = self[i + 1]
            v1 = calculate_bearing(x1, y1, x2, y2)
            t = station - sta1
            x, y = calculate_destination_coordinates(x1, y1, v1, t)
            ratio = t / (sta2 - sta1) if sta2 != sta1 else 0.0
            z = z1 + ratio * (z2 - z1)
            cache[station] = ((x, y, z), (x1, y1, z1), v1)
        return cache[station]

    def point(self, station):
        """측점의 선형 좌표 (x, y, z)"""
        return self.locate(station)[0]

    def bearing(self, station):
        """측점이 속한 블록의 진행 방위 (도, x 축 기준 반시계)"""
        return self.locate(station)[2]

    def elevation(self, station):
        """측점의 레일 높이 (블록 사이 선형 보간) — 캐시"""
        cache = self._cache('elevation')
        if station not in cache:
            if station < self[0][0] or station > self[-1][0]:
                raise ValueError(f"측점 {station} 이(가) 선형 범위({self[0][0]} ~ {self[-1][0]})를 벗어났습니다.")
            i = self._segment_index(station, include_upper=True)
            sta1, _, _, z1 = self[i]
            sta2, _, _, z2 = self[i + 1]
            cache[station] = calculate_height_at_new_distance(z1, z2, sta2 - sta1, station - sta1)
        return cache[station]

    def offset_point(self, station, offset):
        """측점에서 진행방향 수직으로 offset 만큼 떨어진 평면 좌표 (우측 +, calculate_offset_point 와 같은 규칙)"""
        point, _, bearing = self.locate(station)
        return calculate_offset_point(bearing, point, offset)

    def wire_angle(self, pos, next_pos, offset1, offset2, start=True):
        """pos 의 offset1 지점 → next_pos 의 offset2 지점으로 가는 전선의 평면 각도 (도).
        start 면 pos 블록 방위 기준(BVE freeobj yaw), 아니면 next_pos 블록 방위 기준"""
        point_a, _, vector_a = self.locate(pos)
        point_b, _, vector_b = self.locate(next_pos)
        a = calculate_offset_point(vector_a, point_a, offset1)
        b = calculate_offset_point(vector_b, point_b, offset2)
        a_b_angle = calculate_bearing(a[0], a[1], b[0], b[1])
        return vector_a - a_b_angle if start else a_b_angle - vector_b

    def curve(self, station):
        """(반경, 캔트). 직선이면 (0, 0)"""
        return self.curves.get(float(self.block_of(station)), (0.0, 0.0))

    def pitch(self, station):
        """구배 (비율)"""
        return self.pitches.get(float(self.block_of(station)), 0.0)

    # ── 기존 코드용 목록 ────────────────────────────
    @property
    def curvelist(self):
        """[(측점, 반경, 캔트)] — iscurve 용 (블록 측점 조회 가능)"""
        return StationTable((s, r, c) for s, (r, c) in sorted(self.curves.items()))

    @property
    def pitchlist(self):
        """[(측점, 구배)] — isslope 용 (블록 측점 조회 가능)"""
        return StationTable((s, p) for s, p in sorted(self.pitches.items()))

    @property
    def coordinates(self):
        """[(x, y, z)] — 기존 runner.polyline 형식"""
        return [(x, y, z) for _, x, y, z in self]


def _is_number(text):
    try:
        float(text)
        return True
    except ValueError:
        return False


def offset_points(points, distance):
    """[(측점, x, y, z)] 를 각 점에서 다음 점으로 향하는 방위(마지막 점은 직전 구간)의 수직으로 평행이동"""
    n = len(points)
    if n < 2:
        raise ValueError("오프셋하려면 선형 점이 2개 이상 필요합니다.")
    result = []
    for i, (sta, x, y, z) in enumerate(points):
        if i < n - 1:
            _, x1, y1, _ = points[i]
            _, x2, y2, _ = points[i + 1]
        else:
            _, x1, y1, _ = points[i - 1]
            _, x2, y2, _ = points[i]
        theta = math.atan2(y2 - y1, x2 - x1)
        result.append((sta, x + distance * math.sin(theta), y - distance * math.cos(theta), z))
    return result


def as_alignment(polyline):
    """Alignment 면 그대로, [(측점, x, y, z)] 리스트(구버전 데이터 등)면 같은 리스트에 대해 한 번만 감싸서 반환"""
    if isinstance(polyline, Alignment):
        return polyline
    entry = _LIST_WRAPPERS.get(id(polyline))
    if entry is None or entry[0] is not polyline:
        if len(_LIST_WRAPPERS) > 64:
            _LIST_WRAPPERS.clear()
        entry = (polyline, Alignment.from_points(polyline))
        _LIST_WRAPPERS[id(polyline)] = entry
    return entry[1]


_LIST_WRAPPERS = {}
