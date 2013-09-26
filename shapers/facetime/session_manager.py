from shapers import settings 
import OpenTokSDK
from shapers.facetime.mongo_helper import SessionsDao

class SessionManager(object):
    def __init__(self):
        self._OTSDK = OpenTokSDK.OpenTokSDK(settings.OPENTOK_API_KEY,settings.OPENTOK_API_SECRET)
        self._session_properties = {OpenTokSDK.SessionProperties.p2p_preference: "enabled"}

        self._sessions_dao = SessionsDao()

    def join_or_create_session(self):
        print "join_or_create_session"

        session_id = self._sessions_dao.try_join_session()
        if not session_id:
            print "creating"
            session_id = self._OTSDK.create_session(None, self._session_properties).session_id
            self._sessions_dao.save_session(session_id)
        else:
            print "joining"

        return session_id,self._create_token_for_session(session_id)

    def _create_token_for_session(self,session_id):
        print "_create_token_for_session"
        return self._OTSDK.generate_token(session_id)

    def heartbeat(self,session_id,user):
        print "hearbeat: %s - %s"%(user,session_id)
        return self._sessions_dao.heartbeat(session_id,user)