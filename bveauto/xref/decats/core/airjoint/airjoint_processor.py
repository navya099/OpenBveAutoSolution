from bveauto.xref.decats.core.airjoint.aj_bracket_adder import AirjointBracketAdder
from bveauto.xref.decats.core.mast.mast_builder import MASTBuilder
from bveauto.xref.decats.core.airjoint.aj_data_context import AirjointDataContext
import copy

from bveauto.xref.decats.core.pole.poledata import TwinPole
from bveauto.xref.decats.enums.section_type import DOUBLE_POLE_PAIRED_ROLES, SectionType, section_role


class AirJointProcessor:
    @staticmethod
    def process(pole, polyline_with_sta, dataprocessor, idxlib):
        """에어조인트 구간별 전주 데이터 생성"""
        # 데이터 가져오기
        contact_wire_fitting, messenger_wire_fittings, steady_arm_fittings = dataprocessor.get_fittings()
        mast_idx = dataprocessor.get_mast_index(pole.structure, pole.section)
        mast_name = idxlib.get_name(mast_idx)
        f_bracket_valuse = dataprocessor.get_bracket_codes('F브래킷', pole.structure)
        aj_bracket_values = dataprocessor.get_bracket_codes('에어조인트', pole.structure)

        # 급전선 설비 인덱스 가져오기
        feeder_idx = dataprocessor.get_feeder_insulator_idx(pole.structure)
        feeder_name =idxlib.get_name(feeder_idx)
        # 평행틀 설비 인덱스 가져오기
        length = '1.6m' if section_role(pole.section) == SectionType.AJ_MIDDLE else '1m'
        spreader_idx = dataprocessor.get_spreader_idx(pole.structure, length)
        spreader_name = idxlib.get_name(spreader_idx)
        #F브래킷 인상높이
        f_bracket_height = dataprocessor.get_airjoint_f_bracket_height()

        # 모든 필요한 값들을 전달
        context = AirjointDataContext(
            contact_wire_fitting=contact_wire_fitting,
            messenger_wire_fittings=messenger_wire_fittings,
            steady_arm_fitting=steady_arm_fittings,
            mast_type=mast_idx,
            mast_name=mast_name,
            aj_bracket_values=aj_bracket_values,
            f_bracket_valuse=f_bracket_valuse,
            feeder_idx=feeder_idx,
            feeder_name=feeder_name,
            spreader_name=spreader_name,
            spreader_idx=spreader_idx,
            f_bracket_height=f_bracket_height
        )
        # 에어조인트 구간별 처리(2호주 ,3호주, 4호주)
        adder = AirjointBracketAdder(context, dataprocessor, idxlib)
        adder.add_airjoint_brackets(pole, polyline_with_sta)
        pole.twin = None
        section = SectionType.parse(pole.section)
        if section is not None and section.is_double_pole and section.role in DOUBLE_POLE_PAIRED_ROLES:
            AirJointProcessor.split_double_pole(pole, dataprocessor, idxlib)

    @staticmethod
    def split_double_pole(pole, dataprocessor, idxlib):
        """복주: 단주 규칙으로 만든 브래킷 2개를 전주 2개에 1개씩 나눈다.
        앞 전주(측점 − 간격/2) = 첫 번째 브래킷, 뒤 전주(측점 + 간격/2) = 두 번째 브래킷.
        전주마다 브래킷이 1개라 평행틀은 두지 않고, 기둥은 일반개소 기둥.
        급전선설비는 데이터셋 airjoint.double_pole.feeder: both = 두 전주 모두, front = 앞 전주만."""
        settings = dataprocessor.get_double_pole_settings()
        for i, bracket in enumerate(pole.brackets):
            bracket.on_twin = i >= 1
        pole.equipments = [e for e in pole.equipments if e.type != '평행틀']
        if pole.mast is not None:  # 터널은 기둥 대신 브래킷 피팅(H형강)
            pole.mast = MASTBuilder.build(pole, dataprocessor, idxlib, rotation=pole.mast.rotation, as_normal=True)
        twin_equipments = []
        if settings['feeder'] == 'both':
            twin_equipments = [copy.deepcopy(e) for e in pole.equipments if e.type == '급전선설비']
        pole.twin = TwinPole(spacing=settings['spacing'], mast=copy.deepcopy(pole.mast), equipments=twin_equipments)