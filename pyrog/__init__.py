# @spemgod | @ah3h3 | @moiusrname
#
# This is just for personal use,
# cz telethon is quite slow in transferring files.
#
# Edited on 13-05-2022 // for pyrogram v2.
# 28-06-2022 // added asyncio.gather for faster startup.
# 22-05-2023 // slower startup ~ clients starting one by one in background.

import asyncio
from ast import literal_eval
from copy import deepcopy
from os import getcwd, environ

from pyrogram import Client

from pyUltroid import LOGS
from pyUltroid.configs import Var
from pyUltroid.custom.init import run_async_task


PYROG_CLIENTS = {}
_default_client_values = {
    "api_id": Var.API_ID,
    "api_hash": Var.API_HASH,
    "workdir": getcwd() + "/resources/temp",
    "sleep_threshold": 60,
    "workers": 6,
    "no_updates": True,
}


def app(n=None):
    _default = PYROG_CLIENTS.get(1)
    return PYROG_CLIENTS.get(n, _default) if n else _default


def setup_clients():
    # plugins = {"root": "pyrog/plugins"}
    var = "PYROGRAM_CLIENTS"
    stuff = environ.get(var)
    if not stuff:
        LOGS.warning(
            "'PYROGRAM_CLIENTS' ENV wasn't found, Skipping PyroGram Initialisation."
        )
        return True
    data = literal_eval(stuff)
    if Var.HOST.lower() == "heroku":
        environ.pop(var, None)
    for k, v in data.items():
        _default = deepcopy(_default_client_values)
        _default.update({"name": "bot_" + str(k)})
        if type(v) == dict:
            _default |= v
        else:
            _default.update({"bot_token": v})
        PYROG_CLIENTS.update({int(k): Client(**_default)})


async def pyro_startup():
    if setup_clients():
        return
    LOGS.info("Starting Pyrogram...")
    for count, client in PYROG_CLIENTS.copy().items():
        try:
            await client.start()
        except Exception:
            LOGS.warning(f"Error while starting PyroGram Client: {count}")
            LOGS.debug("", exc_info=True)
            PYROG_CLIENTS.pop(count, None)
        finally:
            await asyncio.sleep(2)

    LOGS.info(
        f"{len(PYROG_CLIENTS)} Pyrogram Clients Running -> {tuple(PYROG_CLIENTS.keys())}"
    )


async def _init_pyrog():
    run_async_task(pyro_startup, id="pyrogram_startup")
    await asyncio.sleep(6)
