import datetime
from .DayTypes import DayTypes
from .BLACK_DAY_PERIOD_TYPES import BLACK_DAY_PERIOD_TYPES
from .RED_DAY_PERIOD_TYPES import RED_DAY_PERIOD_TYPES
from .PeriodInfoModel import PeriodInfoModel


def get_period_info(day_type, date):
    # Returns two values: the total time of the period, and the time remaining in the period.
    time_left = None
    time_total = None
    current_period = None

    if day_type == DayTypes.BLACK_DAY:
        # Determine what period it currently is
        for period in BLACK_DAY_PERIOD_TYPES:
            if date.time() <= period.value["end"]:
                current_period = period.value["type"]
                # Convert the period end time to a datetime.datetime object
                end_time = datetime.datetime.combine(date, period.value["end"])
                time_left = end_time - date
                previous_period = getattr(BLACK_DAY_PERIOD_TYPES, period.value["previous"].name)
                previous_period_end = datetime.datetime.combine(date, previous_period.value["end"])
                time_total = end_time - previous_period_end
                break
    if day_type == DayTypes.RED_DAY:
        # Determine what period it currently is
        for period in RED_DAY_PERIOD_TYPES:
            if date.time() <= period.value["end"]:
                current_period = period.value["type"]
                # Convert the period end time to a datetime.datetime object
                end_time = datetime.datetime.combine(date, period.value["end"])
                time_left = end_time - date
                previous_period = getattr(RED_DAY_PERIOD_TYPES, period.value["previous"].name)
                previous_period_end = datetime.datetime.combine(date, previous_period.value["end"])
                time_total = end_time - previous_period_end
                break
    if day_type == DayTypes.WEEKEND:
        return "WEEKEND"
    return PeriodInfoModel(time_total, time_left, day_type, current_period)
