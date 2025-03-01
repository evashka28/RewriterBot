import json
import os
import re
import string
import time
import logging

import openai

from timeout_function_decorator import timeout
import tiktoken

# from langchain.agents import load_tools, initialize_agent
from langchain.chains import LLMChain
from langchain.chat_models import ChatOpenAI
from langchain_core.prompts import PromptTemplate
from openai import APIError
from pydantic import BaseModel, Field

# from langchain.llms import OpenAI
from langchain.output_parsers import (
    PydanticOutputParser,
    OutputFixingParser,
)
from langchain.memory import ConversationBufferMemory

from tgparse.external_services.telegram_bot import MyCustomException

logging.basicConfig(
    level=logging.INFO,
    filename="../bot_log.log",
    format="%(asctime)s - %(module)s - %(levelname)s - %(funcName)s: %(lineno)d - %(message)s",
    datefmt="%H:%M:%S",
)
analitic_time = 60
writer_time = 120
sh_time = 90
url_time = 60
image_time = 60
sum_time = 30
pr_time = 30


def Error_Handler(func):
    def Inner_Function(*args, **kwargs):
        _delay = 2
        all_time = 0
        max_time = 20
        while all_time < max_time:
            start_time = time.time()
            try:
                result = func(*args, **kwargs)
                return result
            except APIError:
                logging.error("API Error")
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
        logging.error("После перезапуска, программа все еще не работает")
        raise MyCustomException()

    return Inner_Function


