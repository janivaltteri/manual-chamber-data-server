import os
import numpy
import pandas
import datetime
import requests

from flask import (
    flash,
    jsonify,
    make_response,
    render_template,
    redirect,
    request,
    Response,
    send_from_directory,
    url_for,
)

from config import fileserver_url

from application import server, db
from application.models import User, Available, Measurements, Series, Flux, Datum
from application.forms import Loginform

from application.with_authenticate import fetch_url
from application.dbhandler import *
from application.fluxcalc import *

from flask_login import login_required, current_user, login_user, logout_user

@server.route('/js/<path:path>')
def js(path):
    return send_from_directory('js',path)

@server.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    form = Loginform()
    if form.validate_on_submit():
        user = User.query.filter_by(username=form.username.data).first()
        if user is None or not user.check_password(form.password.data):
            flash('Invalid username or password')
            return redirect(url_for('login'))
        login_user(user, remember=form.remember_me.data)
        return redirect(url_for('index'))
    return render_template('login.html', title='Sign In', form=form)

@server.route('/logout')
def logout():
    logout_user()
    return redirect(url_for('login'))

@server.route('/')
@server.route('/index',methods=['GET'])
@login_required
def index():
    meas = Measurements.query.order_by(Measurements.siteids,
                                       Measurements.measure_date).all()
    projectnames = list(set([m.project for m in meas if m.project]))
    return render_template('index.html', meas=meas, pnames=projectnames)

@server.route('/projectdata/<pname>',methods=['GET'])
def sitedata(pname):
    if pname == 'none':
        m = Measurements.query.filter_by(project=None).order_by(Measurements.siteids,Measurements.measure_date).all()
    else:
        m = Measurements.query.filter_by(project=pname).order_by(Measurements.siteids,Measurements.measure_date).all()
    return render_template('projectdata.html', meas=m, pname=pname)

@server.route('/maintenance',methods=['GET'])
@login_required
def maintenance():
    avail = Available.query.order_by(Available.measure_date).all()
    meas = Measurements.query.order_by(Measurements.siteids,
                                       Measurements.measure_date).all()
    seri = Series.query.filter_by(empty=False).order_by(Series.siteid,
                                                        Series.date,Series.start_time).all()
    return render_template('maintenance.html', sub_data=avail, meas=meas, seri=seri)

@server.route('/measurements',methods=['GET'])
@login_required
def measurements():
    avail = Available.query.order_by(Available.measure_date).all()
    return render_template('measurements.html', sub_data=avail)

@server.route('/downloads',methods=['GET'])
@login_required
def downloads():
    seri = Series.query.filter_by(empty=False).order_by(Series.siteid,Series.date,
                                                        Series.start_time).all()
    siteids_all = [s.siteid for s in seri]
    siteids = list(set(siteids_all))
    data = [{'siteid': s,
             'count': siteids_all.count(s)}
            for s in siteids]
    return render_template('downloads.html', data=data)

## route for fetching a dataframe from the database
@server.route('/api/dataframe/<siteid>')
def dataframe(siteid):
    q0 = Series.query.filter_by(siteid=siteid,empty=False).statement
    df = pandas.read_sql_query(q0,db.session.get_bind())
    cdisp = "attachment; filename=export_" + siteid + ".csv"
    ## find associated flux values
    autouser = User.query.filter_by(username="tester").first()
    userid = current_user.get_id()
    ids = df["id"].tolist()
    values = []
    for i in range(len(ids)):
        val = {}
        afco2 = Flux.query.filter_by(series=ids[i],gas=1,trimmer=autouser.id).first()
        afch4 = Flux.query.filter_by(series=ids[i],gas=2,trimmer=autouser.id).first()
        afn2o = Flux.query.filter_by(series=ids[i],gas=3,trimmer=autouser.id).first()
        pfco2 = Flux.query.filter_by(series=ids[i],gas=1,trimmer=userid).first()
        pfch4 = Flux.query.filter_by(series=ids[i],gas=2,trimmer=userid).first()
        pfn2o = Flux.query.filter_by(series=ids[i],gas=3,trimmer=userid).first()
        val["aflux_co2"] = afco2.flux if afco2 else numpy.nan
        val["aflux_ch4"] = afch4.flux if afch4 else numpy.nan
        val["aflux_n2o"] = afn2o.flux if afn2o else numpy.nan
        val["aresid_co2"] = afco2.resid if afco2 else numpy.nan
        val["aresid_ch4"] = afch4.resid if afch4 else numpy.nan
        val["aresid_n2o"] = afn2o.resid if afn2o else numpy.nan
        val["abad_co2"] = afco2.bad if afco2 else numpy.nan
        val["abad_ch4"] = afch4.bad if afch4 else numpy.nan
        val["abad_n2o"] = afn2o.bad if afn2o else numpy.nan
        val["pflux_co2"] = pfco2.flux if pfco2 else numpy.nan
        val["pflux_ch4"] = pfch4.flux if pfch4 else numpy.nan
        val["pflux_n2o"] = pfn2o.flux if pfn2o else numpy.nan
        val["presid_co2"] = pfco2.resid if pfco2 else numpy.nan
        val["presid_ch4"] = pfch4.resid if pfch4 else numpy.nan
        val["presid_n2o"] = pfn2o.resid if pfn2o else numpy.nan
        val["pbad_co2"] = pfco2.bad if pfco2 else numpy.nan
        val["pbad_ch4"] = pfch4.bad if pfch4 else numpy.nan
        val["pbad_n2o"] = pfn2o.bad if pfn2o else numpy.nan
        values.append(val)
    df["co2_a_flux"] = [v["aflux_co2"] for v in values]
    df["ch4_a_flux"] = [v["aflux_ch4"] for v in values]
    df["n2o_a_flux"] = [v["aflux_n2o"] for v in values]
    df["co2_a_resid"] = [v["aresid_co2"] for v in values]
    df["ch4_a_resid"] = [v["aresid_ch4"] for v in values]
    df["n2o_a_resid"] = [v["aresid_n2o"] for v in values]
    df["co2_a_bad"] = [v["abad_co2"] for v in values]
    df["ch4_a_bad"] = [v["abad_ch4"] for v in values]
    df["n2o_a_bad"] = [v["abad_n2o"] for v in values]
    df["co2_p_flux"] = [v["pflux_co2"] for v in values]
    df["ch4_p_flux"] = [v["pflux_ch4"] for v in values]
    df["n2o_p_flux"] = [v["pflux_n2o"] for v in values]
    df["co2_p_resid"] = [v["presid_co2"] for v in values]
    df["ch4_p_resid"] = [v["presid_ch4"] for v in values]
    df["n2o_p_resid"] = [v["presid_n2o"] for v in values]
    df["co2_p_bad"] = [v["pbad_co2"] for v in values]
    df["ch4_p_bad"] = [v["pbad_ch4"] for v in values]
    df["n2o_p_bad"] = [v["pbad_n2o"] for v in values]
    return Response(df.to_csv(), mimetype="text/csv", headers={"Content-disposition": cdisp})

