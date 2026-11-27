
from bveauto.xref.decats.core.equipment.equipment_data import EquipmentDATA
from bveauto.xref.decats.core.alignment.alignment import as_alignment
from bveauto.xref.decats.utils.math_util import change_permile_to_degree


from bveauto.xref.decats.enums.component_role import ComponentRole
from bveauto.xref.decats.enums.section_type import FlowStop, SectionType, section_role

FLOWSTOP_TAGS = (FlowStop.START, FlowStop.MIDDLE, FlowStop.END)
FLOWSTOP_EQUIPMENT_TYPES = ('흐름방지장치', '봉강지선')


class AnticreepingDeviceProcessor:
    """흐름방지장치 처리기.

    process() 를 부를 때마다 현재 전주 데이터에서 처음부터 다시 계산한다 (상태를 누적하지 않음):
      1) 이전 계산 결과(전주 흐름방지 위치 PoleDATA.flowstop, 장비, 흐름방지선) 제거
      2) 자동 구간: 인접한 두 에어조인트 사이(앞 에어조인트 끝점 ~ 다음 에어조인트 시작점)의 가운데 전주
      3) 사용자 추가/삭제 요청(manual_ops)을 요청 순서대로 다시 적용
      4) 전주 장비·전선 반영
    그래서 전주 이동/추가/삭제, 에어조인트 추가/삭제 뒤에도 항상 현재 배치와 일치한다.
    """

    def __init__(self, poledata, wiredata, airjoint_list=None, wire_processor=None):
        self.devices_by_track = {}
        self.poledata = poledata      # {"main": [...], "sub": [...]}
        self.wiredata = wiredata
        self.airjoint_list = airjoint_list  # 호환용 (자동 구간은 현재 전주의 에어조인트 구간에서 계산)
        self.wire_processor = wire_processor
        self.manual_ops = []          # [("add"|"remove", track, start_pos, end_pos, mid_pos), ...]

    def set_data(self, poledata, wiredata, wire_processor=None):
        self.poledata = poledata  # {"main": [...], "sub": [...]}
        self.wiredata = wiredata
        if wire_processor is not None:
            self.wire_processor = wire_processor

    def process(self):
        self.clear()
        self.define_section()
        self.apply()

    # ── 계산 ────────────────────────────────────────
    def clear(self):
        """이전 계산 결과 제거 (전주 흐름방지 위치·장비, 흐름방지선)"""
        for poles in self.poledata.values():
            for pole in poles:
                if pole.section in FLOWSTOP_TAGS:  # 구버전 데이터: 흐름방지 위치가 section 에 저장돼 있던 경우
                    pole.section = None
                pole.flowstop = None
                pole.equipments = [e for e in pole.equipments if e.type not in FLOWSTOP_EQUIPMENT_TYPES]
        for wires in (self.wiredata or {}).values():
            for wire in wires:
                wire.wires = [w for w in wire.wires if w.label != '흐름방지선']

    @staticmethod
    def _device_rows(track_name, poles_in_section, mid_index):
        """가운데 전주 기준 앞·가운데·뒤 3개 전주에 시작/중간/끝 태그"""
        indices = [max(0, mid_index - 1), mid_index, min(len(poles_in_section) - 1, mid_index + 1)]
        return [{
            "track": track_name,
            "pos": poles_in_section[idx].pos,
            "post_number": poles_in_section[idx].post_number,
            "device_type": "Anticreeping",
            "tag": tag,
        } for tag, idx in zip(FLOWSTOP_TAGS, indices)]

    @staticmethod
    def _airjoint_gaps(poles):
        """[(앞 에어조인트 끝점 pos, 다음 에어조인트 시작점 pos), ...]"""
        gaps = []
        last_end = None
        for pole in sorted(poles, key=lambda p: p.pos):
            role = section_role(pole.section)  # 복주 에어조인트 포함
            if role == SectionType.AJ_END:
                last_end = pole.pos
            elif role == SectionType.AJ_START and last_end is not None:
                gaps.append((last_end, pole.pos))
                last_end = None
            elif pole.section is not None:
                last_end = None  # 사이에 다른 구간(에어조인트 중간 등)이 끼면 인접 쌍이 아님
        return gaps

    def define_section(self):
        self.devices_by_track = {}
        for track_name, poles in self.poledata.items():
            devices = []
            for start_pos, end_pos in self._airjoint_gaps(poles):
                poles_in_section = [p for p in poles if start_pos <= p.pos <= end_pos]
                if poles_in_section:
                    devices.extend(self._device_rows(track_name, poles_in_section, len(poles_in_section) // 2))
            self.devices_by_track[track_name] = devices

        for op, track_name, start_pos, end_pos, mid_pos in getattr(self, 'manual_ops', []):
            if track_name not in self.poledata:
                continue
            self._remove_section(track_name, start_pos, end_pos, mid_pos)
            if op == "add":
                self._add_section(track_name, start_pos, end_pos, mid_pos)

    def _section_around(self, track_name, start_pos, end_pos, mid_pos):
        poles_in_section = [p for p in self.poledata[track_name] if start_pos <= p.pos <= end_pos]
        if not poles_in_section:
            return None, None
        mid_pole = min(poles_in_section, key=lambda p: abs(p.pos - mid_pos))  # midpos 에 가장 가까운 전주
        return poles_in_section, poles_in_section.index(mid_pole)

    def _add_section(self, track_name, start_pos, end_pos, mid_pos):
        poles_in_section, mid_index = self._section_around(track_name, start_pos, end_pos, mid_pos)
        if poles_in_section:
            self.devices_by_track.setdefault(track_name, []).extend(
                self._device_rows(track_name, poles_in_section, mid_index))

    def _remove_section(self, track_name, start_pos, end_pos, mid_pos):
        poles_in_section, mid_index = self._section_around(track_name, start_pos, end_pos, mid_pos)
        if not poles_in_section:
            return
        targets = {row["pos"] for row in self._device_rows(track_name, poles_in_section, mid_index)}
        self.devices_by_track[track_name] = [d for d in self.devices_by_track.get(track_name, [])
                                             if d["pos"] not in targets]

    # ── 사용자 편집 ──────────────────────────────────
    def add_manual_section(self, track_name, start_pos, end_pos, mid_pos):
        """사용자가 midpos 를 지정해서 흐름방지 구간 추가 (이후 재계산에도 유지)"""
        self._ops().append(("add", track_name, start_pos, end_pos, mid_pos))
        self.process()

    def remove_manual_section(self, track_name, start_pos, end_pos, mid_pos):
        """사용자가 지정한 흐름방지 구간 제거 (자동 구간 포함, 이후 재계산에도 유지)"""
        self._ops().append(("remove", track_name, start_pos, end_pos, mid_pos))
        self.process()

    def _ops(self):
        if not hasattr(self, 'manual_ops'):  # 구버전 pickle
            self.manual_ops = []
        return self.manual_ops

    def apply(self):
        """실제로 poledata에 장치 태그 반영"""
        self.apply_pole_devices()
        self.apply_wires()

    def apply_pole_devices(self):
        for track_name, devices in self.devices_by_track.items():
            for device in devices:
                pole = next((p for p in self.poledata[track_name] if p.pos == device["pos"]), None)
                wire = next((w for w in self.wiredata[track_name] if w.pos == device["pos"]), None)
                if not wire:
                    continue
                if not pole:
                    continue
                cw = next((w for w in wire.wires if w.label == '전차선'), None)
                if cw is None:
                    continue  # 전차선이 없으면 건너뜀
                pole.flowstop = device['tag']  # 구간(section)은 그대로 둠
                # 기존 흐름방지 장치 제거
                pole.equipments = [
                    e for e in pole.equipments
                    if e.type not in ['흐름방지장치', '봉강지선']
                ]

                if device['tag'] == FlowStop.START:
                    x1 = pole.gauge
                    x2 = cw.end_point[0]
                    adjusted_angle = as_alignment(self.wire_processor.polyline_by_track[track_name]).wire_angle(
                        pole.pos, pole.next_pos, x1, x2)
                    if pole.structure != '터널':
                        pole.equipments.extend([
                            EquipmentDATA(*self._equipment('흐름방지장치', '흐름방지장치_강관주용'), offset=(pole.gauge, 0), rotation=adjusted_angle, type='흐름방지장치', role=ComponentRole.ANTICREEP),
                            EquipmentDATA(*self._equipment('봉강지선', '봉강지선'), offset=(pole.gauge, 0), rotation=0.0, type='봉강지선', role=ComponentRole.ANTICREEP_GUY)
                        ])
                    else:
                        pole.equipments.append(
                            EquipmentDATA(*self._equipment('흐름방지장치', '흐름방지장치_강관주용'), offset=(pole.gauge, 0),
                                          rotation=adjusted_angle, type='흐름방지장치', role=ComponentRole.ANTICREEP))
                elif device['tag'] == FlowStop.END:
                    x1 = pole.gauge
                    x2 = cw.offset[0]
                    adjusted_angle = as_alignment(self.wire_processor.polyline_by_track[track_name]).wire_angle(
                        pole.pos, pole.next_pos, x1, x2)
                    if pole.structure != '터널':
                        pole.equipments.extend([
                            EquipmentDATA(*self._equipment('흐름방지장치', '흐름방지장치_강관주용'), offset=(pole.gauge, 0), rotation=180 - adjusted_angle, type='흐름방지장치', role=ComponentRole.ANTICREEP),
                            EquipmentDATA(*self._equipment('봉강지선', '봉강지선'), offset=(pole.gauge, 0), rotation=180, type='봉강지선', role=ComponentRole.ANTICREEP_GUY)
                        ])
                    else:
                        pole.equipments.append(
                            EquipmentDATA(*self._equipment('흐름방지장치', '흐름방지장치_강관주용'), offset=(pole.gauge, 0),
                                          rotation=180 - adjusted_angle, type='흐름방지장치', role=ComponentRole.ANTICREEP))
    def _equipment(self, name, default_name):
        """(오브젝트 이름, 인덱스): 인덱스는 데이터셋 equipment, 이름은 인덱스 라이브러리 (없으면 기본 이름)"""
        index = self.wire_processor.pro.get_equipment_index(name)
        idxlib = getattr(self, 'idxlib', None)
        found = idxlib.get_name(index) if idxlib is not None else None
        return found or default_name, index

    def apply_wires(self):
        for track_name, devices in self.devices_by_track.items():
            for device in devices:
                pole = next((p for p in self.poledata[track_name] if p.pos == device["pos"]), None)
                if not pole:
                    continue
                wire = next((w for w in self.wiredata[track_name] if w.pos == device["pos"]), None)
                if not wire:
                    continue
                # 기존 흐름방지선 제거
                wire.wires = [w for w in wire.wires if w.label != '흐름방지선']
                cw = next((w for w in wire.wires if w.label == '전차선'), None)
                if cw is None:
                    continue  # 전차선이 없으면 건너뜀
                if device['tag'] == FlowStop.START and wire:
                    extrawire = self.make_flowstop_wire(pole, cw, track_name, isstart=True)
                    wire.add_wire(extrawire)
                elif device['tag'] == FlowStop.MIDDLE and wire:
                    extrawire = self.make_flowstop_wire(pole, cw, track_name, isstart=False)
                    wire.add_wire(extrawire)

    def make_flowstop_wire(self, pole, wire, track_name, isstart=True):
        windex = self.wire_processor.pro.get_protection_wire_span(pole.span)
        system_heigh, contact_height = self.wire_processor.pro.get_contact_wire_and_massanger_wire_info(pole.structure)
        start_x = wire.offset[0]
        end_x = wire.end_point[0]
        if isstart:
            start = (pole.gauge, 5.7)
            end = (end_x, system_heigh + contact_height)
        else:
            start = (start_x, system_heigh + contact_height)
            end = (pole.next_gauge, 5.7)
        pitch_angle = change_permile_to_degree(pole.pitch)

        return self.wire_processor.com.run(
            polyline_with_sta=self.wire_processor.polyline_by_track[track_name],
            index=windex, pos=pole.pos, next_pos=pole.next_pos,
            current_z=pole.z, next_z=pole.next_z,
            start=start, end=end, pitch_angle=pitch_angle,
            label='흐름방지선'
        )
