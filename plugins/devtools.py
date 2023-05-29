# Ultroid - UserBot
# Copyright (C) 2021-2022 TeamUltroid
#
# This file is a part of < https://github.com/TeamUltroid/Ultroid/ >
# PLease read the GNU Affero General Public License in
# <https://www.github.com/TeamUltroid/Ultroid/blob/main/LICENSE/>.

from . import get_help

__doc__ = get_help("help_devtools")

import inspect
import sys
import traceback
from io import BytesIO, StringIO
from os import remove
from pathlib import Path
from pprint import pprint
from random import choice

from telethon.utils import get_display_name

from pyUltroid import _ignore_eval
from pyUltroid.custom.multi_db import *
from pyUltroid.custom._transfer import pyroUL, pyroDL

from . import *

# Used for Formatting Eval Code, if installed
try:
    import black
except ImportError:
    black = None

try:
    from yaml import safe_load
except ImportError:
    from pyUltroid.fns.tools import safe_load

try:
    from telegraph import upload_file as uf
except ImportError:
    uf = None

from telethon.tl import functions

fn = functions


@ultroid_cmd(
    pattern="(sysinfo|neofetch)$",
)
async def _(e):
    xx = await e.eor(get_string("com_1"))
    x, y = await bash("neofetch|sed 's/\x1B\\[[0-9;\\?]*[a-zA-Z]//g' >> neo.txt")
    if y and y.endswith("NOT_FOUND"):
        return await xx.edit(f"Error: `{y}`")
    np = await asyncread("neo.txt")
    all_col = (await asyncread("resources/colorlist.txt")).splitlines()
    p = np.replace("\n\n", "")
    haa = await Carbon(code=p, file_name="neofetch", backgroundColor=choice(all_col))
    if isinstance(haa, dict):
        return await xx.edit(f"`{haa}`")
    await e.reply(file=haa)
    osremove("neo.txt")
    await xx.delete()


@ultroid_cmd(pattern="bash", fullsudo=True, only_devs=True)
async def _(event):
    carb, rayso, nolog, yamlf = False, False, False, False
    try:
        cmd = event.text.split(" ", maxsplit=1)[1]
        if cmd.split()[0] == "-c":  # --carbon
            cmd = cmd.split(maxsplit=1)[1]
            carb = True
        elif cmd.split()[0] == "-r":  # --rayso
            cmd = cmd.split(maxsplit=1)[1]
            rayso = True
        elif cmd.split()[0] == "-nl":
            cmd = cmd.split(maxsplit=1)[1]
            nolog = True
    except IndexError:
        return await event.eor(get_string("devs_1"), time=10)

    if not nolog:
        LOGS.debug(cmd)
    xx = await event.eor(get_string("com_1"))

    is_preview = any(
        (
            carb,
            rayso,
            udB.get_key("CARBON_ON_BASH"),
            udB.get_key("RAYSO_ON_BASH"),
        )
    )
    reply_to_id = event.reply_to_msg_id or event.id
    stdout, stderr = await bash(cmd, run_code=1)
    OUT = f"**☞ BASH\n\n• COMMAND:**\n`{cmd}` \n\n"
    err, out = "", ""
    if stderr:
        err = f"**• ERROR:** \n`{stderr}`\n\n"
    if stdout:
        if is_preview:
            colors = (await asyncread("resources/colorlist.txt")).splitlines()
            li = await Carbon(
                code=stdout,
                file_name="_bash",
                download=True,
                backgroundColor=choice(colors),
                rayso=rayso or udB.get_key("RAYSO_ON_BASH"),
            )
            if isinstance(li, dict):
                return await xx.edit(
                    f"Unknown Response from Carbon: `{li}`\n\n**Output:** `{stdout}`\n**Error:** `{stderr}`"
                )
            url = await get_imgbb_link(
                "_bash.jpg",
                hq=True,
                expire=7200,
                delete=True,
                preview=True,
            )
            OUT = f"[\xad]({url}){OUT}"
            out = "**• OUTPUT:**"
        else:
            if "pip" in cmd and all(":" in line for line in stdout.split("\n")):
                try:
                    load = safe_load(stdout)
                    stdout = ""
                    for data in list(load.keys()):
                        res = load[data] or ""
                        if res and "http" not in str(res):
                            res = f"`{res}`"
                        stdout += f"**{data}**  :  {res}\n"
                    yamlf = True
                except Exception as er:
                    stdout = f"`{stdout}`"
                    LOGS.exception(er)
            else:
                stdout = f"`{stdout}`"
            out = f"**• OUTPUT:**\n{stdout}"
    if not stderr and not stdout:
        out = "**• OUTPUT:**\n`Success`"
    OUT += err + out
    if len(OUT) > 4096:
        for i in ("**", "__", "`"):
            OUT = OUT.replace(i, "")
        with BytesIO(OUT.encode()) as out_file:
            out_file.name = "bash.txt"
            await event.client.send_file(
                event.chat_id,
                out_file,
                force_document=True,
                thumb=ULTConfig.thumb,
                allow_cache=False,
                caption=f"```{cmd}```" if len(cmd) < 998 else None,
                reply_to=reply_to_id,
            )
            await xx.delete()
    else:
        await xx.edit(OUT, link_preview=is_preview)
    if not nolog:
        await evalogger(cmd, event)


