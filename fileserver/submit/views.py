import numpy
import pandas
import datetime

import logging

# from django.shortcuts import render

from django.http import HttpResponse, HttpResponseRedirect, FileResponse, JsonResponse
from django.contrib import messages
from django.template import loader
from django.shortcuts import render, get_object_or_404

from django.contrib.auth import authenticate, login
from django.contrib.auth.models import User
from django.contrib.auth.decorators import login_required, user_passes_test

from rest_framework.decorators import (
    api_view,
    renderer_classes
)
from rest_framework.response import Response
from rest_framework.renderers import JSONRenderer

from .models import Project, Measurements
from .forms import ProjectForm, MeasurementsForm, ChangeRecordForm
from .uploads import handle_uploaded_file
from .filecheck import *

logger = logging.getLogger(__name__)

## this view shows the login page

def index(request):
    template = loader.get_template('submit/index.html')
    return HttpResponse(template.render({},request))

## this is the main view shown after login
## - shows uploaded files for the current user
## - presents a form for uploading a new measurement set
@login_required
def upload(request):
    if request.method == 'POST':
        form = MeasurementsForm(request.POST,request.FILES)
        if form.is_valid():
            if request.FILES['datafile'].size > 6000000:
                messages.info(request,'Upload failed, datafile size must be under 6 MB')
                
            elif request.FILES['fieldfile'].size > 6000000:
                messages.info(request,'Upload failed, fieldform size must be under 6 MB')
                
            else:
                current_user       = request.user
                userid: int        = current_user.id
                
                md_year: str       = request.POST.get("measure_date_year")
                md_month: str      = request.POST.get("measure_date_month")
                md_day: str        = request.POST.get("measure_date_day")
                measdate           = datetime.date(int(md_year), int(md_month), int(md_day))

                datafilename: str  = request.FILES['datafile'].name
                fieldfilename: str = request.FILES['fieldfile'].name
                comment: str       = request.POST.get("comment", "")
                fftype: str        = request.POST.get("fftype")
                device: str        = request.POST.get("device")
                chamber: str       = request.POST.get("chamber")
                soil: str          = request.POST.get("soil")
                projid_str: str    = request.POST.get("project")

                if not device:
                    messages.info(request,'Please select device')
                elif not chamber:
                    messages.info(request,'Please select chamber type')
                elif not soil:
                    messages.info(request,'Please select soil type')
                elif not projid_str:
                    messages.info(request,'Please select project')
                else:

                    accepted_datafile_exts = ['.txt','.TXT','.dat','.DAT','data','DATA',
                                              '.csv','.CSV','text','TEXT']
                    if fieldfilename[-5:] != '.xlsx':
                        messages.info(request,
                                      'Field form file extension must be .xlsx !')
                    elif datafilename[-4:] not in accepted_datafile_exts:
                        messages.info(request,
                                      'Datafile extension must be one of {0}'
                                      .format(" ".join(accepted_datafile_exts)))
                    elif len(fieldfilename) > 100: # todo: set limit in models
                        messages.info(request,
                                      'Field form file name exceeds maximum of 75 characters')
                    elif len(datafilename) > 100:
                        messages.info(request,
                                      'Data file name exceeds maximum of 75 characters')
                    else:
                        projid: int = int(projid_str) ## todo: can this fail?
                        res = handle_uploaded_file(request.FILES['datafile'],
                                                   request.FILES['fieldfile'],
                                                   datafilename,fieldfilename,
                                                   fftype,measdate,userid,projid,
                                                   comment,device,chamber,soil)
                        if res['ok']:
                            messages.info(request,'Uploaded files ' + datafilename +
                                          ', ' + fieldfilename)
                            logger.info('user ' + str(userid) + ' succesfully uploaded ' +
                                        datafilename + ', ' + fieldfilename)
                        elif res.get('msg'):
                            messages.info(request,'Errors: ' + str(res.get('msg')))
                            logger.info('user ' + str(userid) + ' failed uploading ' +
                                        datafilename + ', ' + fieldfilename + ' errors: '
                                        + str(res.get('msg')))
                        else:
                            messages.info(request,'Upload fails with an undetermined error')
                            logger.info('user ' + str(userid) + ' failed uploading ' +
                                        datafilename + ', ' + fieldfilename +
                                        ' with undetermined error')
            return HttpResponseRedirect('/submit/upload/')
        else:
            messages.info(request,'error: form not valid')
    else:
        current_user = request.user
        userid = current_user.id
        uobj = User.objects.get(pk=userid)
        measurements = Measurements.objects.filter(measurer=userid).order_by('-measure_date')
        form = MeasurementsForm()
    return render(request, 'submit/meas/upload.html',
                  {'form': form, 'measurements': measurements})

