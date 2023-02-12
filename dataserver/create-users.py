import json
import sqlite3

from werkzeug.security import generate_password_hash

##from application import db
##from application.models import User

print('executing create-users.py for dataserver')

with open('userlist.json', 'r') as f:
    ul = json.load(f)

con = sqlite3.connect('/opt/mcds/datadb/data.db')
cobj = con.cursor()
    
for i in range(len(ul['user'])):
    uname = ul['user'][i]['name']
    upass = ul['user'][i]['pass']
    cobj.execute('SELECT * FROM User')
    rows = cobj.fetchall()
    names = [row[1] for row in rows]
    if uname in names:
        print('user ' + uname + ' already present')
    else:
        uemail = "none"
        upassh = generate_password_hash(upass)
        vs = (uname,uemail,upassh)
        cobj.execute("INSERT INTO User (username,email,password_hash) VALUES (?,?,?)",vs)
        con.commit()
        print('added user ' + uname)

con.close()
