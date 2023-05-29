# Ultroid - UserBot
# Copyright (C) 2021-2022 TeamUltroid
#
# This file is a part of < https://github.com/TeamUltroid/Ultroid/ >
# PLease read the GNU Affero General Public License in
# <https://github.com/TeamUltroid/pyUltroid/blob/main/LICENSE>.

from ast import literal_eval
from os import environ, system
from copy import deepcopy
from random import randrange
from sys import executable

from redis.exceptions import ResponseError

from ..configs import Var
from .. import LOGS, HOSTED_ON


# ---------------------------------------------------------------------------------------------

# DB Imports!
try:
    from redis import Redis
    from pymongo import MongoClient
except ModuleNotFoundError:
    LOGS.info("Installing Redis and pymongo for database.")
    system(f"{executable} -m pip install -q redis[hiredis] pymongo[srv]")
    from redis import Redis
    from pymongo import MongoClient


if Var.DATABASE_URL:
    try:
        import psycopg2
    except ImportError:
        LOGS.info("Installing 'pyscopg2' for database.")
        system(f"{executable} -m pip install -q psycopg2-binary")
        import psycopg2

# ---------------------------------------------------------------------------------------------


class _BaseDatabase:
    def __init__(self, *args, **kwargs):
        self._cache = {}
        if not self.to_cache:
            if randrange(100) > 40:
                self.__nocache__()
        else:
            self.re_cache()

    def ping(self):
        return 1

    @property
    def usage(self):
        return 0

    def keys(self):
        return []

    def del_key(self, key):
        if self.to_cache:
            self._cache.pop(key, None)
        self.delete(key)
        return True

    def _get_data(self, key=None, data=None):
        if key:
            try:
                data = self.get(str(key))
            except ResponseError:
                return "WRONGTYPE"
        if data and type(data) == str:
            try:
                data = literal_eval(data)
            except Exception:
                pass
        return data

    def re_cache(self, key=None):
        if not self.to_cache:
            raise TypeError("Caching is disabled")
        if key:
            self._cache.pop(key, None)
            if data := self.get_key(key, force=True):
                self._cache[key] = data
                return True
            return "Key not found"
        for key in self.keys():
            if not key.startswith("__"):
                self._cache.update({key: self.get_key(key, force=True)})

    def get_key(self, key, *, force=False):
        if not self.to_cache:
            if key in self.keys():
                return self._get_data(key=key)
        elif key in self._cache:
            return deepcopy(self._cache[key])
        elif force:
            if key in self.keys():
                value = self._get_data(key=key)
                if not key.startswith("__"):
                    self._cache.update({key: value})
                return deepcopy(value)

    def set_key(self, key, value, cache_only=False):
        value = self._get_data(data=value)
        if self.to_cache:
            if not key.startswith("__"):
                self._cache.update({key: value})
            if cache_only:
                return True
        self.set(str(key), str(value))
        return True

    def rename(self, key1, key2):
        if val := self.get_key(key1, force=True):
            self.del_key(key1)
            return self.set_key(key2, val)
        return False

    def append(self, key, value):
        if not (data := self.get_key(key)):
            return "Key doesn't exists!"
        value = self._get_data(data=value)
        if type(data) == set:
            data.add(value)
        elif type(data) == dict:
            data = data | value
        elif type(data) == list:
            data.append(value)
        elif type(data) == tuple:
            lst = list(data)
            lst.append(value)
            data = tuple(lst)
        else:
            data += " " + str(value)
        return self.set_key(key, data)

    def __nocache__(self):
        self.del_key("__nocache__")


# ---------------------------------------------------------------------------------------------