pp = pprint  # ignore: pylint
bot = ultroid = ultroid_bot


class u:
    _ = ""


def _parse_eval(value=None):
    if not value:
        return value
    if hasattr(value, "stringify"):
        try:
            return value.stringify()
        except TypeError:
            pass
    elif isinstance(value, dict):
        try:
            return json_parser(value, indent=4)
        except Exception:
            pass
    elif isinstance(value, list):
        newlist = "["
        for index, child in enumerate(value):
            if type(child) == str:
                newlist += f"\n  '{_parse_eval(child)}'"
            else:
                newlist += f"\n  {_parse_eval(child)}"
            if index < len(value) - 1:
                newlist += ","
        newlist += "\n]"
        return newlist
    return str(value)


@ultroid_cmd(pattern="eval", fullsudo=True, only_devs=True)
async def _(event):
    try:
        cmd = event.text.split(maxsplit=1)[1]
    except IndexError:
        return await event.eor(get_string("devs_2"), time=5)

    xx, mode = None, ""
    spli = cmd.split(maxsplit=1)

    async def get_():
        try:
            cm = cmd.split(maxsplit=1)[1]
        except IndexError:
            await event.eor("->> Wrong Format <<-")
            cm = None
        return cm

    if spli[0] == "-s":  # --silent
        if event.out:
            await event.delete()
        mode = "silent"
    elif spli[0] == "-n":  # --noedit
        mode = "no-edit"
        xx = await event.reply(get_string("com_1"))
    elif spli[0] == "-c":  # --carbon
        mode = "carb"
    elif spli[0] == "-r":  # --rayso
        mode = "rayso"
    elif spli[0] == "-nl":
        mode = "nolog"
    elif spli[0] == "-b":  # --black
        mode = "black"
    elif spli[0] in ("-gs", "--source"):
        mode = "gsource"
    elif spli[0] in ("-ga", "--args"):
        mode = "g-args"
    if mode:
        cmd = await get_()

    if not cmd:
        return

    if mode != "silent" and not xx:
        xx = await event.eor(get_string("com_1"))
    if mode != "nolog":
        LOGS.debug(cmd)
    if mode == "black" and black:
        try:
            cmd = black.format_str(cmd, mode=black.Mode())
        except Exception:
            # Consider it as Code Error, and move on to be shown ahead.
            pass

    reply_to_id = event.reply_to_msg_id or event
    if any(item in cmd for item in KEEP_SAFE().All) and (
        not (event.out or event.sender_id == ultroid_bot.uid)
    ):
        warning = await event.forward_to(udB.get_key("LOG_CHANNEL"))
        await warning.reply(
            f"Malicious Activities suspected by {inline_mention(await event.get_sender())}"
        )
        if not udB.get_key("_SKIP_WARNINGS"):
            _ignore_eval.append(event.sender_id)
            return await xx.edit(
                "`Malicious Activities suspected⚠️!\nReported to owner. Aborted this request!`"
            )
    old_stderr = sys.stderr
    old_stdout = sys.stdout
    redirected_output = sys.stdout = StringIO()
    redirected_error = sys.stderr = StringIO()
    stdout, stderr, exc, timeg = None, None, None, None
    tima = time.time()
    try:
        value = await aexec(cmd, event)
    except Exception:
        value = None
        exc = traceback.format_exc()
    tima = time.time() - tima
    stdout = redirected_output.getvalue()
    stderr = redirected_error.getvalue()
    sys.stdout = old_stdout
    sys.stderr = old_stderr
    if value:
        try:
            if mode == "gsource":
                exc = inspect.getsource(value)
            elif mode == "g-args":
                args = inspect.signature(value).parameters.values()
                name = ""
                if hasattr(value, "__name__"):
                    name = value.__name__
                exc = f"**{name}**\n\n" + "\n ".join([str(arg) for arg in args])
        except Exception:
            exc = traceback.format_exc()
    evaluation = exc or stderr or stdout or _parse_eval(value) or get_string("instu_4")
    if mode == "silent":
        if exc:
            msg = f"• <b>EVAL ERROR\n\n• CHAT:</b> <code>{get_display_name(event.chat)}</code> [<code>{event.chat_id}</code>]"
            msg += f"\n\n∆ <b>CODE:</b>\n<code>{cmd}</code>\n\n∆ <b>ERROR:</b>\n<code>{exc}</code>"
            log_chat = udB.get_key("LOG_CHANNEL")
            if len(msg) > 4000:
                with BytesIO(msg.encode()) as out_file:
                    out_file.name = "Eval-Error.txt"
                return await event.client.send_message(
                    log_chat, f"`{cmd}`", file=out_file
                )
            await event.client.send_message(log_chat, msg, parse_mode="html")
        return
    tmt = tima * 1000
    timef = time_formatter(tmt)
    timeform = timef if not timef == "0s" else f"{tmt:.3f}ms"
    if mode in ("carb", "rayso"):
        colors = (await asyncread("resources/colorlist.txt")).splitlines()
        lin = await Carbon(
            code=evaluation,
            file_name="_eval",
            download=True,
            rayso=mode == "rayso",
            backgroundColor=choice(colors),
        )
        url = await get_imgbb_link(
            "_eval.jpg",
            hq=True,
            expire=7200,
            delete=True,
            preview=True,
        )
        final_output = f"__►__ **EVAL** (__{timeform}__)\n```{cmd}``` \n\n __►__ **OUTPUT**: [⁮⁮⁮\xad]({url})"
    else:
        final_output = "__►__ **EVAL** (__{}__)\n```{}``` \n\n __►__ **OUTPUT**: \n```{}``` \n".format(
            timeform,
            cmd,
            evaluation,
        )
    if len(final_output) > 4096:
        for i in ("**", "__", "`"):
            final_output = final_output.replace(i, "")
        with BytesIO(final_output.encode()) as out_file:
            out_file.name = "eval.txt"
            await event.client.send_file(
                event.chat_id,
                out_file,
                force_document=True,
                thumb=ULTConfig.thumb,
                allow_cache=False,
                caption=f"```{cmd}```" if len(cmd) < 998 else None,
                reply_to=reply_to_id,
            )
        return await xx.delete()
    await xx.edit(final_output, link_preview=mode == "carb")
    if mode != "nolog":
        await evalogger(cmd, event)


