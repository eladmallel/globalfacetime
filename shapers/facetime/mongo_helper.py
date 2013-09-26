from pymongo import MongoClient
from shapers import settings
import datetime

client = MongoClient(settings.MONGO_URL)
client.globalfacetime.authenticate(settings.MONGO_USERNAME, settings.MONGO_PASSWORD)
db = client.globalfacetime

def get_sessions_collection():
	return db.sessions

class SessionsDao(object):
	def __init__(self):
		self._sessions = get_sessions_collection()

	def all_sessions(self):
		return list(self._sessions.find())

	def try_join_session(self):
		session = self._sessions.find_and_modify(
			query={'peer_count':1, 'looking_to_merge': False},
			update={'$inc':{'peer_count':1}},
			upsert=False,
			new=False)
		if session:
			return session['session_id']

		return None

	def save_session(self, session_id):
		session = {
			'peer_count': 1,
			'session_id': session_id,
			'looking_to_merge': False,
			'date': datetime.datetime.utcnow()
		}
		self._sessions.insert(session)

