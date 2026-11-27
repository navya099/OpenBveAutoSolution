"""에어조인트·에어섹션 공통 브래킷·설비 구성 (평행 개소 전주)

에어조인트(bveauto.xref.decats.core/airjoint/aj_bracket_adder.py)와 에어섹션(bveauto.xref.decats.core/airsection/as_bracket_adder.py)은
같은 부품(F형 브래킷, AJ형 브래킷, 급전선설비·평행틀, 장력장치·인류장치 + 지선)을 쓰고 위치 오프셋 표만 다르다.
OFFSET_GETTER 로 데이터셋 오프셋 표(airjoint / airsection)를 고른다.
"""
from bveauto.xref.decats.core.alignment.alignment import as_alignment
from bveauto.xref.decats.core.bracket.bracket_data import BracketDATA
from bveauto.xref.decats.core.bracket.fitting_data import FittingDATA
from bveauto.xref.decats.core.equipment.equipment_data import EquipmentDATA
from bveauto.xref.decats.core.mast.mast_builder import MASTBuilder
from bveauto.xref.decats.core.pole.normal_section_processor import NormalSectionProcessor
from bveauto.xref.decats.core.pole.poledata import PoleDATA
from bveauto.xref.decats.core.pole.tunnel_section_processor import TunnelSectionProcessor
from bveauto.xref.decats.enums.component_role import EQUIPMENT_TYPE_ROLE, ComponentRole


