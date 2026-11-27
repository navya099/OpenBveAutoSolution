from bveauto.xref.post.curvepost.base_builder import CurveDATABuilder
from bveauto.xref.post.model.curve.ipdata import IPdata


class CIVIL3DCURVEDATABuilder(CurveDATABuilder):
    def build(self, data, brokenchain) -> list[IPdata]:
        raise NotImplementedError

    def preprocess(self, data, brokenchain) -> IPdata:
        raise NotImplementedError
