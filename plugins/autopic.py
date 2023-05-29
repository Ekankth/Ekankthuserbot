# Ultroid - UserBot
# Copyright (C) 2021-2022 TeamUltroid
#
# This file is a part of < https://github.com/TeamUltroid/Ultroid/ >
# PLease read the GNU Affero General Public License in
# <https://www.github.com/TeamUltroid/Ultroid/blob/main/LICENSE/>.

from urllib.parse import urlparse
from urllib.parse import parse_qs

from telethon.tl.functions.photos import UploadProfilePhotoRequest

from pyUltroid.fns.helper import download_file
from pyUltroid.fns.misc import unsplashsearch

from . import (
    LOGS,
    osremove,
    check_filename,
    get_help,
    get_string,
    scheduler,
    udB,
    ultroid_bot,
    ultroid_cmd,
)


__doc__ = get_help("help_autopic")

autopic_links = set()


async def genLinks(search):
    def is_cropped(data):
        for i in ("h", "w"):
            if value := data.get(i):
                if int(value[0]) < 480:
                    return True

    global autopic_links
    links = await unsplashsearch(search, limit=None, shuf=True)
    for url in links:
        parsed_data = parse_qs(urlparse(url).query)
        if not is_cropped(parsed_data):
            autopic_links.add(url)


async def autopic_func():
    global autopic_links
    if not (search := udB.get_key("AUTOPIC")):
        return
    if not autopic_links:
        await genLinks(search)
        if not autopic_links:
            return LOGS.error(f"Autopic Error: Found No Photos for {search}")
    img = autopic_links.pop()
    path = check_filename("resources/downloads/autopic.jpg")
    try:
        await download_file(img, path)
        tg_file = await ultroid_bot.upload_file(path)
        await ultroid_bot(UploadProfilePhotoRequest(file=tg_file))
    except Exception as exc:
        LOGS.warning(f"autopic error: {exc}, Link: {img}")
    finally:
        osremove(path)


@ultroid_cmd(pattern="autopic( (.*)|$)")
async def autopic(e):
    global autopic_links
    search = e.pattern_match.group(2)
    if udB.get_key("AUTOPIC") and (not search or search == "stop"):
        udB.del_key("AUTOPIC")
        autopic_links.clear()
        if scheduler:
            scheduler.remove_job("autopic")
        return await e.eor(get_string("autopic_5"))

    if not search:
        return await e.eor(get_string("autopic_1"), time=6)

    if not scheduler:
        return await e.eor("`APScheduler is missing, Can't Use Autopic`", time=6)

    eris = await e.eor(get_string("com_1"))
    await genLinks(search)
    if not autopic_links:
        return await eris.eor(get_string("autopic_2").format(search), time=10)

    udB.set_key("AUTOPIC", search)
    await eris.edit(get_string("autopic_3").format(search))
    sleep = udB.get_key("SLEEP_TIME") or 1221
    scheduler.add_job(
        autopic_func,
        trigger="interval",
        seconds=sleep,
        id="autopic",
        jitter=60,
    )


if udB.get_key("AUTOPIC"):
    sleep = udB.get_key("SLEEP_TIME") or 1221
    if scheduler:
        scheduler.add_job(
            autopic_func,
            "interval",
            seconds=sleep,
            id="autopic",
            jitter=60,
        )
    else:
        LOGS.error(f"autopic: 'Apscheduler' not installed.")
