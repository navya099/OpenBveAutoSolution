from bveauto.xref.decats.core.equipment.equipment_data import EquipmentDATA
from bveauto.xref.decats.enums.component_role import ComponentRole
from bveauto.xref.decats.core.mast.mast_builder import MASTBuilder
from bveauto.xref.decats.core.pole.curve_section_processor import CurveSectionProcessor
from bveauto.xref.decats.core.pole.straight_section_processor import StraightSectionProcessor


class TunnelSectionProcessor:
    @staticmethod
    def process(pole, dataprocessor, idxlib):
        flip = (pole.side == 1)
        if flip:
            bracket_rotation = 180
            mast_raotation = 180
            feeder_rotation = 0
            stagger_flip = True
        else:
            bracket_rotation = 0
            mast_raotation = 0
            feeder_rotation = 180
            stagger_flip = False


        feeder_idx = dataprocessor.get_feeder_insulator_idx(pole.structure)
        feeder_name = idxlib.get_name(feeder_idx)

        if pole.radius == 0:
            StraightSectionProcessor.process(pole, dataprocessor, idxlib, bracket_rotation, stagger_flip=stagger_flip)
        else:
            CurveSectionProcessor.process(pole, dataprocessor, idxlib, bracket_rotation)

        # 터널 특수 규칙 적용
        # 전주 빌더 호출
        mast = MASTBuilder.build(pole, dataprocessor, idxlib, mast_raotation)

        equipment = EquipmentDATA(name=feeder_name, index=feeder_idx,
                                  offset=(pole.gauge * -1, 0), rotation=feeder_rotation,
                                  type='급전선설비', role=ComponentRole.FEEDER)
        pole.mast = mast
        pole.equipments.append(equipment)