## routes for fetching data from the fileserver

## fetches all available datasets on the file server and writes
## their details to 'Available' table of database
## this route is called from maintenance view in browser
## note: this should not be used, shell_update should do this
@server.route('/api/update')
def update():
    target = fileserver_url + '/submit/submissions/'
    rdata = fetch_url(target)
    if rdata is not None:
        for i in range(len(rdata)):
            new_available(rdata[i])
    return redirect("/maintenance")

## fetch a measurement set from fileserver
## this is intended to be called from maintenance view via browser
## note: this should not be used, shell_fetch should do this
@server.route('/api/fetch/<id>')
def fetch(id):
    meas = Measurements.query.filter_by(fileserver_id=id).all()
    if len(meas) > 1:
        flash("error: multiple Measurements with this id " + id)
        return redirect("/index")
    elif len(meas) == 1:
        flash("Mesurement set " + id + " already present")
        return redirect("/index")
    target = fileserver_url + '/submit/submission/' + id + '/'
    meas_data = fetch_url(target)
    if meas_data is None:
        flash("Error: received no measurements data")
        return redirect("/index")
    new_meas = new_measurements(meas_data) ## adds to db session
    if not new_meas.get('ok'):
        flash("Error: could not insert Measurements to database")
        return redirect("/index")
    new_meas_id = new_meas.get('local_id')
    assoc_series = Series.query.filter_by(measurements=new_meas_id).all()
    if len(assoc_series) > 0:
        flash("Error: fetched measurement " + new_meas_id +
              " already associated with " + str(len(assoc_series)) + " series")
    else:
        ## got Meas, now fetch series
        flash("fetched Measurement set")
        target = fileserver_url + '/submit/field/' + id + '/'
        series_data = fetch_url(target)
        if not series_data:
            flash("Error: received no series data")
            return redirect("/index")
        new_s = new_series(series_data,new_meas_id) ## adds to db session
        ## set siteids for the Measurements set
        new_meas['meas'].siteids = " ".join(new_s['siteids'])
        ## got series, now fetch datapoints
        for i in range(len(new_s['ids'])):
            target = fileserver_url + '/submit/dataseries/' + id + '/' + str(i) + '/'
            point_data = fetch_url(target)
            if point_data is None:
                flash("Error: received no point data")
                return redirect("/index")
            new_d = new_data(point_data,new_s['ids'][i]) ## adds to db session
            if new_d['empty']:
                new_s['objs'][i].empty = True
            else:
                new_s['objs'][i].empty = False
                if 'co2' in new_d['gases']:
                    new_s['objs'][i].co2 = True
                if 'ch4' in new_d['gases']:
                    new_s['objs'][i].ch4 = True
                if 'n2o' in new_d['gases']:
                    new_s['objs'][i].n2o = True
    avail = Available.query.filter_by(fileserver_id=id).first()
    avail.fetched = True
    new_meas['meas'].successful = True
    db.session.commit() ## this should be the only commit
    return redirect("/maintenance")

@login_required
@server.route('/dataview/<local_id>')
def dataview(local_id):
    autouser = User.query.filter_by(username="tester").first()
    userid = current_user.get_id()
    #print("my_user " + str(userid))
    series = Series.query.filter_by(measurements=local_id, empty=False).all()
    s_fields = ('id','date','siteid','subsiteid','point',
                'start_time','end_time','start_temp','end_temp',
                'chamber_vol','chamber_area',
                'co2','ch4','n2o')
    objs = [series[i].to_dict(only=s_fields) for i in range(len(series))]
    for i in range(len(series)):
        ## get actual measured values from Datum model
        gases = ['time']
        if series[i].co2:
            gases.append('co2_ppm')
        if series[i].ch4:
            gases.append('ch4_ppb')
        if series[i].n2o:
            gases.append('n2o_ppb')
        data = Datum.query.filter_by(series=series[i].id).all()
        ## todo: to_dict() omits seconds from time format
        dobjs = [data[j].to_dict(only=tuple(gases)) for j in range(len(data))]
        objs[i]['data'] = dobjs
        ## get autotrimmed flux values
        co2_af = Flux.query.filter_by(series=series[i].id,gas=1,trimmer=autouser.id).first()
        ch4_af = Flux.query.filter_by(series=series[i].id,gas=2,trimmer=autouser.id).first()
        n2o_af = Flux.query.filter_by(series=series[i].id,gas=3,trimmer=autouser.id).first()
        objs[i]['co2_af'] = co2_af.to_dict() if co2_af else 'none'
        objs[i]['ch4_af'] = ch4_af.to_dict() if ch4_af else 'none'
        objs[i]['n2o_af'] = n2o_af.to_dict() if n2o_af else 'none'
        ## get personal flux values
        co2_pf = Flux.query.filter_by(series=series[i].id,gas=1,trimmer=userid).first()
        ch4_pf = Flux.query.filter_by(series=series[i].id,gas=2,trimmer=userid).first()
        n2o_pf = Flux.query.filter_by(series=series[i].id,gas=3,trimmer=userid).first()
        objs[i]['co2_pf'] = co2_pf.to_dict() if co2_pf else 'none'
        objs[i]['ch4_pf'] = ch4_pf.to_dict() if ch4_pf else 'none'
        objs[i]['n2o_pf'] = n2o_pf.to_dict() if n2o_pf else 'none'
    return render_template('dataview.html', data = objs)

