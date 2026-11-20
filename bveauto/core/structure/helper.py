# 오브젝트 딕셔너리 (교량, 터널)
OBJECT_DICTIONARY = {
    150: {'토공': (32, 32), '교량': (28, 33), '터널': (51, 22)},
    250: {'토공': (62, 21), '교량': (28, 33), '터널': (51, 22)},
    350: {'토공': (9, 1), '교량': (88, 81), '터널': (91, 80)}
}

# 오브젝트 딕셔너리 (교량, 터널)
ERATH_AND_PORTAL_OBJECT_DICTIONARY = {
    150: {'토공압성토': (480, 480), '터널시점갱문': (60, 77), '터널종점갱문': (61, 77)},
    250: {'토공압성토': (480, 480), '터널시점갱문': (60, 77), '터널종점갱문': (61, 77)},
    350: {'토공압성토': (480, 480), '터널시점갱문': (0, 174), '터널종점갱문': (0, 174)},
}

def get_obj_index(design_speed, line_count):
    """
    설계 속도와 선로 개수에 따라 교량 및 터널의 객체 인덱스를 반환하는 함수
    param design_speed: 설계 속도 (int)
    param line_count: 선로 개수 (int) (1: 단선, 2 이상: 복선)
    return: (교량 인덱스, 터널 인덱스) -> (idx_br, idx_tn)
    """


    # 유효한 설계 속도 확인
    if design_speed not in OBJECT_DICTIONARY:
        raise ValueError(f"Invalid DESIGNSPEED: {design_speed}. Valid values are {list(OBJECT_DICTIONARY.keys())}.")

    # 단선(1)일 경우 [0], 복선(2 이상)일 경우 [1] 반환
    idx_E = OBJECT_DICTIONARY[design_speed]['토공'][0] if line_count == 1 else OBJECT_DICTIONARY[design_speed]['토공'][1]
    idx_br = OBJECT_DICTIONARY[design_speed]['교량'][0] if line_count == 1 else OBJECT_DICTIONARY[design_speed]['교량'][1]
    idx_tn = OBJECT_DICTIONARY[design_speed]['터널'][0] if line_count == 1 else OBJECT_DICTIONARY[design_speed]['터널'][1]

    return idx_E, idx_br, idx_tn


def get_earthwork_embank_index(design_speed, line_count):
    """
    설계 속도와 선로 개수에 따라 토공 압성토 객체 인덱스를 반환하는 함수
    param DESIGNSPEED: 설계 속도 (int)
    param LINECOUNT: 선로 개수 (int) (1: 단선, 2 이상: 복선)
    return: (교량 인덱스, 터널 인덱스) -> (idx_br, idx_tn)
    """


    # 유효한 설계 속도 확인
    if design_speed not in ERATH_AND_PORTAL_OBJECT_DICTIONARY:
        raise ValueError(f"Invalid DESIGNSPEED: {design_speed}. Valid values are {list(OBJECT_DICTIONARY.keys())}.")

    # 단선(1)일 경우 [0], 복선(2 이상)일 경우 [1] 반환
    idx_E = ERATH_AND_PORTAL_OBJECT_DICTIONARY[design_speed]['토공압성토'][0] if line_count == 1 else OBJECT_DICTIONARY[design_speed]['토공압성토'][1]
    idx_br = ERATH_AND_PORTAL_OBJECT_DICTIONARY[design_speed]['터널시점갱문'][0] if line_count == 1 else \
    ERATH_AND_PORTAL_OBJECT_DICTIONARY[design_speed]['터널시점갱문'][1]
    idx_tn = ERATH_AND_PORTAL_OBJECT_DICTIONARY[design_speed]['터널종점갱문'][0] if line_count == 1 else \
    ERATH_AND_PORTAL_OBJECT_DICTIONARY[design_speed]['터널종점갱문'][1]

    return idx_E, idx_br, idx_tn