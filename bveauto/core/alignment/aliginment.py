from dataclasses import dataclass

from bveauto.core.alignment.coord.coorddata import CoordCollection, CoordData
from bveauto.core.alignment.curve.curvedata import CurveCollection, CurveData
from bveauto.core.alignment.profile.profiledata import ProfileCollection, ProfileData


@dataclass
class Alignment:
    """선형 객체 클래스
    제공 메서드: 측점 조회, 좌표 조회

    Attributes:
        coords: 좌표 컬렉션
        curves: 곡선 컬렉션
        profiles: 구배 컬렉션

        name: 선형 이름
        start_station: 선형 시작 측점(m)

    """

    #기하 속성
    coords: CoordCollection
    curves: CurveCollection
    profiles: ProfileCollection

    # 메타데이터
    name: str = ''
    start_station: float = 0.0

    def __post_init__(self):
        """길이 검증(3 객체는 반드시 같아야함)"""
        if not (
                len(self.coords)
                == len(self.curves)
                == len(self.profiles)
        ):
            raise ValueError(
                "coords, curves, profiles length mismatch"
            )
        # station 매칭 인덱스 딕셔너리 생성
        self._station_index = {
            curve.station: i
            for i, curve in enumerate(self.curves)
        }

    @property
    def length(self) -> float:
        if len(self.curves) == 0:
            return 0.0

        return self.curves[-1].station

    @property
    def start_point(self):
        return self.coords.first

    @property
    def end_point(self):
        return self.coords.last

    @property
    def end_station(self):
        return self.start_station + self.length

    # 공개 API
    def get_curve(self, station: float) -> CurveData | None:
        """측점으로 곡선 데이터 조회"""
        return self.curves.find_by_station(station)

    def get_grade(self, station: float) -> ProfileData | None:
        """측점으로 구배 데이터 조회"""
        return self.profiles.find_by_station(station)

    def get_coord(self, station: float) -> CoordData | None:
        """측점으로 좌표 조회"""
        index = self._station_index.get(station)

        if index is None:
            return None

        return self.coords[index]

    #TODO
    def get_station_by_coord(self, coord: CoordData) -> float:
        """좌표로 측점찾기"""
        raise NotImplementedError
