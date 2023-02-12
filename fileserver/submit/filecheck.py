import numpy
import pandas
#import chardet

import datetime

from math import pi
from pathlib import Path
from .models import Measurements

## dimesions as (radius, height) in metres
## this is here for legacy fieldforms
chamber_dimensions = {
    "EE1": (0.15, 0.303),
    "LV1": (0.15, 0.301),
    "LV2": (0.15, 0.302),
    "LV3": (0.15, 0.302),
    "LT1": (0.1575, 0.31),
    "FI1": (0.1575, 0.31),
    "FI2": (0.1575, 0.31),
    "FI3": (0.1575, 0.31),
    "FI4": (0.1575, 0.31),
    "FI5": (0.1575, 0.31),
    "FI6": (0.1575, 0.31),
    "FI7": (0.1575, 0.31),
    "FI8": (0.1575, 0.31),
    "FI10": (0.1575, 0.30),
    "FI11": (0.155, 0.30),
    "FI12": (0.1575, 0.31),
    "FI31": (0.1575, 0.21),
    "FI32": (0.1575, 0.21),
    "FI33": (0.1575, 0.21)
}

## check functions: used when uploading

#def check_df_encoding(filepath):
#    rawdata = open(filepath,'rb').read()
#    result = chardet.detect(rawdata)
#    return result['encoding']

def check_df_is_licor(filepath):
    is_licor = False
    with open(filepath, "r") as rd:
        line = rd.readline()
        if line[0:6] == "Model:":
            is_licor = True
        elif line[0:6] == "\ufeffModel":
            ## utf-8 byte order mark is present in some files
            is_licor = True
    return is_licor

def check_df_is_licor_smart(filepath: str):
    is_licor_smart = False
    with open(filepath, "r") as rd:
        line = rd.readline()
        if line[0:3] == "LI-":
            is_licor_smart = True
    return is_licor_smart

def check_df_is_gasmet(filepath):
    is_gasmet = False
    with open(filepath, "r") as rd:
        line = rd.readline()
        if line[0:4] == "Line":
            is_gasmet = True
    return is_gasmet

def check_df_is_egm5(filepath):
    is_egm5 = False
    with open(filepath, "r") as rd:
        found_start = False
        found_end = False
        found_zero = False
        while True:
            line = rd.readline()
            if not line:
                break
            elif line[:5] == "Start":
                found_start = True
            elif line[:3] == "End":
                found_end = True
            elif line[:4] == "Zero":
                found_zero = True
            if found_start & found_end:
                is_egm5 = True
                break
    return is_egm5

def check_df_is_egm4(filepath):
    is_egm4 = False
    with open(filepath, "r") as rd:
        found_egm4 = False
        found_plot = False
        while True:
            line = rd.readline()
            if not line:
                break
            elif line[:5] == ";Plot":
                found_plot = True
            elif line[:6] == ";EGM-4":
                found_egm4 = True
            if found_egm4 | found_plot:
                is_egm4 = True
                break
    return is_egm4

## get functions: used by detail views and data API

## used by get_ff_pandas
def read_ff_pandas(filepath):
    out = {'ok': False, 'msg': []}
    try:
        df = pandas.read_excel(filepath,sheet_name="Measurements",
                               header=0,skiprows=[1])
    except FileNotFoundError as e:
        out['msg'].append("file not found on the server filesystem ")
    except Exception as e:
        out['msg'].append("exception occurred in pandas.read_excel ")
    else:
        df.dropna(subset=['Start time'],inplace=True)
        out['ok'] = True
        out['df'] = df
    return out