## full file listing view available for staff users
@user_passes_test(lambda user: user.is_staff)
def measurements_list(request):
    measurements = Measurements.objects.all().order_by('measurer','-measure_date')
    return render(request, 'submit/meas/list.html',
                  {'measurements': measurements})

## maintenance view available for staff users
@user_passes_test(lambda user: user.is_staff)
def maintenance(request):
    if request.method == 'POST':
        form = ProjectForm(request.POST)
        ## get fields from form
        current_user            = request.user
        userid: int             = current_user.id
        uobj                    = User.objects.get(pk=userid)
        proj_name: str          = request.POST.get("name")
        proj_contact_name: str  = request.POST.get("contact_name")
        proj_contact_email: str = request.POST.get("contact_email")
        if form.is_valid():
            newproj = Project(measurer=uobj,
                              name=proj_name,
                              contact_name=proj_contact_name,
                              contact_email=proj_contact_email)
            newproj.save()
            return HttpResponseRedirect('/submit/maintenance/')
        else:
            messages.info(request,'error: form not valid')
    else:
        form = ProjectForm()
        projects = Project.objects.all().order_by('-date')
    return render(request, 'submit/meas/maintenance.html',
                  {'form': form, 'projects': projects})

@user_passes_test(lambda user: user.is_staff)
def delete_project(request, pid):
    proj = Project.objects.filter(id=pid).first()
    measurements = Measurements.objects.filter(project=pid).order_by('-measure_date')
    if len(measurements) > 0:
        messages.info(request,'error: cannot delete a project which contains submissions')
    else:
        proj.delete()
        messages.info(request,'project deleted')
    return HttpResponseRedirect('/submit/maintenance/')