def _stringify(text=None, *args, **kwargs):
    if text:
        u._ = text
        text = _parse_eval(text)
    return print(text, *args, **kwargs)


async def evalogger(cmd, e):
    await asyncio.sleep(1)
    msg = "<b>CMD Executed!</b> \n\n<code>{0}</code> \n\n–  {1}:  {2} \n–  <a href='{3}'>{4}</a>"
    sndr = e.sender or await e.get_sender()
    try:
        _msg = msg.format(
            cmd,
            get_display_name(sndr),
            inline_mention(sndr, custom=sndr.id, html=True),
            e.message_link,
            get_display_name(e.chat or await e.get_chat()),
        )
        await asst.send_message(TAG_LOG, _msg, link_preview=False, parse_mode="html")
    except Exception:
        return LOGS.exception("EVAL Logger error")


async def aexec(code, event):
    exec(
        (
            "async def __aexec(e, client): "
            + "\n print = p = _stringify"
            + "\n message = event = e"
            + "\n u.r = reply = rm = await event.get_reply_message()"
            + "\n chat = event.chat_id"
            + "\n u.lr = locals()"
        )
        + "".join(f"\n {l}" for l in code.split("\n"))
    )

    return await locals()["__aexec"](event, event.client)


DUMMY_CPP = """#include <iostream>
using namespace std;

int main(){
!code
}
"""


