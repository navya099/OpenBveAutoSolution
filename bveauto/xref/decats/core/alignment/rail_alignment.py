"""BVEParser rail_info.txt 기반 상선(부본선) 선형

rail_info.txt 형식 (BVEParser ApplyRouteData 출력):
    sta,rail_key,x,y,z[,visible]
    - x, y: 평면 좌표, z: 높이 (bve_coordinates.txt 와 같은 축 순서)
    - visible: 그 블록에서 레일이 그려지는지 (RailStarted, 1/0). 구버전 파서는 이 열이 없다.

BVE 파서는 .RailEnd 이후에도 레일 항목과 마지막 오프셋을 다음 블록으로 복사하므로,
좌표는 레일이 보이지 않는 구간에도 계속 기록된다. 따라서 visible 열 없이는
'실제로 깔린 레일'과 '남아 있는 좌표'를 구분할 수 없다.

블록 b 의 visible=1 은 b → b+BLOCK 구간에 레일이 그려진다는 뜻이다.
"""
import math

from bveauto.xref.decats.core.alignment.alignment import BLOCK, Alignment
from bveauto.xref.decats.utils.comom_util import get_block_index



class RailAlignment(Alignment):
    """상선 선형 (Alignment) + 레일이 그려지는 블록 정보.

    곡선·구배는 본선과 같은 측점 값을 쓴다 (상선은 본선과 측점을 공유).
    visible_blocks 가 None 이면 전 구간 표시로 간주한다.
    """

    def __init__(self, points, visible_blocks=None, rail_key=None, base=None):
        super().__init__(points, getattr(base, 'curves', None), getattr(base, 'pitches', None),
                         block=getattr(base, 'block', BLOCK), source=getattr(base, 'source', None))
        self.visible_blocks = visible_blocks
        self.rail_key = rail_key


def parse_rail_info(filepath, rail_key):
    """rail_info.txt 에서 rail_key 레일만 읽는다.

    :return: (points, has_visibility)
        points: {sta: (x, y, z, visible)}
        has_visibility: 파일에 visible 열이 있었는지
    """
    points = {}
    has_visibility = None
    with open(filepath, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            cols = line.split(',')
            if int(float(cols[1])) != rail_key:
                continue
            if has_visibility is None:
                has_visibility = len(cols) >= 6
            visible = int(float(cols[5])) == 1 if has_visibility else True
            points[float(cols[0])] = (float(cols[2]), float(cols[3]), float(cols[4]), visible)
    if not points:
        raise ValueError(f"rail_info 에 레일 {rail_key} 데이터가 없습니다: {filepath}")
    return points, bool(has_visibility)


def build_rail_alignment(main_alignment, rail_points, fallback_alignment, rail_key=None, has_visibility=True):
    """본선 측점마다 상선 좌표를 만든다.

    - 레일이 그려지는 블록과 그 끝점(직전 블록이 그려진 점)은 rail_info 좌표 사용
    - 그 외(레일 시작 전/RailEnd 이후, 데이터 없음)는 fallback(일정 간격 오프셋) 좌표로 채워
      보간이 끊기지 않게 한다. 이 구간에는 상선 전주/전선을 만들지 않는다.
    """
    visible_blocks = {sta for sta, p in rail_points.items() if p[3]} if has_visibility else None
    points = []
    for (sta, *_), fb in zip(main_alignment, fallback_alignment):
        rp = rail_points.get(float(sta))
        drawn_here = rp is not None and (visible_blocks is None or sta in visible_blocks
                                         or (sta - BLOCK) in visible_blocks)
        if drawn_here:
            points.append((sta, rp[0], rp[1], rp[2]))
        else:
            points.append(fb)
    return RailAlignment(points, visible_blocks, rail_key, base=main_alignment)


def is_span_visible(alignment, pos, next_pos):
    """[pos, next_pos] 구간의 모든 블록에 레일이 그려지는지. 표시 정보가 없으면 True."""
    visible = getattr(alignment, 'visible_blocks', None)
    if visible is None:
        return True
    if next_pos is None:
        return get_block_index(pos) in visible
    first = get_block_index(pos)
    last = math.ceil(next_pos / BLOCK - 1e-9) * BLOCK - BLOCK  # next_pos 가 블록 경계면 그 직전 블록까지
    b = first
    while b <= max(first, last):
        if b not in visible:
            return False
        b += BLOCK
    return True


def visible_ranges(alignment):
    """레일이 그려지는 연속 구간 [(start, end), ...] (로그/표시용)"""
    visible = getattr(alignment, 'visible_blocks', None)
    if visible is None:
        return None
    ranges = []
    for b in sorted(visible):
        if ranges and b == ranges[-1][1]:
            ranges[-1][1] = b + BLOCK
        else:
            ranges.append([b, b + BLOCK])
    return [tuple(r) for r in ranges]
