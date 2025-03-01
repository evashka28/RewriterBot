import functools
from datetime import timezone

import apscheduler

from apscheduler.executors.asyncio import AsyncIOExecutor
from apscheduler.jobstores.sqlalchemy import SQLAlchemyJobStore
from apscheduler.schedulers.background import BackgroundScheduler
from dotenv import load_dotenv
from sqlalchemy import create_engine
from telethon import TelegramClient, events
from telethon.tl.functions.channels import JoinChannelRequest, LeaveChannelRequest
from telethon.tl.types import (
    ReplyKeyboardMarkup,
    KeyboardButtonRow,
    KeyboardButton,
    ReplyInlineMarkup,
    KeyboardButtonCallback,
    KeyboardButtonUrl,
)

from tgparse.models.models import *
from tgparse.utils.EmailSender import EmailSender
from tgparse.external_services.telegram_bot import *
import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "bot.settings")
django.setup()
os.environ["DJANGO_ALLOW_ASYNC_UNSAFE"] = "true"

load_dotenv()
telegram_api_id = int(os.getenv("API_ID"))
telegram_api_hash = os.getenv("API_HASH")
bot_token = os.getenv("BOT_TOKEN")

client = TelegramClient("bot", telegram_api_id, telegram_api_hash)
bot = client.start(bot_token=bot_token)

user_bot = TelegramBot()

try:
    email_sender = EmailSender()
except Exception as e:
    logging.error(e, exc_info=True)

is_free = True


def job():
    for i in TgUser.objects.all():
        i.num_of_posts = 0
        i.save()


db_url = 'postgresql://postgres:vinnikova@localhost:5432/userbotdb'
engine = create_engine(db_url)
executors = {"default": AsyncIOExecutor(), "threadpool": apscheduler.executors.pool.ThreadPoolExecutor(max_workers=20)}
task_defaults = {"coalesce": False, "max_instances": 4}
jobstore = SQLAlchemyJobStore(engine=engine)

scheduler = BackgroundScheduler(jobstores={'default': jobstore})
scheduler.add_job(job, 'cron', hour=00, minute=00)
scheduler.start()

main_menu = ReplyKeyboardMarkup(
    [
        KeyboardButtonRow(
            [
                KeyboardButton(text="Мои каналы"),
            ]
        ),
        KeyboardButtonRow(
            [
                KeyboardButton(text="Создать пост"),
            ]
        ),
        KeyboardButtonRow(
            [
                KeyboardButton(text="Сообщение об ошибках"),
            ]
        ),
        KeyboardButtonRow(
            [
                KeyboardButton(text="Оставить отзыв"),
            ]
        )
    ],
    resize=False
)


def is_active(user):
    if user.fin_time < datetime.now().replace(
            tzinfo=timezone(timedelta(hours=3))):
        asyncio.ensure_future(bot.send_message(
            entity=int(user.tg_id),
            message="К сожалению ваша пробная подписка окончена",
        ))
        user.is_active = False
        user.save()
        return False
    return True


@bot.on(events.NewMessage(pattern="/start|Назад"))
async def start(event):
    active = TgUser.objects.filter(is_active=True)
    if active.count() < 100:  # NOTE макс количество человек
        user = await client.get_entity(event.peer_id)
        user_obj, created = TgUser.objects.get_or_create(tg_id=user.id, name=user.username)

        if not user_obj.is_active:
            await bot.send_message(
                entity=event.peer_id,
                message="К сожалению ваша пробная подписка окончена",
            )
        else:
            if created:
                user_obj.fin_time = datetime.now().replace(
                    tzinfo=timezone(timedelta(hours=3))) + timedelta(
                    hours=72)  # NOTE ОГРАНИЧЕНИЕ ПО ВРЕМЕНИ hours=72
                user_obj.save()

            await bot.send_message(
                entity=event.peer_id,
                message="Особенности пробной подписки:"
                        "\n3-дневная пробная версия позволяет вам полностью оценить все преимущества Makepost_bot.\n"
                        "\nГенерируйте до 3 постов в день, испытывая разнообразие функционала и качество генерируемого контента.\n"
                        "\nПерегенерация постов до 3 раз на случай, если результат не соответствует вашим ожиданиям, вы можете изменить его, чтобы добиться идеального поста.\n"
                        "\nИспользуйте Makepost_bot, чтобы ваши сообщения в социальных сетях всегда были яркими и запоминающимися, а ваше присутствие – стабильным и эффективным. Попробуйте сейчас и убедитесь в преимуществах автоматизации контента с Makepost_bot!",
                buttons=main_menu,
            )
    else:
        await bot.send_message(
            entity=event.peer_id,
            message="К сожалению в боте сейчас слишком много человек, мы вам сообщим как появятся места", #NOTE не сообщим)
        )


