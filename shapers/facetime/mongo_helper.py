from pymongo import MongoClient
from shapers import settings
import datetime
import os
import random
import urllib, hashlib

#SECONDS_TILL_CONSIDERED_SEEN = 10
SECONDS_TILL_CONSIDERED_SEEN = 1

client = MongoClient(settings.MONGO_URL)

if settings.MONGO_USERNAME is not None:
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
        self._cached_num_users = 0
        self._last_user_num_cache = None

    def get_by_id(self, profile_id):
        profile = self._profiles.find_one({'profile_id': profile_id})
        profile['_id'] = str(profile['_id'])
        return profile

    def heartbeat(self, session_id, user):
        now = datetime.datetime.utcnow()

        try:
            user = int(user)
        except ValueError:
            return

        self._profiles.find_and_modify(
            query={'profile_id':user},
            update={'$set': {'last_heartbeat': now}},
            upsert=False)

    def get_num_alive_users(self, force=False):
        if force or \
            self._last_user_num_cache is None or \
            self._last_user_num_cache < datetime.datetime.utcnow() - datetime.timedelta(milliseconds=settings.USER_NUM_CACHE_TIME_MILLI):

            staleness_threshold = datetime.datetime.utcnow() - datetime.timedelta(milliseconds=settings.CHAT_MAXIMUM_STALENESS_ALLOWED_MILLI)
            self._cached_num_users = self._profiles.find({'last_heartbeat': {'$gte': staleness_threshold}}).count()

        return self._cached_num_users

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

    def add_seen_users_and_match(self, profile_id, seen, match_score):
        print "ADDSEEN", seen, profile_id, match_score

        profile = self._profiles.find_one({'profile_id':int(profile_id)})

        if profile is None:
            return

        added_seen = False
        to_add = {}

        for u in seen:
            if u not in profile.get('seen',{}):
                to_add['seen.'+u] = 1
                added_seen = True

        # If we added someone to seen, update our match score
        if added_seen:
            previous_match_score = profile.get('match_score', 0)
            previous_match_part = previous_match_score * 1. / settings.MATCH_SCORE_WINDOW * (settings.MATCH_SCORE_WINDOW - 1)
            current_match_part = match_score * 1. / settings.MATCH_SCORE_WINDOW
            new_match_score = previous_match_part + current_match_part
            to_add['match_score'] = new_match_score
            print "NEW MATCH SCORE",to_add['match_score']

        self._profiles.update(
            spec={'profile_id':int(profile_id)},
            document={'$set':to_add})

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

        print "Relevant query",query

        return [x for x in self._sessions.find(query)]

    def _try_join_specific_session(self,user_id,profile,session_id,match_score):
        query = {'_id':session_id, 'peer_count': 1}

        session = self._sessions.find_and_modify(
            query=query,
            update={
                '$inc':{'peer_count': 1, 'peers.'+user_id: 1},
                '$set':{
                    'joined.'+user_id:datetime.datetime.utcnow(),
                    'user_profiles.'+user_id:profile,
                    'match_score': match_score
                }
            },
            upsert=False,
            new=False)
        if session:
            return session['host'], session['_id']

        return None,None

    # TODO: Move to outside of DAO

    def _prioritize_sessions(self, user_id, profile, sessions):
        # Prioritize by conflict country, then other country then other ip then else
        # Low number - better match

        # Match score is higher if its a better match, to favor people who historically got shittier matches

        CONFLICT_SCORE = 0
        CONFLICT_MATCH_SCORE = 5

        OTHER_COUNTRY_SCORE = 10000
        OTHER_COUNTRY_MATCH_SCORE = 3

        OTHER_IP_SCORE = 20000
        OTHER_IP_MATCH_SCORE = 1

        ELSE_SCORE = 30000
        ELSE_MATCH_SCORE = 0

        user_country = profile['country_for_match']
        user_ip = profile['ip']

        scored_sessions = []
        for s in sessions:
            host_profile = s['user_profiles'][s['host']]
            host_country = host_profile['country_for_match']
            host_ip = host_profile['ip']
            host_match_score = host_profile.get('match_score',0)

            conflict_countries = CONFLICTS_BY_COUNTRY.get(user_country,[])
            if host_country in conflict_countries:
                scored_sessions.append((CONFLICT_SCORE+host_match_score, s, CONFLICT_MATCH_SCORE))
                continue

            if host_country != user_country:
                scored_sessions.append((OTHER_COUNTRY_SCORE+host_match_score, s, OTHER_COUNTRY_MATCH_SCORE))
                continue

            if host_ip != user_ip:
                scored_sessions.append((OTHER_IP_SCORE+host_match_score, s, OTHER_IP_MATCH_SCORE))
                continue

            else:
                scored_sessions.append((ELSE_SCORE+host_match_score, s, ELSE_MATCH_SCORE))

        scored_sessions.sort(key=lambda x: x[0])
        sorted_sessions = [{'session_id': x[1]['_id'], 'match_score': x[2]} for x in scored_sessions]
        return sorted_sessions

    def try_join_session(self,user_id,profile,event_slug):
        relevant_sessions = self._get_relevant_sessions(profile, event_slug)

        if len(relevant_sessions) == 0:
            return None,None

        prioritized_sessions_ids = self._prioritize_sessions(user_id, profile, relevant_sessions)

        if len(prioritized_sessions_ids) == 0:
            return None, None

        for info in prioritized_sessions_ids:
            session_id = info['session_id']
            match_score = info['match_score']
            print "Trying to join ", user_id, session_id, match_score
            host,joined_id = self._try_join_specific_session(user_id, profile, session_id, match_score)
            if host is not None:
                print "Joined!"
                return host, joined_id

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

    def heartbeat(self, session_id, user):
        now = datetime.datetime.utcnow()
        session = self._sessions.find_and_modify(
            query={'_id':session_id},
            update={'$set': {'heartbeats.'+user: now, 'latest_heartbeat': now}},
            upsert=False,
            new=True)

        # Now if we've been enough time together, mark us seen to eachother
        # TODO: Might cause a performance issue with multiple updates on each heartbeat

        seen = []
        match_score = None

        # TODO: Make seen detection use the lastest joiner instead of each by himself
        # Like by using the max on joined instead of the per-user value

        for uid, joined in session.get('joined',{}).items():
            if uid == user:
                continue

            print "SEEN", uid, joined, now, (now-joined).total_seconds(), session.get('match_score', None)

            if (now - joined).total_seconds() >= SECONDS_TILL_CONSIDERED_SEEN:
                seen.append(uid)
                match_score = session.get('match_score', None)

        return now, session["heartbeats"], seen, match_score
