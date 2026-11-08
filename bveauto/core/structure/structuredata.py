from dataclasses import dataclass
from enum import Enum


class StructureType(Enum):
    BRIDGE = 0
    TUNNEL  = 1


@dataclass
class StructureData:
    """구조물 데이터 클래스
    Attributes:
        name: 구조물 이름
        start_station: 시작 측점
        end_station: 끝 측점

    """
    name:  str
    start_station: float
    end_station: float
    structure_type: StructureType

    def __post_init__(self):
        if self.start_station < 0:
            raise ValueError("측점은 0 이상이어야 합니다.")

        if self.end_station < self.start_station:
            raise ValueError(
                "end_station must be greater than start_station"
            )

    @property
    def length(self) -> float:
        return self.end_station - self.start_station

    def contains(self, station: float) -> bool:
        return self.start_station <= station <= self.end_station



class StructureCollection:
    """
    구조물 데이터 관리 클래스
    """

    def __init__(self):
        self.structures: list[StructureData] = []

    def __len__(self):
        return len(self.structures)

    def __iter__(self):
        return iter(self.structures)

    def __getitem__(self, item):
        return self.structures[item]

    def add(self, data: StructureData):
        self.structures.append(data)
        self.sort()

    def delete(self, index: int):
        self.structures.pop(index)

    def delete_all(self):
        self.structures.clear()

    def get(self, index: int) -> StructureData:
        return self.structures[index]

    def sort(self):
        self.structures.sort(
            key=lambda x: x.start_station
        )

    def find_by_station(
            self,
            station: float
    ) -> StructureData | None:
        """측점이 포함된 구조물 찾기"""
        for structure in self.structures:
            if structure.contains(station):
                return structure

        return None

    def find_by_type(
            self,
            type_: StructureType
    ) -> list[StructureData]:
        """특정 타입만 조회"""
        return [
            s
            for s in self.structures
            if s.type == type_
        ]

    def is_bridge(
            self,
            station: float
    ) -> bool:
        """측점이 교량인지 판단"""
        structure = self.find_by_station(station)



        return (
                structure is not None
                and structure.type == StructureType.BRIDGE
        )

    def is_tunnel(
            self,
            station: float
    ) -> bool:
        """측점이 터널인지 판단"""
        structure = self.find_by_station(station)

        return (
                structure is not None
                and structure.type == StructureType.TUNNEL
        )

    def total_bridge_count(self) -> int:
        return len(self.find_by_type(StructureType.BRIDGE))

    def total_tunnel_count(self) -> int:
        return len(self.find_by_type(StructureType.TUNNEL))