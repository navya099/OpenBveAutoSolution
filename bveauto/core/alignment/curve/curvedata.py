from dataclasses import dataclass
from enum import IntEnum


class CurveDirection(IntEnum):
    TANGENT = 0
    LEFT = -1
    RIGHT = 1


@dataclass
class CurveData:
    """곡선 데이터
    Attributes:
        station: 측점(m)
        radius: 곡선반경(m)
        direction: 곡선 방향(TANGENT, LEFT, RIGHT)
        cant:   캔트(m)
    """
    station: float
    radius: float      # m, 항상 양수
    direction: CurveDirection
    cant: float

    @property
    def cant_mm(self) -> float:
        return self.cant * 1000


class CurveCollection:
    """
    곡선데이터 관리 클래스
    """
    def __init__(self):
        self.curves: list[CurveData] = []

    def __len__(self):
        return len(self.curves)

    def __iter__(self):
        return iter(self.curves)

    def __getitem__(self, item):
        return self.curves[item]

    def add(self, data: CurveData):
        if any(c.station == data.station for c in self.curves):
            raise ValueError(f"Station {data.station} already exists")

        self.curves.append(data)
        self.sort()

    def delete_all(self):
        self.curves.clear()

    def delete(self, index: int):
        self.curves.pop(index)

    def sort(self):
        self.curves.sort(key=lambda x: x.station)

    def get(self, index: int) -> CurveData:
        return self.curves[index]

    def find_by_station(self, station: float) -> CurveData | None:
        for curve in self.curves:
            if curve.station == station:
                return curve
        return None