# каналы
@bot.on(events.NewMessage(pattern="Мои каналы"))
async def ch_menu(event):
    user = TgUser.objects.get(tg_id=str(event.peer_id.user_id))
    if not is_active(user):
        return

    buttons = [KeyboardButtonRow(
        [
            KeyboardButton(
                text="Посмотреть каналы",
            ),

        ]
    ), KeyboardButtonRow(
        [
            KeyboardButton(
                text="Добавить канал",
            )
        ]
    ), KeyboardButtonRow(
        [
            KeyboardButton(
                text="Удалить канал",
            )
        ]
    ), KeyboardButtonRow(
        [
            KeyboardButton(
                text="Назад",
            )
        ]
    )]

    inline_buttons = ReplyKeyboardMarkup(buttons)

    await bot.send_message(
        entity=event.peer_id, message="Эта функция позволяет вам легко управлять каналами, в которые будут публиковаться посты. \n \nВыберите пункт меню:", buttons=inline_buttons
    )


@bot.on(events.NewMessage(pattern="Посмотреть каналы"))
async def get_ch(event):
    buttons = []
    user = TgUser.objects.get(tg_id=str(event.peer_id.user_id))
    if not is_active(user):
        return
    for i in MyChannel.objects.filter(tg_id=user):
        buttons.append(KeyboardButtonRow([KeyboardButtonUrl(text=i.name, url=i.name)]))
    if not buttons:
        buttons.append(
            KeyboardButtonRow(
                [KeyboardButtonCallback(text="Тут пусто(", data=bytes("no", "utf-8"))]
            )
        )
    inline_buttons = ReplyInlineMarkup(buttons)

    await bot.send_message(
        entity=event.peer_id, message="Твои каналы:", buttons=inline_buttons
    )


@bot.on(events.NewMessage(pattern="Добавить канал"))
async def add_ch(event):
    k = True
    user = TgUser.objects.get(tg_id=str(event.peer_id.user_id))
    if not is_active(user):
        return
    while k:
        async with bot.conversation(event.peer_id) as conv:
            try:
                await conv.send_message("Введите ссылку на ваш канал в котором вы хотите публиковать посты")
                channel = await conv.get_response(timeout=600)
                await user_bot.client(JoinChannelRequest(channel.message))
                user = TgUser.objects.get(tg_id=str(event.peer_id.user_id))
                ch_obj, created = MyChannel.objects.get_or_create(tg_id=user,
                                                                  name=channel.message)
                k = False
                if not created:
                    await conv.send_message("Такой канал уже есть. попробуй еще")
                    k = True
                    await conv.cancel_all()
                else:
                    await conv.send_message(
                        "Канал успешно добавлен. Пожалуйста дайте права админитратора боту TestBot в вашем канале, иначе он не будет работать.")
                    await conv.cancel_all()
            except ValueError as e:
                pattern = re.compile(
                    "Посмотреть каналы|Добавить канал|Удалить канал|Назад"
                )
                pattern.match(channel.message)
                if pattern.match(channel.message):
                    await conv.cancel_all()
                    break
                logging.error(e, exc_info=True)
                await conv.send_message("Не знаю такого канала, возможно это закрытый канал, попробуй еще раз")
                await conv.cancel_all()

            except asyncio.exceptions.TimeoutError as e:
                await conv.send_message("Что-то вы долго, нажмите кнопку еще раз")
                logging.error(e, exc_info=True)
                k = False
                await conv.cancel_all()

            except Exception as e:
                await conv.send_message("Что-то не то")
                logging.error(e, exc_info=True)
                k = False
                await conv.cancel_all()


