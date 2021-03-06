import hashlib
import logging
import time
import requests
import json
from rasa.utils.common import raise_warning
from sanic import Blueprint, response
from sanic.request import Request
from typing import Text, List, Dict, Any, Callable, Awaitable, Iterable, Optional
from rasa.core.channels.channel import UserMessage, OutputChannel, InputChannel
from sanic.response import HTTPResponse
from rasa.core.channels.wechat_utils.receive import parse_xml, Msg
from rasa.core.channels.wechat_utils.reply import TextMsg, ImageMsg

logger = logging.getLogger(__name__)


class MessengerBot(OutputChannel):
    """A bot that uses wechat to communicate."""

    @classmethod
    def name(cls) -> Text:
        return "wechat"

    def __init__(
        self,
        wechat_secret: Optional[Text] = None,
        wechat_appid: Optional[Text] = None,
        automatic_mode: Optional[bool] = False,
    ) -> None:

        self.wechat_secret = wechat_secret
        self.wechat_appid = wechat_appid
        self.exp_time = 0
        self.access_token = ""
        self.automatic_mode = automatic_mode
        self.automatic_response = []
        super().__init__()

    async def get_token(self):
        if time.time() > self.exp_time:
            r = requests.get(
                "https://api.weixin.qq.com/cgi-bin/token?grant_type=client_credential&appid={0}&secret={1}".format(
                    self.wechat_appid, self.wechat_secret
                )
            )
            d = json.loads(r.text)
            self.access_token = d["access_token"]
            self.exp_time = time.time() + d["expires_in"] - 10
        return self.access_token

    def prepare_message(
        self, recipient_id: Text, bot_reply: Text, msgtype: Text
    ) -> Dict[Text, Any]:
        data = {
            "touser": recipient_id,
            "msgtype": msgtype,
            "text": {"content": bot_reply},
        }
        return data

    async def send(self, replyMsg: Dict[Text, Any]) -> None:
        """Sends a message to the recipient using the messenger client."""
        access_token = await self.get_token()
        url = "https://api.weixin.qq.com/cgi-bin/message/custom/send?access_token={}".format(
            access_token
        )
        send_response = requests.post(url, data=json.dumps(replyMsg))

        if send_response.status_code != requests.codes.ok:
            logger.error(
                "Error trying to send wechat message. Response: %s", send_response.text,
            )

    async def send_text_message(
        self, recipient_id: Text, text: Text, **kwargs: Any
    ) -> None:
        """Send a message through this channel."""
        for message_part in text.strip().split("\n\n"):
            if not self.automatic_mode:
                replyMsg = self.prepare_message(recipient_id, message_part, "Text")
                await self.send(replyMsg)
            else:
                self.automatic_response.append({"Text": text})

    async def send_image_url(
        self, recipient_id: Text, image: Text, **kwargs: Any
    ) -> None:
        """Sends an image. Default will just post the url as a string."""
        if not self.automatic_mode:
            replyMsg = self.prepare_message(recipient_id, image, "Image")
            await self.send(replyMsg)
        else:
            self.automatic_response.append({"Image": image})


class WechatInput(InputChannel):
    """Wechat input channel implementation. Based on the HTTPInputChannel."""

    @classmethod
    def name(cls) -> Text:
        return "wechat"

    @classmethod
    def from_credentials(cls, credentials: Optional[Dict[Text, Any]]) -> InputChannel:
        if not credentials:
            cls.raise_missing_credentials_exception()

        # pytype: disable=attribute-error
        return cls(
            credentials.get("appid"),
            credentials.get("verify"),
            credentials.get("secret"),
            credentials.get("customer_mode"),
        )
        # pytype: enable=attribute-error

    def __init__(
        self,
        wechat_appid: Text,
        wechat_verify: Text,
        wechat_secret: Text,
        customer_mode: bool,
    ) -> None:
        """Create a wechat input channel.

        Args:
            wechat_appid: wechat appid
            wechat_verify: wechat Verification string
                (can be chosen by yourself on webhook creation)
            wechat_secret: wechat application secret
            customer_mode: use customer to reply or not
        """
        self.wechat_appid = wechat_appid
        self.wechat_verify = wechat_verify
        self.wechat_secret = wechat_secret
        self.customer_mode = customer_mode

    def blueprint(
        self, on_new_message: Callable[[UserMessage], Awaitable[Any]]
    ) -> Blueprint:

        wechat_webhook = Blueprint("wechat_webhook", __name__)

        @wechat_webhook.route("/webhook", methods=["GET"])
        async def token_verification(request: Request) -> HTTPResponse:

            data = lambda x: request.args.get(x)
            signature = data("signature")
            timestamp = data("timestamp")
            nonce = data("nonce")
            echostr = data("echostr")
            token = self.wechat_verify
            list_ = [token, timestamp, nonce]
            list_.sort()
            sha1 = hashlib.sha1()
            sha1.update(list_[0].encode("utf-8"))
            sha1.update(list_[1].encode("utf-8"))
            sha1.update(list_[2].encode("utf-8"))
            hashcode = sha1.hexdigest()
            print("handle/GET func: hashcode, signature: ", hashcode, signature, token)
            if hashcode == signature:
                return response.text(echostr)
            else:
                logger.warning(
                    "Invalid wechat verify token! Make sure this matches "
                    "your webhook settings on the wechat app."
                )
                return response.text("failure, invalid token")

        @wechat_webhook.route("/webhook", methods=["POST"])
        async def webhook(request: Request) -> HTTPResponse:
            xmldata = request.body
            recMsg = parse_xml(xmldata)

            try:
                automatic_mode = not self.customer_mode

                out_channel = MessengerBot(
                    self.wechat_secret, self.wechat_appid, automatic_mode
                )

                user_msg = UserMessage(
                    text=recMsg.Content,
                    output_channel=out_channel,
                    sender_id=recMsg.FromUserName,
                    input_channel=self.name(),
                )

                await on_new_message(user_msg)

                # there is no customer, so use automatic reply instead.
                if not self.customer_mode:
                    contents = out_channel.automatic_response
                    if len(contents) > 1:
                        get_val = lambda x: list(x.values())[0]
                        joint_msg = " ".join([get_val(x) for x in contents])
                        content = {"Text": joint_msg}
                    else:
                        content = contents[0] if contents else {"Text": "Hello!"}

                    toUser = recMsg.FromUserName
                    fromUser = recMsg.ToUserName
                    if "Text" in content:
                        replyMsg = TextMsg(toUser, fromUser, content["Text"])
                    elif "Image" in content:
                        replyMsg = ImageMsg(toUser, fromUser, content["Image"])

                    return response.text(replyMsg.send())

            except Exception as e:
                logger.error(f"Exception when trying to handle message.{e}")
                logger.debug(e, exc_info=True)
                pass

            return response.text("success")

        return wechat_webhook






