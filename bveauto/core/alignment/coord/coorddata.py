from dataclasses import dataclass



@dataclass
class CoordData:
    """좌표 데이터
    Attributes:
        x: X좌표(m)
        y: y좌표(m)
        z: z좌표(m) - 표고
    """
    x: float
    y: float    
    z: float


class CoordCollection:
    """
    좌표데이터 관리 클래스
    """

    def __init__(self):
        self.coords: list[CoordData] = []

    def __len__(self):
        return len(self.coords)

    def __iter__(self):
        return iter(self.coords)

    def __getitem__(self, item):
        return self.coords[item]

    def add(self, data: CoordData):
        self.coords.append(data)

    def delete(self, index: int):
        self.coords.pop(index)

    def delete_all(self):
        self.coords.clear()

    def get(self, index: int) -> CoordData:
        return self.coords[index]

    @property
    def first(self) -> CoordData:
        return self.coords[0]

    @property
    def last(self) -> CoordData:
        return self.coords[-1]

    def to_xy(self) -> list[tuple[float, float]]:
        return [(c.x, c.y) for c in self.coords]

    def to_xyz(self) -> list[tuple[float, float, float]]:
        return [(c.x, c.y, c.z) for c in self.coords]
