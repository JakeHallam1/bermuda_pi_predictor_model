class Region:
    def __init__(self,min_lat,max_lat,min_long,max_long):
        self.min_lat = min_lat
        self.max_lat = max_lat
        self.min_long = min_long
        self.max_long = max_long

class Time_Frame:
    def __init__(self,s_datetime,f_datetime):
        self.s_datetime = s_datetime
        self.f_datetime = f_datetime
