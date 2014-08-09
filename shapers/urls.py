from django.conf.urls import patterns, include, url

# Uncomment the next two lines to enable the admin:
from django.contrib import admin
admin.autodiscover()

urlpatterns = patterns('',
    # Examples:
    url(r'^profile$', 'shapers.facetime.views.edit_profile'),
    url(r'^chat$', 'shapers.facetime.views.chat'),
    url(r'^connect$', 'shapers.facetime.views.connect'),
    url(r'^login$', 'shapers.facetime.views.login'),
    url(r'^heartbeat', 'shapers.facetime.views.heartbeat'),
    url(r'^video$', 'shapers.facetime.views.video'),
    url(r'^_get_alive_sessions$', 'shapers.facetime.views.get_alive_sessions'),
    url(r'^about_you$', 'shapers.facetime.views.about_you'),
    url(r'^password$', 'shapers.facetime.views.password'),
    url(r'^sharecontact$', 'shapers.facetime.views.share_contact'),
    url(r'^newdemo', 'shapers.facetime.views.newdemo'),
    url(r'^about$', 'shapers.facetime.views.about_chatsummit'),
    url(r'^help$', 'shapers.facetime.views.get_help'),
    url(r'^api/v1/select_event/(?P<event_slug>\w+)$', 'shapers.facetime.views.api_select_event'),
    url(r'^api/v1/create_profile/(?P<event_slug>\w+)$', 'shapers.facetime.views.api_create_profile'),
    url(r'^admin/?', include(admin.site.urls)),

    # TODO: This is bad practice because now the routes above us are basically "reserved event names"
    # TODO: Needs to refactor by moving all API calls to /api/v1/
    # TODO: Needs to refactor by moving all user http calls to /<event slug>/url
    url(r'^(?P<event_slug>\w+)$', 'shapers.facetime.views.event_login'),
    # url(r'^shapers/', include('shapers.foo.urls')),

    # Uncomment the admin/doc line below to enable admin documentation:
    # url(r'^admin/doc/', include('django.contrib.admindocs.urls')),

    # Uncomment the next line to enable the admin:
)