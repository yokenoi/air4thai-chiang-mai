# Air4thai Data for Chiang Mai

API for Chiang Mai air quality index from Air4thai (http://air4thai.pcd.go.th/) written in Python (containerized by 
Docker).

There are 2 station which provide the pollution data.
- `35t`: Chiang Mai Governance Center (Chang Phueak, Chiang Mai, Chiang Mai)
- `36t`: Yupparaj Wittayalai School (Si Phum, Chiang Mai, Chiang Mai)

There are 6 pollution measured by the station.
- `PM25` (**PM<sub>2.5</sub>**) : Particulate matter less than 2.5 micrometers (μg/m<sup>3</sup>: microgram per cubic meter)
- `PM10` (**PM<sub>10</sub>**): Particulate matter less than 10 micrometers (μg/m<sup>3</sup>: microgram per cubic meter)
- `CO` (**CO**): Carbon Monoxide (ppm: Part per million)
- `O3` (**O<sub>3</sub>**) Ozone (ppb: Part per billion)
- `SO2` (**SO<sub>2</sub>**) Sulfur Dioxide (ppb: Part per billion)
- `NO2` (**NO<sub>2</sub>**) Nitrogen Dioxide (ppb: Part per billion)

The API also provide AQI data which the original API does not.

### Latest Data

Path:
> `/api/latest`

Parameter: 
> - `lat` (Latitude: real number)
> - `long` (Longitude: real number)

Example: 
> `/api/latest?lat=17.54394&long=19.34935`

Result:

> `{
   "AQI": 76,
   "CO": null, 
   "NO2": 11, 
   "O3": 31, 
   "PM10": 49, 
   "PM25": 49, 
   "SO2": 1
 }`

Return the latest PM2.5, PM10, O3, CO, SO2, NO2, and AQI of the nearest location specified by `lat` and `long` in JSON
format.

If `lat` and `long` are not specified, the data of 35t (Goverance center) station will be returned.

The database will be automatically updated if the latest data is requested.

### Querying the data

Path:
> `/api/query`

Parameter: 
> - `sdate` (Start Date: `YYYY-MM-DD`)
> - `stime` (Start Time (hours): `HH`)
> - `edate` (End Date: `YYYY-MM-DD`)
> - `etime` (End Time (hours): `HH`)
> - `station` (Station: `35t`, `36t` or `35t,36t`)
> - `parameter` (Selected pollution parameter)

Example: 
> `/api/query?sdate=2020-12-01&stime=09&edate=2020-12-01&etime=12&station=35t&parameter=CO,PM25,AQI`

Result:
> `[
     {
       "AQI": 25, 
       "CO": null, 
       "DATETIMEDATA": "2020-12-01 09:00:00", 
       "PM25": 27.0, 
       "stationID": "35t"
     }, 
     {
       "AQI": 25, 
       "CO": null, 
       "DATETIMEDATA": "2020-12-01 10:00:00", 
       "PM25": 24.0, 
       "stationID": "35t"
     }, 
     {
       "AQI": 25, 
       "CO": null, 
       "DATETIMEDATA": "2020-12-01 11:00:00", 
       "PM25": 24.0, 
       "stationID": "35t"
     }, 
     {
       "AQI": 25, 
       "CO": null, 
       "DATETIMEDATA": "2020-12-01 12:00:00", 
       "PM25": 23.0, 
       "stationID": "35t"
     }
   ]`

Return the query of the data by the parameter provided in JSON format. The parameter can be omitted.

