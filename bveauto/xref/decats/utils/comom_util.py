import re
import math


from bveauto.xref.decats.utils.math_util import return_new_point


def find_last_block(data):
    """
    데이터 리스트에서 마지막 블록 번호(첫 번째 숫자)를 반환.
    예: ['45676,500,0','4646,366,35'] → 4646
    """
    last_block = None

    for line in data:
        if isinstance(line, str):
            # 문자열 맨 앞의 숫자만 추출 (콤마 앞까지)
            match = re.match(r'(\d+)', line)
            if match:
                last_block = int(match.group(1))

    return last_block

def get_max_span_by_radius(radius):
    """곡선 반경(R)에 따른 최대 경간 (편위·풍압 기준, 설계속도와 무관). 직선(0)은 제한 없음 → 설계속도 한도 적용"""
    radius = abs(radius)
    if radius == 0 or radius >= 1500: return 60
    if radius >= 1000: return 55
    if radius >= 800: return 50
    if radius >= 600: return 45
    if radius >= 400: return 40
    return 35 # 급곡선


def get_max_span_at(pos, design_speed, curvelist=None, structure_list=None):
    """측점의 최대 경간 = min(설계속도 한도(직선 또는 터널), 곡선 반경 한도)

    곡선 한도는 설계속도와 무관하므로, 저속에서 완만한 곡선 경간이 직선 경간보다 길어지지 않도록
    설계속도 한도로 함께 제한한다. 터널 안 곡선도 반경 한도를 적용한다."""
    from bveauto.xref.decats.core.alignment.define_funtion import iscurve
    from bveauto.xref.decats.core.structure.define_structure import isbridge_tunnel
    if isbridge_tunnel(pos, structure_list) == '터널':
        limit = get_max_span_tunnel(design_speed)
    else:
        limit = get_max_span_straight(design_speed)
    curve_type, r, _ = iscurve(pos, curvelist)
    if curve_type == '곡선':
        limit = min(limit, get_max_span_by_radius(r))
    return limit


def span_check_points(start, end, block=25):
    """경간 한도를 확인할 측점: 시작점, 경간 안의 블록(25m) 경계, 끝점
    (곡선·구조물은 블록 단위라 블록마다 한 번씩 보면 경간이 걸치는 모든 구간을 본다)"""
    points = [start]
    k = math.floor(start / block) + 1
    while k * block < end:
        points.append(k * block)
        k += 1
    points.append(end)
    return points


def get_max_span_between(start, end, design_speed, curvelist=None, structure_list=None):
    """start~end 경간이 걸치는 모든 측점(시작·안쪽 블록·끝) 중 가장 엄격한 최대 경간"""
    return min(get_max_span_at(p, design_speed, curvelist, structure_list) for p in span_check_points(start, end))


def get_span_from(pos, design_speed, curvelist=None, structure_list=None):
    """pos 에서 시작하는 경간 길이: 경간이 걸치는 시작점·끝점·안쪽 모든 블록의 최대 경간을 넘지 않는 값
    (직선에서 시작해 급곡선·터널 안에서 끝나거나, 경간 가운데에만 짧은 급곡선이 있는 경우 포함)"""
    span = get_max_span_at(pos, design_speed, curvelist, structure_list)
    while True:
        limit = get_max_span_between(pos, pos + span, design_speed, curvelist, structure_list)
        if limit >= span:
            return span
        span = limit


def distribute_pole_spacing_flexible(start_m, end_m, curvelist=None,structure_list=None, design_speed=0):
    """
    시작점부터 측점별 최대 경간(get_span_from)으로 전주를 배치.
    마지막 전주는 종점보다 약간 앞에 위치할 수도 있음.

    :param design_speed: 설계속도
    :param structure_list:
    :param curvelist:
    :param start_m: 시작점 (m)
    :param end_m: 끝점 (m)
    :return: 전주 위치 리스트
    """
    start_m = int(start_m)
    end_m = int(end_m)
    positions = [start_m]
    current_pos = start_m
    while current_pos < end_m:
        current_span = get_span_from(current_pos, design_speed, curvelist, structure_list)
        if current_pos + current_span > end_m:
            break
        current_pos += current_span
        positions.append(current_pos)
    return positions

