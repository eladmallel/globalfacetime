import requests
import posixpath
import json
import time
import threading
import copy

SERVER_URL = 'http://localhost:8000'
API_KEY = 'anyuni123'
HEARBEAT_TIME = 1

class Session(object):
    def __init__(self):
        self._s = requests.Session()
        self.current_event_slug = None

    def get_request(self,endpoint,*args,**kwargs):
        resp = self._s.get(posixpath.join(SERVER_URL,endpoint),*args,**kwargs)
        return resp

    def post_request(self,endpoint,*args,**kwargs):
        resp = self._s.post(posixpath.join(SERVER_URL,endpoint),*args,**kwargs)
        return resp

    # TODO: Error handling
    def select_event(self,event_slug):
        # No need to re-select
        if self.current_event_slug == event_slug:
            return True

        success = self.get_request('api/v1/select_event/'+event_slug).json()['success']

        if success:
            self.current_event_slug = event_slug

        return success

    # TODO: Error handling
    def create_profile(self, event_slug, name='', email='', country='', city='', interests='', ip=None):
        self.select_event(event_slug)

        data = {
            'name': name,
            'email': email,
            'country': country,
            'city': city,
            'interests': interests,
            'api_key': API_KEY,
        }

        if ip is not None:
            data['ip'] = ip

        resp = self.post_request('api/v1/create_profile/'+event_slug,data=data)

        return resp.json()['user_id']

    def heartbeat(self,event_slug,user_id,session_id):
        self.select_event(event_slug)
        return self.get_request('heartbeat',params={'user':user_id,'sessionId':session_id}).json()

    def connect(self,event_slug,user_id):
        self.select_event(event_slug)
        return self.get_request('connect',params={'profile_id':user_id}).json()

class HeartbeatThread(threading.Thread):
    def __init__(self,session):
        self._heartbeat_for = {}
        self._lock = threading.Lock()
        self._session = session

        threading.Thread.__init__(self)
        self.setDaemon(True)
        self.start()

    def run(self):
        while True:
            with self._lock:
                curr_heartbeats = copy.copy(self._heartbeat_for)

            for info,callback in curr_heartbeats.items():
                event_slug,user_id,session_id = info
                callback(self._session.heartbeat(event_slug,user_id,session_id))

            time.sleep(HEARBEAT_TIME)

    def add_heartbeat(self,event_slug,user_id,session_id,callback):
        with self._lock:
            self._heartbeat_for[(event_slug,user_id,session_id)] = callback

    def remove_heartbeat(self,event_slug,user_id,session_id):
        with self._lock:
            del self._heartbeat_for[(event_slug,user_id,session_id)]

class Connection(object):
    def __init__(self):
        self._s = Session()
        self._ht = HeartbeatThread(self._s)

    def get_event(self,event_slug):
        return Event(self,event_slug)

class User(object):
    def __init__(self,connection,event_slug,user_id):
        self.id = user_id
        self.event_slug = event_slug
        self.current_session = None
        self.last_heartbeat = None
        self._c = connection

    def disconnect(self):
        if self.current_session is None:
            return

        self._c._ht.remove_heartbeat(self.event_slug,self.id,self.current_session['sessionId'])
        self.current_session = None
        self.heartbeat_info = None

    def connect(self):
        self.disconnect()
        self.current_session = self._c._s.connect(self.event_slug,self.id)
        self._c._ht.add_heartbeat(self.event_slug,self.id,self.current_session['sessionId'],self.handle_heartbeat)

    def handle_heartbeat(self,data):
        if self.current_session is None:
            return

        self.last_heartbeat = data

        #print "User %s got heartbeat: %s"%(self.id,data)
        print "User %s got heartbeat - in event with %s"%(self.id, data['heartbeats'].keys())


class Event(object):
    def __init__(self,connection,event_slug):
        self._c = connection
        self.slug = event_slug

    def get_user(self,user_id, user_class=User):
        return user_class(self._c,self.slug,user_id)

    def create_user(self,*args,**kwargs):
        if 'user_class' in kwargs:
            user_class = kwargs['user_class']
            del kwargs['user_class']
        else:
            user_class = User

        user_id = self._c._s.create_profile(self.slug,*args,**kwargs)
        return self.get_user(user_id, user_class)