def get_ff_pandas(filepath: str, device = 'undetermined'):
    out = read_ff_pandas(filepath)

    if not out['ok']:
        return out

    df = out['df']

    ## check that required columns exist
    ## todo: add soil temps, topsoil moisture, wt real ?
    req_cols = ["Date (yyyy-mm-dd)","Monitoring site","Sub-site ID",
                "Monitoring point ID","Start time","End time",
                "Chamber start T, C","Chamber end T, C",
                "Chamber volume, dm3","Chamber area, dm2"]
    for i in range(len(req_cols)):
        if not req_cols[i] in df.columns:
            out['msg'].append(req_cols[i] + ' missing from fieldform ')
            out['ok'] = False
            return out
    ## renaming 'Monitoring site' to the old name 'Monitoring site ID'
    df.rename(columns = {'Monitoring site':'Monitoring site ID'}, inplace = True)

    ## start times
    are_start_times = df["Start time"].apply(lambda x: True if type(x) == datetime.time else False)
    if are_start_times.all():
        out['startend_ok'] = True
    else:
        try:
            df["Start time"] = pandas.to_datetime(df["Start time"]).dt.time
        except ValueError:
            out['msg'].append('ValueError in parsing Start time ')
            out['startend_ok'] = False
            out['ok'] = False
            return out
        except TypeError:
            out['msg'].append('TypeError in parsing Start time ')
            out['startend_ok'] = False
            out['ok'] = False
            return out
        except:
            out['msg'].append('error in parsing Start time ')
            out['startend_ok'] = False
            out['ok'] = False
            return out
        else:
            out['startend_ok'] = True

    ## end times
    are_end_times = df["End time"].apply(lambda x: True if type(x) == datetime.time else False)
    if are_end_times.all():
        out['startend_ok'] = True
    else:
        try:
            df["End time"] = pandas.to_datetime(df["End time"]).dt.time
        except ValueError:
            out['msg'].append('ValueError in parsing End time ')
            out['startend_ok'] = False
            out['ok'] = False
            return out
        except TypeError:
            out['msg'].append('TypeError in parsing End time ')
            out['startend_ok'] = False
            out['ok'] = False
            return out
        except:
            out['msg'].append('error in parsing End time ')
            out['startend_ok'] = False
            out['ok'] = False
            return out
        else:
            out['startend_ok'] = True

    ## check that the date column is readable
    date_dtype = df.dtypes["Date (yyyy-mm-dd)"]
    if date_dtype == "int64":
        ## if date column type is int64, then the dashes are probably missing
        df["Date (yyyy-mm-dd)"] = pandas.to_datetime(df["Date (yyyy-mm-dd)"],
                                                     format='%Y%m%d',errors='coerce')
        if df["Date (yyyy-mm-dd)"].isnull().any():
            out['msg'].append('cannot parse Date (yyyy-mm-dd) column ')
            out['datetime_ok'] = False
            out['ok'] = False
            return out
    else:
        df["Date (yyyy-mm-dd)"] = pandas.to_datetime(df["Date (yyyy-mm-dd)"],
                                                     format='%Y-%m-%d',errors='coerce')
        if df["Date (yyyy-mm-dd)"].isnull().any():
            out['msg'].append('cannot parse Date (yyyy-mm-dd) column ')
            out['datetime_ok'] = False
            out['ok'] = False
            return out
    out['datetime_ok'] = True

    ## check that measurement durations are sensible
    ## todo: improve error messages
    out['durations_ok'] = True
    starts = df["Start time"].to_list()
    ends = df["End time"].to_list()
    if len(starts) != len(ends):
        out['msg'].append('start and end times mismatch ')
        out['durations_ok'] = False
        out['ok'] = False
        return out
    else:
        for i in range(len(starts)):
            start_t = datetime.datetime.combine(datetime.date.today(),starts[i])
            end_t = datetime.datetime.combine(datetime.date.today(),ends[i])
            duration = (end_t - start_t).total_seconds()
            if duration < 5:
                if device != 'egm4':
                    out['msg'].append('a measurement with duration < 5 seconds ')
                    out['durations_ok'] = False
                    out['ok'] = False
                    return out
            elif duration > 1800:
                out['msg'].append('a measurement with duration > 1800 seconds ')
                out['durations_ok'] = False
                out['ok'] = False
                return out

    ## check that site ID is available for all rows
    out['siteid_ok'] = True
    siteids = df["Monitoring site ID"].to_list()
    if pandas.isna(siteids[0]):
        out['msg'].append('first site id is missing ')
        out['siteid_ok'] = False
        out['ok'] = False
        return out
    missing = pandas.isna(siteids)
    if any(missing):
        for i in range(1,len(siteids)):
            if pandas.isna(siteids[i]):
                siteids[i] = siteids[i-1]
        new_siteids = pandas.Series(siteids, index = df.index)
        df["Monitoring site ID"] = new_siteids
    
    ## check that subsite ID is available for all rows
    out['subsiteid_ok'] = True
    subsiteids = df["Sub-site ID"].to_list()
    if pandas.isna(subsiteids[0]):
        out['msg'].append('first subsite id is missing ')
        out['subsiteid_ok'] = False
        out['ok'] = False
        return out
    missing = pandas.isna(subsiteids)
    if any(missing):
        for i in range(1,len(subsiteids)):
            if pandas.isna(subsiteids[i]):
                subsiteids[i] = subsiteids[i-1]
        new_subsiteids = pandas.Series(subsiteids, index = df.index)
        df["Sub-site ID"] = new_subsiteids

    ## check that chamber ID is available for all rows
    ## todo: chamber id should not be necessary
    #out['chamberid_ok'] = True
    #chamberids = df["Chamber ID"].to_list()
    #keys_present = all(i in chamber_dimensions.keys() for i in chamberids)
    #if not keys_present:
    #    out['msg'].append('missing chamber ID values ')
    #    out['chamberid_ok'] = False
    #    ## out['ok'] = False
    #    return out

    ## check the 'Start ppm' and 'End ppm' columns, create if missing
    if not 'Start ppm' in df.columns:
        startppms = pandas.Series([numpy.nan for i in range(df.shape[0])],
                                  index = df.index)
        df["Start ppm"] = startppms
    if not 'End ppm' in df.columns:
        endppms = pandas.Series([numpy.nan for i in range(df.shape[0])],
                                index = df.index)
        df["End ppm"] = endppms        

    ## check that required columns are numeric
    out['numerics_ok'] = True
    numerics = ["Start ppm","End ppm","Chamber start T, C","Chamber end T, C"]
    for i in range(len(numerics)):
        if df.dtypes[numerics[i]] == numpy.object:
            try:
                df[numerics[i]] = pandas.to_numeric(
                    df[numerics[i]].astype(str).str.replace(',','.'))
            except ValueError as e:
                out['msg'].append('cannot convert ' + numerics[i] + ' to numeric ')
                out['numerics_ok'] = False
                out['ok'] = False
                return out
    startnans = df["Chamber start T, C"].apply(lambda x: True if numpy.isnan(x) else False)
    endnans = df["Chamber end T, C"].apply(lambda x: True if numpy.isnan(x) else False)
    if startnans.any() and endnans.any():
        out['msg'].append('numerical values not available for either start temp or end temp ')
        out['numerics_ok'] = False
        out['ok'] = False
        return out

    ## check: chamber volume column is numeric, finite, and positive
    out['volume_ok'] = True
    if df.dtypes["Chamber volume, dm3"] == numpy.object:
        out['msg'].append('chamber volumes are not numeric ')
        out['volume_ok'] = False
        out['ok'] = False
        return out
    chvols = df["Chamber volume, dm3"].to_numpy()
    numpyfloats = all(isinstance(i,numpy.floating) or isinstance(i,numpy.integer)
                      for i in chvols)
    if not numpyfloats:
        out['msg'].append('some chamber volumes are not numeric ')
        out['volume_ok'] = False
        out['ok'] = False
        return out
    finites = all(numpy.isfinite(i) for i in chvols)
    if not finites:
        out['msg'].append('some chamber volumes are not finite ')
        out['volume_ok'] = False
        out['ok'] = False
        return out
    if len(chvols) != len(chvols[chvols > 0.0]):
        out['msg'].append('some chamber volumes are not positive ')
        out['volume_ok'] = False
        out['ok'] = False
        return out

    ## check: chamber areas column is numeric, finite, and positive
    out['area_ok'] = True
    if df.dtypes["Chamber area, dm2"] == numpy.object:
        out['msg'].append('chamber areas are not numeric ')
        out['area_ok'] = False
        out['ok'] = False
        return out
    chareas = df["Chamber area, dm2"].to_numpy()
    numpyfloats = all(isinstance(i,numpy.floating) or isinstance(i,numpy.integer)
                      for i in chareas)
    if not numpyfloats:
        out['msg'].append('some chamber areas are not numeric ')
        out['area_ok'] = False
        out['ok'] = False
        return out
    finites = all(numpy.isfinite(i) for i in chareas)
    if not finites:
        out['msg'].append('some chamber areas are not finite ')
        out['area_ok'] = False
        out['ok'] = False
        return out
    if len(chareas) != len(chareas[chareas > 0.0]):
        out['msg'].append('some chamber areas are not positive ')
        out['area_ok'] = False
        out['ok'] = False
        return out

    ## write back to out dict
    out['df'] = df
    out['dims'] = df.shape
    return out


