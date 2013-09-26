from shapers import settings 
import OpenTokSDK

class SessionManager(object):
    def __init__(self):
        self._OTSDK = OpenTokSDK.OpenTokSDK(settings.OPENTOK_API_KEY,settings.OPENTOK_API_SECRET)
        self._sessionProperties = {OpenTokSDK.SessionProperties.p2p_preference: "enabled"}
        
        self._open_sessions = []

    def join_or_create_session(self):
        print "join_or_create_session"
        if len(self._open_sessions) == 0:            
            session_id = self._OTSDK.create_session(None, self._sessionProperties ).session_id
            self._open_sessions.append(session_id)
            print "creating"
        else:
            session_id = self._open_sessions.pop(0)
            print "joining"

        return session_id,self._create_token_for_session(session_id)

    def _create_token_for_session(self,session_id):
        print "_create_token_for_session"
        return self._OTSDK.generate_token(session_id)
