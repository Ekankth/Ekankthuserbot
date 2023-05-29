import asyncio
import os
import sys
import time
import traceback
from io import BytesIO, StringIO
from getpass import getuser
from shutil import which

from pyrogram import Client, filters
from pyrogram.errors import MessageNotModified
from pyrogram.enums import ParseMode

from pyUltroid import LOGS, udB
from ..helper import _HANDLERS, _AUTH_USERS


# ~~~~~~~~~~~~~~~~~~~~ Eval ~~~~~~~~~~~~~~~~~~~~~~~~~~


async def apexec(code, client, message):
    exec(
        f"async def __aexec(client, message): "
        + "\n  app = client"
        + "\n  chat = message.chat.id"
        + "\n  m = message"
        + "\n  p = print"
        + "\n  rm = reply = message.reply_to_message \n"
        + "".join(f"\n  {l}" for l in code.split("\n"))
    )
    return await locals()["__aexec"](client, message)


@Client.on_message(
    filters.command("eval", prefixes=_HANDLERS) & filters.user(_AUTH_USERS)
)
async def _eval(client, m):
    try:
        cmd = m.text.split(maxsplit=1)[1]
    except IndexError:
        return await m.reply_text("Give Command as well :)", quote=True)

    status = await m.reply_text("`Processing...`", quote=True)
    old_stderr = sys.stderr
    old_stdout = sys.stdout
    redirected_output = sys.stdout = StringIO()
    redirected_error = sys.stderr = StringIO()
    stdout, stderr, exc = None, None, None
    try:
        await apexec(cmd, client, m)
    except Exception:
        exc = traceback.format_exc()
    stdout = redirected_output.getvalue()
    stderr = redirected_error.getvalue()
    sys.stdout = old_stdout
    sys.stderr = old_stderr
    evaluation = ""
    if exc:
        evaluation = exc
    elif stderr:
        evaluation = stderr
    elif stdout:
        evaluation = stdout
    else:
        evaluation = "Success"

    if len(cmd + evaluation) < 4050:
        final_output = f"<b>></b>  <code>{cmd}</code> \n\n<b>>></b>  <code>{evaluation.strip()}</code>"
        return await status.edit(final_output, parse_mode=ParseMode.HTML)

    # output greater than 4096 chars..
    final_output = f">  {cmd} \n\n>>  {evaluation.strip()}"
    with BytesIO(final_output.encode()) as out_file:
        out_file.name = "pyro_eval.txt"
        await m.reply_document(
            document=out_file,
            caption=f"<code>{cmd[:1024]}</code>",
            parse_mode=ParseMode.HTML,
            disable_notification=True,
        )
    await status.delete()


# ~~~~~~~~~~~~~~~~~~~~ Bash ~~~~~~~~~~~~~~~~~~~~~~~~~~~~


async def bash(cmd):
    process = await asyncio.create_subprocess_shell(
        cmd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
        executable=which("bash"),
    )
    stdout, stderr = await process.communicate()
    err = stderr.decode(errors="replace").strip() or None
    out = stdout.decode(errors="replace").strip()
    return out, err


@Client.on_message(
    filters.command(["bash", "term"], prefixes=_HANDLERS) & filters.user(_AUTH_USERS)
)
async def _terminal(client, m):
    """run commands in bash terminal"""
    try:
        cmd = m.text.split(maxsplit=1)[1]
    except IndexError:
        return await m.reply_text("`Give some cmd too..`", quote=True)

    msg = await m.reply_text("`Processing ...`", quote=True)
    OUT = f"**{getuser()} ~** `{cmd}` \n\n"
    stdout, stderr = await bash(cmd)
    err, out = "", ""
    if stderr:
        err = f"**error ~** \n`{stderr}` \n\n"
    out = f"**result ~** \n`{stdout if stdout else 'Success'}`"
    OUT += err + out
    if len(OUT) < 4096:
        return await msg.edit(OUT)

    # output greater than 4096..
    OUT = OUT.replace("`", "").replace("**", "").replace("__", "")
    with BytesIO(OUT.encode()) as out_file:
        out_file.name = "pyro_bash.txt"
        await m.reply_document(
            document=out_file,
            caption=f"<code>{cmd[:1024]}</code>",
            disable_notification=True,
            parse_mode=ParseMode.HTML,
        )
    await msg.delete()