class MongoDB(_BaseDatabase):
    def __init__(self, key, to_cache, _name="MongoDB", dbname="UltroidDB"):
        self.dB = MongoClient(key, serverSelectionTimeoutMS=5000)
        self.db = self.dB[dbname]
        self.to_cache = to_cache
        self._name = _name
        super().__init__()

    def __repr__(self):
        info = f"-cached_keys: {len(self._cache)}" if self.to_cache else ""
        return f"<Ultroid.MonGoDB \n-name: {self.name} \n{info}\n>"

    @property
    def name(self):
        return self._name

    @property
    def usage(self):
        return self.db.command("dbstats")["dataSize"]

    def ping(self):
        if self.dB.server_info():
            return True

    def keys(self):
        return self.db.list_collection_names()

    def set(self, key, value):
        value = self._get_data(data=value)
        if key in self.keys():
            self.db[key].replace_one({"_id": key}, {"value": str(value)})
        else:
            self.db[key].insert_one({"_id": key, "value": str(value)})
        if self.to_cache:
            self._cache.update({key: value})
        return True

    def delete(self, key):
        if self.to_cache:
            self._cache.pop(key, None)
        if key in self.keys():
            self.db.drop_collection(key)
            return True

    def get(self, key):
        if x := self.db[key].find_one({"_id": key}):
            return x["value"]


"""
def flushall(self):
        self.dB.drop_database("UltroidDB")
        self._cache.clear()
        return True
"""

# ---------------------------------------------------------------------------------------------

# Thanks to "Akash Pattnaik" / @BLUE-DEVIL1134
# for SQL Implementation in Ultroid.
#
# Please use https://elephantsql.com/ !


class SqlDB(_BaseDatabase):
    def __init__(self, url, to_cache, _name="SQL_DB"):
        self._connection = None
        self._cursor = None
        self.url = url
        self.to_cache = to_cache
        self._name = _name
        try:
            self._connection = psycopg2.connect(dsn=url)
            self._connection.autocommit = True
            self._cursor = self._connection.cursor()
            self._cursor.execute(
                "CREATE TABLE IF NOT EXISTS Ultroid (ultroidCli varchar(70))"
            )
        except Exception as error:
            LOGS.exception(error)
            LOGS.info("Invaid SQL Database")
            if self._connection:
                self._connection.close()
            quit("SQL Error..")
        super().__init__()

    @property
    def name(self):
        return self._name

    def __repr__(self):
        info = f"-cached_keys: {len(self._cache)}" if self.to_cache else ""
        return f"<Ultroid.SQLDB \n-name: {self.name} \n{info}\n>"

    @property
    def usage(self):
        self._cursor.execute(
            "SELECT pg_size_pretty(pg_relation_size('Ultroid')) AS size"
        )
        data = self._cursor.fetchall()
        return int(data[0][0].split()[0])

    def keys(self):
        self._cursor.execute(
            "SELECT column_name FROM information_schema.columns WHERE table_schema = 'public' AND table_name  = 'ultroid'"
        )  # case sensitive
        data = self._cursor.fetchall()
        return [_[0] for _ in data]

    def get(self, variable):
        try:
            self._cursor.execute(f"SELECT {variable} FROM Ultroid")
        except psycopg2.errors.UndefinedColumn:
            return None
        data = self._cursor.fetchall()
        if not data:
            return None
        if len(data) >= 1:
            for i in data:
                if i[0]:
                    return i[0]

    def set(self, key, value):
        try:
            self._cursor.execute(f"ALTER TABLE Ultroid DROP COLUMN IF EXISTS {key}")
        except (psycopg2.errors.UndefinedColumn, psycopg2.errors.SyntaxError):
            pass
        except Exception as er:
            LOGS.exception(er)
        self._cache.update({key: value})
        self._cursor.execute(f"ALTER TABLE Ultroid ADD {key} TEXT")
        self._cursor.execute(f"INSERT INTO Ultroid ({key}) values (%s)", (str(value),))
        return True

    def delete(self, key):
        try:
            self._cursor.execute(f"ALTER TABLE Ultroid DROP COLUMN {key}")
        except psycopg2.errors.UndefinedColumn:
            return False
        return True


"""
def flushall(self):
    self._cache.clear()
    self._cursor.execute("DROP TABLE Ultroid")
    self._cursor.execute(
        "CREATE TABLE IF NOT EXISTS Ultroid (ultroidCli varchar(70))"
    )
    return True
"""

