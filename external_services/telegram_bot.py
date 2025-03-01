import asyncio
import os
import threading
import django
import requests
from datetime import timedelta
from openai import APIError

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "bot.settings")
django.setup()
os.environ["DJANGO_ALLOW_ASYNC_UNSAFE"] = "true"

from PIL import Image
from telethon import TelegramClient
from tgparse.external_services.ai_content_generator import *

load_dotenv()
telegram_api_id = int(os.getenv("API_ID"))
telegram_api_hash = os.getenv("API_HASH")

all_messages = []
admins = ["mira_mira28", "evatestbot28"]


def Error_Handler(func):
    def Inner_Function(*args, **kwargs):
        _delay = 10
        all_time = 0
        max_time = 600
        while all_time < max_time:
            start_time = time.time()
            try:
                result = func(*args, **kwargs)
                return result
            except APIError:
                logging.error(APIError, exc_info=True)
                time.sleep(_delay)
            except RuntimeError:
                logging.error(RuntimeError, exc_info=True)
                time.sleep(_delay)
            except Exception as e:
                logging.error(e, exc_info=True)
                time.sleep(_delay)
            finally:
                end_time = time.time()
                execution_time = end_time - start_time
                all_time += execution_time
        raise MyCustomException()

    return Inner_Function


def add_url(message: dict) -> tuple:
    s = message["message"]
    sdvig = 0
    has_url = 0
    media_url = ""
    for i in message["entities"]:
        if i["_"] == "MessageEntityTextUrl":
            url = i["url"]
            check = re.match(
                r"(?P<protocol>https?)?(?::\/\/)?(?:(?:t\.me)|(?:telegram)\.(?:(?:me)))",
                url,
            )

            if not check and media_url == "":
                has_url = 1
                pos = i["offset"] + i["length"] + sdvig
                char_to_insert = "[" + url + "]"
                sdvig = len(char_to_insert) + sdvig
                s = s[:pos] + char_to_insert + s[pos:]
    return s, has_url


def count_mes(
        channel_to_mes: list, channel_from_mes: list, left_time_interval: timedelta,
        right_time_interval: timedelta
):
    j = 0
    count = 0

    for i in channel_to_mes:
        while j < len(channel_from_mes) and channel_from_mes[j]["date"] < i["date"] - left_time_interval:
            j += 1
        if j >= len(channel_from_mes):
            break
        if i["date"] - left_time_interval < channel_from_mes[j]["date"] < i["date"] + right_time_interval:
            count += 1
            j += 1
    return count


class TelegramBot:
    _instance = None

    def __new__(
            cls, *args, **kwargs
    ):  # синглтон
        if cls._instance is None:
            cls._instance = super(TelegramBot, cls).__new__(cls)
            cls._instance._init_instance()
        return cls._instance

    def _init_instance(self):
        self.new_loop = asyncio.new_event_loop()

        self.message_rewriter = AIContentGenerator()
        self.client = TelegramClient(
            "my_session",
            telegram_api_id,
            telegram_api_hash,
            system_version="4.16.30-vxCUSTOM",
        )

        asyncio.run_coroutine_threadsafe(self.client.connect(), loop=self.client.loop)

        # asyncio.run_coroutine_threadsafe(self.main(), loop=self.client.loop)
        thread = threading.Thread(target=self.new_loop.run_forever)
        thread.start()

        self.send = Error_Handler(self.client.send_message)  # обработка ошибок
        self.get_mes = Error_Handler(self.client.get_messages)
        self.edit_mes = Error_Handler(self.client.edit_message)
        self.get_hist = Error_Handler(self.client.edit_message)

    def add_task(self, coro):
        fut = asyncio.ensure_future(coro, loop=self.client.loop)
        # fut = asyncio.run_coroutine_threadsafe(coro, loop=self.client.loop)
        return fut

    async def check_admin(self, ch):
        user = await self.client.get_me()
        permissions = await self.client.get_permissions(ch.name, user)
        return permissions.is_admin

    async def send_post(self, post):
        await self.send(
            post.channel.name,
            post.rewrite,
            file="image.jpg",
            force_document=False,
            parse_mode="html",
        )

    def img(self, image_url: str):
        img_data = requests.get(image_url).content
        with open("image.jpg", "wb") as handler:
            handler.write(img_data)
        foo = Image.open("image.jpg")
        foo = foo.resize((512, 512), Image.LANCZOS)
        foo.save("image.jpg", optimize=True, quality=75)

    async def gen(self, message: dict):
        loop = self.client.loop
        if message["_"] == "Message":
            text, has_url = add_url(message)
            answer = await loop.run_in_executor(
                None, self.message_rewriter.rewrite_message, text
            )
            if answer:
                if has_url:
                    answer = await loop.run_in_executor(
                        None, self.message_rewriter.right_url, text, answer
                    )
                url = await loop.run_in_executor(
                    None, self.message_rewriter.new_image, answer
                )
                self.img(url)
                return answer, url
        return 0

    async def gen_text(self, post):
        loop = self.client.loop
        st = post.original.replace('\xa0', ' ')
        k = st.replace("'", '"')
        message = eval(k)
        url = post.img
        if message["_"] == "Message":
            text, has_url = add_url(message)
            answer = await loop.run_in_executor(
                None, self.message_rewriter.rewrite_message, text
            )
            if answer:
                if has_url:
                    answer = await loop.run_in_executor(
                        None, self.message_rewriter.right_url, text, answer
                    )
                return answer, url
        return 0

    async def gen_img(self, post):
        loop = self.client.loop
        url = await loop.run_in_executor(
            None, self.message_rewriter.new_image, post.rewrite
        )
        self.img(url)
        answer = post.rewrite
        return answer, url
