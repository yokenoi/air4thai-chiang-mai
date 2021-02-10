from datetime import datetime, timedelta
from flask import Flask, jsonify, request, send_file
import json
import pandas as pd
import requests
import sqlite3


def get_data(lat=18.838311, long=98.974234):
    engine = sqlite3.connect('air4thai.db')

    latest = engine.execute("select max(datetime(DATETIMEDATA, '+1 hours')) from history").fetchall()[0][0]
    sdate, stime = latest[:10], latest[11:13]
    now = str(datetime.now() + timedelta(hours=7))
    edate, etime = now[:10], now[11:13]

    try:
        if sdate == edate and stime == etime:
            raise KeyError

        url = f'http://air4thai.pcd.go.th/webV2/history/api/data.php?stationID=35t,36t&param=PM25,PM10,O3,CO,NO2,SO2' \
              f'&type=hr&sdate={sdate}&edate={edate}&stime={stime}&etime={etime}'

        while True:
            response = requests.get(url)
            if response.status_code == 200:
                json = response.json()
                break

        data = []

        for station in json.get('stations'):
            station_data = pd.DataFrame(station.get('data'))
            station_data['stationID'] = station.get('stationID')
            data.append(station_data)
        data = data[0].append(data[1]).sort_values(['DATETIMEDATA', 'stationID'])
        data.to_sql(con=engine, name='history', if_exists='append', index=False)

        sql = f'''
            with Average as (

                select Parent.stationID, Parent.DATETIMEDATA, cast(round(avg(Child.PM25)) as int) as p, 'PM25' as pollution
                from history Parent
                    join history Child on
                        datetime(Parent.DATETIMEDATA, '-1 days') < datetime(Child.DATETIMEDATA) and
                        datetime(Parent.DATETIMEDATA) >= datetime(Child.DATETIMEDATA) and
                        Parent.stationID = Child.stationID
                where datetime(Parent.DATETIMEDATA) >= datetime('{latest}')
                group by Parent.stationID, Parent.DATETIMEDATA
                having count(*) = 24

                union

                select Parent.stationID, Parent.DATETIMEDATA, cast(round(avg(Child.PM10)) as int) as p, 'PM10' as pollution
                from history Parent
                    join history Child on
                        datetime(Parent.DATETIMEDATA, '-1 days') < datetime(Child.DATETIMEDATA) and
                        datetime(Parent.DATETIMEDATA) >= datetime(Child.DATETIMEDATA) and
                        Parent.stationID = Child.stationID
                where datetime(Parent.DATETIMEDATA) >= datetime('{latest}')
                group by Parent.stationID, Parent.DATETIMEDATA
                having count(*) = 24

                union

                select Parent.stationID, Parent.DATETIMEDATA, cast(round(avg(Child.O3)) as int) as p, 'O3' as pollution
                from history Parent
                    join history Child on
                        datetime(Parent.DATETIMEDATA, '-8 hours') < datetime(Child.DATETIMEDATA) and
                        datetime(Parent.DATETIMEDATA) >= datetime(Child.DATETIMEDATA) and
                        Parent.stationID = Child.stationID
                where datetime(Parent.DATETIMEDATA) >= datetime('{latest}')
                group by Parent.stationID, Parent.DATETIMEDATA
                having count(*) = 8

                union

                select Parent.stationID, Parent.DATETIMEDATA, round(avg(Child.CO), 1) as p, 'CO' as pollution
                from history Parent
                    join history Child on
                        datetime(Parent.DATETIMEDATA, '-8 hours') < datetime(Child.DATETIMEDATA) and
                        datetime(Parent.DATETIMEDATA) >= datetime(Child.DATETIMEDATA) and
                        Parent.stationID = Child.stationID
                where datetime(Parent.DATETIMEDATA) >= datetime('{latest}')
                group by Parent.stationID, Parent.DATETIMEDATA
                having count(*) = 8

                union

                select stationID, DATETIMEDATA, NO2 AS p, 'NO2' as pollution
                from history
                where datetime(DATETIMEDATA) >= datetime('{latest}')

                union

                select stationID, DATETIMEDATA, SO2 AS p, 'SO2' as pollution
                from history
                where datetime(DATETIMEDATA) >= datetime('{latest}')

            ), air_quality_index_by_pollution as (

                select stationID, DATETIMEDATA,
                       cast(round(min_aqi + (max_aqi - min_aqi) * (p - min_p) / (max_p - min_p)) as int) as AQI
                from Average A
                    join aqi_interval AQ on A.pollution = AQ.pollution and p >= min_p and p <= max_p

                union

                select stationID, DATETIMEDATA,
                       cast(round(min_aqi + min_aqi * (p - min_p) / min_p) as int) as AQI
                from Average A
                    join aqi_interval AQ on A.pollution = AQ.pollution and p >= min_p and max_aqi is null

            ), air_quality_index as (

                select stationID, DATETIMEDATA, max(AQI) as AQI
                from air_quality_index_by_pollution
                group by stationID, DATETIMEDATA

            )

            update history
            set AQI = (
                select AQI
                from air_quality_index A
                where history.stationID = A.stationID
                  and history.DATETIMEDATA = A.DATETIMEDATA
                )
            where DATETIMEDATA >= datetime('{latest}');  
            '''

        engine.execute(sql)
        engine.commit()

        sql = '''select PM25, PM10, CO, O3, NO2, SO2
                 from history 
                 where DATETIMEDATA = (select max(DATETIMEDATA) from history);
                 '''

        if any(map(lambda row: all(map(lambda x: x is None, row)), engine.execute(sql).fetchall())):
            engine.execute('delete from history where DATETIMEDATA = (select max(DATETIMEDATA) from history);')
            engine.commit()
    except KeyError:
        pass

    lat = lat if lat and long else 18.838311
    long = long if lat and long else 98.974234

    sql = f'''
        with cte(stationID, distance) as (
            select stationID, (lat - {lat}) * (lat - {lat}) + (long - {long}) * (long - {long})
            from stations
        )
        select *
        from history
        where DATETIMEDATA = (select max(datetime(DATETIMEDATA)) from history)
          and stationID = (select stationID from cte
                           where distance = (select min(distance) from cte));
    '''

    station, dt, CO, NO2, SO2, O3, PM10, PM25, AQI = engine.execute(sql).fetchall()[0]
    engine.close()

    return {
        'PM25': int(PM25) if PM25 else None,
        'PM10': int(PM10) if PM10 else None,
        'CO': CO,
        'O3': int(O3) if O3 else None,
        'NO2': int(NO2) if NO2 else None,
        'SO2': int(SO2) if SO2 else None,
        'AQI': int(AQI) if AQI else None
    }


