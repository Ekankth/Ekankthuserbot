__all__ = []

import asyncio
from os import environ, system
from pathlib import Path
from subprocess import run, Popen
from sys import executable, exit
from time import tzset

from ._loop import loop, run_async_task, tasks_db

try:
    from dotenv import load_dotenv
except ModuleNotFoundError:
    load_dotenv = None


def startup_logo():
    # skipping bash startup
    print(
        """
            ┏┳┓╋┏┓╋╋╋╋┏┓┏┓
            ┃┃┣┓┃┗┳┳┳━╋╋┛┃
            ┃┃┃┗┫┏┫┏┫╋┃┃╋┃
            ┗━┻━┻━┻┛┗━┻┻━┛

      Visit @TheUltroid for updates!!

"""
    )


def cleanup_stuff():
    py_path = str(Path(executable).parents[1])
    hitlist = (
        f"{py_path}/lib/python3.*/site-packages/pip/_vendor/.wh*",
        f"{py_path}/lib/python3.*/site-packages/.wh*",
    )
    for path in hitlist:
        run(f"rm -rfv {path}", shell=True)
    for file in ("jewel", "bird", ".wget-hsts", "prvenv"):
        Path(file).unlink(missing_ok=True)


def setup_timezone():
    # use db for this !?
    TZ = environ.get("TZ", "Asia/Kolkata")
    try:
        environ["TZ"] = TZ
    except Exception:
        environ["TZ"] = "UTC"
    finally:
        tzset()


def startup_tasks():
    """
    if not Path("plugins").is_dir():
        print("Plugins Folder does not exists!")
        exit(0)
    """
    startup_logo()
    cleanup_stuff()
    setup_timezone()
    if load_dotenv and Path(".env").is_file():
        load_dotenv(override=True)


startup_tasks()


# startup part 2

from pyUltroid.configs import Var
from pyUltroid.startup import LOGS
from .heroku import herokuApp


async def _updater_task(data):
    try:
        from redis.asyncio import Redis
    except ImportError as e:
        return LOGS.critical(e)

    key, password, other = data.split(" ", maxsplit=2)
    host, port = other.split(":", maxsplit=1)
    while True:
        r = Redis(
            host=host,
            password=password,
            port=port,
            decode_responses=True,
            socket_timeout=10,
        )
        await r.setex(key, 1200, 1205)
        del r
        await asyncio.sleep(1200)


def _host_specifics():
    if Var.HOST.lower() == "heroku":
        LOGS.debug("Starting heroku3 API Setup...")
        herokuApp()
    if environ.get("qBit") and Path("1337x").is_file():
        LOGS.info("Starting qBittorrent")
        Popen("bash 1337x &", shell=True)
    if r_data := environ.get("USR_STATUS_UPDATE"):  # for doprax
        run_async_task(_updater_task, r_data, id="status_update")


def delayed_startup_tasks():
    undel = ("local", "railway", "wfs", "doprax")
    env = Path(".env")
    if Var.HOST.lower() not in undel and env.is_file():
        env.unlink()
    _host_specifics()


# doprax checks
def afterBoot(db):
    if Var.HOST.lower() == "doprax":
        chk = environ.get("CHECKS")
        if not chk or (chk and chk not in db.get_key("DOPRAX")):
            print("check the 'CHECKS' Var...")
            exit(0)


delayed_startup_tasks()
