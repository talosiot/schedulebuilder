# AUTOGENERATED! DO NOT EDIT! File to edit: nbs/init.ipynb (unless otherwise specified).

__all__ = ['logger', 'Period', 'Day', 'Unoccupied', 'AlwaysOn', 'always', 'is_weekend', 'is_weekday', 'is_holiday',
           'is_month', 'LOGIC', 'Logic', 'Logics', 'DayType', 'IncompleteSchedule', 'Schedule']

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

Unoccupied = Day(name='Unoccupied')
AlwaysOn = Day(name="24h", periods=[Period(start="0:00", end="0:00")])

# Cell

def always(ts):
    return True

def is_weekend(ts):
    '''
    Pandas defines the day of the week with Monday=0, Sunday=6.
    '''
    dayofweek = ts.dayofweek
    return dayofweek >= 5

def is_weekday(ts):
    dayofweek = ts.dayofweek
    return dayofweek <= 4

def is_holiday(ts, holiday_calendar='US'):
    _holiday_calendars = {'US': holidays.UnitedStates()}
    hcal = _holiday_calendars.get(holiday_calendar, holiday_calendar)
    return ts.date() in hcal

def is_month(ts, months):
    return ts.month in months

LOGIC = {'weekends': is_weekend,
         'weekend': is_weekend,
         'weekdays': is_weekday,
         'weekday': is_weekday,
         'holidays': is_holiday,
         'holiday': is_holiday,
         'always': always,
         'months': is_month
        }

# Cell
class Logic(BaseModel):
    include: Optional[str]
    exclude: Optional[str]
    kwargs: Optional[dict]={}

    @validator('include')
    @validator('exclude')
    def func_must_be_a_known_name(cls, logic_string):
        if logic_string not in LOGIC:
            raise ValueError("logic must be one of {}".format(LOGIC.keys()))
        return logic_string

    def evaluate(self, ts) -> bool:
        '''
        Returns True if the function named in self.func evaluates to true
        '''
        func_name = self.include or self.exclude
        func = LOGIC[func_name]
        result = func(ts, **self.kwargs)
        if self.exclude:
            result = not result
        return result


# Cell
class Logics(BaseModel):
    '''
    Logics is a chain of logic, linked together with AND
    '''
    logic: List[Logic] = []
    def evaluate(self, ts) -> bool:
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

# Cell

class DayType(BaseModel):
    name:str
    logics:Logics
    day:Day

    def evaluate(self, ts) -> Union[Day, None]:
        '''
        Returns the day object if it evaluates to true for the given timestamp ts.
        Otherwise, returns None
        '''
        if self.logics.evaluate(ts):
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