## this view shows the details from a field form
## and presents a form for changing upload details
@login_required
def formdetail(request, fsid):

    if request.method == 'POST':

        ## update the details of submission via form on the page
        form = ChangeRecordForm(request.POST)
        if form.is_valid():
            comm: str       = request.POST.get("new_comment", "")
            md_year: str    = request.POST.get("new_measure_date_year")
            md_month: str   = request.POST.get("new_measure_date_month")
            md_day: str     = request.POST.get("new_measure_date_day")
            new_soil: str   = request.POST.get("new_soil")
            projid_str: str = request.POST.get("new_project")
            projid: int     = int(projid_str) ## todo: can this fail?
            pobj            = Project.objects.get(pk=projid)
            measdate        = datetime.date(int(md_year), int(md_month), int(md_day))
            Measurements.objects.filter(id=fsid).update(measure_date = measdate)
            Measurements.objects.filter(id=fsid).update(comment = comm)
            Measurements.objects.filter(id=fsid).update(project = pobj)
            Measurements.objects.filter(id=fsid).update(soil = new_soil)
            messages.info(request,'Changed details of submission')
        current_url: str = '/submit/fdetails/' + str(fsid) + '/'
        return HttpResponseRedirect(current_url)

    else:

        submission = Measurements.objects.filter(id=fsid).first()
        ffp        = None
        dimensions = None
        details    = []
        validity   = False

        if submission.fftype == 'legacy':
            ffp = get_ff_pandas_legacy(submission.fieldfilepath,submission.device)
        elif submission.fftype == '2022':
            ffp = get_ff_pandas(submission.fieldfilepath,submission.device)
        else:
            ffp['ok'] = False

        if ffp.get('ok'):
            df = ffp.get('df')
            dimensions = ffp.get('dims')
            df = df[["Date (yyyy-mm-dd)","Monitoring site ID","Sub-site ID",
                     "Monitoring point ID","Start time","Start ppm","End time",
                     "End ppm","Chamber start T, C","Chamber end T, C",
                     "Chamber volume, dm3","Chamber area, dm2","Chamber ID"]]
            df = df.rename(columns={"Date (yyyy-mm-dd)":"date",
                                    "Monitoring site ID":"siteid",
                                    "Sub-site ID":"subsiteid",
                                    "Monitoring point ID":"point",
                                    "Start time":"start_time",
                                    "End time":"end_time",
                                    "Start ppm":"start_ppm",
                                    "End ppm":"end_ppm",
                                    "Chamber start T, C":"start_temp",
                                    "Chamber end T, C":"end_temp",
                                    "Chamber volume, dm3":"chamber_vol",
                                    "Chamber area, dm2":"chamber_area",
                                    "Chamber ID":"chamber_id"})

            if ((ffp.get('ok') or False) &
                (ffp.get('startend_ok') or False) &
                (ffp.get('datetime_ok') or False) &
                (ffp.get('durations_ok') or False) &
                (ffp.get('siteid_ok') or False) &
                (ffp.get('subsiteid_ok') or False) &
                (ffp.get('numerics_ok') or False) &
                (ffp.get('volume_ok') or False) &
                (ffp.get('area_ok') or False)):
                validity = True
                ##print('checks as valid')
            else:
                ## todo: signal an error
                pass
                ##print('checks as not valid')

            details = df.to_dict('records')

    ## we have checked validity above so switch state if necessary
    if validity:
        if submission.fieldstatus != 'valid':
            Measurements.objects.filter(id=fsid).update(fieldstatus = 'valid')
    else:
        if submission.fieldstatus != 'invalid':
            Measurements.objects.filter(id=fsid).update(fieldstatus = 'invalid')

    form = ChangeRecordForm()
    return render(request, 'submit/meas/fdetail.html',
                  {'form':       form,
                   'submission': submission,
                   'ff_ok':            ffp.get('ok'),
                   'ff_startend_ok':   ffp.get('startend_ok'),
                   'ff_datetime_ok':   ffp.get('datetime_ok'),
                   'ff_durations_ok':  ffp.get('durations_ok'),
                   'ff_siteids_ok':    ffp.get('siteid_ok'),
                   'ff_subsiteids_ok': ffp.get('subsiteid_ok'),
                   'ff_numerics_ok':   ffp.get('numerics_ok'),
                   'ff_volume_ok':     ffp.get('volume_ok'),
                   'ff_area_ok':       ffp.get('area_ok'),
                   'validity': validity,
                   'dims':     dimensions,
                   'details':  details})

