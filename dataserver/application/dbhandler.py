import datetime

from application import server, db
from application.models import Available, Measurements, Series, Datum

def new_available(data):
    out = {'ok': False}
    in_fileserver_id = data.get('id')
    fsid = int(in_fileserver_id)
    avail = Available.query.filter_by(fileserver_id=fsid).all()
    if len(avail) == 1:
        ## was available already before, check and update fields
        in_status            = data.get('status')
        in_fieldstatus       = data.get('fieldstatus')
        in_datastatus        = data.get('datastatus')
        avail[0].status      = in_status
        avail[0].fieldstatus = in_fieldstatus
        avail[0].datastatus  = in_datastatus
        meas = Measurements.query.filter_by(fileserver_id=fsid).all()
        if len(meas) == 1:
            ## avail[0].fetched = True # should only be set by shell_fetch
            if in_status != 'submitted':
                meas[0].fs_state = False
            elif in_fieldstatus != 'valid':
                meas[0].fs_state = False
            elif in_datastatus != 'valid':
                meas[0].fs_state = False
            else:
                meas[0].fs_state = True
        elif len(meas) > 1:
            server.logger.warning("new_available: multiple meas matching to fsid " +
                                  str(fsid))
        else:
            pass
            ## avail[0].fetched = False # should only be set by shell_cleanup
        db.session.commit()
    elif len(avail) > 1:
        server.logger.warning("new_available: multiple avail matching to fsid " +
                              str(fsid))
    else:
        ## add to Available table
        in_date          = data.get('date')
        in_measure_date  = data.get('measure_date')
        in_status        = data.get('status')
        in_fieldfilename = data.get('fieldfilename')
        in_datafilename  = data.get('datafilename')
        in_fieldstatus   = data.get('fieldstatus')
        in_datastatus    = data.get('datastatus')
        in_comment       = data.get('comment')
        obj_date         = datetime.datetime.strptime(in_date,'%Y-%m-%dT%H:%M:%S.%fZ')
        obj_measure_date = datetime.datetime.strptime(in_measure_date, "%Y-%m-%d").date()
        new_avail = Available(fileserver_id = fsid,
                              date          = obj_date,
                              measure_date  = obj_measure_date,
                              fieldname     = in_fieldfilename,
                              dataname      = in_datafilename,
                              status        = in_status,
                              fieldstatus   = in_fieldstatus,
                              datastatus    = in_datastatus,
                              fetched = False, ## shell_fetch sets this True when it finishes
                              comment = in_comment)
        db.session.add(new_avail)
        db.session.commit()
        out['ok'] = True
    return out

def new_measurements(data):
    out = {'ok': False}
    in_fileserver_id = data.get('id')
    fileserver_id    = int(in_fileserver_id)
    in_project       = data.get('project')
    in_date          = data.get('date')
    in_measure_date  = data.get('measure_date')
    in_status        = data.get('status')
    in_device        = data.get('device')
    in_chamber       = data.get('chamber')
    in_soil          = data.get('soil')
    in_comment       = data.get('comment')
    obj_date         = datetime.datetime.strptime(in_date,'%Y-%m-%dT%H:%M:%S.%fZ')
    obj_measure_date = datetime.datetime.strptime(in_measure_date, "%Y-%m-%d").date()
    new_meas = Measurements(fileserver_id = fileserver_id,
                            project       = in_project,
                            date          = obj_date,
                            measure_date  = obj_measure_date,
                            device        = in_device,
                            chamber       = in_chamber,
                            soil          = in_soil,
                            comment       = in_comment)
    db.session.add(new_meas)
    db.session.commit()
    out['ok']       = True
    out['local_id'] = new_meas.id
    out['meas']     = new_meas
    return out

def get_string(datum,label,maxsize):
    s = datum.get(label)
    if type(s) == str:
        s = s[:maxsize]
    return s