## autotrim a measument set
## this is intended to be called from maintenance view via browser
## note: this should not be used, shell_autotrim should do this
@login_required
@server.route('/autotrim/<local_id>')
def autotrim(local_id):
    autouser = User.query.filter_by(username="tester").first()
    series = Series.query.filter_by(measurements=local_id, empty=False).all()
    added = 0
    for i in range(len(series)):
        data = Datum.query.filter_by(series=series[i].id).all()
        if series[i].co2:
            ## there should be 0 or 1
            tflux = Flux.query.filter_by(series=series[i].id,gas=1,trimmer=autouser.id).all()
            if len(tflux) == 0:
                # print("series " + str(series[i].id) + " has 0 co2 fluxes, adding")
                fvs = co2_lin_flux(data,series[i].start_temp,series[i].end_temp,
                                   series[i].chamber_vol,series[i].chamber_area,
                                   30,0,series[i].date)
                new_co2_flux = Flux(series    = series[i].id,
                                    trimmer   = autouser.id,
                                    trim_head = 30,
                                    trim_tail = 0,
                                    gas       = 1,
                                    flux      = fvs.lin_flux,
                                    intercept = fvs.intercept,
                                    slope     = fvs.slope,
                                    resid     = fvs.residual_mean)
                db.session.add(new_co2_flux)
                db.session.commit()
                added += 1
            elif len(tflux) == 1:
                # print("series " + str(series[i].id) + " has 1 co2 flux")
                pass
            else:
                ## todo: log error
                # print("series " + str(series[i].id) + " has multiple co2 fluxes")
                pass
        if series[i].ch4:
            ## there should be 0 or 1
            tflux = Flux.query.filter_by(series=series[i].id,gas=2,trimmer=autouser.id).all()
            if len(tflux) == 0:
                # print("series " + str(series[i].id) + " has 0 ch4 fluxes, adding")
                fvs = ch4_lin_flux(data,series[i].start_temp,series[i].end_temp,
                                   series[i].chamber_vol,series[i].chamber_area,
                                   30,0,series[i].date)
                new_ch4_flux = Flux(series    = series[i].id,
                                    trimmer   = autouser.id,
                                    trim_head = 30,
                                    trim_tail = 0,
                                    gas       = 2,
                                    flux      = fvs.lin_flux,
                                    intercept = fvs.intercept,
                                    slope     = fvs.slope,
                                    resid     = fvs.residual_mean)
                db.session.add(new_ch4_flux)
                db.session.commit()
                added += 1
            elif len(tflux) == 1:
                # print("series " + str(series[i].id) + " has 1 ch4 flux")
                pass
            else:
                ## todo: flash error
                # print("series " + str(series[i].id) + " has multiple ch4 fluxes")
                pass
        if series[i].n2o:
            ## there should be 0 or 1
            tflux = Flux.query.filter_by(series=series[i].id,gas=3,trimmer=autouser.id).all()
            if len(tflux) == 0:
                # print("series " + str(series[i].id) + " has 0 n2o fluxes, adding")
                fvs = n2o_lin_flux(data,series[i].start_temp,series[i].end_temp,
                                   series[i].chamber_vol,series[i].chamber_area,
                                   30,0,series[i].date)
                new_n2o_flux = Flux(series    = series[i].id,
                                    trimmer   = autouser.id,
                                    trim_head = 30,
                                    trim_tail = 0,
                                    gas       = 3,
                                    flux      = fvs.lin_flux,
                                    intercept = fvs.intercept,
                                    slope     = fvs.slope,
                                    resid     = fvs.residual_mean)
                db.session.add(new_n2o_flux)
                db.session.commit()
                added += 1
            elif len(tflux) == 1:
                # print("series " + str(series[i].id) + " has 1 n2o flux")
                pass
            else:
                ## todo: flash error
                # print("series " + str(series[i].id) + " has multiple n2o fluxes")
                pass
    flash("autotrim local_id " + str(local_id) + " added " + str(added) + " fluxes")
    return redirect("/maintenance")

## forget and clean up a fetched measurement series
## this is intended to be called from maintenance view via browser
## note: this should not be used, the shell_cleanup should do what this did
@login_required
@server.route('/forget/<local_id>')
def forget(local_id):
    meas = Measurements.query.filter_by(id=local_id).all()
    if(len(meas) == 1):
        fsid = meas[0].fileserver_id
        server.logger.info("forget called for local id " + str(local_id) +
                           " fsid " + str(fsid))
        flash("forgetting Measurement set for local id " + str(local_id) +
              " fsid " + str(fsid))
        assoc_series = Series.query.filter_by(measurements=local_id).all()
        for i in range(len(assoc_series)):
            series = assoc_series[i]
            assoc_data = Datum.query.filter_by(series=series.id).all()
            for j in range(len(assoc_data)):
                datum = assoc_data[j]
                db.session.delete(datum)
            assoc_fluxes = Flux.query.filter_by(series=series.id).all()
            for j in range(len(assoc_fluxes)):
                flux = assoc_fluxes[j]
                db.session.delete(flux)
            db.session.delete(series)
        db.session.delete(meas[0])
        avail = Available.query.filter_by(fileserver_id=fsid).first()
        avail.fetched = False
        db.session.commit()
    elif(len(meas) == 0):
        server.logger.warning("forget: measurement set with local id " + str(local_id) +
                              " not found on database")
        flash("Measurement set " + str(local_id) + " not present")
    else:
        server.logger.warning("forget: local id " + str(local_id) +
                              " matches with multiple measurement sets on database")
        flash("error: multiple Measurements with this local id " + str(local_id))
    return redirect("/maintenance")

## routes for scheduled tasks

## not used
@server.route('/scheduled/update',methods=['POST'])
def scheduled_update():
    uname = request.json.get('username')
    upass = request.json.get('password')
    uobj = User.query.filter_by(username=uname).first()
    if uobj.check_password(upass):
        userid = uobj.id
        server.logger.info("update availables called by user " + str(userid))
        target = fileserver_url + '/submit/submissions/'
        rdata = fetch_url(target)
        if rdata is not None:
            for i in range(len(rdata)):
                new_available(rdata[i])
        return "updated availables", 200
    else:
        server.logger.warning("unauthorised call to update availables")
        return "unauthorised call to update availables", 200

## called from shell script
def shell_update():
    logfile = open("/opt/mcds/datalogs/updatelog.txt","a")
    logfile.write(str(datetime.datetime.now()) + " shell_update\n")
    target = fileserver_url + '/submit/submissions/'
    rdata = fetch_url(target)
    if rdata is not None:
        for i in range(len(rdata)):
            new_available(rdata[i])
    logfile.write("updated availables\n")
    logfile.close()
    return "updated availables"

