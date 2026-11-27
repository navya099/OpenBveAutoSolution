from bveauto.xref.decats.core.alignment.rail_alignment import is_span_visible


class PoleUpdator:
    @staticmethod
    def update_all(poles, alignment=None):
        """트랙 전주 목록을 순서대로 잇는다 (전주.next_* 는 이은 다음 전주에서 바로 계산 — bveauto.xref.decats.core/pole/poledata.py).

        alignment 에 레일 표시 정보(RailAlignment.visible_blocks)가 있으면, 다음 전주까지의 경간에
        레일이 그려지지 않는 경우(레일 단절) 두 전주를 잇지 않는다 → 생성 때 값 유지, 단절 구간을 건너는 전선이 생기지 않음
        (WireProcessor 는 next_pos 가 다음 전주와 같을 때만 전선 생성). 마지막 전주도 잇지 않는다.
        목록 일부만 넘기면 그 끝 전주의 연결이 끊기므로 항상 트랙 전체 목록을 넘긴다.
        """
        for i, current_pole in enumerate(poles):
            next_pole = poles[i + 1] if i < len(poles) - 1 else None
            if next_pole is not None and alignment is not None and not is_span_visible(alignment, current_pole.pos,
                                                                                       next_pole.pos):
                next_pole = None
            current_pole.link_next(next_pole)
