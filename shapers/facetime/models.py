from django.db import models
import datetime

DEFAULT_TIME_PER_USER_SESSION = datetime.timedelta(minutes=7)
DEFAULT_EVENT_TIME = datetime.timedelta(hours=1)

class Person(models.Model):
    name = models.CharField(max_length=512)
    created = models.DateTimeField(default=datetime.datetime.utcnow)
    
    def __unicode__(self):
        return self.name


class Event(models.Model):
	name = models.CharField(max_length=512)
	slug = models.CharField(max_length=128, help_text="This will be part of the URL http://www.chatsummit.com/{slug}. No funny characters please!")
	start_utc = models.DateTimeField(default=datetime.datetime.utcnow)
	end_utc = models.DateTimeField(default=lambda *args,**kwargs: datetime.datetime.utcnow() + DEFAULT_EVENT_TIME)
	time_per_user_session_minutes = models.FloatField(default=DEFAULT_TIME_PER_USER_SESSION.total_seconds() / 60.)
	password = models.CharField(max_length=512)

	def __str__(self):
		return "Event '%s' at '%s' starts at %s UTC password is '%s'"%(self.name,self.slug,self.start_utc,self.password)