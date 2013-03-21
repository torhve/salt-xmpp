import urllib
import urllib2
from cookielib import CookieJar
import json

HEADERS = {
    'Accept': 'application/json',
    'Content-Type': 'application/json',
    'X-Requested-With': 'XMLHttpRequest',
}
cj = CookieJar()
class MyHTTPRedirectHandler(urllib2.HTTPRedirectHandler):
    def http_error_302(self, req, fp, code, msg, headers):
        # patch headers to include salt token
        token = headers['X-Auth-Token']
        HEADERS['X-Auth-Token'] = token
        return urllib2.HTTPRedirectHandler.http_error_302(self, req, fp, code, msg, headers)

    http_error_301 = http_error_303 = http_error_307 = http_error_302
cookieprocessor = urllib2.HTTPCookieProcessor(cj)

opener = urllib2.build_opener(MyHTTPRedirectHandler, cookieprocessor)
urllib2.install_opener(opener)

class SaltREST(object):

    def __init__(self, config):
        self.config = config
        self.login()

    def login(self):
        lowstate_login =[{
            'eauth': 'pam',
            'username': self.config['saltuser'],
            'password': self.config['saltpass'],
        }]
        postdata = json.dumps(lowstate_login).encode()

        req = urllib2.Request(self.config['saltapiurl']+'login', postdata, HEADERS)
        f = urllib2.urlopen(req)
        return f.read()
        #print "Salt says: %s" % f.read()

    def get_minions(self):

        lowstate = [{
            'client': 'local',
            'tgt': '*',
            'fun': 'test.version',
        }]

        postdata = json.dumps(lowstate).encode()
        req = urllib2.Request(self.config['saltapiurl']+'', postdata, HEADERS)
        f = urllib2.urlopen(req)
        ret = json.loads(f.read())
        return ret

    def call(self, lowstate):
        postdata = json.dumps(lowstate).encode()
        req = urllib2.Request(self.config['saltapiurl'], postdata, HEADERS)
        f = urllib2.urlopen(req)
        ret = json.loads(f.read())
        return ret

