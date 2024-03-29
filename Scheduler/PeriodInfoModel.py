class PeriodInfoModel:
    def __init__(self, time_total, time_left, day_type, current_period, next_period_start_time):
        self.time_total = time_total
        self.time_left = time_left
        self.day_type = day_type
        self.current_period = current_period
        self.next_period_start_time = next_period_start_time

    def json(self):
        return {
            "success": True,
            "total_time": self.time_total.seconds,
            "time_left": self.time_left.seconds,
            "day_type": self.day_type.value,
            "period_type": self.current_period.value,
            "next_period_start_time": self.next_period_start_time.isoformat(),
            "WEEKEND": False
        }
