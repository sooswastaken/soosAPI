import enum
import datetime
from .PeriodTypes import PeriodTypes


class RED_DAY_PERIOD_TYPES(enum.Enum):
    BEFORE_SCHOOL = {
        "type": PeriodTypes.BEFORE_SCHOOL,
        "end": datetime.time(8, 2),
        "previous": PeriodTypes.AFTER_SCHOOL,
    }
    FIRST_PERIOD_TRANSITION = {
        "type": PeriodTypes.FIRST_PERIOD_TRANSITION,
        "end": datetime.time(8, 10),
        "previous": PeriodTypes.BEFORE_SCHOOL,
    }
    FIRST_PERIOD = {
        "type": PeriodTypes.FIRST_PERIOD,
        "end": datetime.time(9, 37),
        "previous": PeriodTypes.FIRST_PERIOD_TRANSITION,
    }
    THIRD_PERIOD_TRANSITION = {
        "type": PeriodTypes.THIRD_PERIOD_TRANSITION,
        "end": datetime.time(9, 45),
        "previous": PeriodTypes.FIRST_PERIOD,
    }
    THIRD_PERIOD = {
        "type": PeriodTypes.THIRD_PERIOD,
        "end": datetime.time(11, 12),
        "previous": PeriodTypes.THIRD_PERIOD_TRANSITION,
    }
    FIFTH_PERIOD_TRANSITION = {
        "type": PeriodTypes.FIFTH_PERIOD_TRANSITION,
        "end": datetime.time(11, 20),
        "previous": PeriodTypes.THIRD_PERIOD,
    }
    FIFTH_PERIOD = {
        "type": PeriodTypes.FIFTH_PERIOD,
        "end": datetime.time(13, 19),
        "previous": PeriodTypes.FIFTH_PERIOD_TRANSITION,
    }
    SEVENTH_PERIOD_TRANSITION = {
        "type": PeriodTypes.SEVENTH_PERIOD_TRANSITION,
        "end": datetime.time(13, 27),
        "previous": PeriodTypes.FIFTH_PERIOD,
    }
    SEVENTH_PERIOD = {
        "type": PeriodTypes.SEVENTH_PERIOD,
        "end": datetime.time(14, 55),
        "previous": PeriodTypes.SEVENTH_PERIOD_TRANSITION,
    }
    AFTER_SCHOOL = {
        "type": PeriodTypes.AFTER_SCHOOL,
        "end": datetime.time(23, 59, 59, 59),
        "previous": PeriodTypes.SEVENTH_PERIOD,
    }