def get_ff_pandas_legacy(filepath: str, device = 'undetermined'):
    out = read_ff_pandas(filepath)
    if not out['ok']:
        return out
    df = out['df']

    ## check that required columns exist
    ## todo: add soil temps, topsoil moisture, wt real
    req_cols = ["Date (yyyy-mm-dd)","Monitoring site ID","Sub-site ID",
                "Monitoring point ID","Start time","End time",
                "Chamber start T, C","Chamber end T, C",
                "Chamber volume, dm3","Chamber ID"]
    for i in range(len(req_cols)):
        if not req_cols[i] in df.columns:
            out['msg'].append(req_cols[i] + ' missing from fieldform ')
            out['ok'] = False
            return out

    are_start_times = df["Start time"].apply(lambda x: True if type(x) == datetime.time else False)
    are_end_times = df["End time"].apply(lambda x: True if type(x) == datetime.time else False)
    if are_start_times.all() and are_end_times.all():
        out['startend_ok'] = True
    else:
        try:
            ## try to coerce start and end times to datetime
            df["Start time"] = pandas.to_datetime(df["Start time"]).dt.time
            df["End time"] = pandas.to_datetime(df["End time"]).dt.time
        except ValueError:
            out['msg'].append('ValueError in parsing Start time and End time ')
            out['startend_ok'] = False
            out['ok'] = False
            return out
        except TypeError:
            out['msg'].append('TypeError in parsing Start time and End time ')
            out['startend_ok'] = False
            out['ok'] = False
            return out
        except:
            out['msg'].append('error in parsing Start time and End time ')
            out['startend_ok'] = False
            out['ok'] = False
            return out
        else:
            out['startend_ok'] = True

    ## check that the date column is readable
    df["Date (yyyy-mm-dd)"] = pandas.to_datetime(df["Date (yyyy-mm-dd)"],
                                                 format='%Y-%m-%d',errors='coerce')
    if df["Date (yyyy-mm-dd)"].isnull().any():
        out['msg'].append('cannot parse Date (yyyy-mm-dd) column ')
        out['datetime_ok'] = False
        out['ok'] = False
        return out
    else:
        out['datetime_ok'] = True

    ## check that measurement durations are sensible
    ## todo: improve error messages
    out['durations_ok'] = True
    starts = df["Start time"].to_list()
    ends = df["End time"].to_list()
    if len(starts) != len(ends):
        out['msg'].append('start and end times mismatch ')
        out['durations_ok'] = False
        out['ok'] = False
        return out
    else:
        for i in range(len(starts)):
            start_t = datetime.datetime.combine(datetime.date.today(),starts[i])
            end_t = datetime.datetime.combine(datetime.date.today(),ends[i])
            duration = (end_t - start_t).total_seconds()
            if duration < 5:
                if device != 'egm4':
                    out['msg'].append('a measurement with duration < 5 seconds ')
                    out['durations_ok'] = False
                    out['ok'] = False
                    return out
            elif duration > 1800:
                out['msg'].append('a measurement with duration > 1800 seconds ')
                out['durations_ok'] = False
                out['ok'] = False
                return out

    ## check that site ID is available for all rows
    out['siteid_ok'] = True
    siteids = df["Monitoring site ID"].to_list()
    if pandas.isna(siteids[0]):
        out['msg'].append('first site id is missing ')
        out['siteid_ok'] = False
        out['ok'] = False
        return out
    missing = pandas.isna(siteids)
    if any(missing):
        for i in range(1,len(siteids)):
            if pandas.isna(siteids[i]):
                siteids[i] = siteids[i-1]
        new_siteids = pandas.Series(siteids, index = df.index)
        df["Monitoring site ID"] = new_siteids
    
    ## check that subsite ID is available for all rows
    out['subsiteid_ok'] = True
    subsiteids = df["Sub-site ID"].to_list()
    if pandas.isna(subsiteids[0]):
        out['msg'].append('first subsite id is missing ')
        out['subsiteid_ok'] = False
        out['ok'] = False
        return out
    missing = pandas.isna(subsiteids)
    if any(missing):
        for i in range(1,len(subsiteids)):
            if pandas.isna(subsiteids[i]):
                subsiteids[i] = subsiteids[i-1]
        new_subsiteids = pandas.Series(subsiteids, index = df.index)
        df["Sub-site ID"] = new_subsiteids

    ## check that chamber ID is available for all rows
    out['chamberid_ok'] = True
    chamberids = df["Chamber ID"].to_list()
    keys_present = all(i in chamber_dimensions.keys() for i in chamberids)
    if not keys_present:
        out['msg'].append('missing chamber ID values ')
        out['chamberid_ok'] = False
        out['ok'] = False
        return out

    ## check the 'Start ppm' and 'End ppm' columns, create if missing
    if not 'Start ppm' in df.columns:
        startppms = pandas.Series([numpy.nan for i in range(df.shape[0])],
                                  index = df.index)
        df["Start ppm"] = startppms
    if not 'End ppm' in df.columns:
        endppms = pandas.Series([numpy.nan for i in range(df.shape[0])],
                                index = df.index)
        df["End ppm"] = endppms        

    ## check that required columns are numeric
    out['numerics_ok'] = True
    numerics = ["Start ppm","End ppm","Chamber start T, C","Chamber end T, C"]
    for i in range(len(numerics)):
        if df.dtypes[numerics[i]] == numpy.object:
            try:
                df[numerics[i]] = pandas.to_numeric(
                    df[numerics[i]].astype(str).str.replace(',','.'))
            except ValueError as e:
                out['msg'].append('cannot convert ' + numerics[i] + ' to numeric ')
                out['numerics_ok'] = False
                out['ok'] = False
                return out
    startnans = df["Chamber start T, C"].apply(lambda x: True if numpy.isnan(x) else False)
    endnans = df["Chamber end T, C"].apply(lambda x: True if numpy.isnan(x) else False)
    if startnans.any() and endnans.any():
        out['msg'].append('numerical values not available for either start temp or end temp ')
        out['numerics_ok'] = False
        out['ok'] = False
        return out

    ## check the infamous chamber volume column
    out['volume_ok'] = True
    if df.dtypes["Chamber volume, dm3"] == numpy.object:
        ch_ids = df["Chamber ID"].to_list()
        ch_chs = df["Change in chamber height, cm"].to_list()
        try:
            hgts = [chamber_dimensions.get(ch_ids[i])[1] + (float(ch_chs[i])/100.0)
                    for i in range(len(ch_ids))]
            rads = [chamber_dimensions.get(ch_ids[i])[0] for i in range(len(ch_ids))]
        except TypeError as e:
            out['msg'].append('cannot infer chamber volume ')
            out['volume_ok'] = False
            out['ok'] = False
            return out
        else:
            areas = [pi * r * r for r in rads]
            ## volumes in dm3
            volumes = pandas.Series([1000.0 * areas[i] * hgts[i] for i in range(len(areas))],
                                    index = df.index)
            df["Chamber volume, dm3"] = volumes
    chvols = df["Chamber volume, dm3"].to_numpy()
    numpyfloats = all(isinstance(i,numpy.floating) for i in chvols)
    if not numpyfloats:
        out['msg'].append('some chamber volumes are not numeric ')
        out['volume_ok'] = False
        out['ok'] = False
        return out
    else:
        finites = all(numpy.isfinite(i) for i in chvols)
        if not finites:
            out['msg'].append('some chamber volumes are not finite ')
            out['volume_ok'] = False
            out['ok'] = False
            return out

    ## legacy ff does not have chamber areas, create based on chamber IDs
    out['area_ok'] = True
    ch_ids = df["Chamber ID"].to_list()
    try:
        rads = [chamber_dimensions.get(ch_ids[i])[0] for i in range(len(ch_ids))]
    except TypeError as e:
        out['msg'].append('cannot infer chamber area ')
        out['area_ok'] = False
        out['ok'] = False
        return out
    else:
        areas = pandas.Series([pi * r * r * 100.0 for r in rads],index=df.index)
        df["Chamber area, dm2"] = areas

    ## write back to out dict
    out['df'] = df
    out['dims'] = df.shape
    return out


