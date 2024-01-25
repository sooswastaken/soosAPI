import enum
import datetime
from .PeriodTypes import PeriodTypes


class BLACK_DAY_PERIOD_TYPES(enum.Enum):
    BEFORE_SCHOOL = {
        "type": PeriodTypes.BEFORE_SCHOOL,
        "end": datetime.time(8, 2),
        "previous": PeriodTypes.AFTER_SCHOOL,
    }
    SECOND_PERIOD_TRANSITION = {
        "type": PeriodTypes.SECOND_PERIOD_TRANSITION,
        "end": datetime.time(8, 10),
        "previous": PeriodTypes.BEFORE_SCHOOL,
    }
    SECOND_PERIOD = {
        "type": PeriodTypes.SECOND_PERIOD,
        "end": datetime.time(9, 37),
        "previous": PeriodTypes.SECOND_PERIOD_TRANSITION,
    }
    STINGER_FIRST_HALF_TRANSITION = {
        "type": PeriodTypes.STINGER_FIRST_HALF_TRANSITION,
        "end": datetime.time(9, 45),
        "previous": PeriodTypes.SECOND_PERIOD,
    }
    STINGER_FIRST_HALF = {
        "type": PeriodTypes.STINGER_FIRST_HALF,
        "end": datetime.time(10, 25),
        "previous": PeriodTypes.STINGER_FIRST_HALF_TRANSITION,
    }
    STINGER_SECOND_HALF_TRANSITION = {
        "type": PeriodTypes.STINGER_SECOND_HALF_TRANSITION,
        "end": datetime.time(10, 33),
        "previous": PeriodTypes.STINGER_FIRST_HALF,
    }
    STINGER_SECOND_HALF = {
        "type": PeriodTypes.STINGER_SECOND_HALF,
        "end": datetime.time(11, 12),
        "previous": PeriodTypes.STINGER_SECOND_HALF_TRANSITION,
    }
    SIXTH_PERIOD_TRANSITION = {
        "type": PeriodTypes.SIXTH_PERIOD_TRANSITION,
        "end": datetime.time(11, 20),
        "previous": PeriodTypes.STINGER_SECOND_HALF,
    }
    SIXTH_PERIOD = {
        "type": PeriodTypes.SIXTH_PERIOD,
        "end": datetime.time(13, 19),
        "previous": PeriodTypes.SIXTH_PERIOD_TRANSITION,
    }
    EIGHTH_PERIOD_TRANSITION = {
        "type": PeriodTypes.EIGHTH_PERIOD_TRANSITION,
        "end": datetime.time(13, 27),
        "previous": PeriodTypes.SIXTH_PERIOD,
    }
    EIGHTH_PERIOD = {
        "type": PeriodTypes.EIGHTH_PERIOD,
        "end": datetime.time(14, 55),
        "previous": PeriodTypes.EIGHTH_PERIOD_TRANSITION,
    }
    AFTER_SCHOOL = {
        "type": PeriodTypes.AFTER_SCHOOL,
        "end": datetime.time(23, 59, 59, 59),
        "previous": PeriodTypes.EIGHTH_PERIOD,
    }
