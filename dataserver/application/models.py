from application import db
from datetime import datetime

from flask_login import UserMixin
from sqlalchemy_serializer import SerializerMixin

from werkzeug.security import generate_password_hash, check_password_hash

from application import login

## todo: string max lengths should be checked when adding to database

class User(UserMixin,db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), index=True, unique=True)
    email = db.Column(db.String(120))
    password_hash = db.Column(db.String(128))

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def __repr__(self):
        return '<User {}>'.format(self.username) 

class Available(db.Model):
    id            = db.Column(db.Integer, primary_key=True)
    fileserver_id = db.Column(db.Integer, unique=True)
    date          = db.Column(db.DateTime)
    measure_date  = db.Column(db.Date)
    fieldname     = db.Column(db.String(100))
    dataname      = db.Column(db.String(100))
    status        = db.Column(db.String(25))
    fieldstatus   = db.Column(db.String(25))
    datastatus    = db.Column(db.String(25))
    comment       = db.Column(db.String(256))
    updated       = db.Column(db.DateTime, default=datetime.utcnow)
    fetched       = db.Column(db.Boolean, default=False)

class Measurements(db.Model):
    id            = db.Column(db.Integer, primary_key=True)
    fileserver_id = db.Column(db.Integer, unique=True)
    project       = db.Column(db.String(60))
    date          = db.Column(db.DateTime)
    measure_date  = db.Column(db.Date)
    device        = db.Column(db.String(20))
    chamber       = db.Column(db.String(10))
    soil          = db.Column(db.String(20))
    comment       = db.Column(db.String(256))
    siteids       = db.Column(db.String(128))
    fs_state      = db.Column(db.Boolean, default=True)
    successful    = db.Column(db.Boolean, default=False)
    fetch_date    = db.Column(db.DateTime, default=datetime.utcnow)
    series        = db.relationship('Series',backref='seriesref',lazy='dynamic')

class Series(db.Model, SerializerMixin):
    id             = db.Column(db.Integer, primary_key=True)
    measurements   = db.Column(db.Integer, db.ForeignKey('measurements.id'))
    date           = db.Column(db.Date) ## todo: is this measure date?
    siteid         = db.Column(db.String(25))
    subsiteid      = db.Column(db.String(25))
    point          = db.Column(db.String(25))
    pointtype      = db.Column(db.String(64))
    sitedesc       = db.Column(db.String(64))
    chambersetting = db.Column(db.String(64))
    notes1         = db.Column(db.String(256))
    notes2         = db.Column(db.String(256))
    notes3         = db.Column(db.String(256))
    fabric         = db.Column(db.String(128))
    weather        = db.Column(db.String(128))
    wind           = db.Column(db.String(128))
    start_time     = db.Column(db.Time)
    end_time       = db.Column(db.Time)
    start_ppm      = db.Column(db.Float)
    end_ppm        = db.Column(db.Float)
    start_temp     = db.Column(db.Float)
    end_temp       = db.Column(db.Float)
    chamber_vol    = db.Column(db.Float)
    chamber_area   = db.Column(db.Float)
    t05            = db.Column(db.Float)
    t10            = db.Column(db.Float)
    t15            = db.Column(db.Float)
    t20            = db.Column(db.Float)
    t30            = db.Column(db.Float)
    t40            = db.Column(db.Float)
    tsmoisture     = db.Column(db.Float)
    sm             = db.Column(db.Float)
    wt             = db.Column(db.Float)
    t05_egm        = db.Column(db.Float)
    tsm_egm        = db.Column(db.Float)
    empty          = db.Column(db.Boolean, default=True)
    co2            = db.Column(db.Boolean, default=False)
    ch4            = db.Column(db.Boolean, default=False)
    n2o            = db.Column(db.Boolean, default=False)
    data           = db.relationship('Datum',backref='datumref',lazy='dynamic')

class Flux(db.Model, SerializerMixin):
    id            = db.Column(db.Integer, primary_key=True)
    series        = db.Column(db.Integer, db.ForeignKey('series.id'))
    trimmer       = db.Column(db.Integer, db.ForeignKey('user.id'))
    datetime      = db.Column(db.DateTime, default=datetime.utcnow)
    trim_head     = db.Column(db.Integer, default=0)
    trim_tail     = db.Column(db.Integer, default=0)
    gas           = db.Column(db.Integer) # 1 co2 2 ch4 3 n2o
    slope         = db.Column(db.Float)
    intercept     = db.Column(db.Float)
    flux          = db.Column(db.Float)
    resid         = db.Column(db.Float)
    bad           = db.Column(db.Boolean, default=False)

class Datum(db.Model, SerializerMixin):
    time_format = '%H:%M:%S'
    id           = db.Column(db.Integer, primary_key=True)
    series       = db.Column(db.Integer, db.ForeignKey('series.id'))
    time         = db.Column(db.Time)
    co2_ppm      = db.Column(db.Float)
    ch4_ppb      = db.Column(db.Float)
    n2o_ppb      = db.Column(db.Float)

@login.user_loader
def load_user(id):
    return User.query.get(int(id))

@login.request_loader
def load_user_from_request(request):
    auth = request.authorization
    if not auth:
        return None
    user = User.query.filter_by(username = auth.username).first()
    if not user:
        return None
    if user.check_password(auth.password):
        return user
    else:
        return None