class SectionBracketBuilder:
    OFFSET_GETTER = None   # 'get_airjoint_offset' | 'get_airsection_offset'

    def __init__(self, params, dataprocessor, idxlib):
        self.params = params            # AirjointDataContext (브래킷·피팅·설비 인덱스)
        self.prosc = dataprocessor
        self.idxlib = idxlib

    # ── 오프셋 ──────────────────────────────────────
    def offset(self, name):
        """데이터셋 오프셋 (x, y)"""
        value = getattr(self.prosc, self.OFFSET_GETTER)(name)
        return value.get('x'), value.get('y')

    def side_offset(self, pole, name, flip_side):
        """오프셋 (x, y), 전주 방향이 flip_side 이면 x 반전"""
        x, y = self.offset(name)
        return (-x if pole.side == flip_side else x), y

    # ── 전주 구성 ────────────────────────────────────
    def base_components(self, pole):
        """구간 시작·끝 전주: 일반 개소(터널은 터널) 구성"""
        if pole.structure == '터널':
            TunnelSectionProcessor.process(pole, self.prosc, self.idxlib)
        else:
            NormalSectionProcessor.process(pole, self.prosc, self.idxlib)

    def add_anchor(self, pole, polyline_with_sta, equipment='장력장치', end=False, flip_side=1):
        """장력장치(또는 인류장치) + 지선(터널 제외).
        시작(end=False): F형 시점 쪽 무효선 방향 — 전주 게이지 → 다음 전주 F형 시점 x(좌측이면 반전), 회전 = 각도
        끝(end=True):    F형 끝 x(방향이 flip_side 면 반전) → 다음 전주 게이지, 회전 = 180 + 각도, 지선 180"""
        al = as_alignment(polyline_with_sta)
        index = self.prosc.get_equipment_index(equipment)
        if not end:
            x = self.offset('F형_시점')[0]
            if pole.side == -1:
                x *= -1
            rotation = al.wire_angle(pole.pos, pole.next_pos, pole.gauge, x)
            guy_rotation = 0
        else:
            x = self.offset('F형_끝')[0]
            if pole.side == flip_side:
                x *= -1
            rotation = 180 + al.wire_angle(pole.pos, pole.next_pos, x, pole.next_gauge)
            guy_rotation = 180
        pole.equipments.append(EquipmentDATA(name=self.idxlib.get_name(index), index=index, offset=(pole.gauge, 0),
                                             rotation=rotation, type=equipment, role=EQUIPMENT_TYPE_ROLE[equipment]))
        if pole.structure != '터널':
            guy = self.prosc.get_equipment_index('지선')
            pole.equipments.append(EquipmentDATA(name=self.idxlib.get_name(guy), index=guy, offset=(pole.gauge, 0),
                                                 rotation=guy_rotation, type='지선설비', role=ComponentRole.GUY))

    def add_common_equipts(self, pole):
        """평행 개소 공통 설비: 기둥(터널 제외), 급전선설비, 평행틀(터널 제외)"""
        p = self.params
        if pole.structure == '터널':
            feeder_rotation = 180 if pole.side == -1 else 0
            pole.equipments.append(EquipmentDATA(name=p.feeder_name, index=p.feeder_idx, offset=(pole.gauge * -1, 0),
                                                 rotation=feeder_rotation, type='급전선설비', role=ComponentRole.FEEDER))
            return
        mast_rotation = 180 if pole.side == 1 else 0
        pole.mast = MASTBuilder.build(pole, dataprocessor=self.prosc, idxlib=self.idxlib, rotation=mast_rotation)
        pole.equipments.append(EquipmentDATA(name=p.feeder_name, index=p.feeder_idx, offset=(pole.gauge, 0),
                                             rotation=mast_rotation, type='급전선설비', role=ComponentRole.FEEDER))
        pole.equipments.append(EquipmentDATA(name=p.spreader_name, index=p.spreader_idx, offset=(pole.gauge, 0),
                                             rotation=mast_rotation, type='평행틀', role=ComponentRole.SPREADER))

    # ── 브래킷 ──────────────────────────────────────
    def _cw_mw_heights(self, pole):
        sys_height, cw_height = self.prosc.get_contact_wire_and_massanger_wire_info(pole.structure)
        return cw_height, cw_height + sys_height

    def _tunnel_hanger(self, pole, bracket, rotation):
        """터널: 브래킷을 다는 H형강 하수강 (기둥 대신)"""
        if pole.structure == '터널':
            self.add_bracket_fittng(bracket, self.params.mast_type, self.params.mast_name, (pole.gauge, 0), rotation,
                                    ComponentRole.HANGER)

    def add_f_bracket(self, pole: PoleDATA, bracket_code, x1, y1, spec=''):
        """F형 가동 브래킷(무효선 인상) 및 금구류"""
        p = self.params
        rotation = 180 if pole.side == 1 else 0
        cw_height, mw_height = self._cw_mw_heights(pole)
        h = p.f_bracket_height
        bracket = BracketDATA(bracket_type='F', index=bracket_code, bracket_name=self.idxlib.get_name(bracket_code),
                              offset=(0, h), rotation=rotation, role=ComponentRole.BRACKET_F, spec=spec)
        cw_fitting = p.contact_wire_fitting
        mw_fitting = p.messenger_wire_fittings['무효인상용']
        steady_arm = (p.steady_arm_fitting.get('F') or {}).get('R')
        self.add_bracket_fittng(bracket, cw_fitting, self.idxlib.get_name(cw_fitting), (x1, cw_height + y1), rotation,
                                ComponentRole.FIT_CW)
        self.add_bracket_fittng(bracket, mw_fitting, self.idxlib.get_name(mw_fitting), (x1, mw_height + h), rotation,
                                ComponentRole.FIT_MW, '무효인상용')
        if steady_arm:
            self.add_bracket_fittng(bracket, steady_arm, self.idxlib.get_name(steady_arm), (x1, y1 + cw_height),
                                    rotation, ComponentRole.FIT_STEADY, 'R')
        self._tunnel_hanger(pole, bracket, rotation)
        pole.brackets.append(bracket)

    def add_paired_bracket(self, pole: PoleDATA, bracket_type, bracket_code, x1, y1, end=False):
        """AJ형 가동 브래킷(평행 개소) 및 금구류. 곡선당김금구는 시작 쪽 L, 끝 쪽(end) R"""
        p = self.params
        rotation = 180 if pole.side == 1 else 0
        cw_height, mw_height = self._cw_mw_heights(pole)
        bracket = BracketDATA(bracket_type='AJ', index=bracket_code, bracket_name=self.idxlib.get_name(bracket_code),
                              offset=(0, y1), rotation=rotation, role=ComponentRole.BRACKET_AJ, spec=bracket_type)
        mw_fitting = p.messenger_wire_fittings['에어조인트용']
        steady_arm = p.steady_arm_fitting[bracket_type]['R' if end else 'L']
        self.add_bracket_fittng(bracket, mw_fitting, self.idxlib.get_name(mw_fitting), (x1, mw_height + y1), rotation,
                                ComponentRole.FIT_MW, '에어조인트용')
        self.add_bracket_fittng(bracket, steady_arm, self.idxlib.get_name(steady_arm), (x1, cw_height), rotation,
                                ComponentRole.FIT_STEADY, 'R' if end else 'L')
        self._tunnel_hanger(pole, bracket, rotation)
        pole.brackets.append(bracket)

    def add_middle_brackets(self, pole, first, second):
        """가운데 전주: AJ형 브래킷 2개. first/second = (오프셋 이름, 브래킷 타입 I/O)
        첫 번째는 좌측(side −1)일 때, 두 번째는 우측일 때 x 반전, 두 번째 곡선당김금구는 R"""
        pole.brackets.clear()
        values = self.params.aj_bracket_values
        (name1, type1), (name2, type2) = first, second
        x, y = self.side_offset(pole, name1, flip_side=-1)
        self.add_paired_bracket(pole, type1, values.get(type1), x, y)
        x, y = self.side_offset(pole, name2, flip_side=1)
        self.add_paired_bracket(pole, type2, values.get(type2), x, y, end=True)

    @staticmethod
    def add_bracket_fittng(bracket, idx, label, offset, rotation, role='', spec=''):
        bracket.fittings.append(FittingDATA(index=idx, label=label, offset=offset, rotation=rotation, role=role,
                                            spec=spec))