@bot.on(events.NewMessage(pattern="Удалить канал"))
async def del_ch(event):
    user = TgUser.objects.get(tg_id=str(event.peer_id.user_id))
    if not is_active(user):
        return
    if is_free:
        buttons = []
        for i in MyChannel.objects.filter(tg_id=user):
            buttons.append(
                KeyboardButtonRow(
                    [
                        KeyboardButtonCallback(
                            text=i.name, data=bytes(str(i.id) + "_del", "utf-8")
                        )
                    ]
                )
            )
        if not buttons:
            buttons.append(
                KeyboardButtonRow(
                    [KeyboardButtonCallback(text="Тут пусто(", data=bytes("no", "utf-8"))]
                )
            )
        inline_buttons = ReplyInlineMarkup(buttons)
        await bot.send_message(
            entity=event.peer_id,
            message="Выберите канал для удаления:",
            buttons=inline_buttons,
        )
    else:
        await bot.send_message(
            entity=event.peer_id,
            message="Вы не можете выполнять удаление, пока выполняется генерация",
        )


@bot.on(events.CallbackQuery(pattern="^\d*_del"))
async def del_this_ch(event):
    await client.edit_message(event.original_update.user_id, event.original_update.msg_id, buttons=None)
    ch_id = event.original_update.data.decode("utf-8")
    ch_id = ch_id.replace("_del", "")
    ch = MyChannel.objects.get(id=ch_id)
    user = TgUser.objects.get(tg_id=event.original_update.user_id)

    if not is_active(user):
        return

    async with bot.conversation(event.original_update.user_id) as conv:
        await conv.send_message(
            f"Вы уверены что хотите удалить канал - {ch.name}. Напишите в ответ Да. "
        )
        try:
            ans = await conv.get_response(timeout=600)
            if ans.message == "Да" or ans.message == "да":
                ch.delete()
                await user_bot.client(LeaveChannelRequest(ch.name))
                await conv.send_message("Канал был успешно удален")
                await conv.cancel_all()
            else:
                await conv.send_message("Видимо вы передумали")
                await conv.cancel_all()
        except asyncio.exceptions.TimeoutError as e:
            await conv.send_message("Что-то вы долго, нажмите кнопку еще раз")
            logging.error(e, exc_info=True)
            await conv.cancel_all()


def helper_done_callback(event, mes, ch, task):
    user = TgUser.objects.get(tg_id=str(event.original_update.user_id))
    global is_free

    if task.exception():
        try:
            task.result()
        except Exception as e:
            asyncio.run_coroutine_threadsafe(
                bot.send_message(
                    entity=event.original_update.user_id,
                    message=f"Ошибка, попробуйте еще раз",
                ),
                loop=client.loop,
            )
            logging.exception(f"Task {task} failed with exception {e}")


    else:
        try:
            answer, url = task.result()

            user.num_posts = user.num_posts + 1
            user.save()

            mes_dict = mes.to_dict()
            del mes_dict["date"]
            mes_dict["message"] = mes_dict["message"].replace('\xa0', ' ')
            mes_dict["message"] = mes_dict["message"].replace('"', '')

            post_obj = Post.objects.create(user=user, channel=ch, original=mes_dict, rewrite=answer,
                                           img=url)
            buttons = [KeyboardButtonRow(
                [KeyboardButtonCallback(text="Опубликовать", data=bytes(str(post_obj.id) + "_send", "utf-8"))]
            ), KeyboardButtonRow(
                [KeyboardButtonCallback(text="Перегенерировать текст", data=bytes(str(post_obj.id) + "_text", "utf-8"))]
            ), KeyboardButtonRow(
                [KeyboardButtonCallback(text="Перегенерировать картинку", data=bytes(str(post_obj.id) + "_img", "utf-8"))]
            )]

            inline_buttons = ReplyInlineMarkup(buttons)
            asyncio.ensure_future(
                bot.send_message(entity=event.original_update.user_id, message=answer, file="image.jpg",
                                 force_document=False,
                                 parse_mode="html",
                                 buttons=inline_buttons)

            )

            is_free = True
        except Exception as e:
            asyncio.run_coroutine_threadsafe(
                bot.send_message(
                    entity=event.original_update.user_id,
                    message=f"Ошибка, попробуйте еще раз",
                ),
                loop=client.loop,
            )
            logging.exception(f"Task {task} failed with exception {e}")


