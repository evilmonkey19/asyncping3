import os
import sys
import anyio

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import asyncping3 as ping3  # noqa: linter (pycodestyle) should not lint this line.


# ping3.DEBUG = True
HOSTS = ['baidu.com', 'example.com', '8.8.8.8', '1.1.1.1', '9.9.9.9', '127.0.0.1']


async def ping_in_thread_or_process(host):
    while True:
        delay = await ping3.ping(host, unit='ms')
        await anyio.sleep(1)
        print(host, delay)


async def standard_delay():
    for h in HOSTS:
        print('Standard Delay:', h, await ping3.ping(h, unit='ms'))


async def multi_processing_ping():
    async with anyio.create_task_group() as tg:
        for h in HOSTS:
            tg.start_soon(ping_in_thread_or_process, h)


if __name__ == '__main__':
    anyio.run(standard_delay)
    anyio.run(multi_processing_ping)
