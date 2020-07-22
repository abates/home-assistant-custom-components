# Feels Like Component

The Feels Like Component creates a sensor that is a composite of thermometer
and hygrometer.  The sensor will compute the "feels like" (also known as heat
index) temperature using a formula obtained from NOAA

## Configuration

Example configuration

```yaml
sensor:
  - platform: feels_like
    name: Feels Like Temp
    temp_sensor: sensors.outside_temp
    humidity_sensor: sensors.outside_humidity
```