def again_done_callback(event, post, task):
    user = TgUser.objects.get(tg_id=str(event.original_update.user_id))
    action = event.original_update.data.decode("utf-8")
    global is_free

    if task.exception():
        try:
            task.result()
        except Exception as e:
            asyncio.run_coroutine_threadsafe(
                bot.send_message(
                    entity=event.original_update.user_id,
                    message=f"Ошибка, попробуйте еще раз",
                ),
                loop=client.loop,
            )
            logging.exception(f"Task {task} failed with exception {e}")


    else:
        try:
            answer, url = task.result()
            buttons = [KeyboardButtonRow(
                [KeyboardButtonCallback(text="Опубликовать", data=bytes(str(post.id) + "_send", "utf-8"))]
            ), KeyboardButtonRow(
                [KeyboardButtonCallback(text="Перегенерировать текст", data=bytes(str(post.id) + "_text", "utf-8"))]
            ), KeyboardButtonRow(
                [KeyboardButtonCallback(text="Перегенерировать картинку", data=bytes(str(post.id) + "_img", "utf-8"))]
            )]
            inline_buttons = ReplyInlineMarkup(buttons)

            post.rewrite = answer
            post.img = url
            post.again = post.again + 1

            asyncio.run_coroutine_threadsafe(
                bot.send_message(entity=event.original_update.user_id, message=answer, file="image.jpg",
                                 force_document=False,
                                 parse_mode="html", buttons=inline_buttons), loop=client.loop,
            )
            if post.again_post_id is None:
                post.again_post_id = str(event.original_update.msg_id)
            else:
                post.again_post_id = str(post.again_post_id) + "," + str(event.original_update.msg_id)
            post.save()
            is_free = True
        except Exception as e:
            asyncio.run_coroutine_threadsafe(
                bot.send_message(
                    entity=event.original_update.user_id,
                    message=f"Ошибка, попробуйте еще раз",
                ),
                loop=client.loop,
            )
            logging.exception(f"Task {task} failed with exception {e}")


@bot.on(events.NewMessage(pattern="Создать пост"))
async def write_post(event):
    user = TgUser.objects.get(tg_id=str(event.peer_id.user_id))
    if not is_active(user):
        return
    if is_free:
        buttons = []

        for i in MyChannel.objects.filter(tg_id=user):
            buttons.append(
                KeyboardButtonRow(
                    [
                        KeyboardButtonCallback(
                            text=i.name, data=bytes(str(i.id) + "_write", "utf-8")
                        )
                    ]
                )
            )
        if not buttons:
            buttons.append(
                KeyboardButtonRow(
                    [KeyboardButtonCallback(text="Тут пусто(", data=bytes("no", "utf-8"))]
                )
            )
        inline_buttons = ReplyInlineMarkup(buttons)

        await bot.send_message(
            entity=event.peer_id,
            message="Выбери канал для которого хотите написать пост:",
            buttons=inline_buttons,
        )


