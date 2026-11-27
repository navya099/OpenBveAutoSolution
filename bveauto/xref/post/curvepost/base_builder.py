from abc import ABC, abstractmethod

from bveauto.xref.post.model.curve.ipdata import IPdata
from bveauto.xref.post.model.grade.vipdata import VIPdata

class CurveDATABuilder(ABC):
    """추상 곡선데이터 빌더"""
    @abstractmethod
    def build(self, data, brokenchain) -> list[IPdata]:
        raise NotImplementedError

    @abstractmethod
    def preprocess(self, data, brokenchain) -> IPdata:
        raise NotImplementedError