from bveauto.xref.decats.core.equipment.equipment_data import EquipmentDATA
from bveauto.xref.decats.enums.component_role import ComponentRole
from bveauto.xref.decats.core.mast.mast_builder import MASTBuilder
from bveauto.xref.decats.core.pole.curve_section_processor import CurveSectionProcessor
from bveauto.xref.decats.core.pole.poledata import PoleDATA
from bveauto.xref.decats.core.pole.straight_section_processor import StraightSectionProcessor



class NormalSectionProcessor:
    @staticmethod
    def process(pole: PoleDATA, dataprocessor, idxlib):
        """노말구간 데이터 생성"""
        #공통변수
        flip = True if pole.side == 1 else False

        # 급전선 설비 인덱스 가져오기
        feeder_idx = dataprocessor.get_feeder_insulator_idx(pole.structure)
        feeder_name = idxlib.get_name(feeder_idx)

        #베이스타입 뒤집기
        if flip:
            rotation = 180
        else:
            rotation = 0

        #브래킷 빌더 호출
        if pole.radius == 0:
            StraightSectionProcessor.process(pole, dataprocessor, idxlib, rotation, stagger_flip=flip)
        else:
            CurveSectionProcessor.process(pole, dataprocessor, idxlib, rotation)


        #전주 빌더 호출
        mast = MASTBuilder.build(pole, dataprocessor, idxlib, rotation)

        #급전선 설비
        equipment = EquipmentDATA(name=feeder_name,index=feeder_idx, offset=(pole.gauge,0),rotation=rotation,type='급전선설비', role=ComponentRole.FEEDER)

        #pole에 기록
        pole.mast = mast
        pole.equipments.append(equipment)
