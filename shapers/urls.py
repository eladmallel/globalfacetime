from django.conf.urls import patterns, include, url

# Uncomment the next two lines to enable the admin:
from django.contrib import admin
admin.autodiscover()

urlpatterns = patterns('',
    # Examples:
    url(r'^$', 'shapers.facetime.views.index'),
    url(r'^profile$', 'shapers.facetime.views.edit_profile'),
    url(r'^chat$', 'shapers.facetime.views.chat'),
    url(r'^connect$', 'shapers.facetime.views.connect'),
    url(r'^login$', 'shapers.facetime.views.login'),
    url(r'^heartbeat', 'shapers.facetime.views.heartbeat'),
    url(r'^video$', 'shapers.facetime.views.video'),
    url(r'^_get_alive_sessions$', 'shapers.facetime.views.get_alive_sessions'),
    url(r'^about_you$', 'shapers.facetime.views.about_you'),
    url(r'^password$', 'shapers.facetime.views.password'),
    # url(r'^shapers/', include('shapers.foo.urls')),

    # Uncomment the admin/doc line below to enable admin documentation:
    # url(r'^admin/doc/', include('django.contrib.admindocs.urls')),

    # Uncomment the next line to enable the admin:
    url(r'^admin/', include(admin.site.urls)),
)