## not used
@server.route('/scheduled/fetch', methods=['POST'])
def scheduled_fetch():
    uname = request.json.get('username')
    upass = request.json.get('password')
    uobj = User.query.filter_by(username=uname).first()
    if not uobj.check_password(upass):
        server.logger.warning("unauthorised call to fetch")
        return "unauthorised call to fetch", 200
    fetched_meas = 0
    fetched_series = 0
    skipped = 0
    avail = Available.query.all()
    for i in range(len(avail)):
        if avail[i].fetched:
            skipped += 1
        else:
            fsid = avail[i].fileserver_id
            ## associated Measurements should not exist
            meas = Measurements.query.filter_by(fileserver_id=fsid).all()
            if len(meas) > 0:
                server.logger.warning("tried to fetch available " + str(avail[i].id) +
                                      ", fsid " + str(fsid) +
                                      ", but " + str(len(meas)) +
                                      " measurements with this fsid already exists")
                ## avail[i].fetched = true ?
                continue
            target = fileserver_url + '/submit/submission/' + str(fsid) + '/'
            meas_data = fetch_url(target)
            if meas_data is None:
                server.logger.warning("tried to fetch available " + str(avail[i].id) +
                                      ", fsid " + str(fsid) +
                                      " received no measurements data")
                continue
            new_meas = new_measurements(meas_data) ## adds to db session
            if not new_meas.get('ok'):
                server.logger.warning("tried to fetch available " + str(avail[i].id) +
                                      ", fsid " + str(fsid) +
                                      " received measurements status not ok")
                continue            
            new_meas_id = new_meas.get('local_id')
            assoc_series = Series.query.filter_by(measurements=new_meas_id).all()
            if len(assoc_series) > 0:
                server.logger.warning("tried to fetch available " + str(avail[i].id) +
                                      ", fsid " + str(fsid) +
                                      " but measuments already associated with " +
                                      str(len(assoc_series)) + " series")
                continue
            ## got Meas, now fetch series
            target = fileserver_url + '/submit/field/' + str(fsid) + '/'
            series_data = fetch_url(target)
            if not series_data:
                server.logger.warning("tried to fetch available " + str(avail[i].id) +
                                      ", fsid " + str(fsid) +
                                      " but received no series data")
                continue
            new_s = new_series(series_data,new_meas_id) ## adds to db session
            ## set siteids for the Measurements set
            new_meas['meas'].siteids = " ".join(new_s['siteids'])
            fetched_meas += 1
            ## got series, now fetch datapoints
            for j in range(len(new_s['ids'])):
                target = fileserver_url + '/submit/dataseries/' + str(fsid) + '/' + str(j) + '/'
                point_data = fetch_url(target)
                if point_data is None:
                    server.logger.warning("fetching available " + str(avail[j].id) +
                                          ", fsid " + str(fsid) + ", series " + str(j) +
                                          " but received no point data")
                    continue
                new_d = new_data(point_data,new_s['ids'][j]) ## adds to db session
                if new_d['empty']:
                    new_s['objs'][j].empty = True
                else:
                    new_s['objs'][j].empty = False
                    ## todo: shorten
                    if 'co2' in new_d['gases']:
                        new_s['objs'][j].co2 = True
                    if 'ch4' in new_d['gases']:
                        new_s['objs'][j].ch4 = True
                    if 'n2o' in new_d['gases']:
                        new_s['objs'][j].n2o = True
                fetched_series += 1
            avail[i].fetched = True
            new_meas['meas'].successful = True
    db.session.commit() ## this should be the only commit
    server.logger.info("scheduled fetch received " + str(fetched_meas) +
                       " measurements, " + str(fetched_series) + " series, skipped " +
                       str(skipped) + " pre-existing measurements, called by user " +
                       str(uobj.username))
    return "successful scheduled fetch", 200

## called from shell script
def shell_fetch():
    logfile = open("/opt/mcds/datalogs/updatelog.txt","a")
    logfile.write(str(datetime.datetime.now()) + " shell_fetch\n")
    fetched_meas = 0
    fetched_series = 0
    skipped = 0
    avail = Available.query.all()
    for i in range(len(avail)):
        if avail[i].fetched:
            skipped += 1
        elif avail[i].status != 'submitted':
            skipped += 1
        elif avail[i].fieldstatus != 'valid':
            skipped += 1
        elif avail[i].datastatus != 'valid':
            skipped += 1
        else:
            fsid = avail[i].fileserver_id
            ## associated Measurements should not exist
            meas = Measurements.query.filter_by(fileserver_id=fsid).all()
            if len(meas) > 0:
                logfile.write("tried to fetch available " + str(avail[i].id) +
                              ", fsid " + str(fsid) + ", but " + str(len(meas)) +
                              " measurements with this fsid already exists\n")
                ## avail[i].fetched = true ?
                continue
            target = fileserver_url + '/submit/submission/' + str(fsid) + '/'
            meas_data = fetch_url(target)
            if meas_data is None:
                logfile.write("tried to fetch available " + str(avail[i].id) +
                              ", fsid " + str(fsid) + " received no measurements data\n")
                continue
            new_meas = new_measurements(meas_data) ## adds to db session
            if not new_meas.get('ok'):
                logfile.write("tried to fetch available " + str(avail[i].id) +
                              ", fsid " + str(fsid) + " received measurements status not ok\n")
                continue            
            new_meas_id = new_meas.get('local_id')
            assoc_series = Series.query.filter_by(measurements=new_meas_id).all()
            if len(assoc_series) > 0:
                logfile.write("tried to fetch available " + str(avail[i].id) +
                              ", fsid " + str(fsid) +
                              " but measuments already associated with " +
                              str(len(assoc_series)) + " series\n")
                continue
            ## got Meas, now fetch series
            target = fileserver_url + '/submit/field/' + str(fsid) + '/'
            series_data = fetch_url(target)
            if not series_data:
                logfile.write("tried to fetch available " + str(avail[i].id) +
                              ", fsid " + str(fsid) + " but received no series data\n")
                continue
            new_s = new_series(series_data,new_meas_id) ## adds to db session
            ## set siteids for the Measurements set
            new_meas['meas'].siteids = " ".join(new_s['siteids'])
            fetched_meas += 1
            ## got series, now fetch datapoints
            for j in range(len(new_s['ids'])):
                target = fileserver_url + '/submit/dataseries/' + str(fsid) + '/' + str(j) + '/'
                point_data = fetch_url(target)
                if point_data is None:
                    logfile.write("fetching available " + str(avail[j].id) +
                                  ", fsid " + str(fsid) + ", series " + str(j) +
                                  " but received no point data\n")
                    continue
                new_d = new_data(point_data,new_s['ids'][j]) ## adds to db session
                if new_d['empty']:
                    new_s['objs'][j].empty = True
                else:
                    new_s['objs'][j].empty = False
                    ## todo: shorten
                    if 'co2' in new_d['gases']:
                        new_s['objs'][j].co2 = True
                    if 'ch4' in new_d['gases']:
                        new_s['objs'][j].ch4 = True
                    if 'n2o' in new_d['gases']:
                        new_s['objs'][j].n2o = True
                fetched_series += 1
            avail[i].fetched = True
            new_meas['meas'].successful = True
    db.session.commit() ## this should be the only commit
    logfile.write("shell_fetch received " + str(fetched_meas) +
                  " measurements, " + str(fetched_series) + " series, skipped " +
                  str(skipped) + " pre-existing measurements\n")
    logfile.close()
    return "successful shell fetch"

