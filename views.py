import asyncio
import os

from dotenv import load_dotenv
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status, mixins
from rest_framework.viewsets import GenericViewSet

from tgparse.external_services.telegram_bot import TelegramBot

from tgparse.serializers import ChannelToDonorSerializer

load_dotenv()
leo_url = os.getenv("LEO_URL")

"""
class TodoListApiView(APIView):
    # add permission to check if user is authenticated
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, *args, **kwargs):
        
        data = {
            'my_chanel': request.data.get('my_chanel'),
            'donor': request.data.get('donor'),
            'l': request.data.get('l'),
            'r': request.data.get('r'),

        }
        bot = TelegramBot()
        bot.edit_old_between_interval(donor, my_channel,l,r)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
"""


class CheckPostApiView(APIView):
    # add permission to check if user is authenticated
    # permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        channel = (request.query_params.get("channel"),)
        bot = TelegramBot()
        answer = asyncio.run(bot.check_posts(channel))
        url = "jj"
        payload = {"date": answer, "url": url}
        print(payload)

        # requests.get(leo_url, params=payload)
        return Response("done", status=status.HTTP_201_CREATED)


class ChannelToDonorViewSet(
    mixins.CreateModelMixin,
    mixins.DestroyModelMixin,
    mixins.ListModelMixin,
    GenericViewSet,
):

    serializer_class = ChannelToDonorSerializer
