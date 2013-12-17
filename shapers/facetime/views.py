from django import shortcuts
from django.template import RequestContext
import json
from django.http import HttpResponse
from session_manager import SessionManager
from django.core.serializers.json import DjangoJSONEncoder

global session_manager
session_manager = SessionManager()

def index(request):
	c = {}
	return shortcuts.render_to_response('index.html', c, context_instance=RequestContext(request))

def chat(request):
	c = {}
	return shortcuts.render_to_response('chat.html', c, context_instance=RequestContext(request))

def connect(request):
	global session_manager
	user = request.GET.get('user')
	peer_id,session_id = session_manager.join_or_create_session(user)

	response_data = {}

	#response_data['sessionId'] = '2_MX40MTgwNTc5Mn4xMjcuMC4wLjF-VGh1IFNlcCAyNiAwMjoxMDo1OCBQRFQgMjAxM34wLjkzMzI0MDF-'
	#response_data['token'] = 'T1==cGFydG5lcl9pZD00MTgwNTc5MiZzZGtfdmVyc2lvbj10YnJ1YnktdGJyYi12MC45MS4yMDExLTAyLTE3JnNpZz0wMzU3MDAwYWU0NDg2ODU0NjhhNmNiMTJhZTEzMDc3MDU3MDE3ZTNhOnJvbGU9cHVibGlzaGVyJnNlc3Npb25faWQ9Ml9NWDQwTVRnd05UYzVNbjR4TWpjdU1DNHdMakYtVkdoMUlGTmxjQ0F5TmlBd01qb3hNRG8xT0NCUVJGUWdNakF4TTM0d0xqa3pNekkwTURGLSZjcmVhdGVfdGltZT0xMzgwMTg2NjU5Jm5vbmNlPTAuMDk5NTY4MzE4NTc0ODE1MDcmZXhwaXJlX3RpbWU9MTM4MDI3MzA2NSZjb25uZWN0aW9uX2RhdGE9'

	response_data['peerId'] = peer_id
	response_data['sessionId'] = session_id

	return HttpResponse(json.dumps(response_data), content_type="application/json")

def heartbeat(request):
	global session_manager
	session_id = request.GET.get("sessionId")
	user = request.GET.get("user")

	now,heartbeats = session_manager.heartbeat(session_id,user)

	return HttpResponse(
		json.dumps(
			{'now':now,'heartbeats':heartbeats},
			cls=DjangoJSONEncoder
		),
		content_type="application/json")

def login(request):
	global session_manager
	user = request.GET.get("user")

	auth_token = session_manager.login(user)
	return HttpResponse(json.dumps({'token':auth_token}), content_type="application/json")

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