def new_series(data,meas_id):
    out = {'ok': False, 'ids': []}
    num_new_series = len(data)
    new_series_v = []
    siteids_v = []
    for i in range(num_new_series):
        in_s_date       = data[i].get('date')
        in_s_start_time = data[i].get('start_time')
        in_s_end_time   = data[i].get('end_time')
        ## note: date string lengths sometimes differ
        if len(in_s_date) > 10:
            obj_s_date = datetime.datetime.strptime(in_s_date, "%Y-%m-%dT%H:%M:%S").date()
        else:
            obj_s_date = datetime.datetime.strptime(in_s_date, "%Y-%m-%d").date()
        obj_s_start_time = datetime.datetime.strptime(in_s_start_time, "%H:%M:%S").time()
        obj_s_end_time   = datetime.datetime.strptime(in_s_end_time, "%H:%M:%S").time()
        numerics = {
            't05': data[i].get('t05'),
            't10': data[i].get('t10'),
            't15': data[i].get('t15'),
            't20': data[i].get('t20'),
            't30': data[i].get('t30'),
            't40': data[i].get('t40'),
            'tsmoisture': data[i].get('tsmoisture'),
            'sm': data[i].get('sm'),
            'wt': data[i].get('wt')
        }
        for k, v in numerics.items():
            if type(v) == str:
                try:
                    if ',' in v:
                        vr = v.replace(',','.')
                        numerics[k] = float(vr)
                    elif '.' in v:
                        numerics[k] = float(v)
                except:
                    print("could not convert " + k)
                    pass
            elif type(v) == int:
                numerics[k] = float(v)
            if type(numerics[k]) != float:
                numerics[k] = None
        pt = data[i].get('pointtype')
        strings = {
            'pointtype': get_string(data[i],'pointtype',64),
            'sitedesc':  get_string(data[i],'sitedesc',64),
            'chambersetting': get_string(data[i],'chambersetting',64),
            'notes1':    get_string(data[i],'notes1',256),
            'notes2':    get_string(data[i],'notes2',256),
            'notes3':    get_string(data[i],'notes3',256),
            'fabric':    get_string(data[i],'fabric',128),
            'weather':   get_string(data[i],'weather',128),
            'wind':      get_string(data[i],'wind',128)
        }
        new_series_v.append(Series(measurements = meas_id,
                                   date         = obj_s_date,
                                   siteid       = data[i].get('siteid'), #todo: check lengths
                                   subsiteid    = data[i].get('subsiteid'),
                                   point        = data[i].get('point'),
                                   start_time   = obj_s_start_time,
                                   end_time     = obj_s_end_time,
                                   start_ppm    = data[i].get('start_ppm'),
                                   end_ppm      = data[i].get('end_ppm'),
                                   start_temp   = data[i].get('start_temp'),
                                   end_temp     = data[i].get('end_temp'),
                                   chamber_vol  = data[i].get('chamber_vol'),
                                   chamber_area = data[i].get('chamber_area'),
                                   t05 = numerics['t05'],
                                   t10 = numerics['t10'],
                                   t15 = numerics['t15'],
                                   t20 = numerics['t20'],
                                   t30 = numerics['t30'],
                                   t40 = numerics['t40'],
                                   tsmoisture = numerics['tsmoisture'],
                                   sm = numerics['sm'],
                                   wt = numerics['wt'],
                                   pointtype = strings['pointtype'],
                                   sitedesc = strings['sitedesc'],
                                   chambersetting = strings['chambersetting'],
                                   notes1 = strings['notes1'],
                                   notes2 = strings['notes2'],
                                   notes3 = strings['notes3'],
                                   fabric = strings['fabric'],
                                   weather = strings['weather'],
                                   wind = strings['wind']))
        siteids_v.append(data[i].get('siteid'))
    for i in range(num_new_series):
        db.session.add(new_series_v[i])
    db.session.commit()
    for i in range(num_new_series):
        out['ids'].append(new_series_v[i].id)
    siteids_v = list(dict.fromkeys(siteids_v))
    out['objs'] = new_series_v
    out['siteids'] = siteids_v
    out['ok'] = True
    return out

def new_data(data,series_id):
    out = {'ok': False}
    data_length = len(data['time']) # assuming gas has the same length, todo: check
    if data_length < 1:
        out['empty'] = True
        out['ok'] = True
    else:
        out['empty'] = False
        data_v = []
        gases = []
        if 'co2' in data:
            gases.append('co2')
        if 'ch4' in data:
            gases.append('ch4')
        if 'n2o' in data:
            gases.append('n2o')
        for i in range(data_length):
            in_d_time = data['time'][i]
            obj_d_time = datetime.datetime.strptime(in_d_time, "%H:%M:%S").time()
            data_v.append(Datum(series = series_id,
                                time = obj_d_time,
                                co2_ppm = data['co2'][i] if 'co2' in gases else None,
                                ch4_ppb = data['ch4'][i] if 'ch4' in gases else None,
                                n2o_ppb = data['n2o'][i] if 'n2o' in gases else None))
        for i in range(data_length):
            db.session.add(data_v[i])
        db.session.commit()
        out['ok'] = True
        out['gases'] = gases
    return out