@bot.on(events.CallbackQuery(pattern="^\d*_write"))
async def write_this(event):
    user = TgUser.objects.get(tg_id=str(event.original_update.user_id))
    if not is_active(user):
        return
    try:
        await client.edit_message(event.original_update.user_id, event.original_update.msg_id, buttons=None)
    except Exception as e:
        logging.error(e, exc_info=True)
    global is_free
    if is_free:
        ch_id = event.original_update.data.decode("utf-8")
        ch_id = ch_id.replace("_write", "")
        ch = MyChannel.objects.get(id=ch_id)

        admin = await user_bot.check_admin(ch)
        if not admin:
            await bot.send_message(
                entity=event.original_update.user_id,
                message="Бот не является администратором канала, пожалуйста добавьте TestBot в администраторы.")
            return

        if user.num_posts >= 3:
            await bot.send_message(entity=event.original_update.user_id,
                                   message="Вы превысили лимит в день")
            return

        keyboard_buttons = ReplyKeyboardMarkup(
            [
                KeyboardButtonRow(
                    [
                        KeyboardButton(text="Назад"),
                    ]
                )
            ], resize=True)

        async with bot.conversation(event.original_update.user_id) as conv:
            try:
                await conv.send_message(
                    "Теперь вы можете создавть посты для канала. Ограничение - 3 в день. Напишите текст для рерайта",
                    buttons=keyboard_buttons)
                k = True
                while k:
                    mes = await conv.get_response(timeout=600)
                    pattern = re.compile(
                        "Назад"
                    )
                    pattern.match(mes.message)
                    if pattern.match(mes.message):
                        k = False
                        await conv.cancel()

                    if is_free:
                        await conv.send_message(
                            "Подождите, пост генерируется. После генерации вы сможете выполнить повторную генерацию 3 раза.")

                        is_free = False

                        fut = user_bot.add_task(user_bot.gen(mes.to_dict()))
                        fut.add_done_callback(functools.partial(helper_done_callback, event, mes, ch))
                    else:
                        await conv.send_message(
                            "Уже идет генерация поста, подождите")

                await conv.cancel_all()

            except Exception as e:
                await bot.send_message(entity=event.original_update.user_id, message="Возвращаем вас в главное меню",
                                       buttons=main_menu)
                logging.error(e, exc_info=True)
                await conv.cancel_all()


@bot.on(events.CallbackQuery(pattern="^\d*_text"))
async def again_text(event):
    try:
        user = TgUser.objects.get(tg_id=str(event.original_update.user_id))
        global is_free
        if is_free:
            p_id = event.original_update.data.decode("utf-8")
            p_id = p_id.replace("_text", "")
            post = Post.objects.get(id=p_id)
            if post.again >= 3:
                await bot.send_message(entity=event.original_update.user_id, message="Превышен лимит повторной генерации")
            else:
                await bot.send_message(entity=event.original_update.user_id, message="Подождите, идет генерация")

                is_free = False

                fut = user_bot.add_task(user_bot.gen_text(post))
                fut.add_done_callback(functools.partial(again_done_callback, event, post))
    except Exception as e:
        asyncio.run_coroutine_threadsafe(
            bot.send_message(
                entity=event.original_update.user_id,
                message=f"Ошибка, попробуйте еще раз",
            ),
            loop=client.loop,
        )
        logging.exception(f"Task failed with exception {e}")


@bot.on(events.CallbackQuery(pattern="^\d*_img"))
async def again_img(event):
    try:
        user = TgUser.objects.get(tg_id=str(event.original_update.user_id))
        global is_free
        if is_free:
            p_id = event.original_update.data.decode("utf-8")
            p_id = p_id.replace("_img", "")
            post = Post.objects.get(id=p_id)
            if post.again >= 3:
                await bot.send_message(entity=event.original_update.user_id, message="Превышен лимит повторной генерации")
            else:
                await bot.send_message(entity=event.original_update.user_id, message="Подождите, идет генерация")

                is_free = False

                fut = user_bot.add_task(user_bot.gen_img(post))
                fut.add_done_callback(functools.partial(again_done_callback, event, post))
    except Exception as e:
        asyncio.run_coroutine_threadsafe(
            bot.send_message(
                entity=event.original_update.user_id,
                message=f"Ошибка, попробуйте еще раз",
            ),
            loop=client.loop,
        )
        logging.exception(f"Task  failed with exception {e}")