def read_df_egm4(filepath: str, return_df: bool):
    out = {'ok': False, 'msg': []}
    textlines = []
    with open(filepath, "r") as rd:
        i = 0
        for line in rd:
            if not line:
                break
            elif line[:1] == ";":
                textlines.append(i)
            i += 1
    ## read in file
    try:
        cnames = ['Plot','RecNo','Day','Month','Hour','Min','CO2','mb Ref',
                  'mbR Temp','Input A','Input B','Input C','Input D','Input E',
                  'Input F','Input G','Input H','ATMP','Probe Type']
        df = pandas.read_csv(filepath,sep='\s+',names=cnames,skiprows=textlines)
    except:
        out['msg'].append("read_df_egm4: error in pandas.read_csv() ")
        return out
    ## add record index column
    try:
        recnumbers = df['RecNo'].to_list()
        rec_index = [0] * df.shape[0]
        num_recs = 1
        for i in range(1,df.shape[0]):
            if recnumbers[i] != recnumbers[i-1] + 1:
                num_recs += 1
            rec_index[i] = num_recs - 1
        out['num_records'] = num_recs
        df["rec_index"] = pandas.Series(rec_index, index = df.index)
    except:
        out['msg'].append("error in processing record indices ")
        return out
    ## add date column
    try:
        months = df['Month'].to_list()
        days = df['Day'].to_list()
        ## todo: using a hard coded 2021, fix this
        date_objs = [datetime.date(2021,i,j) for i,j in zip(months,days)]
        df["Date"] = pandas.Series(date_objs, index = df.index)
    except:
        out['msg'].append("error in processing date values ")
        return out
    ## add time column
    try:
        hours = df['Hour'].to_list()
        minutes = df['Min'].to_list()
        time_objs = [datetime.time(i,j,0) for i,j in zip(hours,minutes)]
        df["Time"] = pandas.Series(time_objs, index = df.index)
    except:
        out['msg'].append("error in processing time values ")
        return out
    ## success, fill out object if needed
    out['ok'] = True
    out['dims'] = df.shape
    out['skiprows'] = textlines
    if return_df:
        out['df'] = df
    return out