## this view shows the details from a data file
@login_required
def datadetail(request, fsid):
    submission = Measurements.objects.filter(id=fsid).first()
    check_read = None
    dimensions = None
    gases_present = None
    validity = False
    ff_ok = None
    start_times = []
    nrows = []
    if submission.device == 'licor':
        dfp = read_df_licor(submission.datafilepath,True)
        gases_present = dfp.get('present')
    elif submission.device == 'licorsmart':
        dfp = read_df_licor_smart(submission.datafilepath,True)
    elif submission.device == 'gasmet':
        dfp = read_df_gasmet(submission.datafilepath,True)
    elif submission.device == 'egm5':
        dfp = read_df_egm5(submission.datafilepath,True)
    elif submission.device == 'egm4':
        dfp = read_df_egm4(submission.datafilepath,True)
    else:
        dfp['msg'] = 'submission.device: ' + submission.device + ', not currently supported'
    if (dfp.get('ok') or False):
        check_read = True
        validity = True
        dimensions = dfp.get('dims')
        ddf = dfp.get('df')
        if submission.fftype == 'legacy':
            fdf_out = get_ff_pandas_legacy(submission.fieldfilepath,submission.device)
        elif submission.fftype == '2022':
            fdf_out = get_ff_pandas(submission.fieldfilepath,submission.device)
        else:
            fdf_out = {'ok': False}
        if (fdf_out.get('ok') or False):
            ff_ok = True
            fdf = fdf_out.get('df')
            len_series = len(fdf["Date (yyyy-mm-dd)"].to_list())
            for i in range(len_series):
                start_time = fdf.iloc[i, fdf.columns.get_loc('Start time')]
                end_time   = fdf.iloc[i, fdf.columns.get_loc('End time')]
                meas_date  = fdf.iloc[i, fdf.columns.get_loc('Date (yyyy-mm-dd)')]
                ## todo: check new devices for this
                if submission.device == 'licor':
                    part = ddf[(ddf['DATE'] == meas_date) &
                               (ddf['TIME'] > start_time) &
                               (ddf['TIME'] < end_time)]
                else:
                    part = ddf[(ddf['Date'] == meas_date) &
                               (ddf['Time'] >= start_time) &
                               (ddf['Time'] <= end_time)]
                part_shape = part.shape
                start_times.append(str(start_time))
                nrows.append(str(part_shape[0]))
        else:
            ff_ok = False
    else:
        check_read = False
        messages.info(request,'Read fails with message: ' + str(dfp.get('msg')))

    ## we have checked validity above, change state if necessary
    if validity:
        if submission.datastatus != 'valid':
            Measurements.objects.filter(id=fsid).update(datastatus = 'valid')
    else:
        if submission.datastatus != 'invalid':
            Measurements.objects.filter(id=fsid).update(datastatus = 'invalid')

    return render(request, 'submit/meas/ddetail.html',
                  {'submission': submission,
                   'df_h_ok': check_read,
                   'df_dimensions': dimensions,
                   'gases': gases_present,
                   'validity': validity,
                   'dims': dimensions,
                   'ff_ok': ff_ok,
                   'start_times': start_times,
                   'nrows': nrows})

def sendformfile(response, fsid):
    submission = Measurements.objects.filter(id=fsid).first()
    origname = submission.fieldorigname
    cdisp = 'inline; filename="' + origname + '"'
    resp = FileResponse(open(submission.fieldfilepath,'rb'))
    resp['Content-Disposition'] = cdisp
    return resp

def senddatafile(response, fsid):
    submission = Measurements.objects.filter(id=fsid).first()
    origname = submission.fieldorigname
    cdisp = 'inline; filename="' + origname + '"'
    resp = FileResponse(open(submission.datafilepath,'rb'))
    resp['Content-Disposition'] = cdisp
    return resp

## detail ajax views

## todo: this route should be POST and require login
## todo: should be possible only by the uploader or project manager or admin
def statuschange(request):
    #uname = request.GET.get('uname')
    #uobj = User.objects.filter(username=uname).first()
    fsid = request.GET.get('fsid')
    submission = Measurements.objects.filter(id=fsid).first()
    old_status = submission.status
    out = {'ok': 'true'}
    if old_status == 'submitted':
        Measurements.objects.filter(id=fsid).update(status = 'retracted')
    elif old_status == 'retracted':
        Measurements.objects.filter(id=fsid).update(status = 'submitted')
    else:
        logger.info('statuschange: invalid status')
        out['ok'] = 'false'
    return JsonResponse(out)

