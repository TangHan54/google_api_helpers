import base64
import smtplib
import mimetypes

from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email.mime.application import MIMEApplication
from email.mime.audio import MIMEAudio
from email.mime.image import MIMEImage

from googleapiclient import discovery

from google_api_helpers import creds


class Mail:
    def __init__(self):
        self.service = discovery.build("gmail", "v1", credentials=creds)

    def send_gmail(
        self,
        sender="",
        to=[],
        cc=[],
        bcc=[],
        subject="",
        message_text="",
        attachments=[],
    ):
        # create message object
        message = MIMEMultipart()
        message["from"] = sender
        message["to"] = ",".join(to)
        message["cc"] = ",".join(cc)
        message["bcc"] = ",".join(bcc)

        message["subject"] = subject

        msg = MIMEText(message_text, "html")
        message.attach(msg)
        for file in attachments:
            content_type, encoding = mimetypes.guess_type(file)

            if content_type is None or encoding is not None:
                content_type = "application/octet-stream"
            main_type, sub_type = content_type.split("/", 1)
            if main_type == "text":
                fp = open(file, "rb")
                msg = MIMEText(fp.read(), _subtype=sub_type)
                fp.close()
            elif main_type == "image":
                fp = open(file, "rb")
                msg = MIMEImage(fp.read(), _subtype=sub_type)
                fp.close()
            elif main_type == "audio":
                fp = open(file, "rb")
                msg = MIMEAudio(fp.read(), _subtype=sub_type)
                fp.close()
            else:
                fp = open(file, "rb")
                msg = MIMEBase(main_type, sub_type)
                msg.set_payload(fp.read())
                fp.close()
            filename = os.path.basename(file)
            msg.add_header("Content-Disposition", "attachment", filename=filename)
            message.attach(msg)

        message = {
            "raw": base64.urlsafe_b64encode(message.as_string().encode()).decode()
        }

        message = (
            self.service.users().messages().send(userId="me", body=message).execute()
        )