def define_airjoint_section(positions, airjoint_span, tags=None):
    """airjoint_span 배수 근처마다 에어조인트 구간(전주 5개)을 지정. tags: 전주별 구간 값 (기본 단주 2경간)"""
    from bveauto.xref.decats.enums.section_type import AIRJOINT_SEQUENCE
    tags = tuple(tags or AIRJOINT_SEQUENCE)
    airjoint_list = []  # 결과 리스트

    def is_near_multiple_of_DIG(number, tolerance=100):
        """주어진 수가 1200의 배수에 근사하는지 판별하는 함수"""
        remainder = number % airjoint_span
        return number > airjoint_span and (remainder <= tolerance or remainder >= (airjoint_span - tolerance))

    i = 0  # 인덱스 변수
    while i < len(positions) - 1:  # 마지막 전주는 제외
        pos = positions[i]  # 현재 전주 위치

        if is_near_multiple_of_DIG(pos):  # 조건 충족 시
            next_values = positions[i + 1:min(i + 6, len(positions))]  # 다음 5개 값 가져오기
            # (전주 위치, 태그) 쌍을 리스트에 추가 (최대 5개까지만)
            airjoint_list.extend(list(zip(next_values, tags[:len(next_values)])))

            # 다음 5개의 값을 가져왔으므로 인덱스를 건너뛰기
            i += 5
        else:
            i += 1  # 조건이 맞지 않으면 한 칸씩 이동

    return airjoint_list

def generate_postnumbers(lst):
    postnumbers = []
    prev_km = -1
    count = 0

    for number in lst:
        km = number // 1000  # 1000으로 나눈 몫이 같은 구간
        if km == prev_km:
            count += 1  # 같은 구간에서 숫자 증가
        else:
            prev_km = km
            count = 1  # 새로운 구간이므로 count를 0으로 초기화

        postnumbers.append((number, f'{km}-{count}'))

    return postnumbers

def casting_key_str_to_int(dic):
    return {int(k): v for k, v in dic.items()}

def get_block_index(current_track_position, block_interval=25):
    """현재 트랙 위치를 블록 인덱스로 변환"""
    return math.floor(current_track_position / block_interval + 0.001) * block_interval

def find_post_number(lst, pos):
    for arg in lst:
        if arg[0] == pos:
            return arg[1]

def initialrize_tenstion_device(pos, gauge, currentspan, contact_height, system_heigh, y=0, tension_device_length=6.555, cw_height=5.563936, mw_height= 6.04784):
    """장력장치구간 전차선과 조가선 각도 높이를 반환
    Arguments:
        pos: 현재 측점
        gauge: 현재 건식게이지
        currentspan: 현재 스판
        contact_height: 전차선 높이
        system_heigh: 가고
        y: 보정 높이
        tension_device_length: 장력장치 길이
        cw_height: 전차선 높이
        mw_height: 조가선 높이
    Returns:
        slope_degree1: 전차선 종단각도
        slope_degree2: 조가선 종단각도
        h1: 장력장치 전차선 높이
        h2: 장력장치 조가선 높이
        pererall_d: 보정 거리
        sta2: 보정된 전선 측점

    """
    # 전선 각도
    pererall_d, vertical_offset = return_new_point(gauge, currentspan, tension_device_length)  # 선형 시작점에서 전선까지의 거리

    sta2 = pos + vertical_offset  # 전선 시작 측점

    slope_radian1 = math.atan((cw_height - (contact_height + y)) / currentspan)  # 전차선 각도(라디안)
    slope_radian2 = math.atan((mw_height - (contact_height + system_heigh)) / currentspan)  # 조가선 각도(라디안)

    slope_degree1 = math.degrees(slope_radian1)  # 전차선 각도(도)
    slope_degree2 = math.degrees(slope_radian2)  # 조가선 각도(도)

    return slope_degree1, slope_degree2, cw_height, mw_height ,pererall_d, sta2

def offsets(n, s):
    if n == 1:
        return [0.0]
    if n == 2:
        return [-s * 0.5, s * 0.5]
    return [(i - (n - 1) / 2) * s * 0.5 for i in range(n)]

MAX_SPAN_STRAIGHT = {150: 50, 250: 60, 350: 63}
MAX_SPAN_TUNNEL = {150: 40, 250: 45, 350: 50}


def get_max_span_straight(speed):
    try:
        return MAX_SPAN_STRAIGHT[speed]
    except KeyError:
        raise ValueError(f"지원하지 않는 설계속도입니다(직선 최대경간): {speed}") from None


def get_max_span_tunnel(speed):
    try:
        return MAX_SPAN_TUNNEL[speed]
    except KeyError:
        raise ValueError(f"지원하지 않는 설계속도입니다(터널 최대경간): {speed}") from None