def read_df_egm5(filepath: str, return_df: bool):
    out = {'ok': False, 'msg': []}
    textlines = [0] ## append to this, always skip header
    with open(filepath, "r") as rd:
        i = 0
        for line in rd:
            if not line:
                break
            elif (line[:5] == "Start") | (line[:3] == "End") | (line[:4] == "Zero"):
                textlines.append(i)
            i += 1
    ## read in file
    try:
        ## on EGM5 there may be columns without names on the header
        ## they are named c18-c23 here
        cnames = ['Tag(M3)','Date','Time','Plot No.','Rec No.','CO2','Pressure',
                  'Flow','H2O','Tsen','O2','Error','Aux V','PAR','Tsoil','Tair',
                  'Msoil','c18','c19','c21','c22','c23']
        df = pandas.read_csv(filepath,sep=',',names=cnames,skiprows=textlines)
    except Exception as e:
        ## todo: add e to string
        out['msg'].append("read_df_egm5: error in pandas.read_csv() ")
        ##print(e)
        return out
    ## interpret date
    try:
        df["Date"] = pandas.to_datetime(df["Date"],format='%d/%m/%y').dt.date
    except:
        try:
            df["Date"] = pandas.to_datetime(df["Date"],format='%d/%m/%Y').dt.date
        except:
            out['msg'].append('read_df_egm5: cannot parse Date column ')
            return out
    ## interpret time
    try:
        df["Time"] = pandas.to_datetime(df["Time"]).dt.time # can this fail?
    except:
        out['msg'].append("read_df_egm5: cannot parse Time column ")
        return out
    ## success, fill out object if needed
    out['ok'] = True
    out['dims'] = df.shape
    out['skiprows'] = textlines
    if return_df:
        out['df'] = df
    return out