def dataget(request):
    #uname = request.GET.get('uname')
    #uobj = User.objects.filter(username=uname).first()
    fsid = request.GET.get('fsid')
    submission = Measurements.objects.filter(id=fsid).first()
    out = {'ok': 'false'}
    if submission.device == 'egm5': ## todo: these could be more concise
        out['device'] = 'egm5'
        dfp = read_df_egm5(submission.datafilepath,True)
        if (dfp.get('ok') or False):
            df = dfp.get('df')
            dimensions = dfp.get('dims')
            out['ok'] = 'true'
            out['skiprows'] = dfp.get('skiprows')
            time = []
            co2 = []
            for i in range(dimensions[0]):
                if i in dfp['skiprows']:
                    continue
                else:
                    time.append(df.iloc[i,df.columns.get_loc('Time')])
                    co2.append(int(df.iloc[i,df.columns.get_loc('CO2')]))
                    out['time'] = time
                    out['co2'] = co2
    elif submission.device == 'egm4':
        out['device'] = 'egm4'
        dfp = read_df_egm4(submission.datafilepath,True)
        if (dfp.get('ok') or False):
            df = dfp.get('df')
            dimensions = dfp.get('dims')
            out['ok'] = 'true'
            out['skiprows'] = dfp.get('skiprows')
            index = []
            co2 = []
            for i in range(dimensions[0]):
                if i in dfp['skiprows']:
                    continue
                else:
                    index.append(i)
                    co2.append(int(df.iloc[i,df.columns.get_loc('CO2')]))
                    out['time'] = index
                    out['co2'] = co2
    elif submission.device == 'licor':
        out['device'] = 'licor'
        dfp = read_df_licor(submission.datafilepath,True)
        if dfp['ok']:
            df = dfp['df']
            out['ok'] = 'true'
            out['time'] = df["TIME"].to_list()
            out['co2'] = df["CO2"].to_list()
    elif submission.device == 'licorsmart':
        out['device'] = 'licorsmart'
        dfp = read_df_licor_smart(submission.datafilepath,True)
        if dfp['ok']:
            df = dfp['df']
            out['ok'] = 'true'
            out['time'] = df['Time'].to_list()
            out['co2'] = df['CO2'].to_list()
    elif submission.device == 'gasmet':
        out['device'] = 'gasmet'
        dfp = read_df_gasmet(submission.datafilepath,True)
        if dfp['ok']:
            df = dfp['df']
            out['ok'] = 'true'
            out['time'] = df['Time'].to_list()
            out['co2'] = df['Carbon dioxide CO2'].to_list()
    else:
        out['msg'] = 'device not supported'
    return JsonResponse(out)

## API access routes used for data transfer to dataserver

## this is called by the 'update' in dataserver to
## populate the Available table
@api_view(['GET'])
#@permission_classes((IsAuthenticated, ))
#@authentication_classes((JSONWebTokenAuthentication,))
def get_submissions(request):
    submissions = Measurements.objects.all()
    data = {'num': len(submissions)} ## todo: remove
    data['data'] = [{'id':            s.id,
                     'date':          s.date,
                     'measure_date':  s.measure_date,
                     'status':        s.status,
                     'device':        s.device,
                     'soil':          s.soil,
                     'chamber':       s.chamber,
                     'fieldfilename': s.fieldorigname,
                     'datafilename':  s.dataorigname,
                     'datastatus':    s.datastatus,
                     'fieldstatus':   s.fieldstatus,
                     'comment':       s.comment}
                    for s in submissions]
    return JsonResponse(data)

## this is used by the data server
@api_view(['GET'])
#@permission_classes((IsAuthenticated, ))
#@authentication_classes((JSONWebTokenAuthentication,))
def get_submission(request, mid):
    data = {}
    s = Measurements.objects.filter(id=mid).first()
    if s is not None:
        data['ok'] = True
        data['data'] = {
            'id':            s.id,
            'project':       s.project.name,
            'date':          s.date,
            'measure_date':  s.measure_date,
            'status':        s.status,
            'device':        s.device,
            'soil':          s.soil,
            'chamber':       s.chamber,
            'fieldfilename': s.fieldorigname,
            'datafilename':  s.dataorigname,
            'datastatus':    s.datastatus,
            'fieldstatus':   s.fieldstatus,
            'comment':       s.comment
        }
    else:
        logger.info('get_submission: no submission with id ' + str(mid))
        data['ok'] = False
        data['msg'] = "No submission with id " + str(mid)
    return JsonResponse(data)

