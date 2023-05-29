import asyncio
import secrets

try:
    import uvloop

    uvloop.install()
except ImportError:
    pass


tasks_db = {}


try:
    loop = asyncio.get_running_loop()
except RuntimeError:
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)


def run_async_task(func, *args, **kwargs):
    pid = kwargs.pop("id", None)
    while not pid or pid in tasks_db:
        pid = secrets.token_hex(nbytes=8)
    task = loop.create_task(func(*args, **kwargs))
    tasks_db[pid] = task
    task.add_done_callback(lambda task: tasks_db.pop(pid))
    return pid
