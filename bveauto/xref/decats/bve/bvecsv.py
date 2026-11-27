from bveauto.xref.decats.enums.section_type import SectionType, section_role
from bveauto.xref.decats.enums.section_type import section_label as section_label_of


class BVECSV:
    """BVE CSV 구문을 생성하는 클래스
    Attributes:
        poledata (PoleDATAManager): PoleDATAManager.poledata 인스턴스
        wiredata (WireDataManager): WireDataManager.wiredata 인스턴스
        lines (list[str]]): 구문 정보를 저장할 문자열 리스트
    """

    def __init__(self, poledata=None, wiredata=None, track_index=None):
        self.poledata = poledata  # ✅ PoleDATAManager.poledata 인스턴스를 가져옴
        self.wiredata = wiredata
        self.track_index = track_index
        self.lines = []
        self.errors = []   # CSV 에서 빠진 전주·전선 ("측점: 오류") → 저장 시 알림

    def create_pole_csv(self):
        """전주 구문 생성 메서드"""
        self.lines = []
        self.errors = [e for e in self.errors if '전주 CSV' not in e]

        def write_equipment(pos, eqs):
            for eq in eqs:
                if eq:
                    if eq.index:
                        self.lines.append(
                            f'{pos},.freeobj {self.track_index};{eq.index};{eq.offset[0]};{eq.offset[1]};{eq.rotation};,;{eq.name}\n'
                        )

        def write_mast(pos, mast):
            if mast is not None:
                if mast.index:
                    self.lines.append(
                        f'{pos},.freeobj {self.track_index};{mast.index};{mast.offset[0]};{mast.offset[1]};{mast.rotation};,;{mast.name}\n'
                    )

        def write_mast_accessories(pos: str, mast) -> None:
            if mast and mast.accessories:
                for ac in mast.accessories:
                    if ac:
                        if ac.index:
                            line = (
                                f"{pos},.freeobj {self.track_index};"
                                f"{ac.index};{ac.offset[0]};{ac.offset[1]};"
                                f"{ac.rotation};,;{ac.name}\n"
                            )
                            self.lines.append(line)
        def write_base(pos, mast):
            if mast:
                if mast.base:
                    base = mast.base
                    if base.index:
                        self.lines.append(
                            f'{pos},.freeobj {self.track_index};{base.index};{base.offset[0]};{base.offset[1]};{base.rotation};,;{base.name}\n'
                        )

        def write_brackets(pos, brs):
            for br in brs:
                self.lines.append(
                    f'{pos},.freeobj {self.track_index};{br.index};{br.offset[0]};{br.offset[1]};{br.rotation},;{br.bracket_name}\n'
                )
                write_fittings(pos, br.fittings)

        def write_fittings(pos, fittings):
            for fit in fittings:
                if fit:
                    if fit.index:
                        self.lines.append(
                            f'{pos},.freeobj {self.track_index};{fit.index};{fit.offset[0]};{fit.offset[1]};{fit.rotation};,;{fit.label}\n'
                        )

        pos = 0
        for pole in self.poledata:
            try:
                pos = pole.pos
                post_number = pole.post_number
                section = pole.section
                structure = pole.structure
                curve = '직선' if pole.radius == 0.0 else '곡선'
                eqs = pole.equipments
                brs = pole.brackets
                mast = pole.mast
                section_label = section_label_of(pole)

                self.lines.append(f',;{post_number}\n')
                self.lines.append(f',;-----{section_label}({structure})({curve})-----\n')

                if getattr(pole, 'twin', None) is not None:
                    # 복주: 주 전주(측점 − 간격/2)와 두 번째 전주(측점 + 간격/2)에 기둥·설비·브래킷을 따로 기록
                    front_offset, rear_offset = pole.station_offsets
                    for offset, p_mast, p_eqs, on_twin in ((front_offset, mast, eqs, False),
                                                           (rear_offset, pole.twin.mast, pole.twin.equipments, True)):
                        p = round(pos + offset, 6)
                        self.lines.append(f',;{post_number}-{"B" if on_twin else "F"} (복주 {"뒤" if on_twin else "앞"} 전주)\n')
                        write_mast(p, p_mast)
                        write_mast_accessories(p, p_mast)
                        write_base(p, p_mast)
                        write_equipment(p, p_eqs)
                        for br in brs:
                            if bool(getattr(br, 'on_twin', False)) == on_twin:
                                self.lines.append(',;가동브래킷구문\n')
                                write_brackets(p, [br])

                elif section_role(section) in [SectionType.AJ_START, SectionType.AJ_END]:
                    write_mast(pos, mast)
                    write_mast_accessories(pos, mast)
                    write_base(pos, mast)
                    write_brackets(pos, [brs[0]])
                    write_equipment(pos, eqs)

                elif section_role(section) in [SectionType.AJ_2, SectionType.AJ_MIDDLE, SectionType.AJ_4]:
                    poss = (pos - 0.528, pos + 0.528) if section_role(section) in [SectionType.AJ_2, SectionType.AJ_4] else (
                    pos - 0.8, pos + 0.8)
                    write_mast(pos, mast)
                    write_mast_accessories(pos, mast)
                    write_base(pos, mast)
                    write_equipment(pos, eqs)
                    for p, br in zip(poss, brs):
                        self.lines.append(',;가동브래킷구문\n')
                        write_brackets(p, [br])

                elif section in [SectionType.AS1_1, SectionType.AS1_5, SectionType.AS2_4]:
                    write_mast(pos, mast)
                    write_mast_accessories(pos, mast)
                    write_base(pos, mast)
                    write_brackets(pos, [brs[0]])
                    write_equipment(pos, eqs)

                elif section in [SectionType.AS1_2, SectionType.AS1_3, SectionType.AS1_4_S,SectionType.AS1_4_D, SectionType.AS2_1, SectionType.AS2_2, SectionType.AS2_3]:
                    # 에어섹션 평행개소는 모두 ±0.528 오프셋 (elif 조건과 동일 목록이라 else 분기는 도달 불가였음)
                    poss = (pos - 0.528, pos + 0.528)
                    write_mast(pos, mast)
                    write_mast_accessories(pos, mast)
                    write_base(pos, mast)
                    write_equipment(pos, eqs)
                    for p, br in zip(poss, brs):
                        self.lines.append(',;가동브래킷구문\n')
                        write_brackets(p, [br])

                else:
                    write_equipment(pos, eqs)
                    write_mast(pos, mast)
                    write_mast_accessories(pos, mast)
                    write_base(pos, mast)
                    write_brackets(pos, brs)

            except Exception as e:
                self.errors.append(f'{pos}m 전주 CSV 일부 누락: {e}')
                print(f"poledata 데이터 누락: {pos}, 오류: {e}")

        print('create_pole_csv 실행이 완료됐습니다.')
        return self.lines

    def create_wire_csv(self):
        """
        전선 구문 생성 메서드
        """
        self.lines = []  # 코드 실행전 초기화
        self.errors = [e for e in self.errors if '전선 CSV' not in e]
        # zip 으로 순서대로 짝지으면 전선이 하나라도 빠질 때 이후 전선이 모두 한 경간씩 밀린다
        poles_by_pos = {p.pos: p for p in self.poledata}
        pos = None
        for wire in self.wiredata:
            pole = poles_by_pos.get(wire.pos)
            if pole is None:
                self.errors.append(f'{wire.pos}m 전선에 해당하는 전주가 없어 전선 CSV 누락')
                print(f"전선에 해당하는 전주 없음: {wire.pos}")
                continue
            try:
                pos = pole.pos
                post_number = pole.post_number
                structure = pole.structure
                curve = '직선' if pole.radius == 0.0 else '곡선'
                section_label = section_label_of(pole)

                # 구문 작성
                self.lines.append(f',;{post_number}\n')
                self.lines.append(f',;-----{section_label}({structure})({curve})-----\n')

                for wr in wire.wires:
                    sta = wr.station if wr.station else pos
                    self.lines.append(f'{sta},.freeobj {self.track_index};{wr.index};{wr.offset[0]};{wr.offset[1]};{wr.adjusted_angle};{wr.topdown_angle};0;,;{wr.label}\n')
                if wire.insulators:
                    for insulator in wire.insulators:
                        self.lines.append(f'{insulator.pos},.freeobj {self.track_index};{insulator.index};'
                                          f'{insulator.offset[0]};{insulator.offset[1]};'
                                          f'{insulator.yaw};{insulator.pitch};{insulator.roll};,;{insulator.type}\n')
            except Exception as e:
                self.errors.append(f'{pos}m 전선 CSV 일부 누락: {e}')
                print(f"Wire 데이터 누락: index {pos}, 오류: {e}")

        print('create_wire_csv실행이 완료됐습니다.')
        return self.lines