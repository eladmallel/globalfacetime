from django import shortcuts
from django.template import RequestContext

def index(request):
	c = {}
	return shortcuts.render_to_response('index.html', c, context_instance=RequestContext(request))