"""에어조인트(2경간, 단주·복주) 전주별 브래킷·설비

    1호주(AJ_START)  일반 개소 구성 + 장력장치·지선 (무효선 시작)
    2호주(AJ_2)      F형(무효선 인상) + AJ형 I 브래킷
    3호주(AJ_MIDDLE) AJ형 I + AJ형 O 브래킷 (평행 개소 가운데)
    4호주(AJ_4)      AJ형 O + F형 브래킷
    5호주(AJ_END)    일반 개소 구성 + 장력장치·지선 (무효선 끝)
복주 에어조인트는 같은 위치 역할(section_role)의 규칙으로 만든 뒤 AirJointProcessor 가 전주 2개로 나눈다.
"""
from bveauto.xref.decats.core.airjoint.aj_data_context import AirjointDataContext
from bveauto.xref.decats.core.bracket.section_bracket_builder import SectionBracketBuilder
from bveauto.xref.decats.core.pole.poledata import PoleDATA
from bveauto.xref.decats.enums.section_type import SectionType, section_role


class AirjointBracketAdder(SectionBracketBuilder):
    OFFSET_GETTER = 'get_airjoint_offset'

    def __init__(self, params: AirjointDataContext, dataprocessor, idxlib):
        super().__init__(params, dataprocessor, idxlib)

    def add_airjoint_brackets(self, pole: PoleDATA, polyline_with_sta):
        """에어조인트 각 구간별 브래킷 추가 (복주 에어조인트도 같은 위치 역할의 규칙 사용)"""
        role = section_role(pole.section)
        if role == SectionType.AJ_START:
            self.base_components(pole)
            self.add_anchor(pole, polyline_with_sta)
        elif role == SectionType.AJ_2:
            self.add_common_equipts(pole)
            self.add_f_and_aj_brackets(pole)
        elif role == SectionType.AJ_MIDDLE:
            self.add_common_equipts(pole)
            self.add_middle_brackets(pole, ('AJ형_중간1', 'I'), ('AJ형_중간2', 'O'))
        elif role == SectionType.AJ_4:
            self.add_common_equipts(pole)
            self.add_f_and_aj_brackets(pole, end=True)
        elif role == SectionType.AJ_END:
            self.base_components(pole)
            self.add_anchor(pole, polyline_with_sta, end=True, flip_side=1)

    def add_f_and_aj_brackets(self, pole, end=False):
        """2호주: F형(시점) → AJ형 I(시점), 4호주: AJ형 O(끝) → F형(끝)"""
        f_bracket, aj_bracket = self.params.f_bracket_valuse, self.params.aj_bracket_values
        pole.brackets.clear()
        if not end:
            self.add_f_bracket(pole, f_bracket['I'], *self.side_offset(pole, 'F형_시점', flip_side=-1), spec='I')
            self.add_paired_bracket(pole, 'I', aj_bracket['I'], *self.side_offset(pole, 'AJ형_시점', flip_side=-1))
        else:
            self.add_paired_bracket(pole, 'O', aj_bracket['O'], *self.side_offset(pole, 'AJ형_끝', flip_side=1),
                                    end=True)
            self.add_f_bracket(pole, f_bracket['O'], *self.side_offset(pole, 'F형_끝', flip_side=1), spec='O')

    # 이전 이름 호환
    add_aj_bracket = SectionBracketBuilder.add_paired_bracket
