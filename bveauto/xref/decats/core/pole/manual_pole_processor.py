from bveauto.xref.decats.core.alignment.define_funtion import iscurve, isslope
from bveauto.xref.decats.core.pole.normal_section_processor import NormalSectionProcessor
from bveauto.xref.decats.core.pole.poledata import PoleDATA
from bveauto.xref.decats.core.structure.define_structure import isbridge_tunnel
from bveauto.xref.decats.enums.section_type import SectionType
from bveauto.xref.decats.core.alignment.alignment import as_alignment


class ManualPoleProcessor:
    """단일 전주 생성기"""
    @staticmethod
    def create_pole(alignment, db, idxlib ,curvelist, pitchlist,structure_list, pos, post_number, gauge, section, base_type, track="main", side=-1):
        """단일 전주 생성 메서드
        Args:
            alignment: 선형객체
            curvelist: 곡선 리스트
            pitchlist: 구배 리스트
            pos: 측점
            post_number: 전주번호
            gauge: 건식게이지
            section: 구간 str
            base_type: 기본타입 I, O ,F
            track: 트랙 구분 main or sub
            side: 트랙사이드 L, R
        return:
            PoleDATA
        """

        alignment = as_alignment(alignment)
        z = alignment.elevation(pos)
        current_curve, R, c = iscurve(pos, curvelist)
        current_slope, pitch = isslope(pos, pitchlist)
        pos_coord_with_offset = alignment.offset_point(pos, gauge)
        current_structure = isbridge_tunnel(pos, structure_list)
        # PoleDATA 객체 생성
        pole = PoleDATA(
            pos=pos,
            next_pos=None,
            span=None,
            gauge=gauge,
            next_gauge=None,
            structure=current_structure,
            next_structure=None,
            radius=R,
            cant=c,
            pitch=pitch,
            section=SectionType.parse(section),
            post_number=post_number,
            brackets=[],
            mast=None,
            equipments=[],
            z=z,
            next_z=None,
            base_type=base_type,
            next_base_type=None,
            coord=pos_coord_with_offset,
            track=track,
            side=side,
            next_side = None
        )
        NormalSectionProcessor.process(pole, db, idxlib)
        return pole