@bot.on(events.CallbackQuery(pattern="^\d*_send"))
async def send_post(event):
    try:
        user = TgUser.objects.get(tg_id=str(event.original_update.user_id))
        p_id = event.original_update.data.decode("utf-8")
        p_id = p_id.replace("_send", "")
        post = Post.objects.get(id=p_id)
        if not is_active(user):
            return
        if post.again_post_id is not None:
            mas_id = post.again_post_id.split(",")
            for i in mas_id:
                await client.edit_message(event.original_update.user_id, int(i), buttons=None)
        await client.edit_message(event.original_update.user_id, event.original_update.msg_id, buttons=None)

        if is_free:
            await user_bot.send_post(post)
            await bot.send_message(entity=event.original_update.user_id, message="Пост успешно опубликован")
    except Exception as e:
        asyncio.run_coroutine_threadsafe(
            bot.send_message(
                entity=event.original_update.user_id,
                message=f"Ошибка, попробуйте еще раз",
            ),
            loop=client.loop,
        )
        logging.exception(f"Task failed with exception {e}")


@bot.on(events.NewMessage(pattern="Оставить отзыв"))
async def send_feedback(event):
    async with bot.conversation(event.peer_id) as conv:
        try:
            await conv.send_message("Напишите отзыв о боте в свободной форме.")
            feedback = await conv.get_response(timeout=600)
            pattern = re.compile(
                "Мои каналы|Доноры|Создать пост|Сообщение об ошибках|Оставить отзыв"
            )
            pattern.match(feedback.message)
            if pattern.match(feedback.message):
                await conv.cancel()
            await conv.send_message(f"Ваш отзыв:\n {feedback.message} \nОтправить отзыв? Напишите в ответ Да")
            ans = await conv.get_response(timeout=200)
            user = TgUser.objects.get(tg_id=str(event.peer_id.user_id))

            if ans.message == "Да" or ans.message == "да":
                email_sender.send_email(text=feedback.message, user_obj=user, subject=event.message.message)
                await conv.send_message("Спасибо, за ваш отзыв")
                await conv.cancel()
            else:
                await conv.send_message("Видимо вы передумали")
                await conv.cancel()

        except ValueError as e:
            logging.error(e, exc_info=True)
            await conv.send_message("Не понимаю вас")
            await conv.cancel_all()

        except asyncio.exceptions.TimeoutError as e:
            await conv.send_message("Что-то вы долго, нажмите кнопку еще раз")
            logging.error(e, exc_info=True)
            await conv.cancel_all()

        except Exception as e:
            await conv.send_message("Функция не работает, мы исправим в ближайшее время(")
            logging.error(e, exc_info=True)
            await conv.cancel_all()


@bot.on(events.NewMessage(pattern="Сообщение об ошибках"))
async def send_error(event):
    async with bot.conversation(event.peer_id) as conv:
        try:
            await conv.send_message("Напишите подробно в чем была ошибка")
            error = await conv.get_response(timeout=600)
            pattern = re.compile(
                "Мои каналы|Доноры|Создать пост|Сообщение об ошибках|Оставить отзыв"
            )
            if pattern.match(error.message):
                await conv.cancel()
            else:
                await conv.send_message(f"Ваш текст:\n {error.message} \nОтправить? Напишите в ответ Да")
                ans = await conv.get_response(timeout=200)
                user = TgUser.objects.get(tg_id=str(event.peer_id.user_id))

                if ans.message == "Да" or ans.message == "да":
                    email_sender.send_email(text=error.message, user_obj=user, subject=event.message.message)
                    await conv.send_message("Спасибо, мы исправим данную ошибку")
                    await conv.cancel()
                else:
                    await conv.send_message("Видимо вы передумали")
                    await conv.cancel()

        except ValueError as e:
            logging.error(e, exc_info=True)
            await conv.send_message("Не понимаю вас")
            await conv.cancel_all()

        except asyncio.exceptions.TimeoutError as e:
            await conv.send_message("Что-то вы долго, нажмите кнопку еще раз")
            logging.error(e, exc_info=True)
            await conv.cancel_all()

        except Exception as e:
            await conv.send_message("Функция не работает, мы исправим в ближайшее время(")
            logging.error(e, exc_info=True)
            await conv.cancel_all()


def main():
    client.run_until_disconnected()


if __name__ == "__main__":
    main()
