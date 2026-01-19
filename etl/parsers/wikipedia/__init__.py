"""Wikipedia data source parsers."""

from etl.parsers.wikipedia.nurburgring import NurburgringParser
from etl.parsers.wikipedia.acceleration import AccelerationParser
from etl.parsers.wikipedia.speed_records import SpeedRecordsParser
from etl.parsers.wikipedia.power_output import PowerOutputParser
from etl.parsers.wikipedia.top_gear import TopGearParser

__all__ = [
    "NurburgringParser",
    "AccelerationParser",
    "SpeedRecordsParser",
    "PowerOutputParser",
    "TopGearParser",
]