def read_df_licor_smart(filepath: str, return_df: bool):
    out = {'ok': False, 'msg': []}
    textlines = []
    with open(filepath, "r") as rd:
        i = 0
        for line in rd:
            if not line:
                break
            elif (line[:2] != "1,"):
                textlines.append(i)
            i += 1
    ## read in file
    try:
        cnames = ['Type','Etime','Date','Tcham','Pressure','H2O','CO2',
                  'Cdry','Tsoil','cell_p','DOY','Hour','cell_t','chamber_p_t','co2_wet',
                  'flow_rate','soilp_c','soilp_m','soilp_t']
        df = pandas.read_csv(filepath,sep=',',names=cnames,skiprows=textlines)
    except Exception as e:
        ## todo: add e to msg string
        out['msg'].append("read_df_licor_smart: error in pandas.read_csv() ")
        print(e)
        return out
    ## interpret time
    try:
        df["Time"] = pandas.to_datetime(df["Date"],format='%Y-%m-%d %H:%M:%S').dt.time
    except:
        out['msg'].append("read_df_licor_smart: cannot parse time from Date column ")
        return out
    ## interpret date
    try:
        df["Date"] = pandas.to_datetime(df["Date"],format='%Y-%m-%d %H:%M:%S').dt.date
    except:
        out['msg'].append('read_df_licor_smart: cannot parse date from Date column ')
        return out
    ## success, fill out object if needed
    out['ok'] = True
    out['dims'] = df.shape
    out['skiprows'] = textlines
    if return_df:
        out['df'] = df
    return out

