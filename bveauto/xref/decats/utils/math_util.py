"""기하 계산 유틸

순수 계산 함수(방위, 오프셋 좌표, 구배 각도, 편위 등)는 여기에 있다.
선형(측점) 기준 계산은 bveauto.xref.decats.core.alignment.alignment.Alignment 의 메서드로 옮겼고, 아래 같은 이름의 함수
(interpolate_cached, interpolate_coordinates, get_elevation_pos, calculate_curve_angle, offset_polyline)는
Alignment 로 위임하는 호환용이다. [(측점, x, y, z)] 리스트를 넘겨도 동작한다.
"""
import math
from functools import lru_cache



def _alignment(polyline):
    from bveauto.xref.decats.core.alignment.alignment import as_alignment
    return as_alignment(polyline)


def clear_geometry_caches():
    """호환용: 캐시는 이제 선형 객체마다 있어 전역으로 비울 것이 없다 (리스트 감싸기 캐시만 비움)"""
    from bveauto.xref.decats.core.alignment import alignment
    alignment._LIST_WRAPPERS.clear()

@lru_cache(maxsize=None)
def calculate_bearing(x1, y1, x2, y2):
    """도 반환 각도"""
    dx = x2 - x1
    dy = y2 - y1
    return math.degrees(math.atan2(dy, dx))

def calculate_curve_angle(polyline_with_sta, pos, next_pos, stagger1, stagger2, start=True):
    """호환용 → Alignment.wire_angle"""
    return _alignment(polyline_with_sta).wire_angle(pos, next_pos, stagger1, stagger2, start=start)

def calculate_offset_point(vector, point_a, offset_distance):
    if offset_distance > 0:  # 우측 오프셋
        vector -= 90
    else:
        vector += 90  # 좌측 오프셋
    offset_a_xy = calculate_destination_coordinates(point_a[0], point_a[1], vector, abs(offset_distance))
    return offset_a_xy

def interpolate_cached(polyline_with_sta, pos):
    """호환용 → Alignment.locate ((x, y, z), 블록 시작점, 방위)"""
    return _alignment(polyline_with_sta).locate(pos)

def interpolate_coordinates(polyline, target_sta):
    """호환용 → Alignment.locate"""
    return _alignment(polyline).locate(target_sta)

def offset_polyline(polyline_with_sta, distance):
    """호환용 → Alignment.offset (리스트를 넘기면 리스트 반환)"""
    from bveauto.xref.decats.core.alignment.alignment import Alignment, offset_points
    if isinstance(polyline_with_sta, Alignment):
        return polyline_with_sta.offset(distance)
    return offset_points(polyline_with_sta, distance)

def calculate_destination_coordinates(x1, y1, bearing, distance):
    # Calculate the destination coordinates given a starting point, bearing, and distance in Cartesian coordinates
    angle = math.radians(bearing)
    x2 = x1 + distance * math.cos(angle)
    y2 = y1 + distance * math.sin(angle)
    return x2, y2

def get_elevation_pos(pos, polyline_with_sta):
    """호환용 → Alignment.elevation"""
    return _alignment(polyline_with_sta).elevation(pos)

def calculate_height_at_new_distance(h1, h2, L, L_new):
    """주어진 거리 L에서의 높이 변화율을 기반으로 새로운 거리 L_new에서의 높이를 계산"""
    h3 = h1 + ((h2 - h1) / L) * L_new
    return h3

def calculate_slope(h1, h2, gauge):
    """주어진 높이 차이와 수평 거리를 바탕으로 기울기(각도) 계산"""
    slope = (h2 - h1) / gauge  # 기울기 값 (비율)
    return math.degrees(math.atan(slope))  # 아크탄젠트 적용 후 degree 변환

# 새로운 점 계산 함수
def return_new_point(x, y, L):
    A = (x, 0)
    B = (0, 0)
    C = (0, y)
    theta = calculate_bearing(A[0],A[1], C[0],C[1])
    D = calculate_destination_coordinates(A[0], A[1], theta, L)
    E = B[0], B[1] + D[1]

    d1 = calculate_distance(D[0], D[1], E[0], E[1])
    d2 = calculate_distance(B[0], B[1], E[0], E[1])

    # 외적 좌우 판별
    v_x, v_y = C[0] - B[0], C[1] - B[1]
    w_x, w_y = A[0] - B[0], A[1] - B[1]
    cross = v_x * w_y - v_y * w_x
    sign = -1 if cross > 0 else 1

    # abs(d1)로 거리값을 안정화하고 sign으로 좌우만 결정
    return abs(d1) * sign, d2

def calculate_distance(x1, y1, x2, y2):
    """두 점 (x1, y1)과 (x2, y2) 사이의 유클리드 거리 계산"""
    return math.hypot(x2 - x1, y2 - y1)  # math.sqrt((x2 - x1)**2 + (y2 - y1)**2)와 동일

def change_permile_to_degree(permile):
    """퍼밀 값을 도(degree)로 변환"""
    # 정수 또는 문자열이 들어오면 float으로 변환
    if not isinstance(permile, (int, float)):
        permile = float(permile)

    return math.degrees(math.atan(permile / 1000))  # 퍼밀을 비율로 변환 후 계산

def calculate_curve_stagger(cant, gauge=1.5, contact_wire_height=5.0, offset=0.2, direction=1):
    theta = math.atan(cant / gauge)

    # 점 P
    # 점 P
    if direction == 1:
        angle_p = math.radians(90) - theta
    else:
        angle_p = math.radians(90) + theta
    p_x = contact_wire_height * math.cos(angle_p)
    p_y = contact_wire_height * math.sin(angle_p)

    # 점 S (offset 적용)
    s_x = p_x + offset
    s_y = p_y

    # 점 T
    angle_t = math.radians(90)
    t_x = contact_wire_height * math.cos(angle_t)
    t_y = contact_wire_height * math.sin(angle_t)

    # 편위 거리
    stagger = math.sqrt((s_x - t_x)**2 + (s_y - t_y)**2)
    return stagger * direction