## todo: clear autotrims route

## not used
@server.route('/scheduled/autotrim', methods=['POST'])
def scheduled_autotrim():
    uname = request.json.get('username')
    upass = request.json.get('password')
    uobj = User.query.filter_by(username=uname).first()
    if not uobj.check_password(upass):
        server.logger.warning("unauthorised call to fetch")
        return "unauthorised call to fetch", 200
    autouser = User.query.filter_by(username="tester").first()
    series = Series.query.filter_by(empty=False).all()
    added = 0
    skipped = 0
    for i in range(len(series)):
        if series[i].co2:
            tflux = Flux.query.filter_by(series=series[i].id,gas=1,trimmer=autouser.id).all()
            if len(tflux) == 0:
                data = Datum.query.filter_by(series=series[i].id).all()
                server.logger.info("scheduled_autotrim: series " + str(series[i].id) +
                                   " has 0 co2 fluxes, adding")
                fvs = co2_lin_flux(data,series[i].start_temp,series[i].end_temp,
                                   series[i].chamber_vol,series[i].chamber_area,
                                   30,0,series[i].date)
                new_co2_flux = Flux(series    = series[i].id,
                                    trimmer   = autouser.id,
                                    trim_head = 30,
                                    trim_tail = 0,
                                    gas       = 1,
                                    flux      = fvs.lin_flux,
                                    intercept = fvs.intercept,
                                    slope     = fvs.slope,
                                    resid     = fvs.residual_mean)
                db.session.add(new_co2_flux)
                db.session.commit()
                added += 1
            elif len(tflux) == 1:
                skipped += 1
            else:
                server.logger.info("scheduled_autotrim: series " + str(series[i].id) +
                                   " autouser has multiple co2 fluxes")
        if series[i].ch4:
            tflux = Flux.query.filter_by(series=series[i].id,gas=2,trimmer=autouser.id).all()
            if len(tflux) == 0:
                data = Datum.query.filter_by(series=series[i].id).all()
                server.logger.info("scheduled_autotrim: series " + str(series[i].id) +
                                   " has 0 ch4 fluxes, adding")
                fvs = ch4_lin_flux(data,series[i].start_temp,series[i].end_temp,
                                   series[i].chamber_vol,series[i].chamber_area,
                                   30,0,series[i].date)
                new_ch4_flux = Flux(series    = series[i].id,
                                    trimmer   = autouser.id,
                                    trim_head = 30,
                                    trim_tail = 0,
                                    gas       = 2,
                                    flux      = fvs.lin_flux,
                                    intercept = fvs.intercept,
                                    slope     = fvs.slope,
                                    resid     = fvs.residual_mean)
                db.session.add(new_ch4_flux)
                db.session.commit()
                added += 1
            elif len(tflux) == 1:
                skipped += 1
            else:
                server.logger.info("scheduled_autotrim: series " + str(series[i].id) +
                                   " autouser has multiple ch4 fluxes")
        if series[i].n2o:
            tflux = Flux.query.filter_by(series=series[i].id,gas=3,trimmer=autouser.id).all()
            if len(tflux) == 0:
                data = Datum.query.filter_by(series=series[i].id).all()
                server.logger.info("scheduled_autotrim: series " + str(series[i].id) +
                                   " has 0 n2o fluxes, adding")
                fvs = n2o_lin_flux(data,series[i].start_temp,series[i].end_temp,
                                   series[i].chamber_vol,series[i].chamber_area,
                                   30,0,series[i].date)
                new_n2o_flux = Flux(series    = series[i].id,
                                    trimmer   = autouser.id,
                                    trim_head = 30,
                                    trim_tail = 0,
                                    gas       = 3,
                                    flux      = fvs.lin_flux,
                                    intercept = fvs.intercept,
                                    slope     = fvs.slope,
                                    resid     = fvs.residual_mean)
                db.session.add(new_n2o_flux)
                db.session.commit()
                added += 1
            elif len(tflux) == 1:
                skipped += 1
            else:
                server.logger.info("scheduled_autotrim: series " + str(series[i].id) +
                                   " autouser has multiple n2o fluxes")
    server.logger.info("scheduled_autotrim added " + str(added) + " fluxes, skipped " +
                       str(skipped) + " pre-existing")
    return "successful scheduled autotrim", 200