def read_df_licor(filepath: str, return_df: bool):
    out = {'ok': False, 'msg': []}
    ## read file
    try:
        df = pandas.read_csv(filepath,sep='\t',skiprows=5)
    except FileNotFoundError as e:
        out['msg'].append("read_df_licor: FileNotFoundError ")
        return out
    except Exception as e:
        out['msg'].append("read_df_licor: error in pandas.read_csv() ")
        return out
    df = df.drop(0)
    ## ensure date is readable
    try:
        df["DATE"] = pandas.to_datetime(df["DATE"],format='%Y-%m-%d').dt.date
    except:
        out['msg'].append('read_df_licor: cannot parse DATE column ')
        return out
    ## ensure TIME is datetime
    try:
        df["TIME"] = pandas.to_datetime(df["TIME"]).dt.time
    except:
        out['msg'].append("read_df_licor: error in pandas.to_datetime() ")
        return out
    ## check which of CO2, CH4, N2O are present
    gas_columns = ['CO2','CH4','N2O']
    present = []
    for g in gas_columns:
        if g in df.columns:
            present.append(g)
    out['present'] = present
    ## ensure CO2 is numeric if present
    if 'CO2' in present:
        try:
            df["CO2"] = pandas.to_numeric(df["CO2"])
        except:
            out['msg'].append("read_df_licor: error in reading CO2 with pandas.to_numeric() ")
            return out
    ## ensure CH4 is numeric if present
    if 'CH4' in present:
        try:
            df["CH4"] = pandas.to_numeric(df["CH4"])
        except:
            out['msg'].append("read_df_licor: error in reading CH4 with pandas.to_numeric() ")
            return out
    ## ensure N2O is numeric if present
    if 'N2O' in present:
        try:
            df["N2O"] = pandas.to_numeric(df["N2O"])
        except:
            out['msg'].append("read_df_licor: error in reading N2O with pandas.to_numeric() ")
            return out
    ## fill out obj
    df.dropna(subset=present,inplace=True)
    out['ok'] = True
    out['dims'] = df.shape
    if return_df:
        out['df'] = df
    return out

def read_df_gasmet(filepath: str, return_df: bool):
    out = {'ok': False, 'msg': []}
    textlines = []
    with open(filepath, "r") as rd:
        i = 0
        for line in rd:
            if i > 0:
                if not line:
                    break
                elif (line[:4] == "Line"):
                    textlines.append(i)
            i += 1
    ## read file
    try:
        df = pandas.read_csv(filepath,sep='\t',skiprows=textlines)
    except FileNotFoundError as e:
        out['msg'].append("read_df_gasmet: FileNotFoundError ")
        return out
    except Exception as e:
        out['msg'].append("read_df_gasmet: error in pandas.read_csv() ")
        return out
    ## ensure date is readable
    try:
        df["Date"] = pandas.to_datetime(df["Date"],format='%Y-%m-%d').dt.date
    except:
        out['msg'].append('read_df_gasmet: cannot parse Date column ')
        return out
    ## ensure TIME is datetime
    try:
        df["Time"] = pandas.to_datetime(df["Time"]).dt.time
    except:
        out['msg'].append("read_df_gasmet: cannot parse Time column ")
        return out
    ## ensure CO2 is numeric
    try:
        df["Carbon dioxide CO2"] = pandas.to_numeric(df["Carbon dioxide CO2"])
    except:
        out['msg'].append("read_df_gasmet: error reading CO2 with pandas.to_numeric() ")
        return out
    ## fill out obj
    df.dropna(subset=['Carbon dioxide CO2'],inplace=True)
    out['ok'] = True
    out['dims'] = df.shape
    if return_df:
        out['df'] = df
    return out
