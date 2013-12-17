from pymongo import MongoClient
from shapers import settings
import datetime
import os
import random

client = MongoClient(settings.MONGO_URL)
client.globalfacetime.authenticate(settings.MONGO_USERNAME, settings.MONGO_PASSWORD)
db = client.globalfacetime

def get_sessions_collection():
	return db.sessions

def _generate_session_id():
	return os.urandom(10).encode('hex')

def get_profiles_collection():
	return db.profiles

class ProfilesDao(object):
	def __init__(self):
		self._profiles = get_profiles_collection()

	def get_by_id(self, profile_id):
		profile = self._profiles.find_one({'profile_id': profile_id})
		profile['_id'] = str(profile['_id'])
		return profile

	def create_new_profile(self, name, email, country, city, interests):
		profile_id = random.randint(0,1<<32)

		profile = {
			'profile_id': profile_id,
			'name': name,
			'email': email,
			'country': country,
			'city': city,
			'interests': interests
		}

		self._profiles.insert(profile)
		return profile_id

class SessionsDao(object):
	def __init__(self):
		self._sessions = get_sessions_collection()

	def all_sessions(self):
		return list(self._sessions.find())

	def get_alive_sessions(self):
		staleness_threshold = datetime.datetime.utcnow() - datetime.timedelta(milliseconds=settings.CHAT_MAXIMUM_STALENESS_ALLOWED_MILLI)
		return list(self._sessions.find({'latest_heartbeat': {'$gte': staleness_threshold}}))

	def try_join_session(self,user):
		staleness_threshold = datetime.datetime.utcnow() - datetime.timedelta(milliseconds=settings.CHAT_MAXIMUM_STALENESS_ALLOWED_MILLI)

		session = self._sessions.find_and_modify(
			query={'peer_count':1, 'looking_to_merge': False, 'latest_heartbeat': {'$gte': staleness_threshold}},
			update={'$inc':{'peer_count':1,'peers.'+user:1}},
			upsert=False,
			new=False)
		if session:

			return session['host'], session['_id']

		return None,None

	def create_session(self, user_id):
		session = {
			'_id': _generate_session_id(), # Generate a random session id to help randomize session matches
			'peer_count': 1,
			'host': user_id,
			'peers': {user_id:1},
			'looking_to_merge': False,
			'date': datetime.datetime.utcnow(),
			'heartbeats': {},
			'latest_heartbeat': datetime.datetime.utcnow(),
		}
		self._sessions.insert(session)
		return session['_id']

	def heartbeat(self,session_id,user):
		now = datetime.datetime.utcnow()
		session = self._sessions.find_and_modify(
			query={'_id':session_id},
			update={'$set':{'heartbeats.'+user:now,'latest_heartbeat':now}},
			upsert=False,
			new=True)

		return now,session["heartbeats"]