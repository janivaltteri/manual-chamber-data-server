import os
import datetime
from pathlib import Path
from django.contrib.auth.models import User
from .models import Project, Measurements
from .filecheck import *

def handle_uploaded_file(datafile,fieldfile,dataname,fieldname,
                         fftype,measdate,uid,pid,
                         comment_str,dev,chambertype,soiltype):
    uobj = User.objects.get(pk=uid)
    pobj = Project.objects.get(pk=pid)

    ## set output filename
    datatemp_pre: str  = '/opt/mcds/filetemp/data-u'
    fieldtemp_pre: str = '/opt/mcds/filetemp/field-u'
    dataext: str   = '.txt'
    fieldext: str  = '.xlsx'

    ## write temporary files to temp directory, removing previous if present
    datatemp: str  = datatemp_pre + str(uid) + dataext
    fieldtemp: str = fieldtemp_pre + str(uid) + fieldext
    datatemppath = Path(datatemp)
    fieldtemppath = Path(fieldtemp)
    if datatemppath.is_file():
        os.remove(datatemp)
    if fieldtemppath.is_file():
        os.remove(fieldtemp)
    with open(datatemp, 'wb+') as destination:
        for chunk in datafile.chunks():
            destination.write(chunk)
    with open(fieldtemp, 'wb+') as destination:
        for chunk in fieldfile.chunks():
            destination.write(chunk)

    ## validity checking starts here
    out = {'ok': True, 'msg': []}
    fstatus = 'undetermined'
    dstatus = 'undetermined'

    if chambertype == 'light':
        out['ok'] = False
        out['msg'].append("light chambers not yet supported")
        return out

    ## check datafile for encoding
    utf8_enc = check_file_encoding(datatemp)
    if not utf8_enc:
        convert_to_utf8(datatemp)

    ## check that datafile type is correct
    if dev == 'licor':
        if not check_df_is_licor(datatemp):
            out['ok'] = False
            out['msg'].append("datafile cannot be identified as a licor datafile")
            return out
    elif dev == 'licorsmart':
        if not check_df_is_licor_smart(datatemp):
            out['ok'] = False
            out['msg'].append("datafile cannot be identified as a licor smartchamber csvfile")
            return out
    elif dev == 'gasmet':
        if not check_df_is_gasmet(datatemp):
            out['ok'] = False
            out['msg'].append("datafile cannot be identified as a gasmet datafile")
            return out
    elif dev == 'egm5':
        if not check_df_is_egm5(datatemp):
            out['ok'] = False
            out['msg'].append("datafile cannot be identified as an egm5 datafile")
            return out
    elif dev == 'egm4':
        if not check_df_is_egm4(datatemp):
            out['ok'] = False
            out['msg'].append("datafile cannot be identified as an egm4 datafile")
            return out
    else:
        out['ok'] = False
        out['msg'].append("datafile type not currently supported")
        return out

    out['device'] = dev

    if fftype == 'legacy':
        ffp_out = get_ff_pandas_legacy(fieldtemp,dev)
    elif fftype == '2022':
        ffp_out = get_ff_pandas(fieldtemp,dev)
    else:
        out['ok'] = False
        out['msg'].append("undefined field form type")

    if not ffp_out['ok']:
        fstatus = 'invalid'
        out['ok'] = False
        msgs = ffp_out.get('msg')
        if msgs:
            for i in range(len(msgs)):
                out['msg'].append(msgs[i])
        else:
            out['msg'].append("unexpected errors in reading field form ")
        return out
    else:
        fstatus = 'valid'

    ## todo: check datafile contents
    if dev == 'licor':
        rdf_out = read_df_licor(datatemp,True)
    elif dev == 'licorsmart':
        rdf_out = read_df_licor_smart(datatemp,True)
    elif dev == 'gasmet':
        rdf_out = read_df_gasmet(datatemp,True)
    elif dev == 'egm5':
        rdf_out = read_df_egm5(datatemp,True)
    elif dev == 'egm4':
        rdf_out = read_df_egm4(datatemp,True)
    else:
        rdf_out = {'ok': False, 'msg': 'device not supported '}
    if not rdf_out['ok']:
        dstatus = 'invalid'
        out['ok'] = False
        msgs = rdf_out.get('msg')
        if msgs:
            for i in range(len(msgs)):
                out['msg'].append(msgs[i])
            else:
                out['msg'].append("errors in read_df_ ")
        return out
    else:
        dstatus = 'valid'

    ## create Measurements object and store
    newmeas = Measurements(measurer      = uobj,
                           project       = pobj,
                           fftype        = fftype,
                           measure_date  = measdate,
                           comment       = comment_str,
                           device        = dev,
                           chamber       = chambertype,
                           soil          = soiltype,
                           datastatus    = dstatus,
                           datafilepath  = "",
                           dataorigname  = dataname,
                           fieldstatus   = fstatus,
                           fieldfilepath = "",
                           fieldorigname = fieldname)
    newmeas.save()
    new_num = newmeas.id

    ## write file to disk
    datapre: str   = '/opt/mcds/filesubmit/data-'
    fieldpre: str  = '/opt/mcds/filesubmit/field-'
    datapath: str  = datapre + str(new_num) + dataext
    fieldpath: str = fieldpre + str(new_num) + fieldext
    with open(datapath, 'wb+') as destination:
        for chunk in datafile.chunks():
            destination.write(chunk)
    with open(fieldpath, 'wb+') as destination:
        for chunk in fieldfile.chunks():
            destination.write(chunk)
    if not utf8_enc:
        convert_to_utf8(datapath)

    newmeas.datafilepath = datapath
    newmeas.fieldfilepath = fieldpath
    newmeas.save()

    return out

def check_file_encoding(filepath):
    try:
        with open(filepath,"r") as rd:
            line = rd.readline()
    except UnicodeDecodeError as e:
        ## todo: use chardet and return the encoding
        return False
    else:
        return True

def convert_to_utf8(filepath):
    ## todo: read any encoding
    with open(filepath,"r",encoding="iso_8859_1") as rd:
        data = rd.read()
    f = open(filepath,"w",encoding="utf-8")
    f.write(data)
    f.close()