# ---------------------------------------------------------------------------------------------


class RedisDB(_BaseDatabase):
    def __init__(
        self,
        host,
        port,
        password,
        to_cache,
        platform="",
        _name="RedisDB",
        logger=LOGS,
        *args,
        **kwargs,
    ):
        if host and ":" in host:
            spli_ = host.split(":")
            host = spli_[0]
            port = int(spli_[-1])
            if host.startswith("http"):
                logger.critical("Your REDIS_URI should not start with http !")
                quit("Redis Error..")
        elif not host or not port:
            logger.critical("Redis error: Host or Port missing..")
            quit("Redis Error..")

        kwargs["host"] = host
        kwargs["password"] = password
        kwargs["port"] = port

        if platform.lower() == "qovery" and not host:
            var, hash_, host, password = "", "", "", ""
            for vars_ in environ:
                if vars_.startswith("QOVERY_REDIS_") and vars.endswith("_HOST"):
                    var = vars_
            if var:
                hash_ = var.split("_", maxsplit=2)[1].split("_")[0]
            if hash:
                kwargs["host"] = environ.get(f"QOVERY_REDIS_{hash_}_HOST")
                kwargs["port"] = environ.get(f"QOVERY_REDIS_{hash_}_PORT")
                kwargs["password"] = environ.get(f"QOVERY_REDIS_{hash_}_PASSWORD")

        self.db = Redis(**kwargs)
        self.set = self.db.set
        self.get = self.db.get
        self.keys = self.db.keys
        self.delete = self.db.delete
        self.to_cache = to_cache
        self._name = _name
        super().__init__()

    @property
    def name(self):
        return self._name

    def __repr__(self):
        info = f"-cached_keys: {len(self._cache)}" if self.to_cache else ""
        return f"<Ultroid.RedisDB \n-name: {self._name} \n{info}\n>"

    @property
    def usage(self):
        return sum(self.db.memory_usage(x) for x in self.keys())

    def real(self, key):
        try:
            return self.db.get(key)
        except ResponseError:
            try:
                return self.db.lrange(key, 0, -1)
            except ResponseError:
                try:
                    return self.db.hgetall(key)
                except Exception as exc:
                    return exc


# --------------------------------------------------------------------------------------------- #


class LocalDB(_BaseDatabase):
    def __init__(self):
        try:
            from localdb import Database
        except ModuleNotFoundError:
            LOGS.info("Using local file as database.")
            system("pip3 install -q localdb.json")
            from localdb import Database

        self.db = Database("ultroid")
        self._name = "LocalDB"
        self.to_cache = True
        self.get = self.db.get
        self.set = self.db.set
        self.delete = self.db.delete
        super().__init__()

    def keys(self):
        return self._cache.keys()

    @property
    def name(self):
        return self._name

    def __repr__(self):
        return f"<Ultroid.LocalDB\n -total_keys: {len(self.keys())}\n>"


# ---------------------------------------------------------------------------------------------


def UltroidDB():
    try:
        if Var.REDIS_URI or Var.REDISHOST:
            return RedisDB(
                host=Var.REDIS_URI or Var.REDISHOST,
                password=Var.REDIS_PASSWORD or Var.REDISPASSWORD,
                port=Var.REDISPORT,
                platform=HOSTED_ON,
                decode_responses=True,
                socket_timeout=6,
                retry_on_timeout=True,
                to_cache=True,
                _name="Redis",
            )
        elif Var.MONGO_URI:
            return MongoDB(key=Var.MONGO_URI, _name="Mongo", to_cache=True)
        elif Var.DATABASE_URL:
            return SqlDB(url=Var.DATABASE_URL, to_cache=True, _name="SQL")
        else:
            LOGS.critical(
                "No DB requirement fullfilled!\nPlease install redis, mongo or sql dependencies...\nTill then using local file as database."
            )
            return LocalDB()
    except BaseException as err:
        LOGS.exception(err)
    quit(0)


LOGS.info("Connecting to Database..")
udB = UltroidDB()
LOGS.info(f"Connected to {udB.name} Successfully!")
