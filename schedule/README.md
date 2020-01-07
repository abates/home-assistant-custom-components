# Schedule Component

The Schedule component creates a sensor whose state is based on a reccurring schedule.
The inspiration for this component was programmable thermostats that allow setting
times for "wake", "leave", "return" and "sleep".  Many thermostats allow you to have
a different schedule every day.  The Schedule sensor allows you to create a single schedule
that matches dates or times for named slots.  Additionally, if a single schedule doesn't
meet the need, then multiple schedules can be created and the active schedule is
based on a condition.

## Examples

### Single Schedule Based on Dates

This is a single schedule based on dates.  It uses both static dates as well as 
templates.

```yaml
sensor:
  - platform: schedule
    name: Season
    schedule:
      - { name: "winter", date: "01/01" }
      - { name: "spring", date: "03/21" }
      - { name: "summer", date: "06/21" }
      - { name: "fall", date: "09/1" }
      - { name: "halloween", date: "9/21" }
      - { name: "thanksgiving", date: "11/1" }
      # Christmas starts the day after Thanksgiving.  Thanksgiving is defined
      # as the fourth Thursday of November
      - name: "christmas"
        date_template: "{{ nth_day(now().year, 11, 3, 4) }}"
```

### Multiple Schedules with Conditions

Multiple schedules can be created.  In the event of multiple schedules the
sensor will check each schedul's condition stopping at the first one that
evaluates true.  The schedules will be re-evaluated the next time the sensors
updates.  Update intervales are based on the time of slots used in the
schedule.  If a schedule is created with slots using time or time_template
attributes then the update interval is every 60 seconds.  If date or
date_template attributes are used, then the update interval is once a day.

One advantage to the schedule sensor is that the schedule itself
wraps around.  In the following example, the first schedule will have a state
"sleep" between 00:00 and 07:00 will.  Otherwise, the sensor state matches
times equal to or later than those specified.  Times from 7:00 to 7:59 on the
first schedule will have the state "wake".

```yaml
sensor:
  - platform: schedule
    name: Day
    schedules:
      - name: "weekend schedule"
        schedule:
          - { name: wake, time: "7:00" }
          - { name: breakfast, time: "8:00" }
          - { name: day, time: "9:00" }
          - { name: dinner, time: "18:30" }
          - name: quiet
            time_template: "{% if is_state('binary_sensor.week_night', 'on')%}19:30{% else %}21:00{% endif %}"
          - name: sleep
            time_template: "{% if is_state('binary_sensor.week_night', 'on')%}20:30{% else %}21:30{% endif %}"
        condition:
          condition: state
          entity_id: binary_sensor.week_day
          state: "off"
      - name: "regular schedule"
        schedule:
          - { name: wake, time: "5:00" }
          - { name: breakfast, time: "6:00" }
          - { name: leave, time: "8:00" }
          - { name: day, time: "8:30" }
          - { name: return, time: "16:00" }
          - { name: dinner, time: "18:30" }
          - name: quiet
            time_template: "{% if is_state('binary_sensor.week_night', 'on')%}19:30{% else %}21:00{% endif %}"
          - name: sleep
            time_template: "{% if is_state('binary_sensor.week_night', 'on')%}20:30{% else %}21:30{% endif %}"

```
