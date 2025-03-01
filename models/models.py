from datetime import datetime

from django.db import models
from django.contrib.auth.models import User
from django.db.models import JSONField


class TgUser(models.Model):
    tg_id = models.CharField(max_length=255, verbose_name="category")
    name = models.CharField(max_length=255, verbose_name="category")
    is_active = models.BooleanField(default=True)
    fin_time = models.DateTimeField(null=True, default=None)
    num_posts = models.IntegerField(default=0)

    def __str__(self):
        return self.name


class MyChannel(models.Model):
    tg_id = models.ForeignKey(TgUser, on_delete=models.CASCADE)
    name = models.URLField(max_length=200)

    def __str__(self):
        return self.name


class Post(models.Model):
    user = models.ForeignKey(TgUser, on_delete=models.CASCADE)
    channel = models.ForeignKey(MyChannel, on_delete=models.CASCADE, default=None)
    original = models.CharField()
    rewrite = models.CharField(null=True, default=None)
    img = models.CharField(null=True, default=None)
    again = models.IntegerField(default=0)
    again_post_id = models.CharField(null=True, default=None)

    def __str__(self):
        return self.original
