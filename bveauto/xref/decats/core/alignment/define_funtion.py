from bveauto.xref.decats.utils.comom_util import get_block_index


def iscurve(cur_sta, curve_list):
    """sta가 곡선 구간에 해당하는지 구분하는 함수"""
    rounded_sta = get_block_index(cur_sta)  # 25 단위로 반올림

    lookup = getattr(curve_list, 'lookup', None)  # Alignment.curvelist: 블록 측점으로 바로 조회
    rows = [lookup(rounded_sta)] if lookup else curve_list
    for row in rows:
        if row is None:
            break
        sta, R, c = row
        if rounded_sta == sta:
            if R == 0:
                return '직선', 0, 0  # 반경이 0이면 직선
            return '곡선', R, c  # 반경이 존재하면 곡선

    return '직선', 0, 0  # 목록에 없으면 기본적으로 직선 처리


def isslope(cur_sta, curve_list):
    """sta가 곡선 구간에 해당하는지 구분하는 함수"""
    rounded_sta = get_block_index(cur_sta)  # 25 단위로 반올림

    lookup = getattr(curve_list, 'lookup', None)  # Alignment.pitchlist: 블록 측점으로 바로 조회
    rows = [lookup(rounded_sta)] if lookup else curve_list
    for row in rows:
        if row is None:
            break
        sta, g = row
        if rounded_sta == sta:
            if g == 0:
                return '수평', 0  # 반경이 0이면 직선
            else:
                return '기울기', f'{g * 1000:.2f}'

    return '수평', 0  # 목록에 없으면 기본적으로 직선 처리