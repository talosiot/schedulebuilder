# Schedule Builder
> Build and evaluate a building schedule


## Quick Start

Create a yaml file to describe the schedule of your building.  This one means the building is `occupied` from 6:30AM to 6:30PM every weekday that isn't a holiday

```python
import yaml
import pandas as pd

from schedulebuilder import Schedule

config = '''
daytypes:
      - name: workday
        day:
            periods:
                - start: '6:30'
                  end: '18:30'
                  status: occupied
            name: workday
        logic: 
            - select: weekdays
            - select: holidays
              exclude: true
'''
config = yaml.safe_load(config)
```

```python
sched = Schedule(**config)
```

Now you can evaluate whether the building is `occupied` at any given date and time.

```python
pdt = pd.to_datetime
jul6_at_noon = pdt('2021-07-06 12:00')
sched.is_occupied(jul6_at_noon)
```




    True



```python
jul6_late_at_night = pdt('2021-07-06 23:00')
sched.is_occupied(jul6_late_at_night)
```




    False



```python
on_newyears = pdt('2021-01-01 12:00')
sched.is_occupied(on_newyears)
```




    False


