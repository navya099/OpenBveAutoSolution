from bveauto.xref.decats.core.mast.base.mast_base import MastBase
from bveauto.xref.decats.core.mast.mast_accessory.accessory_builder import AccessoryBuilder
from bveauto.xref.decats.core.mast.mastdata import Mast
from bveauto.xref.decats.enums.component_role import ComponentRole
from bveauto.xref.decats.core.pole.poledata import PoleDATA



class MASTBuilder:
    """전주 관련 빌더(기둥, 기초, 악세서리)"""
    @staticmethod
    def build(pole: PoleDATA, dataprocessor, idxlib, rotation: float, as_normal: bool = False) -> Mast:
        """as_normal: 구간 전주라도 일반개소 기둥·밴드로 (복주 에어조인트의 쌍 전주 — 전주마다 브래킷 1개)"""
        section = None if as_normal else pole.section
        #기둥
        mast_index = dataprocessor.get_mast_index(pole.structure, section)
        mast_name = idxlib.get_name(mast_index)

        #기초
        foundation_idx = dataprocessor.get_post_base(pole.structure)
        foundation_name = idxlib.get_name(foundation_idx)

        #교량구간 offset -> 교량은 0.381만큼 올려야함
        yoffset = MASTBuilder.get_yoffset(dataprocessor, pole.structure)
        #전주용 밴드 2개
        # 밴드
        accessories = []
        speed = dataprocessor.get_design_speed()
        if section is None:

             size = 'P10' if speed == 150 or speed == 250 else 'H250'
             accessories += AccessoryBuilder.build(dataprocessor, idxlib, '가동브래킷용', size, pole.structure, rotation,
                                                   pole.gauge)
             accessories += AccessoryBuilder.build(dataprocessor, idxlib, '완철용', size, pole.structure, rotation,
                                                   pole.gauge)
             if dataprocessor.get_extra_band_index():
                 extra_band_dictionray = dataprocessor.get_extra_band_index()
                 for key, value in extra_band_dictionray.items():
                     accessories += AccessoryBuilder.build(dataprocessor, idxlib, key, size, pole.structure, rotation,
                                                           pole.gauge)
        else:
            size ='P12'if speed == 150 or speed == 250 else 'H300'
            accessories += AccessoryBuilder.build(dataprocessor, idxlib, '완철용', size, pole.structure, rotation,
                                               pole.gauge)

        base = MastBase(name=foundation_name, index=foundation_idx, offset=(pole.gauge,0), rotation=rotation,
                        role=ComponentRole.FOUNDATION)


        tunnel = pole.structure == '터널'           # 터널은 기둥 대신 하수강 (규격 P10/P12 는 밴드용 구분이라 기록 안 함)
        return Mast(name=mast_name, index=mast_index, offset=(pole.gauge,yoffset), rotation=rotation, base=base,
                    accessories=accessories, role=ComponentRole.HANGER if tunnel else ComponentRole.MAST,
                    spec='' if tunnel else size)

    @staticmethod
    def get_yoffset(dataprocessor, structure: str) -> float:
        speed = dataprocessor.get_design_speed()
        if speed == 150 or speed == 250:
            return 0.381 if structure == '교량' else 0
        else:
            return 0