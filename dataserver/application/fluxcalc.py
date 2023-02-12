import numpy
import datetime

from scipy.stats import linregress
from collections import namedtuple

from application.models import Datum

Fluxvalues = namedtuple("Fluxvalues",
                        ["lin_flux","intercept","slope","residual_mean"])

coefs = {
    # 'vm': 0.0224,
    'zerotemp': 273.15,
    'convf': 3600.0, # number of seconds in an hour
    'molmass_co2': 44.0095,
    'molmass_ch4': 16.0425,
    'molmass_n2o': 44.0130
}

def co2_lin_flux(data,temp_b,temp_e,ch_vol,ch_area,trim_b,trim_e,date):

    size = len(data)
    init_time = data[0].time
    init = datetime.datetime.combine(date,init_time)

    secs0 = [(datetime.datetime.combine(date,data[i].time) - init).seconds
             for i in range(len(data))]
    end_time = secs0[len(secs0) - 1]

    secs = []
    co2 = []
    for i in range(len(data)):
        if (secs0[i] >= trim_b) & (secs0[i] <= (end_time - trim_e)):
            secs.append(secs0[i])
            co2.append(data[i].co2_ppm)

    fit = linregress(secs,co2)
    residuals = numpy.array([co2[i] - (fit.intercept + fit.slope * secs[i])
                             for i in range(len(secs))])
    residual_mean = numpy.mean(numpy.power(residuals,2))

    try:
        temp = (temp_b + temp_e)/2.0
    except:
        temp = temp_b

    volume = ch_vol/1000.0 # dm3 to m3
    area = ch_area/100.0 # dm2 to m2

    lflux = (((101325.0 * fit.slope * 1e-6) /
              (8.31446 * (temp + coefs['zerotemp']))) *
             (volume / area) * coefs['molmass_co2'] * coefs['convf'])

    fv = Fluxvalues(lflux,fit.intercept,fit.slope,residual_mean)

    return fv

def ch4_lin_flux(data,temp_b,temp_e,ch_vol,ch_area,trim_b,trim_e,date):

    size = len(data)
    init_time = data[0].time
    init = datetime.datetime.combine(date,init_time)

    secs0 = [(datetime.datetime.combine(date,data[i].time) - init).seconds
             for i in range(len(data))]
    end_time = secs0[len(secs0) - 1]

    secs = []
    ch4 = []
    for i in range(len(data)):
        if (secs0[i] >= trim_b) & (secs0[i] <= (end_time - trim_e)):
            secs.append(secs0[i])
            ch4.append(data[i].ch4_ppb)

    fit = linregress(secs,ch4)
    residuals = numpy.array([ch4[i] - (fit.intercept + fit.slope * secs[i])
                             for i in range(len(secs))])
    residual_mean = numpy.mean(numpy.power(residuals,2))

    try:
        temp = (temp_b + temp_e)/2.0
    except:
        temp = temp_b

    volume = ch_vol / 1000.0 # dm3 to m3
    area = ch_area / 100.0 # dm2 to m2

    lflux = (((101325.0 * fit.slope * 1e-9) /
              (8.31446 * (temp + coefs['zerotemp']))) *
             (volume / area) * coefs['molmass_ch4'] * coefs['convf'])

    fv = Fluxvalues(lflux,fit.intercept,fit.slope,residual_mean)

    return fv

def n2o_lin_flux(data,temp_b,temp_e,ch_vol,ch_area,trim_b,trim_e,date):

    size = len(data)
    init_time = data[0].time
    init = datetime.datetime.combine(date,init_time)

    secs0 = [(datetime.datetime.combine(date,data[i].time) - init).seconds
             for i in range(len(data))]
    end_time = secs0[len(secs0) - 1]

    secs = []
    n2o = []
    for i in range(len(data)):
        if (secs0[i] >= trim_b) & (secs0[i] <= (end_time - trim_e)):
            secs.append(secs0[i])
            n2o.append(data[i].n2o_ppb)

    fit = linregress(secs,n2o)
    residuals = numpy.array([n2o[i] - (fit.intercept + fit.slope * secs[i])
                             for i in range(len(secs))])
    residual_mean = numpy.mean(numpy.power(residuals,2))

    try:
        temp = (temp_b + temp_e)/2.0
    except:
        temp = temp_b

    volume = ch_vol / 1000.0 # dm3 to m3
    area = ch_area / 100.0 # dm2 to m2

    lflux = (((101325.0 * fit.slope * 1e-9) /
              (8.31446 * (temp + coefs['zerotemp']))) *
             (volume / area) * coefs['molmass_n2o'] * coefs['convf'])

    fv = Fluxvalues(lflux,fit.intercept,fit.slope,residual_mean)

    return fv