class AIContentGenerator:
    def __init__(self):
        self.encoding = tiktoken.encoding_for_model("gpt-3.5-turbo-1106")
        self.memory = ConversationBufferMemory()
        self.model_4_preview = "gpt-4-1106-preview"
        self.model_35_turbo = "gpt-3.5-turbo-0613" #TODO чекнуть версию с которой работает
        self.temperature = 0.0
        self.llm_35 = ChatOpenAI(model_name=self.model_35_turbo, temperature=self.temperature)
        self.llm_4 = ChatOpenAI(
            model_name=self.model_4_preview, temperature=self.temperature, max_tokens=1000
        )
        openai.api_key = os.getenv("OPENAI_API_KEY")

        class Analys(BaseModel):
            description: str = Field(description="краткое описание новости")
            recommendations: str = Field(description="рекомендации для написание поста")

        parser = PydanticOutputParser(pydantic_object=Analys)
        self.fix_parser = OutputFixingParser.from_llm(parser=parser, llm=self.llm_35)

        self.news_analitic_template = """
                    Ты в роле новостного аналитика. Твоя задача провести суммаризацию новости
                    для написание поста в канал специалистом SMM. Не сокращай элементы списков!
                    Также предоставь рекомендации по написанию поста.
                    Избавься от всех ссылок. НЕ ГОВОРИ про визуализацию.
                    Верни ответ в формате словаря со следующими ключами:
                    description - краткое описание новости 
                    recommendations - рекомендации для написание поста

                    Текст новости:
                    -----
                    {text}
                    -----
                    
                    Формат: 
                    -----
                    {format_instructions}
                    -----
                    """

        self.prompt_analitic = PromptTemplate(
            input_variables=["text"],
            template=self.news_analitic_template,
            partial_variables={"format_instructions": parser.get_format_instructions()},
        )

        self.post_righter_template = """
                    Ты специалист SMM, который публикует посты в новостной канал. 
                    Твоя задача составить текст поста МЕНЕЕ 800 символов по краткому содержанию новости и рекомендациям по написанию.
                    Избегай повторяющихся фраз и неестественного размещения ключевых слов.
                    Пиши просто и понятно. Избегай слишком длинных предложений.
                    Пиши в третьем лице, НИКОГДА НЕ ИСПОЛЬЗУЙ 'МЫ', 'НАШ'!
                    Обязательно разбей текст на несколько параграфов.
                    Добавь стикеры.
                    Логическая ЗАКОНЧЕННОСТЬ каждого предложения.
                    Проверь количество знаков их МЕНЬШЕ 800!
                    Добавь в конце хэштеги! Проверь наличие хэштегов.
                    Вывод: Только написанный тобой текст
                    
                    Содержание новости:
                    -----
                    {question}
                    -----

                    Рекомендации:
                    -----
                    {query}
                    -----
                    """

        self.prompt_righter = PromptTemplate(
            input_variables=["question", "query", "urls"],
            template=self.post_righter_template,
        )

        self.add_url_template = """
                    Тебе дано два текста один из них содержит ссылки, а второй нет.
                    Твоя задача правильно вставить КАЖДУЮ ссылку внутрь второго текст.
                    Чтобы вставить ссылку в слово используй "<a href='ссылка'> слово </a>".
                    Если НЕ ЗНАЕШЬ куда вставить ссылку,добавь в конце текста слово "Источники:" и после него ссылка.
                    Каждая ссылка используется ОДИН раз!
                    Выведи исправленный второй текст.
                    

        Текст 1:
        -----
        {text1}
        -----
        
        
        Текст 2:
        -----
        {text2}
        -----
        """

        self.prompt_add_url = PromptTemplate(
            input_variables=["text", "text2"],
            template=self.add_url_template,
        )

        self.news_type_template = """
        Определи является ли представленное сообщение новостью или рекламой. В ответ напиши одно слово: реклама или новость или хз. ХЗ если не можешь определить тип сообщения


        Сообщение:
        -----
        {text}
        -----
        """

        self.prompt_news_type = PromptTemplate(
            input_variables=["text"],
            template=self.news_type_template,
        )

        self.img_prompt_generate_template = """
                Generate a prompt less than 500 symbols to generate an image based on the following description: {image_desc}.
                Изображение должно быть МАКСИМАЛЬНО реалистичным.
                Photo in realistic style. Photo from magazine
                Изображение НЕ ДОЛЖНО содержать текст или слова или описания, только картинки. 
                Image only without typography.
                DON'T USE text-generating elements, just pure visual representation
                No text!"
                """

        self.prompt_generate_img_prompt = PromptTemplate(
            input_variables=["image_desc"],
            template=self.img_prompt_generate_template,
        )
        self.prompt_sum = PromptTemplate(
            input_variables=["text"],
            template="Write SHORTLY a general topic of the text:{text}. Write a theme in one sentence or less. ",
        )
        self.prompt_short = PromptTemplate(
            input_variables=["text"],
            template="Сократи текст так, чтобы в нем стало 900 символов. Если в нем содержится слишком длинный список - сократи его. Проверь что упоминания о количестве элементов списка- правильные. Текст: {text}",
        )

    def num_tokens(self, text: str) -> int:
        num_tokens = len(self.encoding.encode(text))
        return num_tokens

    def right_url(self, text1: str, text2: str) -> int | str:
        conv_add_url = LLMChain(llm=self.llm_4, prompt=self.prompt_add_url, verbose=True)
        add_url = Error_Handler(
            timeout(analitic_time, RuntimeError)(conv_add_url.run)
        )  # декорирование
        out = add_url(text1=text1, text2=text2)
        return out

    def rewrite_message(self, text: str) -> int | str:
        print("4")
        conv_analitic = LLMChain(
            llm=self.llm_35, prompt=self.prompt_analitic, verbose=True
        )
        conv_writer = LLMChain(
            llm=self.llm_4, prompt=self.prompt_righter, verbose=True
        )
        conv_short = LLMChain(llm=self.llm_4, prompt=self.prompt_short, verbose=True)
        analysis = Error_Handler(
            timeout(analitic_time, RuntimeError)(conv_analitic.run)
        )  # декорирование
        out = analysis(text)  # вызов аналитика
        try:
            out_right = self.right(out)  # проверка форматирования
            out_dict = json.loads(out, strict=False)
        except Exception as e:
            logging.error(e, exc_info=True)
            out = self.fix_parser.parse(out)
            out_right = self.right(out)  # проверка форматирования
            out_dict = self.to_dict(out_right)

        writer = Error_Handler(
            timeout(writer_time, RuntimeError)(conv_writer.run)
        )  # декорирование
        out = writer(
            question=out_dict["description"], query=out_dict["recommendations"]
        )  # вызов писателя
        while len(out) > 980:
            short = Error_Handler(
                timeout(sh_time, RuntimeError)(conv_short.run)
            )  # декорирование
            out = short(out)  # укорачивание
        answer = self.right_format(out)
        return answer

    def img_generate(self, text: str) -> str:
        res = openai.Image.create(
            model="dall-e-3",
            prompt=text,
            quality="standard",
            n=1,
            size="1024x1024",
        )
        return res["data"][0]["url"]

    def new_image(self, text: str) -> str:
        conv_img_prompt = LLMChain(llm=self.llm_4, prompt=self.prompt_generate_img_prompt)
        conv_sum = LLMChain(llm=self.llm_4, prompt=self.prompt_sum)
        text_sum = Error_Handler(
            timeout(sum_time, RuntimeError)(conv_sum.run)
        )  # декорирование
        summ = text_sum(text)  # суммаризация
        i = 0
        while i < 3:
            try:
                get_img_prompt = Error_Handler(
                    timeout(pr_time, RuntimeError)(conv_img_prompt.run)
                )  # декорирование
                img_prompt = get_img_prompt(summ)  # генерация промпта
                generate_img = Error_Handler(
                    timeout(image_time, RuntimeError)(self.img_generate)
                )  # декорирование
                image_url = generate_img(img_prompt)  # генерация самого изображения (url)
                i = 4
                return image_url
            except Exception as e:
                i += 1
                logging.error(e, exc_info=True)

    @staticmethod
    def right_format(out: string) -> str:
        return re.sub("^\w+:", "", out)

    @staticmethod
    def right(out: string) -> str:
        reg = re.compile("{[^{}]+}")
        return reg.findall(out)[0]

    @staticmethod
    def to_dict(out: string) -> dict:
        dict_ = {}
        d = re.findall('"([^"]*)"', out)
        for i in range(0, len(d), 2):
            dict_[d[i]] = d[i + 1]#TODO тут был out of range
        return dict_
