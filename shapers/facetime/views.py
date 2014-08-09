from django import shortcuts
from django.template import RequestContext
import json
from django.http import HttpResponse
from session_manager import SessionManager
from django.core.serializers.json import DjangoJSONEncoder
from .models import Event
import time
from mongo_helper import ProfilesDao
import pystmark
from shapers import settings
from django.core.exceptions import ObjectDoesNotExist
from django.views.decorators.csrf import csrf_exempt
import datetime
import analytics
import requests

global session_manager
analytics.init("9mh6pdkn3t")

session_manager = SessionManager()

def get_client_ip(request):
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0]
    else:
        ip = request.META.get('REMOTE_ADDR')
    return ip

def getEventInfo(event):
    out = {}
    out['startIn'] = (event.start_utc - datetime.datetime.utcnow()).total_seconds()*1000
    out['eventLength'] = (event.end_utc - event.start_utc).total_seconds()*1000
    out['timePerPerson'] = event.time_per_user_session_minutes * 60 * 1000
    return out

def verify_supersecret(f):
    def wrapped(request):
        if not request.session.get('supersecret', False):
            return shortcuts.redirect('/')
        return f(request)
    return wrapped

def verify_event(f):
    def wrapped(request):
        if not request.session.get('event_slug', False):
            return shortcuts.redirect('/')

        try:
            event = Event.objects.get(slug=request.session['event_slug'])
        except ObjectDoesNotExist:
            return shortcuts.render_to_response('event_doesnt_exist.html', c, context_instance=RequestContext(request))

        request.event = event

        return f(request)
    return wrapped


def event_login(request,event_slug):
    c = {}
    # Find the event for the slug
    try:
        event = Event.objects.get(slug=event_slug)
    except ObjectDoesNotExist:
        return shortcuts.render_to_response('event_doesnt_exist.html', c, context_instance=RequestContext(request))

    request.session['event_slug'] = event_slug

    # Clear the supersecret (So we can login to other events)
    request.session['supersecret'] = False

    c['event_slug'] = event_slug

    return shortcuts.render_to_response('login.html', c, context_instance=RequestContext(request))

def api_select_event(request,event_slug):
    # Find the event for the slug
    try:
        event = Event.objects.get(slug=event_slug)
    except ObjectDoesNotExist:
        return HttpResponse(json.dumps({'success':False,'reason':'not_found'}), content_type="application/json")

    request.session['event_slug'] = event_slug
    return HttpResponse(json.dumps({'success': True}), content_type="application/json")

@verify_event
def edit_profile(request):
    password = request.POST.get('password')
    if password == request.event.password or request.session.get('supersecret') == True:
        request.session['supersecret'] = True
        c = {}
        return shortcuts.render_to_response('about_you.html', c, context_instance=RequestContext(request))
    else:
        c = {}
        return shortcuts.render_to_response('password_error.html', c, context_instance=RequestContext(request))

SECRET_API_KEY = 'anyuni123'

# TODO: Validate API requests
@csrf_exempt
def api_create_profile(request,event_slug):
    if request.POST.get('api_key') != SECRET_API_KEY:
        return HttpResponse(json.dumps({'success':False,'reason':'bad_api_key'}), content_type="application/json")

    profilesDao = ProfilesDao()

    client_ip = request.POST.get('ip', get_client_ip(request))

    geoip_info_response = requests.get('http://freegeoip.net/json/%s'%client_ip)

    if geoip_info_response.status_code == 200:
        geoip_info = geoip_info_response.json()
    else:
        # TODO: Log a bad response code somewhere
        geoip_info = None

    profile_id = profilesDao.create_new_profile(
        name=request.POST['name'],
        email=request.POST['email'],
        country=request.POST['country'],
        city=request.POST['city'],
        interests=request.POST['interests'],
        event_slug=event_slug,
        ip=client_ip,
        geoip_info=geoip_info)

    return HttpResponse(json.dumps({'success':True,'user_id':profile_id}), content_type="application/json")


@verify_supersecret
@verify_event
def chat(request):
    profile_id = None
    if request.POST.get('name'):
        # you did POST - need to create your profile and load page
        profilesDao = ProfilesDao()

        client_ip = get_client_ip(request)

        # Get geoip info
        geoip_info_response = requests.get('http://freegeoip.net/json/%s'%client_ip)

        if geoip_info_response.status_code == 200:
            geoip_info = geoip_info_response.json()
        else:
            # TODO: Log a bad response code somewhere
            geoip_info = None

        profile_id = profilesDao.create_new_profile(
            name=request.POST['name'],
            email=request.POST['email'],
            country=request.POST['country'],
            city=request.POST['city'],
            interests=request.POST['interests'],
            event_slug=request.event.slug,
            ip=client_ip,
            geoip_info=geoip_info)

        analytics.identify(request.POST['email'], {
        		'name': request.POST['name'],
        		'city': request.POST['city'],
        		'interests': request.POST['interests'],
        		'eventSlug': request.event.slug,
        		'ip': get_client_ip(request)
        	})

        analytics.track(request.POST['email'],
            'Joined event', {
            'eventSlug' : request.event.slug,
            'country' : request.POST['country'],
            'ip' : get_client_ip(request)
            })

    else:
        profile_id = request.session.get('profile_id', None)
        if not profile_id:
            return shortcuts.redirect('/')

    c = {
        'profile_id': profile_id
    }
    return shortcuts.render_to_response('chat.html', c, context_instance=RequestContext(request))

