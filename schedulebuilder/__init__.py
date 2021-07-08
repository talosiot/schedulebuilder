# AUTOGENERATED! DO NOT EDIT! File to edit: nbs/init.ipynb (unless otherwise specified).

__all__ = ['logger', 'Period', 'Day', 'always', 'is_weekend', 'is_weekday', 'get_named_weekday', 'specific_weekday',
           'year_of', 'is_holiday', 'is_month', 'make_year_specific_date', 'before', 'after', 'NAMED_FUNCTIONS',
           'Logic', 'DayType', 'IncompleteSchedule', 'Schedule']

# Cell
_FNAME='init'

# Cell
import datetime
import pandas as pd

import holidays
import logging
logger = logging.getLogger()

from pydantic import BaseModel, validator
from typing import List, Optional, Union
from collections import OrderedDict

# Cell
class Period(BaseModel):
    start: datetime.time
    end: datetime.time
    status: Optional[str] = 'occupied'
    def __repr__(self):
        return '<{stat} Period {s}-{e}>'.format(stat=self.status, s=self.start, e=self.end)
    def __str__(self):
        return self.__repr__()
    def during(self, ts) -> bool:
        '''
        ts: a timestamp. Can be a datetime or any other obj with a .time() method.
        If no .time method exists, ts can also be any object that can be compared with datetime.time objects
        '''
        try:
            tod = ts.time()
        except AttributeError:
            tod=ts
        #end needs to be <= to allow for a 24 hour day
        return self.start <= tod <= self.end


# Cell
class Day(BaseModel):
    '''
    A type of day that contains the periods listed
    If a single period is given, that is the only period for the dat
    '''
    periods: List[Period]=[]
    name: Optional[str]=None

    def __repr__(self):
        name = self.name or ''
        return '<{n} Day: {periods}>'.format(n=name, periods=self.periods)
    def __str__(self):
        return self.__repr__()

    def within_period(self, ts, status='occupied') -> bool:
        checks = [p.during(ts) for p in self.periods if p.status==status]
        return sum(checks) >= 1

# Cell

def always(ts):
    return True

def is_weekend(ts):
    '''
    Returns True if the given ts is Saturday or Sunday
    Pandas defines the day of the week with Monday=0, Sunday=6.
    '''
    dayofweek = ts.dayofweek
    return dayofweek >= 5

def is_weekday(ts):
    '''
    Returns True if the given ts is a weekday (Monday-Friday)
    '''

    dayofweek = ts.dayofweek
    return dayofweek <= 4

def get_named_weekday(dayname) -> int:
    '''
    Returns the number day of the week given the name
    '''
    days = {'MONDAY':0,
           'TUESDAY':1,
           'WEDNESDAY':2,
            'THURSDAY': 3,
            'FRIDAY': 4,
            'SATURDAY': 5,
            'SUNDAY': 6
           }
    return days[dayname.upper()]

def specific_weekday(ts, dayname:str):
    '''
    Returns True if the ts is that specific day of the week.
    e.g.
    specific_weekday(pdt('2021-07-05'), 'Monday') --> True
    '''
    return ts.dayofweek == get_named_weekday(dayname)

def year_of(ts):
    year = ts.year
    return '{y}-01-01'.format(y=year), '{y}-12-31'.format(y=year)

def is_holiday(ts, holiday_calendar='US'):
    _holiday_calendars = {'US': holidays.UnitedStates()}
    hcal = _holiday_calendars.get(holiday_calendar, holiday_calendar)
    return ts.date() in hcal

def is_month(ts, months):
    return ts.month in months

def make_year_specific_date(year, month=None, day=None):
    if month and day:
        return pd.to_datetime('{y}-{m}-{d}'.format(y=year, m=month, d=day))

def before(ts, month:int, day:int) -> bool:
    '''
    Teturns True if the ts is earlier in the year than date.
   '''
    return ts < make_year_specific_date(ts.year, month, day)

def after(ts, month, day):
    return ts > make_year_specific_date(ts.year, month, day)

# Cell
NAMED_FUNCTIONS = {'weekends': is_weekend,
                   'weekend': is_weekend,
                   'weekdays': is_weekday,
                   'weekday': is_weekday,
                   'holidays': is_holiday,
                   'holiday': is_holiday,
                   'always': always,
                   'months': is_month,
                   'before': before,
                   'after': after,

        }

# Cell
class Logic(BaseModel):
    include: Optional[str]
    exclude: Optional[str]
    kwargs: Optional[dict]={}

    @validator('include')
    @validator('exclude')
    def func_must_be_a_known_name(cls, logic_string):
        if logic_string not in NAMED_FUNCTIONS:
            raise ValueError("logic must be one of {}".format(NAMED_FUNCTIONS.keys()))
        return logic_string

    def evaluate(self, ts) -> bool:
        '''
        Returns True if the function named in self.func evaluates to true
        '''
        func_name = self.include or self.exclude
        func = NAMED_FUNCTIONS[func_name]
        result = func(ts, **self.kwargs)
        if self.exclude:
            result = not result
        return result


# Cell

class DayType(BaseModel):
    name: Optional[str]=None
    logic: List[Logic] = []
    day:Day

    def evaluate_logic(self, ts) -> bool:
        '''
        Returns True if ALL the functions in self.funcs evaluate to True.
        Returns False otherwise.
        Returns False if the list of self.funcs is empty.
        '''
        result = False
        #a Logics with no funcs always returns False
        for logic in self.logic:
            result = logic.evaluate(ts)
            if result is False:
                return False
        return result

    def evaluate(self, ts) -> Union[Day, None]:
        '''
        Returns the day object if it evaluates to true for the given timestamp ts.
        Otherwise, returns None
        '''
        if self.evaluate_logic(ts):
            return self.day

# Cell
class IncompleteSchedule(Exception):
    pass

class Schedule(BaseModel):
    daytypes:List[DayType] = []

    def find_relevant_day(self, ts):
        '''
        Returns the first day for which the logic func(**kwargs) evaluates True
        '''
        for daytype in self.daytypes:
            day = daytype.evaluate(ts)
            if day:
                return day

    def is_occupied(self, ts):
        return self.check_status(ts, status='occupied')

    def check_status(self, ts, status):
        day = self.find_relevant_day(ts)
        if day:
            return day.within_period(ts)
        else:
            return False