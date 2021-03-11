from django.db import models

class Character(models.Model):
  class Meta:
    db_table = 'characters'

  id = models.IntegerField()
  name = models.CharField(max_length=100)
  emoji = models.CharField(max_length=100)

  def __unicode__(self):
    return "{0} (#{1})".format(self.name, self.id)