@ultroid_cmd(pattern="cpp", only_devs=True, fullsudo=True)
async def doie(e):
    match = e.text.split(" ", maxsplit=1)
    try:
        match = match[1]
    except IndexError:
        return await e.eor(get_string("devs_3"))
    msg = await e.eor(get_string("com_1"))
    if "main(" not in match:
        new_m = "".join(" " * 4 + i + "\n" for i in match.split("\n"))
        match = DUMMY_CPP.replace("!code", new_m)
    with open("cpp-ultroid.cpp", "w+") as f:
        f.write(match)
    m = await bash("g++ -o CppUltroid cpp-ultroid.cpp")
    o_cpp = f"• **Eval-Cpp**\n`{match}`"
    if m[1]:
        o_cpp += f"\n\n**• Error :**\n`{m[1]}`"
        osremove("cpp-ultroid.cpp", "CppUltroid")
        if len(o_cpp) > 3000:
            with BytesIO(str.encode(o_cpp)) as out_file:
                out_file.name = "compile-error-g++.txt"
                return await msg.reply(f"`{match}`", file=out_file)
        return await eor(msg, o_cpp)
    m = await bash("./CppUltroid")
    if m[0] != "":
        o_cpp += f"\n\n**• Output :**\n`{m[0]}`"
    if m[1]:
        o_cpp += f"\n\n**• Error :**\n`{m[1]}`"
    if len(o_cpp) > 3000:
        with BytesIO(str.encode(o_cpp)) as out_file:
            out_file.name = "g++_output.txt"
            await msg.reply(f"`{match}`", file=out_file)
    else:
        await eor(msg, o_cpp)
    os.remove("CppUltroid")
    os.remove("cpp-ultroid.cpp")


# for running C code with gcc (no dummy cpp)
@ultroid_cmd(pattern="gcc", only_devs=True, fullsudo=True)
async def _gcc_compiler(e):
    try:
        match = e.text.split(" ", maxsplit=1)[1]
    except IndexError:
        return await e.eor(get_string("devs_3"))
    msg = await e.eor(get_string("com_1"))
    with open("ultroid.c", "w+") as f:
        f.write(match)
    m = await bash("gcc ultroid.c -o ultroid.out")
    out = f"• **Eval-C**\n```{match}```"
    if m[1]:
        out += f"\n\n**• Error :**\n```{m[1]}```"
        osremove("ultroid.c", "ultroid.out")
        if len(out) > 4000:
            with BytesIO(str.encode(out)) as out_file:
                out_file.name = "compile-error-gcc.txt"
                return await msg.reply(f"```{match}```", file=out_file)
        return await eor(msg, out)
    m = await bash("./ultroid.out")
    if m[0] != "":
        out += f"\n\n**• Output :**\n```{m[0]}```"
    if m[1]:
        out += f"\n\n**• Error :**\n```{m[1]}```"
    if len(out) > 4000:
        with BytesIO(str.encode(out)) as out_file:
            out_file.name = "gcc_output.txt"
            await msg.reply(f"```{match[:1023]}```", file=out_file)
    else:
        await msg.edit(out)
    osremove("ultroid.out", "ultroid.c")
