from pymongo import MongoClient
from shapers import settings
import datetime
import os
import random
import urllib, hashlib

SECONDS_TILL_CONSIDERED_SEEN = 10

client = MongoClient(settings.MONGO_URL)
client.globalfacetime.authenticate(settings.MONGO_USERNAME, settings.MONGO_PASSWORD)
db = client.globalfacetime

CONFLICTS_BY_COUNTRY = {
    'Israel': ['Palestinian Territory', 'Palestine', 'Iran', 'Syria', 'Lebanon', 'Jordan', 'Egypt'],
    'Palestinian Territory': ['Israel' ,'Egypt'],
    'Iran': ['Israel'],
    'Syria': ['Israel'],
    'Lebanon': ['Israel'],
    'Egypt': ['Israel']
}

def calculate_gravatar_url(email):
    gravatar_url = "http://www.gravatar.com/avatar/" + hashlib.md5(email.lower()).hexdigest() + "?"
    gravatar_url += urllib.urlencode({'d':'http://screencritix.com/wp-content/uploads/2013/10/avatar-navi-120x120.jpg', 's':str(120)})
    return gravatar_url

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

    def create_new_profile(self, name, email, country, city, interests, event_slug, ip, geoip_info):
        profile_id = random.randint(0,1<<32)

        avatar_url = calculate_gravatar_url(email)

        if geoip_info is None and 'country_name' in geoip_info and len(geoip_info['country_name']) != 0:
            country_for_match = geoip_info['country_name']
        else:
            country_for_match = country

        profile = {
            'profile_id': profile_id,
            'name': name,
            'email': email,
            'country': country,
            'city': city,
            'interests': interests,
            'avatar': avatar_url,
            'seen': {},
            'event_slug': event_slug,
            'ip': ip,
            'geoip_info': geoip_info,
            'country_for_match': country_for_match
        }


        self._profiles.insert(profile)
        return profile_id

    def add_seen_users(self,profile_id,seen):
        to_add = {}
        for u in seen:
            to_add['seen.'+u] = 1

        print "ADDSEEN",to_add,profile_id

        self._profiles.find_and_modify(
            query={'profile_id':int(profile_id)},
            update={'$inc':to_add}, # TODO: Can't use $set due to bug in MongoDB (Change when its fixed)
            upsert=False,
            new=False)

class SessionsDao(object):
    def __init__(self):
        self._sessions = get_sessions_collection()

    def all_sessions(self):
        return list(self._sessions.find())

    def get_alive_sessions(self):
        staleness_threshold = datetime.datetime.utcnow() - datetime.timedelta(milliseconds=settings.CHAT_MAXIMUM_STALENESS_ALLOWED_MILLI)
        return list(self._sessions.find({'latest_heartbeat': {'$gte': staleness_threshold}}))

    def _get_relevant_sessions(self,profile,event_slug):
        staleness_threshold = datetime.datetime.utcnow() - datetime.timedelta(milliseconds=settings.CHAT_MAXIMUM_STALENESS_ALLOWED_MILLI)

        seen = profile.get('seen',{}).keys()

        query = {
            'event_slug': event_slug, # for this event
            'peer_count': 1, # With only one person
            'latest_heartbeat': {'$gte': staleness_threshold}, # That isn't stale

        }

        # Make sure nobody I know is in the session
        for other_id in seen:
            query['peers.'+other_id] = {'$exists':False}

        # And that it isn't my session
        query['peers.'+str(profile['profile_id'])] = {'$exists':False}

        return [x for x in self._sessions.find(query)]

    def _try_join_specific_session(self,user_id,profile,session_id):
        query = {'_id':session_id}

        session = self._sessions.find_and_modify(
            query=query,
            update={'$inc':{'peer_count':1,'peers.'+user_id:1},'$set':{'joined.'+user_id:datetime.datetime.utcnow(),'user_profiles.'+user_id:profile}},
            upsert=False,
            new=False)
        if session:
            return session['host'], session['_id']

        return None,None

    # TODO: Move to outside of DAO

    def _prioritize_sessions(self, user_id, profile, sessions):
        # Prioritize by conflict country, then other country then other ip then else

        CONFLICT_SCORE = 0
        OTHER_COUNTRY_SCORE = 10000
        OTHER_IP_SCORE = 20000
        ELSE_SCORE = 30000

        user_country = profile['country_for_match']
        user_ip = profile['ip']

        scored_sessions = []
        for s in sessions:
            host_profile = s['user_profiles'][s['host']]
            host_country = host_profile['country_for_match']
            host_ip = host_profile['ip']

            conflict_countries = CONFLICTS_BY_COUNTRY.get(user_country,[])
            if host_country in conflict_countries:
                scored_sessions.append((CONFLICT_SCORE, s))
                continue

            if host_country != user_country:
                scored_sessions.append((OTHER_COUNTRY_SCORE, s))
                continue

            if host_ip != user_ip:
                scored_sessions.append((OTHER_IP_SCORE, s))
                continue

            else:
                scored_sessions.append((ELSE_SCORE, s))

        scored_sessions.sort(key=lambda x: x[0])
        sorted_sessions = [x[1]['_id'] for x in scored_sessions]
        return sorted_sessions

    def try_join_session(self,user_id,profile,event_slug):
        relevant_sessions = self._get_relevant_sessions(profile,event_slug)

        if len(relevant_sessions) == 0:
            return None,None

        prioritized_sessions_ids = self._prioritize_sessions(user_id,profile,relevant_sessions)

        if len(prioritized_sessions_ids) == 0:
            return None, None

        for session_id in prioritized_sessions_ids:
            print "Trying to join ", user_id, session_id
            host,joined_id = self._try_join_specific_session(user_id,profile,session_id)
            if host is not None:
                print "No!"
                return host,joined_id

        return None,None

    def create_session(self, user_id, profile, event_slug):
        session = {
            '_id': _generate_session_id(), # Generate a random session id to help randomize session matches
            'peer_count': 1,
            'host': user_id,
            'peers': {user_id:1},
            'user_profiles': {user_id:profile},
            'date': datetime.datetime.utcnow(),
            'heartbeats': {},
            'joined': {user_id: datetime.datetime.utcnow()},
            'latest_heartbeat': datetime.datetime.utcnow(),
            'event_slug': event_slug,
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

        # Now if we've been enough time together, mark us seen to eachother
        # TODO: Might cause a performance issue with multiple updates on each heartbeat

        seen = []
        for uid,joined in session.get('joined',{}).items():
            if uid == user:
                continue

            print "SEEN",uid,joined,now,(now-joined).total_seconds()

            if (now - joined).total_seconds() >= SECONDS_TILL_CONSIDERED_SEEN:
                seen.append(uid)

        return now,session["heartbeats"],seen
