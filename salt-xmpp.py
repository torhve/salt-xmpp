import sys
import os
import xmpp

import yaml
import saltrest

root = os.path.dirname(os.path.abspath(__file__))

CONFIG = yaml.safe_load(file(root+'/config.yaml').read())

class Bot(object):

    def __init__(self,jabber,remotejid):
        self.jabber = jabber
        self.remotejid = remotejid

    def register_handlers(self):
        self.jabber.RegisterHandler('message',self.xmpp_message)

    def xmpp_message(self, con, event):
        type = event.getType()
        fromjid = event.getFrom().getStripped()
        if type in ['message', 'chat', None] and fromjid == self.remotejid:
            sys.stdout.write(event.getBody() + '\n')

    def stdio_message(self, message):
        m = xmpp.protocol.Message(to=self.remotejid,body=message,typ='chat')
        self.jabber.send(m)
        pass

    def xmpp_connect(self):
        con=self.jabber.connect()
        if not con:
            sys.stderr.write('could not connect!\n')
            return False
        sys.stderr.write('connected with %s\n'%con)
        auth=self.jabber.auth(jid.getNode(),jidparams['password'],resource=jid.getResource())
        if not auth:
            sys.stderr.write('could not authenticate!\n')
            return False
        sys.stderr.write('authenticated using %s\n'%auth)
        self.register_handlers()
        return con

def xmpp_outputter(ret):
    ret = ret['return'][0]
    fret = ''
    for host, val in ret.items():
        fret += '%s: %s\n' %(host.replace(CONFIG['stripdomain'], ''), val)
    return fret


def messageCB(conn, mess):
    text=mess.getBody()
    user=mess.getFrom()
    jid = xmpp.protocol.JID(user).getStripped()
    print 'Got command:', text
    if jid == CONFIG['xmppadminuser']:
        if text == 'minions':
            conn.send(xmpp.Message(mess.getFrom(), ','.join([x.replace(CONFIG['stripdomain'], '') for x in MINIONS['return'][0].keys()])))
        else:
            lowstate = [{
                'client': 'local',
                'tgt': '*',
                'fun': text,
            }]
            ret = xmpp_outputter(salt.call(lowstate))
            conn.send(xmpp.Message(mess.getFrom(), ret) )
        
def startbot(username, password):

    jid=xmpp.protocol.JID(username)
    cli=xmpp.Client(jid.getDomain(), debug=False)
    cli.connect()


    should_register = False
    if should_register:
        # getRegInfo has a bug that puts the username as a direct child of the
        # IQ, instead of inside the query element.  The below will work, but
        # won't return an error when the user is known, however the register
        # call will return the error.
        xmpp.features.getRegInfo(cli,
                                 jid.getDomain(),
                                 #{'username':jid.getNode()},
                                 sync=True)

        if xmpp.features.register(cli,
                                  jid.getDomain(),
                                  {'username':jid.getNode(),
                                   'password':password}):
            sys.stderr.write("Success!\n")
        else:
            sys.stderr.write("Error!\n")

    authres=cli.auth(jid.getNode(),password)
    if not authres:
        print "Unable to authorize - check login/password."
        sys.exit(1)
    if authres<>'sasl':
        print "Warning: unable to perform SASL auth.  Old authentication method used!"
    cli.RegisterHandler('message',messageCB)
    cli.sendInitPresence()
    cli.send(xmpp.protocol.Message(CONFIG['xmppadminuser'],'Salt gateway ready for action.'))
    GoOn(cli)

def StepOn(conn):
    try:
        conn.Process(1)
    except KeyboardInterrupt: return 0
    return 1

def GoOn(conn):
    while StepOn(conn): pass

salt = saltrest.SaltREST(CONFIG)
MINIONS = salt.get_minions()
username = CONFIG['username']
password = CONFIG['password']
startbot(username, password)

