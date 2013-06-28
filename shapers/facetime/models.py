from django.db import models
import datetime

class Person(models.Model):
    name = models.CharField(max_length=512)
    created = models.DateTimeField(default=datetime.datetime.now)
    
    def __unicode__(self):
        return self.name