@verify_event
def connect(request):
    global session_manager
    profile_id = request.GET.get('profile_id')
    peer_id, session_id = session_manager.join_or_create_session(profile_id,request.event.slug)

    response_data = {}

    if int(peer_id) != int(profile_id):
        profilesDao = ProfilesDao()
        profile = profilesDao.get_by_id(int(profile_id))
        response_data['peerProfile'] = profile

    #response_data['sessionId'] = '2_MX40MTgwNTc5Mn4xMjcuMC4wLjF-VGh1IFNlcCAyNiAwMjoxMDo1OCBQRFQgMjAxM34wLjkzMzI0MDF-'
    #response_data['token'] = 'T1==cGFydG5lcl9pZD00MTgwNTc5MiZzZGtfdmVyc2lvbj10YnJ1YnktdGJyYi12MC45MS4yMDExLTAyLTE3JnNpZz0wMzU3MDAwYWU0NDg2ODU0NjhhNmNiMTJhZTEzMDc3MDU3MDE3ZTNhOnJvbGU9cHVibGlzaGVyJnNlc3Npb25faWQ9Ml9NWDQwTVRnd05UYzVNbjR4TWpjdU1DNHdMakYtVkdoMUlGTmxjQ0F5TmlBd01qb3hNRG8xT0NCUVJGUWdNakF4TTM0d0xqa3pNekkwTURGLSZjcmVhdGVfdGltZT0xMzgwMTg2NjU5Jm5vbmNlPTAuMDk5NTY4MzE4NTc0ODE1MDcmZXhwaXJlX3RpbWU9MTM4MDI3MzA2NSZjb25uZWN0aW9uX2RhdGE9'

    response_data['peerId'] = peer_id
    response_data['sessionId'] = session_id

    return HttpResponse(json.dumps(response_data), content_type="application/json")

def heartbeat(request):
    global session_manager
    session_id = request.GET.get("sessionId")
    user = request.GET.get("user")

    now,heartbeats,profiles = session_manager.heartbeat(session_id,user)

    return HttpResponse(
        json.dumps(
            {
                'now': now,
                'heartbeats': heartbeats,
                'profiles': profiles
            },
            cls=DjangoJSONEncoder
        ),
        content_type="application/json")

@verify_event
def login(request):
    global session_manager
    user = request.GET.get("user")

    auth_token = session_manager.login(user)
    return HttpResponse(json.dumps({'token':auth_token, 'eventInfo': getEventInfo(request.event)}), content_type="application/json")

def video(request):
    return shortcuts.render_to_response('video.html',{},context_instance=RequestContext(request))

def get_alive_sessions(request):
    sessions = session_manager.get_alive_sessions()
    for s in sessions:
        del s["_id"] # ObjectIds don't serialize

    return HttpResponse(json.dumps(sessions,cls=DjangoJSONEncoder), content_type="application/json")


def about_you(request):
    return shortcuts.render_to_response('about_you.html',{},context_instance=RequestContext(request))

def password(request):
    return shortcuts.render_to_response('password.html',{},context_instance=RequestContext(request))

def share_contact(request):
    global session_manager
    session_id = request.GET.get("sessionId")
    user = request.GET.get("user")

    now,heartbeats,profiles = session_manager.heartbeat(session_id,user)

    user_profile = None
    peer_profile = None

    print "Going to search within these profiles: %s using this user: %s" % (profiles, user)

    for profile in profiles.values():
        if profile['profile_id'] == long(user):
            user_profile = profile
        else:
            peer_profile = profile

    if user_profile == None or peer_profile == None:
        return HttpResponse(
            json.dumps({
                'successful':False,
                'reason': 'Failed to find one of the profiles.'
            }),
            content_type="application/json")

    from_email = user_profile['email']
    from_name = user_profile['name']
    to_email = peer_profile['email']
    to_name = peer_profile['name']

    message = pystmark.Message(
        sender=settings.POSTMARK_SENDER,
        to=to_email,
        reply_to=from_email,
        subject='%s wants to connect with you' % from_name,
        text=format_email_body(to_name, from_name, from_email))

    email_response = pystmark.send(message, api_key=settings.POSTMARK_API_KEY)

    successful = True if email_response.ok else False
    return HttpResponse(
        json.dumps({
            'successful':successful,
            'reason': ('' if successful else email_response.text)
        }),
        content_type="application/json")

def format_email_body(to_name, from_name, from_email):
    return '''Hi %s,

Looks like %s really liked meeting you on ChatSummit!
Be nice, follow up promptly. 

Just reply to this thread or email %s to get in touch. 

ChatSummit,
On behalf of %s''' % (to_name, from_name, from_email, from_name)


def newdemo(request):
    return shortcuts.render_to_response('newdemo.html',{},context_instance=RequestContext(request))

def about_chatsummit(request): 
    return shortcuts.render_to_response('about_chatsummit.html',{},context_instance=RequestContext(request))

def get_help(request): 
    return shortcuts.render_to_response('help.html',{},context_instance=RequestContext(request))

def no_event(request): 
    return shortcuts.render_to_response('no_event.html',{},context_instance=RequestContext(request))

def enter_event(request):
    event_name = request.POST.get('event_name')
    return event_login(request, event_name)