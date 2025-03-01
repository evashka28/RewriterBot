import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email.mime.image import MIMEImage
from email import encoders
from email.header import Header

from dotenv import load_dotenv

load_dotenv()


class EmailSender:
    def __init__(self):
        load_dotenv()  # Load environment variables from a .env file
        self.my_email_pass = os.getenv("EMAIL_PASS_G")
        #self.from_email = 'uven4@mail.ru'
        self.from_email = 'evashka28@gmail.com'
        self.to_email = 'uven5@mail.ru'
        #self.server = smtplib.SMTP_SSL('smtp.mail.ru', 465)
        self.server = smtplib.SMTP('smtp.gmail.com', 25)
        self.server.starttls()

        self.server.login(self.from_email, self.my_email_pass)

    def disconnect(self):
        if self.server:
            self.server.quit()

    def send_email(self, text: str, user_obj,  subject: str):
        msg = MIMEMultipart()
        msg['From'] = self.from_email
        msg['To'] = self.to_email
        subject_text = f"{subject} {user_obj.name} id: {user_obj.tg_id}"
        #subject_text = subject
        msg['Subject'] = Header(subject_text, 'utf-8')

        msg.attach(MIMEText(text, 'plain', 'utf-8'))

        self.server.sendmail(self.from_email, self.to_email, msg.as_string())
        # self.disconnect()
        # TODO блин хз надо ли его вырубать

#email_sender = EmailSender()
#email_sender.send_email(text="bla bla",  subject="jogjoijg")

