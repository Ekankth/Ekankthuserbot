from time import time

from pyrogram import Client, filters
from pyrogram.raw.functions import Ping

from ..helper import _HANDLERS


# @Client.on_edited_message(filters.command("ping", prefixes=_HAN))
@Client.on_message(filters.command("ping", prefixes=_HANDLERS + ["/"]))
async def ping_pong(client, m):
    msg = await m.reply_text("`Pong!`", quote=True)
    start = time()
    await client.invoke(Ping(ping_id=0))
    end = round((time() - start) * 1000, 3)
    await msg.edit(f"**Pong !!** \n`{end} ms`")