## called from shell script
def shell_autotrim():
    logfile = open("/opt/mcds/datalogs/updatelog.txt","a")
    logfile.write(str(datetime.datetime.now()) + " shell_autotrim\n")
    autouser = User.query.filter_by(username="tester").first()
    series = Series.query.filter_by(empty=False).all()
    added = 0
    skipped = 0
    for i in range(len(series)):
        auto_trim_head = 30
        auto_trim_tail = 0
        meas_id = series[i].measurements
        meas = Measurements.query.filter_by(id=meas_id).first()
        if meas.device == 'egm4':
            auto_trim_head = 0
        if series[i].co2:
            tflux = Flux.query.filter_by(series=series[i].id,gas=1,trimmer=autouser.id).all()
            if len(tflux) == 0:
                data = Datum.query.filter_by(series=series[i].id).all()
                trimbad = len(data) < 60
                trimhead = 0 if trimbad else auto_trim_head
                trimtail = 0 if trimbad else auto_trim_tail
                try:
                    fvs = co2_lin_flux(data,series[i].start_temp,series[i].end_temp,
                                       series[i].chamber_vol,series[i].chamber_area,
                                       trimhead,trimtail,series[i].date)
                    new_co2_flux = Flux(series    = series[i].id,
                                        trimmer   = autouser.id,
                                        trim_head = trimhead,
                                        trim_tail = trimtail,
                                        gas       = 1,
                                        flux      = fvs.lin_flux,
                                        intercept = fvs.intercept,
                                        slope     = fvs.slope,
                                        resid     = fvs.residual_mean,
                                        bad       = trimbad)
                    db.session.add(new_co2_flux)
                    db.session.commit()
                    added += 1
                except:
                    logfile.write("shell_autotrim: series " + str(series[i].id) +
                                  " encountered an exception in co2 autotrim")
            elif len(tflux) == 1:
                skipped += 1
            else:
                logfile.write("shell_autotrim: series " + str(series[i].id) +
                              " autouser has multiple co2 fluxes")
        if series[i].ch4:
            tflux = Flux.query.filter_by(series=series[i].id,gas=2,trimmer=autouser.id).all()
            if len(tflux) == 0:
                data = Datum.query.filter_by(series=series[i].id).all()
                trimbad = len(data) < 60
                trimhead = 0 if trimbad else auto_trim_head
                trimtail = 0 if trimbad else auto_trim_tail
                try:
                    fvs = ch4_lin_flux(data,series[i].start_temp,series[i].end_temp,
                                       series[i].chamber_vol,series[i].chamber_area,
                                       trimhead,trimtail,series[i].date)
                    new_ch4_flux = Flux(series    = series[i].id,
                                        trimmer   = autouser.id,
                                        trim_head = trimhead,
                                        trim_tail = trimtail,
                                        gas       = 2,
                                        flux      = fvs.lin_flux,
                                        intercept = fvs.intercept,
                                        slope     = fvs.slope,
                                        resid     = fvs.residual_mean,
                                        bad       = trimbad)
                    db.session.add(new_ch4_flux)
                    db.session.commit()
                    added += 1
                except:
                    logfile.write("shell_autotrim: series " + str(series[i].id) +
                                  " encountered an exception in ch4 autotrim")
            elif len(tflux) == 1:
                skipped += 1
            else:
                logfile.write("shell_autotrim: series " + str(series[i].id) +
                              " autouser has multiple ch4 fluxes")
        if series[i].n2o:
            tflux = Flux.query.filter_by(series=series[i].id,gas=3,trimmer=autouser.id).all()
            if len(tflux) == 0:
                data = Datum.query.filter_by(series=series[i].id).all()
                trimbad = len(data) < 60
                trimhead = 0 if trimbad else auto_trim_head
                trimtail = 0 if trimbad else auto_trim_tail
                try:
                    fvs = n2o_lin_flux(data,series[i].start_temp,series[i].end_temp,
                                       series[i].chamber_vol,series[i].chamber_area,
                                       trimhead,trimtail,series[i].date)
                    new_n2o_flux = Flux(series    = series[i].id,
                                        trimmer   = autouser.id,
                                        trim_head = trimhead,
                                        trim_tail = trimtail,
                                        gas       = 3,
                                        flux      = fvs.lin_flux,
                                        intercept = fvs.intercept,
                                        slope     = fvs.slope,
                                        resid     = fvs.residual_mean,
                                        bad       = trimbad)
                    db.session.add(new_n2o_flux)
                    db.session.commit()
                    added += 1
                except:
                    logfile.write("shell_autotrim: series " + str(series[i].id) +
                                  " encountered an exception in n2o autotrim")
            elif len(tflux) == 1:
                skipped += 1
            else:
                logfile.write("shell_autotrim: series " + str(series[i].id) +
                              " autouser has multiple n2o fluxes")
    logfile.write("shell_autotrim added " + str(added) + " fluxes, skipped " +
                  str(skipped) + " pre-existing\n")
    logfile.close()
    return "successful shell autotrim"

## called from shell script
def shell_cleanup():
    logfile = open("/opt/mcds/datalogs/updatelog.txt","a")
    logfile.write(str(datetime.datetime.now()) + " shell_cleanup\n")
    meas = Measurements.query.all()
    cleaned_meas = 0
    cleaned_series = 0
    cleaned_data = 0
    cleaned_fluxes = 0
    for i in range(len(meas)):
        if not meas[i].fs_state:
            local_id = meas[i].id
            fsid = meas[i].fileserver_id
            assoc_series = Series.query.filter_by(measurements=local_id).all()
            for j in range(len(assoc_series)):
                series = assoc_series[j]
                assoc_data = Datum.query.filter_by(series=series.id).all()
                for k in range(len(assoc_data)):
                    datum = assoc_data[k]
                    db.session.delete(datum)
                    cleaned_data += 1
                assoc_fluxes = Flux.query.filter_by(series=series.id).all()
                for k in range(len(assoc_fluxes)):
                    flux = assoc_fluxes[k]
                    db.session.delete(flux)
                    cleaned_fluxes += 1
                db.session.delete(series)
                cleaned_series += 1
            db.session.delete(meas[i])
            avail = Available.query.filter_by(fileserver_id=fsid).first()
            avail.fetched = False
            db.session.commit()
            cleaned_meas += 1
    logfile.write("shell_cleanup removed " + str(cleaned_meas) + " measurement sets " +
                  str(cleaned_series) + " series " + str(cleaned_data) + " data " +
                  str(cleaned_fluxes) + " fluxes\n")
    logfile.close()
    return "successful shell cleanup"

## ajax routes called from dataview page

