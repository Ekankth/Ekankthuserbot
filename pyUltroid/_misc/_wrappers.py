# Ultroid - UserBot
# Copyright (C) 2021-2022 TeamUltroid
#
# This file is a part of < https://github.com/TeamUltroid/Ultroid/ >
# PLease read the GNU Affero General Public License in
# <https://github.com/TeamUltroid/pyUltroid/blob/main/LICENSE>.

from asyncio import sleep

from telethon.errors import MessageDeleteForbiddenError, MessageNotModifiedError
from telethon.tl.custom import Message
from telethon.tl.types import MessageService, User


# edit or reply
async def eor(event, text=None, time=None, link_preview=False, edit_time=None, **args):
    reply_to = event.reply_to_msg_id or event
    if event.out and not isinstance(event, MessageService):
        if edit_time:
            await sleep(edit_time)
        if args.get("file") and not event.media:
            await event.delete()
            ok = await event.client.send_message(
                event.chat_id,
                text,
                link_preview=link_preview,
                reply_to=reply_to,
                **args,
            )
        else:
            try:
                ok = await event.edit(text, link_preview=link_preview, **args)
            except MessageNotModifiedError:
                ok = event
    else:
        ok = await event.client.send_message(
            event.chat_id, text, link_preview=link_preview, reply_to=reply_to, **args
        )

    if time:
        await sleep(time)
        return await ok.delete()
    return ok


# edit or delete
async def eod(event, text=None, **kwargs):
    kwargs["time"] = kwargs.get("time", 8)
    return await eor(event, text, **kwargs)


# try delete
async def _try_delete(event, log=False):
    try:
        return await event.delete()
    except MessageDeleteForbiddenError:
        pass
    except BaseException as er:
        if log:
            from . import LOGS

            LOGS.warning("Error while Deleting Message..", exc_info=True)


# copy message
async def copy_message(msg, to_chat, **kwargs):
    if isinstance(msg, Message) and not msg.action:
        try:
            if "caption" in kwargs:
                msg.text = kwargs.pop("caption")
            return await msg.client.send_message(to_chat, msg, **kwargs)
        except Exception:
            raise
    else:
        raise TypeError("Error: Invalid message type")


def get_message_link(self):
    if isinstance(self.chat, User):
        fmt = "tg://openmessage?user_id={user_id}&message_id={msg_id}"
        return fmt.format(user_id=self.chat_id, msg_id=self.id)
    if getattr(self.chat, "username", None):
        return f"https://t.me/{self.chat.username}/{self.id}"
    if self.chat_id:
        if str(self.chat_id).startswith(("-", "-100")):
            chat = int(str(self.chat_id).replace("-100", "").replace("-", ""))
        else:
            chat = self.chat_id
    elif self.chat and self.chat.id:
        chat = self.chat.id
    else:
        return
    return f"https://t.me/c/{chat}/{self.id}"


Message.message_link = property(get_message_link)

setattr(Message, "eor", eor)
setattr(Message, "try_delete", _try_delete)
setattr(Message, "copy", copy_message)
