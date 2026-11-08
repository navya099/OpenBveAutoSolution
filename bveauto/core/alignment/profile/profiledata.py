from dataclasses import dataclass


@dataclass
class ProfileData:
    """구배 데이터
    Attributes:
        station: 측점(m)
        grade: 구배(dy/dx), 음수는 하향구배, 양수는 상향구배, 수평은 0
    """
    station: float
    grade: float

    @property
    def permile(self) -> float:
        return self.grade * 1000

    @property
    def percent(self) -> float:
        return self.grade * 100

class ProfileCollection:
    """
    구배데이터 관리 클래스
    """
    def __init__(self):
        self.profiles: list[ProfileData] = []

    def __len__(self):
        return len(self.profiles)

    def __iter__(self):
        return iter(self.profiles)

    def __getitem__(self, item):
        return self.profiles[item]

    def add(self, data: ProfileData):
        if any(c.station == data.station for c in self.profiles):
            raise ValueError(f"Station {data.station} already exists")

        self.profiles.append(data)
        self.sort()

    def delete_all(self):
        self.profiles.clear()

    def delete(self, index: int):
        self.profiles.pop(index)

    def sort(self):
        self.profiles.sort(key=lambda x: x.station)

    def get(self, index: int) -> ProfileData:
        return self.profiles[index]

    def find_by_station(self, station: float) -> ProfileData | None:
        for profile in self.profiles:
            if profile.station == station:
                return profile
        return None