@login_required
@server.route('/ajax/personal',methods=['POST'])
def calculate_flux():
    out = {'ok': False}
    series_id   = request.json.get('series_id')
    gas_num     = request.json.get('gas')
    start_value = request.json.get('trim_start_value')
    end_value   = request.json.get('trim_end_value')
    bad_value   = request.json.get('bad_value')
    bad_set     = True if bad_value == 'bad' else False
    userid = current_user.get_id()
    series = Series.query.filter_by(id=series_id).first()
    data = Datum.query.filter_by(series=series_id).all()
    date = series.date
    ##print("id " + str(series_id) + " uid " + str(userid) + " start " +
    ##      str(start_value) + " end " + str(end_value) + " bad " + str(bad_value))
    if (gas_num == 1) & series.co2:
        fvs = co2_lin_flux(data,series.start_temp,series.end_temp,series.chamber_vol,
                           series.chamber_area,start_value,end_value,date)
    elif (gas_num == 2) & series.ch4:
        fvs = ch4_lin_flux(data,series.start_temp,series.end_temp,series.chamber_vol,
                           series.chamber_area,start_value,end_value,date)
    elif (gas_num == 3) & series.n2o:
        fvs = n2o_lin_flux(data,series.start_temp,series.end_temp,series.chamber_vol,
                           series.chamber_area,start_value,end_value,date)
    else:
        return jsonify(out)
    pf_q = Flux.query.filter_by(series=series_id,gas=gas_num,trimmer=userid)
    if pf_q.first():
        ##print("previous personal flux exists, updating")
        new_values = {'trim_head': start_value,
                      'trim_tail': end_value,
                      'flux':      fvs.lin_flux,
                      'intercept': fvs.intercept,
                      'slope':     fvs.slope,
                      'resid':     fvs.residual_mean,
                      'bad':       bad_set}
        updata = pf_q.update(new_values)
        db.session.commit()
    else:
        ## create new Flux
        ##print("previous personal flux does not exist")
        new_flux = Flux(series    = series_id,
                        trimmer   = userid,
                        trim_head = start_value,
                        trim_tail = end_value,
                        gas       = gas_num,
                        flux      = fvs.lin_flux,
                        intercept = fvs.intercept,
                        slope     = fvs.slope,
                        resid     = fvs.residual_mean,
                        bad       = bad_set)
        db.session.add(new_flux)
        db.session.commit()
    out['new_slope']     = fvs.slope
    out['new_intercept'] = fvs.intercept
    out['new_lin_flux']  = fvs.lin_flux
    out['new_rmean']     = fvs.residual_mean
    out['new_bad']       = bad_set
    out['ok'] = True
    return jsonify(out)

@login_required
@server.route('/ajax/clear',methods=['POST'])
def clear_personal():
    out       = {'ok': False}
    series_id = request.json.get('series_id')
    gas_num   = request.json.get('gas')
    userid    = current_user.get_id()
    pfs       = Flux.query.filter_by(series=series_id,gas=gas_num,trimmer=userid).all()
    if len(pfs) == 0:
        wstring    = "tried to clear personal flux which does not exist"
        out['msg'] = wstring
        server.logger.warning(wstring)
    elif len(pfs) == 1:
        db.session.delete(pfs[0])
        db.session.commit()
        out['ok'] = True
    else:
        wstring    = "tried to clear personal flux but multiple exist"
        out['msg'] = wstring
        server.logger.warning(wstring)
        for i in range(len(pfs)):
            db.session.delete(pfs[i])
            db.session.commit()
    return(jsonify(out))

## api routes for the R package

## get a list of available siteids from all Series
@login_required
@server.route('/api/get/siteids',methods=['GET'])
def get_siteids():
    siteids_query = Series.query.with_entities(Series.siteid).distinct()
    if siteids_query:
        siteids = [row.siteid for row in siteids_query.all()]
    else:
        siteids = {'msg': 'no siteids on server'}
    return jsonify(siteids)

## get all Series for a specific siteid
@login_required
@server.route('/api/get/series_by_siteid/<site_id>',methods=['GET'])
def get_series_siteid(site_id):
    autouser = User.query.filter_by(username="tester").first()
    userid = current_user.get_id()
    series = Series.query.filter_by(siteid=site_id).all()
    if series:
        out = []
        for s in series:
            if not s.empty:
                aco2f = Flux.query.filter_by(series=s.id,gas=1,trimmer=autouser.id).all()
                pco2f = Flux.query.filter_by(series=s.id,gas=1,trimmer=userid).all()
                ach4f = Flux.query.filter_by(series=s.id,gas=2,trimmer=autouser.id).all()
                pch4f = Flux.query.filter_by(series=s.id,gas=2,trimmer=userid).all()
                an2of = Flux.query.filter_by(series=s.id,gas=3,trimmer=autouser.id).all()
                pn2of = Flux.query.filter_by(series=s.id,gas=3,trimmer=userid).all()
                out.append({'id': s.id,
                            'date': s.date.strftime('%Y-%m-%d'),
                            'siteid': s.siteid, 'subsiteid': s.subsiteid, 'point': s.point,
                            'start_time': s.start_time.strftime('%H:%M:%S'),
                            'end_time': s.end_time.strftime('%H:%M:%S'),
                            'start_ppm': s.start_ppm,'end_ppm': s.end_ppm,
                            'start_temp': s.start_temp, 'end_temp': s.end_temp,
                            'chamber_vol': s.chamber_vol, 'chamber_area': s.chamber_area,
                            'wt': s.wt, 't05': s.t05, 't10': s.t10, 't15': s.t15,
                            't20': s.t20, 't30': s.t30, 't40': s.t40,
                            'co2': s.co2, 'ch4': s.ch4, 'n2o': s.n2o,
                            'notes1': s.notes1, 'notes2': s.notes2, 'notes3': s.notes3,
                            'co2_p_flux': pco2f[0].flux if len(pco2f) == 1 else 'NA',
                            'ch4_p_flux': pch4f[0].flux if len(pch4f) == 1 else 'NA',
                            'n2o_p_flux': pn2of[0].flux if len(pn2of) == 1 else 'NA',
                            'co2_a_flux': aco2f[0].flux if len(aco2f) == 1 else 'NA',
                            'ch4_a_flux': ach4f[0].flux if len(ach4f) == 1 else 'NA',
                            'n2o_a_flux': an2of[0].flux if len(an2of) == 1 else 'NA',
                            'co2_p_resid': pco2f[0].resid if len(pco2f) == 1 else 'NA',
                            'ch4_p_resid': pch4f[0].resid if len(pch4f) == 1 else 'NA',
                            'n2o_p_resid': pn2of[0].resid if len(pn2of) == 1 else 'NA',
                            'co2_a_resid': aco2f[0].resid if len(aco2f) == 1 else 'NA',
                            'ch4_a_resid': ach4f[0].resid if len(ach4f) == 1 else 'NA',
                            'n2o_a_resid': an2of[0].resid if len(an2of) == 1 else 'NA',
                            'co2_p_bad': pco2f[0].bad if len(pco2f) == 1 else 'NA',
                            'ch4_p_bad': pch4f[0].bad if len(pch4f) == 1 else 'NA',
                            'n2o_p_bad': pn2of[0].bad if len(pn2of) == 1 else 'NA',
                            'co2_a_bad': aco2f[0].bad if len(aco2f) == 1 else 'NA',
                            'ch4_a_bad': ach4f[0].bad if len(ach4f) == 1 else 'NA',
                            'n2o_a_bad': an2of[0].bad if len(an2of) == 1 else 'NA'})
    else:
        out = {'msg': 'no series with site id ' + site_id}
    return jsonify(out)

