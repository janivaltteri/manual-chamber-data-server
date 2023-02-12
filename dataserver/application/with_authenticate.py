import os
import requests

from config import fileserver_url
from application import server

def fetch_url(data_url):
    basicauth = {'username': os.environ['DATAUSER'],
                 'password': os.environ['DATAPASS']}
    max_tries = 5
    if os.getenv('API_TOKEN') == None:
        #print("fetch_url: api token is none")
        targeturl = fileserver_url + '/submit/api/token/'
        #print("fetch_url: targeturl is " + targeturl)
        r = requests.post(targeturl, data=basicauth)
        recv = r.json()
        #print(recv)
        os.environ['API_TOKEN'] = recv.get('access')
    tries = 0
    recv_data = None
    while True:
        ##print("fetch_url: api token present")
        headers = {'Authorization': 'JWT ' + os.getenv('API_TOKEN')}
        r = requests.get(data_url,headers=headers)
        recv = r.json()
        ## note: recv_ok not used and error msg only printed
        ## todo: fix this
        ##recv_ok     = recv.get('ok')
        recv_msg    = recv.get('msg')
        recv_data   = recv.get('data')
        recv_detail = recv.get('detail')
        if recv_data:
            ##print("fetch_url: got data")
            break
        elif tries > max_tries:
            server.logger.warning("fetch_url: max_tries reached, giving up")
            #print("fetch_url: max tries reached, giving up")
            break
        else:
            server.logger.warning("fetch_url: did not receive data")
            #print("fetch_url: did not get data",end='')
            if recv_detail:
                ## todo: this should refresh the token?
                #print(", detail: " + recv_detail)
                targeturl = fileserver_url + '/submit/api/token/'
                r = requests.post(targeturl, data=basicauth)
                recv = r.json()
                os.environ['API_TOKEN'] = recv.get('access')
            else:
                #print(", no detail")
                if recv_msg:
                    if type(recv_msg == list):
                        server.logger.warning("msg: " + " ".join(recv_msg))
                        #print("msg: " + " ".join(recv_msg))
                    else:
                        server.logger.warning("msg: " + recv_msg)
                        #print("msg: " + recv_msg)
                break
        tries += 1
    return recv_data
