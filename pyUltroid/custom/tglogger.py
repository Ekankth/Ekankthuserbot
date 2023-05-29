# Original Source : https://github.com/subinps/tglogging
# Modified to make compatible with Ultroid.
#
# first push: 24-09-2022, v0.7
# fixes: 23-01-2023, v0.8

import asyncio
from io import BytesIO
from logging import StreamHandler

from aiohttp import ClientSession

from ._loop import loop, run_async_task


_TG_MSG_LIMIT = 4000
_MAX_LOG_LIMIT = 12000
_PAYLOAD = {"disable_web_page_preview": True, "parse_mode": "Markdown"}


class TGLogHandler(StreamHandler):
    def __init__(self, chat, token):
        self.chat = chat
        self.__tgtoken = f"https://api.telegram.org/bot{token}"
        self.log_db = []
        self.current_log_msg = ""
        self.message_id = None
        self.is_active = False
        self._floodwait = False
        self.doc_message_id = None
        _PAYLOAD.update({"chat_id": chat})
        StreamHandler.__init__(self)

    async def _tg_logger(self):
        try:
            await asyncio.sleep(3)
            while self.log_db:
                await self.handle_logs(self.log_db.copy())
                await asyncio.sleep(8)
        finally:
            self.is_active = False

    def emit(self, record):
        msg = self.format(record)
        self.log_db.append("\n\n" + msg)
        if not (self.is_active or self._floodwait):
            self.is_active = True
            run_async_task(self._tg_logger, id="logger_task")

    def _splitter(self, logs):
        _log = []
        current = self.current_log_msg
        for l in logs:
            edit_left = _TG_MSG_LIMIT - len(current)
            if edit_left > len(l):
                current += l
            else:
                _log.append(current)
                current = l
        _log.append(current)
        return _log

    async def conditionX(self, log_msg):
        lst = self._splitter(log_msg)
        first_msg = lst.pop(0)
        if first_msg != self.current_log_msg:
            await self.edit_message(first_msg)
            await asyncio.sleep(8)
        for i in lst:
            await self.send_message(i)
            await asyncio.sleep(8)

    async def handle_logs(self, db):
        log_msgs = "".join(db)
        edit_left = _TG_MSG_LIMIT - len(self.current_log_msg)
        if edit_left > len(log_msgs):
            await self.edit_message(self.current_log_msg + log_msgs)
        elif any(len(i) > _TG_MSG_LIMIT for i in db) or len(log_msgs) > _MAX_LOG_LIMIT:
            await self.send_file(log_msgs)
        else:
            await self.conditionX(db)
        for _ in range(len(db)):
            self.log_db.pop(0)

    async def send_request(self, url, payload):
        async with ClientSession() as session:
            async with session.request("POST", url, json=payload) as response:
                return await response.json()

    async def handle_floodwait(self, sleep):
        await asyncio.sleep(sleep)
        self._floodwait = False

    async def send_message(self, message):
        payload = _PAYLOAD.copy()
        message = message.lstrip("\n\n")
        payload["text"] = f"```{message}```"
        if ids := self.message_id or self.doc_message_id:
            payload["reply_to_message_id"] = ids
        res = await self.send_request(self.__tgtoken + "/sendMessage", payload)
        if res.get("ok"):
            self.message_id = int(res["result"]["message_id"])
            self.current_log_msg = message
            self.doc_message_id = None
        else:
            await self.handle_error(res)

    async def edit_message(self, message):
        if not self.message_id:
            return await self.send_message(message)
        payload = _PAYLOAD.copy()
        message = message.lstrip("\n\n")
        payload.update({"message_id": self.message_id, "text": f"```{message}```"})
        res = await self.send_request(self.__tgtoken + "/editMessageText", payload)
        self.current_log_msg = message
        if not res.get("ok"):
            await self.handle_error(res)

    async def send_file(self, logs):
        logs = logs.lstrip("\n\n")
        file = BytesIO(logs.encode())
        file.name = "tglogging.txt"
        url = self.__tgtoken + "/sendDocument"
        payload = _PAYLOAD.copy()
        payload["caption"] = "Too much logs, hence sending as file."
        if ids := self.message_id:
            payload["reply_to_message_id"] = ids
        files = {"document": file}
        payload.pop("disable_web_page_preview", None)
        async with ClientSession() as session:
            async with session.request(
                "POST", url, params=payload, data=files
            ) as response:
                res = await response.json()
        if res.get("ok"):
            self.doc_message_id = int(res["result"]["message_id"])
            self.current_log_msg = ""
            self.message_id = None
        else:
            await self.handle_error(res)

    async def handle_error(self, resp):
        error = resp.get("parameters", {})
        if not error:
            description = resp.get("description")
            if resp.get("error_code") in (401, 400) and description.startswith(
                ("Unauthorized", "Bad Request: message is not modified")
            ):
                return  # same message content
            elif resp.get("error_code") == 400 and any(
                i in description
                for i in (
                    "MESSAGE_ID_INVALID",
                    "Bad Request: message to edit not found",
                )
            ):
                self.message_id = None
                return  # deleted message
            print(f"Errors while updating TG logs: {resp}")
            return
        elif s := error.get("retry_after"):
            self._floodwait = True
            print(f"tglogger: floodwait of {s}s")
            run_async_task(self.handle_floodwait, s + s // 4, id="tglogger_floodwait")
