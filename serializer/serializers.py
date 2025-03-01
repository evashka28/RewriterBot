from rest_framework.fields import CharField
from rest_framework.serializers import ModelSerializer, ListSerializer

from tgparse.models import *


class ChannelToDonorSerializer(ModelSerializer):

    class Meta:
        fields = "__all__"
