execfile('test_api.py')
from collections import OrderedDict
import time
import random
import dateutil.parser

# Override default heartbeat time
HEARTBEAT_TIME = 0.3

STALE_TIME = 3

class HeartbeatLoggingUser(User):
    def __init__(self, *args, **kwargs):
        self.seen_sessions = OrderedDict()
        self.current_partner = None

        User.__init__(self, *args, **kwargs)

    def connect(self):
        self.current_partner = None
        User.connect(self)

    def disconnect(self):
        self.current_partner = None
        User.disconnect(self)

    def handle_heartbeat(self,data):
        if self.current_session is None:
            return

        #print "User %s got heartbeat - in event with %s"%(self.id, data['heartbeats'].keys())

        self.seen_sessions[self.current_session['sessionId']] = data

        # Check staleness and find current partner
        server_now = dateutil.parser.parse(data['now'])

        for k,v in data['heartbeats'].items():
            if k == str(self.id):
                continue

            other_heartbeat = dateutil.parser.parse(v)

            #print "COMPARE", server_now - other_heartbeat
            if (server_now - other_heartbeat).total_seconds() > STALE_TIME:
                print "User %s has a stale connection - reconnect"%self.id
                self.disconnect()
                self.connect()
                break
            else:
                self.current_partner = str(k)



print "Initializing connection..."
_connection = Connection()
_event = _connection.get_event('a')

USERS = {}

def register_user(label, ip, country=''):
    u = _event.create_user(ip=ip, country=country, user_class=HeartbeatLoggingUser)
    USERS[str(u.id)] = {'label': label, 'user': u}


def run():
    print "Connecting all users..."
    for u in USERS.values():
        print '\tConnecting user %s'%u['label']
        u['user'].connect()

    print "Done connecting all users."
    print
    print "Running test, press Ctrl+C to stop"

    random.seed(time.time())

    time.sleep(3)
    while True:
        try:
            order = USERS.values()
            random.shuffle(order)
            print "Starting order..."
            for u in order:
                user_partner = u['user'].current_partner
                user_partner_user = USERS.get(user_partner,None)
                if user_partner_user is None:
                    print "\t%s is alone, skipping"%u['label']
                    continue
                else:
                    print "\tCycling %s and %s"%(u['label'], user_partner_user['label'])
                    u['user'].disconnect()
                    u['user'].connect()
                    user_partner_user['user'].disconnect()
                    user_partner_user['user'].connect()
                    time.sleep(3)

        except KeyboardInterrupt:
            break

    print "Done with test"
    print
    print "Disconnecting all users."
    for u in USERS.values():
        print '\tDisconecting user %s'%u['label']
        u['user'].disconnect()

    print "Done disconnecting all users"
    print
    print "-------- REPORT ----------"
    for u in USERS.values():
        print "User %s:"%u['label']
        for s in u['user'].seen_sessions.values():
            other_ids = s['heartbeats'].keys()
            other_labels = [USERS[str(i)]['label'] for i in other_ids if str(i) != str(u['user'].id) and str(i) in USERS]

            if len(other_labels) == 0:
                print "\tAlone"
            else:
                print "\tWith %s"%(', '.join(other_labels))

    print "------- REPORT END --------"
    print
    print "Done!"


# Register test users
register_user('Israel-1', '79.178.171.251')
register_user('Israel-2', '79.178.171.252')
register_user('Israel-3', '79.178.171.253')
register_user('Israel-4', '79.178.171.254')
register_user('Israel-5', '79.178.171.255')
register_user('Palestine-1', '82.213.63.7')
register_user('Palestine-2', '82.213.63.8')
register_user('Palestine-3', '82.213.63.9')
register_user('Palestine-4', '82.213.63.1')
register_user('Palestine-5', '82.213.63.2')


# Run test
run()




