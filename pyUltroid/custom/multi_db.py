import os

from redis.exceptions import ConnectionError, TimeoutError

from pyUltroid import udB, Var
from pyUltroid.startup import HOSTED_ON, LOGS
from pyUltroid.startup._database import MongoDB, RedisDB, SqlDB


def _connect_single_db(data, type, petname, cache):
    if type == "mongo":
        name = "Mongo: " + petname
        try:
            return MongoDB(key=data, _name=name, to_cache=cache)
        except Exception:
            LOGS.warning(f"MultiDB: Error while Connecting to MongoDB: {petname}")
            return LOGS.debug("", exc_info=True)

    elif type == "sql":
        name = "Sql: " + petname
        try:
            return SqlDB(url=data, _name=name, to_cache=cache)
        except Exception:
            LOGS.warning(f"MultiDB: Error while Connecting to SQL DB: {petname}")
            return LOGS.debug("", exc_info=True)

    else:
        name = "Redis: " + petname
        stuff = data.split()
        try:
            return RedisDB(
                host=stuff[1],
                password=stuff[0],
                port=None,
                _name=name,
                platform=HOSTED_ON,
                decode_responses=True,
                socket_timeout=5,
                retry_on_timeout=True,
                to_cache=cache,
            )
        except (ConnectionError, TimeoutError):
            LOGS.warning(f"MultiDB: Error while Connecting to RedisDB: {petname}")
            return LOGS.debug("", exc_info=True)
        except Exception as exc:
            return LOGS.exception(exc)


def _init_multi_dbs(var):
    from ast import literal_eval

    co = 0
    stuff = os.getenv(var)
    if not stuff:
        return LOGS.warning(f"Var {var} is not filled..")
    LOGS.info("Loading Multi DB's..")
    if Var.HOST.lower() == "heroku":
        os.environ.pop(var, None)
    data = literal_eval(str(stuff))
    dct = {}
    for k, v in data.items():
        co += 1
        to_cache = False
        key = "udB" + str(co)
        if type(v) in (tuple, list):
            to_cache = v[1] is True
            v = v[0]

        if v == "self":
            dct[co] = f"{k} -> self"
            globals()[key] = udB

        else:
            if "redislabs" in v:
                _type = "redis"
            elif "mongodb" in v:
                _type = "mongo"
            else:
                _type = "sql"

            if cx := _connect_single_db(v, _type, k, to_cache):
                dct[co] = f"{k} -> {_type}"
                globals()[key] = cx

    if dct:
        from pyUltroid.fns.tools import json_parser

        LOGS.debug(json_parser(dct, indent=2))
        LOGS.info("Loaded all DB's!")