@server.route('/api/get/data_by_series_id/<series_id>',methods=['GET'])
@login_required
def get_data_series_id(series_id):
    out = {}
    autouser = User.query.filter_by(username="tester").first()
    userid = current_user.get_id()
    series = Series.query.filter_by(id=series_id).first()
    if series and not series.empty:
        aco2f = Flux.query.filter_by(series=series.id,gas=1,trimmer=autouser.id).first()
        pco2f = Flux.query.filter_by(series=series.id,gas=1,trimmer=userid).first()
        ach4f = Flux.query.filter_by(series=series.id,gas=2,trimmer=autouser.id).first()
        pch4f = Flux.query.filter_by(series=series.id,gas=2,trimmer=userid).first()
        an2of = Flux.query.filter_by(series=series.id,gas=3,trimmer=autouser.id).first()
        pn2of = Flux.query.filter_by(series=series.id,gas=3,trimmer=userid).first()
        data = Datum.query.filter_by(series=series_id).all()
        out['co2_a_trim_head'] = aco2f.trim_head if aco2f else 'NA'
        out['co2_a_trim_tail'] = aco2f.trim_tail if aco2f else 'NA'
        out['co2_a_slope']     = aco2f.slope     if aco2f else 'NA'
        out['co2_a_intercept'] = aco2f.intercept if aco2f else 'NA'
        out['co2_a_flux']      = aco2f.flux      if aco2f else 'NA'
        out['co2_a_bad']       = aco2f.bad       if aco2f else 'NA'
        out['co2_p_trim_head'] = pco2f.trim_head if pco2f else 'NA'
        out['co2_p_trim_tail'] = pco2f.trim_tail if pco2f else 'NA'
        out['co2_p_slope']     = pco2f.slope     if pco2f else 'NA'
        out['co2_p_intercept'] = pco2f.intercept if pco2f else 'NA'
        out['co2_p_flux']      = pco2f.flux      if pco2f else 'NA'
        out['co2_p_bad']       = pco2f.bad       if pco2f else 'NA'
        out['ch4_a_trim_head'] = ach4f.trim_head if ach4f else 'NA'
        out['ch4_a_trim_tail'] = ach4f.trim_tail if ach4f else 'NA'
        out['ch4_a_slope']     = ach4f.slope     if ach4f else 'NA'
        out['ch4_a_intercept'] = ach4f.intercept if ach4f else 'NA'
        out['ch4_a_flux']      = ach4f.flux      if ach4f else 'NA'
        out['ch4_a_bad']       = ach4f.bad       if ach4f else 'NA'
        out['ch4_p_trim_head'] = pch4f.trim_head if pch4f else 'NA'
        out['ch4_p_trim_tail'] = pch4f.trim_tail if pch4f else 'NA'
        out['ch4_p_slope']     = pch4f.slope     if pch4f else 'NA'
        out['ch4_p_intercept'] = pch4f.intercept if pch4f else 'NA'
        out['ch4_p_flux']      = pch4f.flux      if pch4f else 'NA'
        out['ch4_p_bad']       = pch4f.bad       if pch4f else 'NA'
        out['n2o_a_trim_head'] = an2of.trim_head if an2of else 'NA'
        out['n2o_a_trim_tail'] = an2of.trim_tail if an2of else 'NA'
        out['n2o_a_slope']     = an2of.slope     if an2of else 'NA'
        out['n2o_a_intercept'] = an2of.intercept if an2of else 'NA'
        out['n2o_a_flux']      = an2of.flux      if an2of else 'NA'
        out['n2o_a_bad']       = an2of.bad       if an2of else 'NA'
        out['n2o_p_trim_head'] = pn2of.trim_head if pn2of else 'NA'
        out['n2o_p_trim_tail'] = pn2of.trim_tail if pn2of else 'NA'
        out['n2o_p_slope']     = pn2of.slope     if pn2of else 'NA'
        out['n2o_p_intercept'] = pn2of.intercept if pn2of else 'NA'
        out['n2o_p_flux']      = pn2of.flux      if pn2of else 'NA'
        out['n2o_p_bad']       = pn2of.bad       if pn2of else 'NA'
        if data:
            out['time'] = [data[i].time.strftime('%H:%M:%S')
                           for i in range(len(data))]
            if series.co2:
                out['co2_ppm'] = [data[i].co2_ppm for i in range(len(data))]
            else:
                out['co2_ppm'] = []
            if series.ch4:
                out['ch4_ppb'] = [data[i].ch4_ppb for i in range(len(data))]
            else:
                out['ch4_ppb'] = []
            if series.n2o:
                out['n2o_ppb'] = [data[i].n2o_ppb for i in range(len(data))]
            else:
                out['n2o_ppb'] = []
        else:
            out['time'] = []
            out['co2_ppm'] = []
            out['ch4_ppm'] = []
            out['n2o_ppm'] = []
            out['msg'] = 'no data in series id ' + str(series_id)
    else:
        out['msg'] = 'no data with series id ' + str(series_id)
    return jsonify(out)

## update a measurement set from fileserver
## this is meant for testing
## adds the 'project name' to a measurement
def update_measurement(id):
    meas = Measurements.query.filter_by(fileserver_id=id).all()
    if len(meas) == 1:
        target = fileserver_url + '/submit/submission/' + str(id) + '/'
        meas_data = fetch_url(target)
        projname = meas_data.get('project')
        if projname:
            meas[0].project = projname
            db.session.commit()
            print('updated meas id ' + str(id) + ' -> project ' + meas_data['project'])
        else:
            print('error: did not receive project name for meas id ' + str(id))
    elif len(meas) > 1:
        print('error: multiple measurements match id ' + str(id))
    else:
        print('warning: measurements id ' + str(id) + ' not present')
