import sys
import os
import xmpp
from threading import Thread, Event
import yaml

# Our Salt REST API
import saltrest

# flag to tell all threads to stop
_stop = Event()


def single_node_xmpp_outputter(ret):
    ret = ret['return'][0]
    fret = ''
    for host, val in ret.items():
        fret += '%s\n' %val
    return fret

def xmpp_outputter(ret):
    ret = ret['return'][0]
    fret = ''
    for host, val in ret.items():
        fret += '%s: %s\n' %(host.replace(CONFIG['stripdomain'], ''), val)
    return fret


def masterMessageCB(conn, mess):
    text=mess.getBody()
    user=mess.getFrom()
    jid = xmpp.protocol.JID(user).getStripped()
    print 'Got command:', text
    if jid == CONFIG['xmppadminuser']:
        if text == 'minions':
            # make a nice list
            conn.send(xmpp.Message(mess.getFrom(), ', '.join(MINIONS)))
        else:
            lowstate = [{
                'client': 'local',
                'tgt': '*',
                'fun': text,
            }]
            ret = xmpp_outputter(salt.call(lowstate))
            conn.send(xmpp.Message(mess.getFrom(), ret) )


def make_msg_handler(tgt):
    def minionCB(dispatcher, mess):
        print '[%s] %s' % (dispatcher._owner.Resource, mess)
        text=mess.getBody()
        user=mess.getFrom()
        jid = xmpp.protocol.JID(user).getStripped()
        if jid == CONFIG['xmppadminuser']:
            lowstate = [{
                'client': 'local',
                'tgt': tgt + CONFIG['stripdomain'],
                'fun': text,
            }]
            ret = single_node_xmpp_outputter(salt.call(lowstate))
            dispatcher.send(xmpp.Message(mess.getFrom(), ret) )
    return minionCB


def startminion(username, password):
    jid=xmpp.protocol.JID(username)
    cli=xmpp.Client(jid.getDomain(), debug=False)
    cli.connect()


    should_register = True
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
            sys.stderr.write("Successfully register: %s!\n" %jid.getNode())
        else:
            sys.stderr.write("Error while registering: %s\n" %jid.getNode())

    authres=cli.auth(jid.getNode(),password)
    if not authres:
        print "Unable to authorize %s - check login/password." %jid.getNode()
        return None
        #sys.exit(1)
    if authres<>'sasl':
        print "Warning: unable to perform SASL auth.  Old authentication method used!"
    cli.RegisterHandler('message', make_msg_handler(jid.getNode()))
    cli.sendInitPresence()
    cli.send(xmpp.protocol.Message(CONFIG['xmppadminuser'],'Hello, Salt minion %s reporting for duty.' %jid.getNode()))

    return cli
        
def startmaster(username, password):

    jid=xmpp.protocol.JID(username)
    cli=xmpp.Client(jid.getDomain(), debug=False)
    cli.connect()

    authres=cli.auth(jid.getNode(),password)
    if not authres:
        print "Unable to authorize - check login/password."
        sys.exit(1)
    if authres<>'sasl':
        print "Warning: unable to perform SASL auth.  Old authentication method used!"
    cli.RegisterHandler('message', masterMessageCB)
    cli.sendInitPresence()
    cli.send(xmpp.protocol.Message(CONFIG['xmppadminuser'],'Salt gateway ready for action.'))
    return cli
    
def process_until_disconnect(bot):
    ret = -1
    while ret != 0 and not _stop.is_set():
        ret = bot.Process(1)


root = os.path.dirname(os.path.abspath(__file__))
CONFIG = yaml.safe_load(file(root+'/config.yaml').read())
salt = saltrest.SaltREST(CONFIG)
# Get minions so we can create bots, uses test.ping to get minion list
MINIONS = salt.get_minions()
username = CONFIG['username']
password = CONFIG['password']
_stop.clear()

# Start master
masterbot = startmaster(username, password)
try:
    Thread(target=process_until_disconnect, args=(masterbot,)).start()
    for minion in MINIONS:
        minionbot = startminion(minion+'@salt.idrift.no', 'sharedbotpwfordemo')
        if minionbot:
            Thread(target=process_until_disconnect, args=(minionbot,)).start()
    # Block main thread waiting for KeyboardInterrupt
    #while True:
    #    pass
except KeyboardInterrupt:
    _stop.set()
    print "Bye!"


