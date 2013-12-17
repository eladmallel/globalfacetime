from shapers import settings 
import OpenTokSDK
from shapers.facetime.mongo_helper import SessionsDao, ProfilesDao

import jwt
import time

TOKEN_EXPIRY = 48*60*60 # Two days in seconds

class SessionManager(object):
    def __init__(self):
        #self._OTSDK = OpenTokSDK.OpenTokSDK(settings.OPENTOK_API_KEY,settings.OPENTOK_API_SECRET)
        self._session_properties = {OpenTokSDK.SessionProperties.p2p_preference: "enabled"}

        self._sessions_dao = SessionsDao()
        self._profiles_dao = ProfilesDao()

    def join_or_create_session(self, user):
        print "join_or_create_session"

        while True:
            peer_id, session_id = self._sessions_dao.try_join_session(user)
            if peer_id != user:
                break # Prevent us from joining ourself

        if not peer_id:
            print "creating for user %s"%user
            session_id = self._sessions_dao.create_session(user)
            peer_id = user
        else:
            print "joining user %s to user %s"%(user,peer_id)

        return peer_id,session_id

    def heartbeat(self,session_id,user):
        print "hearbeat: %s - %s"%(user,session_id)
        now, heartbeats = self._sessions_dao.heartbeat(session_id,user)
        profile_ids = heartbeats.keys()
        profiles = dict()
        for profile_id in profile_ids:
            profiles[profile_id] = self._profiles_dao.get_by_id(int(profile_id))
        return now,heartbeats,profiles


    def get_alive_sessions(self):
        return self._sessions_dao.get_alive_sessions()        

    @staticmethod
    def _createAuthToken(serviceId, userId, expiry, apiSecret):
        apiSecretKey = jwt.base64url_decode(apiSecret)
        subject = serviceId + ":" + userId
        payload = { "sub" : subject, "iss" : serviceId, "exp" : expiry }
        return jwt.encode(payload, apiSecretKey);

    def login(self,user):
        return self._createAuthToken(settings.VLINE_SERVICE_ID,user,time.time()+TOKEN_EXPIRY,settings.VLINE_API_SECRET)