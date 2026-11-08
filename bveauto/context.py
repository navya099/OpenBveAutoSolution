# bveauto/context.py
from dataclasses import dataclass, field
from pathlib import Path

from .config import PathConfig, DEFAULT_PATHS, RAILTYPE_MAP
from .core.alignment.coord.coorddata import CoordCollection
from .core.alignment.curve.curvedata import CurveCollection
from .core.alignment.profile.profiledata import ProfileCollection


@dataclass
class BuildContext:
    designspeed: int = 150
    linecount: int = 1
    offset: float = 0.0
    brokenchain: float = 0.0
    iscustommode: bool = False

    paths: PathConfig = field(default_factory=lambda: DEFAULT_PATHS)

    # load_info 이후 채워지는 데이터
    curve_info: CurveCollection = field(default_factory=CurveCollection)
    pitch_info: ProfileCollection = field(default_factory=ProfileCollection)
    structure_list: list = field(default_factory=list)
    bve_coord: CoordCollection = field(default_factory=CoordCollection)
    start_block: float = 0.0
    last_block: float = 0.0

    @property
    def alignment_type(self) -> str:
        return RAILTYPE_MAP.get(self.designspeed, '')

    @property
    def loaded(self) -> bool:
        return bool(self.curve_info and self.structure_list)