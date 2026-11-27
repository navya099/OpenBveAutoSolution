"""에어섹션(단일·이중) 전주별 브래킷·설비

    AS1_1          일반 개소 구성 + 장력장치·지선 (1구간 무효선 시작)
    AS1_2          F형(시점) → AS형 I(시점)
    AS1_3 AS2_2    AS형 O(중간1) + AS형 I(중간2) (평행 개소 가운데)
    AS1_4_S        AS형 I(끝) → F형(끝)  [단일 에어섹션]
    AS1_4_D        AS1_4_S + 장력장치·지선 (2구간 무효선 시작)  [이중 에어섹션 가운데]
    AS1_5          일반 개소 구성 + 장력장치·지선 (무효선 끝)
    AS2_1          F형(끝) → AS형 I(끝) + 인류장치·지선
    AS2_3          AS형 I(시점) → F형(시점)
    AS2_4          일반 개소 구성 + 인류장치·지선
F형 브래킷은 O, AS형 브래킷은 I 를 쓴다 (가운데 전주만 O + I).
"""
from bveauto.xref.decats.core.airjoint.aj_data_context import AirjointDataContext
from bveauto.xref.decats.core.bracket.section_bracket_builder import SectionBracketBuilder
from bveauto.xref.decats.core.pole.poledata import PoleDATA
from bveauto.xref.decats.dataset.bveauto.xref.decats.dataset_getter import bveauto.xref.decats.datasetGetter
from bveauto.xref.decats.enums.section_type import SectionType

# 브래킷 쌍 전주: (F형 오프셋, AS형 오프셋, x 를 반전할 방향, AS형이 먼저인지)
PAIRS = {
    SectionType.AS1_2: ('F형_시점', 'AS형_시점', 1, False),
    SectionType.AS1_4_S: ('F형_끝', 'AS형_끝', -1, True),
    SectionType.AS1_4_D: ('F형_끝', 'AS형_끝', -1, True),
    SectionType.AS2_1: ('F형_끝', 'AS형_끝', -1, False),
    SectionType.AS2_3: ('F형_시점', 'AS형_시점', 1, True),
}


class AirSectionBracketAdder(SectionBracketBuilder):
    OFFSET_GETTER = 'get_airsection_offset'

    def __init__(self, params: AirjointDataContext, dataprocessor: bveauto.xref.decats.datasetGetter, idxlib, mode):
        super().__init__(params, dataprocessor, idxlib)
        self.mode = mode

    def add_airsection_brackets(self, pole: PoleDATA, polyline_with_sta):
        """에어섹션 각 구간별 브래킷 추가"""
        section = pole.section
        if section == SectionType.AS1_1:
            self.base_components(pole)
            self.add_anchor(pole, polyline_with_sta)
        elif section in PAIRS:
            f_name, as_name, flip_side, as_first = PAIRS[section]
            self.add_common_equipts(pole)
            self.add_f_and_as_brackets(pole, *self.side_offset(pole, f_name, flip_side),
                                       *self.side_offset(pole, as_name, flip_side), end=as_first)
            if section == SectionType.AS1_4_D:
                self.add_anchor(pole, polyline_with_sta)                          # 2구간 무효선 시작
            elif section == SectionType.AS2_1:
                self.add_anchor(pole, polyline_with_sta, equipment='인류장치', end=True, flip_side=-1)
        elif section in (SectionType.AS1_3, SectionType.AS2_2):
            self.add_common_equipts(pole)
            self.add_middle_brackets(pole, ('AS형_중간1', 'O'), ('AS형_중간2', 'I'))
        elif section == SectionType.AS1_5:
            self.base_components(pole)
            self.add_anchor(pole, polyline_with_sta, end=True, flip_side=1)
        elif section == SectionType.AS2_4:
            self.base_components(pole)
            self.add_anchor(pole, polyline_with_sta, equipment='인류장치', end=True, flip_side=1)

    def add_f_and_as_brackets(self, pole, f_x, f_y, as_x, as_y, end=False):
        """F형(O) 과 AS형(I) 브래킷. end=True 면 AS형을 먼저"""
        f_o = self.params.f_bracket_valuse['O']
        as_i = self.params.aj_bracket_values['I']
        pole.brackets.clear()
        if not end:
            self.add_f_bracket(pole, f_o, f_x, f_y, spec='O')
            self.add_paired_bracket(pole, 'I', as_i, as_x, as_y)
        else:
            self.add_paired_bracket(pole, 'I', as_i, as_x, as_y)
            self.add_f_bracket(pole, f_o, f_x, f_y, spec='O')

    # 이전 이름 호환
    add_as_bracket = SectionBracketBuilder.add_paired_bracket