app = Flask(__name__)


# GET latest data
@app.route('/api/latest', methods=['GET'])
def latest():
    query_parameters = request.args
    if query_parameters:
        lat = query_parameters.get('lat')
        long = query_parameters.get('long')
        data = get_data(lat=lat, long=long)
    else:
        data = get_data()
    return jsonify(data)


# Query Data
@app.route('/api/query', methods=['GET'])
def query():
    query_parameters = request.args

    sdate = query_parameters.get('sdate')
    stime = query_parameters.get('stime')
    edate = query_parameters.get('edate')
    etime = query_parameters.get('etime')
    station = query_parameters.get('station')
    parameter = query_parameters.get('parameter')

    if sdate and stime:
        sdatetime = f"datetime(DATETIMEDATA) >= datetime('{sdate} {stime}:00:00')"
    elif sdate:
        sdatetime = f"datetime(DATETIMEDATA) >= datetime('{sdate} 00:00:00')"
    elif stime:
        sdatetime = f"datetime(DATETIMEDATA) >= datetime('{(datetime.now() + timedelta(hours=7)).date()} {stime}:00:00')"
    else:
        sdatetime = None

    if edate and etime:
        edatetime = f"datetime(DATETIMEDATA) <= datetime('{edate} {etime}:00:00')"
    elif edate:
        edatetime = f"datetime(DATETIMEDATA) <= datetime('{edate} 23:00:00')"
    elif etime:
        edatetime = f"datetime(DATETIMEDATA) <= datetime('{(datetime.now() + timedelta(hours=7)).date()} {etime}:00:00')"
    else:
        edatetime = None
    if station:
        station = '(' + ','.join(["'" + s + "'" for s in station.split(',')]) + ')'
        station = f"stationID in {station}"
    parameter = f'stationID,DATETIMEDATA,{parameter}' if parameter else '*'
    condition = list(filter(lambda c: c is not None, [sdatetime, edatetime, station]))
    condition = 'where ' + ' and '.join(condition) if condition else ''

    sql = f'select {parameter} from history {condition}'

    engine = sqlite3.connect('air4thai.db')
    df = pd.read_sql(sql, con=engine).T
    data = [json.loads(df[col].to_json()) for col in df]

    return jsonify(data)


# GET database
@app.route('/api/database', methods=['GET'])
def database():
    return  send_file('air4thai.db', as_attachment=True)


app.run(debug=True, host='0.0.0.0')
