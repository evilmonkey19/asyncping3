import os
import sys
import timeit

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import asyncping3 as ping3  # noqa: linter (pycodestyle) should not lint this line.

dev_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
stmt = "anyio.run(ping3.ping,'127.0.0.1')"

if __name__ == "__main__":
    setup = f"import anyio, sys; sys.path.insert(0, {dev_dir !r}); import asyncping3 as ping3"
    for count in (1, 10, 100, 1000, 5000):
        print("Testing `{stmt}` {num} times...".format(stmt=stmt, num=count))
        duration = timeit.timeit(stmt, setup=setup, number=count)
        print("Duration: {drtn:.3f} seconds. {d:.1f} ms/ping".format(drtn=duration, d=duration * 1000 / count))
        print()