## this is used by the data server
@api_view(['GET'])
#@permission_classes((IsAuthenticated, ))
#@authentication_classes((JSONWebTokenAuthentication,))
def get_field_data_id(request, mid):
    data = {}
    s = Measurements.objects.filter(id=mid).first()
    if not s:
        logger.info('get_field_data_id: no series with id ' + str(mid))
        data['msg'] = 'no series with id ' + str(mid)
        data['ok'] = False
        return JsonResponse(data)

    if s.fftype == 'legacy':
        ffp = get_ff_pandas_legacy(s.fieldfilepath,s.device)
    elif s.fftype == '2022':
        ffp = get_ff_pandas(s.fieldfilepath,s.device)
    else:
        ffp['ok'] = False

    if ffp['ok']:
        df0 = ffp.get('df')
        df = df0.filter(["Date (yyyy-mm-dd)","Monitoring site ID","Sub-site ID",
                         "Monitoring point ID","Monitoring point type","Site description",
                         "Start time","Start ppm","End time","End ppm",
                         "Chamber start T, C","Chamber end T, C",
                         "T at 05, C","T at 10, C","T at 15, C",
                         "T at 20, C","T at 30, C","T at 40, C",
                         "SM , m3/m3",
                         "Soil moisture at topsoil","Chamber setting",
                         "Chamber volume, dm3","Chamber area, dm2","WT real, cm",
                         "Notes_1","Notes_2","Notes_3",
                         "Use of fabric on the monitoring point",
                         "Weather","Wind","chamber_area"])
        df.rename(columns={"Date (yyyy-mm-dd)":"date",
                           "Monitoring site ID":"siteid",
                           "Sub-site ID":"subsiteid",
                           "Monitoring point ID":"point",
                           "Monitoring point type":"pointtype",
                           "Site description":"sitedesc",
                           "Start time":"start_time",
                           "End time":"end_time",
                           "Start ppm":"start_ppm",
                           "End ppm":"end_ppm",
                           "Chamber start T, C":"start_temp",
                           "Chamber end T, C":"end_temp",
                           "T at 05, C":"t05",
                           "T at 10, C":"t10",
                           "T at 15, C":"t15",
                           "T at 20, C":"t20",
                           "T at 30, C":"t30",
                           "T at 40, C":"t40",
                           "SM , m3/m3":"sm",
                           "Soil moisture at topsoil":"tsmoisture",
                           "Chamber setting":"chambersetting",
                           "Chamber volume, dm3":"chamber_vol",
                           "Chamber area, dm2":"chamber_area",
                           "WT real, cm":"wt",
                           "Notes_1":"notes1",
                           "Notes_2":"notes2",
                           "Notes_3":"notes3",
                           "Use of fabric on the monitoring point":"fabric",
                           "Weather":"weather",
                           "Wind":"wind"},inplace=True)
        df["point"] = df["point"].astype(str)
        res = df.to_dict('records')
        data['data'] = res
        data['ok'] = 'true'
    else:
        data['msg'] = 'pandas field form reading failed'
        data['ok'] = 'false'
    return JsonResponse(data)

## this is used by the data server
@api_view(['GET'])
#@permission_classes((IsAuthenticated, ))
#@authentication_classes((JSONWebTokenAuthentication,))
def get_data_series(request, mid, series_num):
    out = {'ok': 'false', 'data': {}}
    s = Measurements.objects.filter(id=mid).first()

    if s.fftype == 'legacy':
        ffp = get_ff_pandas_legacy(s.fieldfilepath,s.device)
    elif s.fftype == '2022':
        ffp = get_ff_pandas(s.fieldfilepath,s.device)
    else:
        ffp['ok'] = False

    if ffp['ok']:
        fdf = ffp['df']
        datasize = len(fdf["Date (yyyy-mm-dd)"].to_list()) ## why not fdf.shape[0] ?
        if series_num >= datasize:
            out['msg'] = 'series index out of upper bound'
            return JsonResponse(out)
        elif series_num < 0:
            out['msg'] = 'series index out of lower bound'
            return JsonResponse(out)
        start_time = fdf.iloc[series_num, fdf.columns.get_loc('Start time')]
        end_time   = fdf.iloc[series_num, fdf.columns.get_loc('End time')]
        meas_date  = fdf.iloc[series_num, fdf.columns.get_loc('Date (yyyy-mm-dd)')]
        out['start_time'] = start_time
        out['end_time'] = end_time
        out['date'] = meas_date
        if s.device == 'egm5':
            ## todo: use meas_date
            dfp = read_df_egm5(s.datafilepath,True)
            out['device'] = 'egm5'
            if dfp['ok']:
                ddf = dfp['df']
                part = ddf[(ddf['Date'] == meas_date.date()) &
                           (ddf['Time'] > start_time) &
                           (ddf['Time'] < end_time)]
                out['data']['time'] = part["Time"].to_list()
                out['data']['co2']  = part["CO2"].to_list()
                out['ok'] = 'true'
            else:
                out['msg'] = dfp.get('msg')
        elif s.device == 'egm4':
            dfp = read_df_egm4(s.datafilepath,True)
            out['device'] = 'egm4'
            if dfp['ok']:
                ddf = dfp['df']
                nr = dfp['num_records']
                counts = [ddf[(ddf['rec_index'] == i) &
                              (ddf['Date'] == meas_date.date()) &
                              (ddf['Time'] >= start_time) &
                              (ddf['Time'] <= end_time)].shape[0]
                          for i in range(nr)]
                idx = counts.index(max(counts))
                part = ddf[(ddf['rec_index'] == idx)]
                out['data']['recno'] = part['RecNo'].to_list()
                out['data']['time']  = part['Time'].to_list()
                out['data']['co2']   = part['CO2'].to_list()
                out['ok'] = True
            else:
                out['msg'] = dfp.get('msg')
        elif s.device == 'licor':
            dfp = read_df_licor(s.datafilepath,True)
            out['device'] = 'licor'
            if dfp['ok']:
                ddf = dfp['df']
                gases = dfp.get('present')
                part = ddf[(ddf['DATE'] == meas_date.date()) &
                           (ddf['TIME'] > start_time) &
                           (ddf['TIME'] < end_time)]
                out['data']['time'] = part["TIME"].to_list()
                if 'CO2' in gases:
                    out['data']['co2'] = part["CO2"].to_list()
                if 'CH4' in gases:
                    out['data']['ch4'] = part["CH4"].to_list()
                if 'N2O' in gases:
                    out['data']['n2o'] = part["N2O"].to_list()
                out['ok'] = 'true'
            else:
                out['msg'] = dfp.get('msg')
        elif s.device == 'licorsmart': # works like egm5, check
            dfp = read_df_licor_smart(s.datafilepath,True)
            out['device'] = 'licorsmart'
            if dfp['ok']:
                ddf = dfp['df']
                part = ddf[(ddf['Date'] == meas_date.date()) &
                           (ddf['Time'] > start_time) &
                           (ddf['Time'] < end_time)]
                out['data']['time'] = part["Time"].to_list()
                out['data']['co2'] = part["CO2"].to_list()
                out['ok'] = 'true'
            else:
                out['msg'] = dfp.get('msg')
        elif s.device == 'gasmet':
            dfp = read_df_gasmet(s.datafilepath,True)
            out['device'] = 'gasmet'
            if dfp.get('ok'):
                ddf = dfp['df']
                part = ddf[(ddf['Date'] == meas_date.date()) &
                           (ddf['Time'] > start_time) &
                           (ddf['Time'] < end_time)]
                out['data']['time'] = part['Time'].to_list()
                out['data']['co2']  = part['Carbon dioxide CO2'].to_list()
                if 'Methane CH4' in part.columns:
                    ch4_list = part['Methane CH4'].to_list()
                    out['data']['ch4'] = [ch4_list[i]*1000.0 for i in range(len(ch4_list))]
                if 'Nitrous oxide N2O' in part.columns:
                    n2o_list = part['Nitrous oxide N2O'].to_list()
                    out['data']['n2o'] = [n2o_list[i]*1000.0 for i in range(len(n2o_list))]
                out['ok'] = 'true'
            else:
                out['msg'] = dfp.get('msg')
        else:
            out['msg'] = 'get_data_series: device not supported'
            logger.info('get_data_series: device not supported')
    return JsonResponse(out)
