# AsyncPing
![GitHub release](https://img.shields.io/github/release/M-o-a-T/asyncping3.svg)
[![GitHub license](https://img.shields.io/github/license/M-o-a-T/asyncping3.svg)](https://github.com/M-o-a-T/asyncping3/blob/master/LICENSE)
![PyPI - Downloads](https://img.shields.io/pypi/dm/asyncping3.svg)

AsyncPing is an async-friendly pure python3 version of ICMP ping implementation using raw sockets.\
(Note that on Linux and Windows, ICMP messages can only be sent from processes running as root.)

> The Python2 version originally from [here](http://github.com/samuel/python-ping).\
> The Python3 version originally from [here](http://github.com/kyan001/ping3).\
> This fork maintained at [this github repo](https://github.com/M-o-a-T/asyncping3).

[CHANGELOG](CHANGELOG.md)

## Get Started

* If you met "permission denied", you may need to run this as root. Alternatively see [this](./TROUBLESHOOTING.md#permission-denied-on-linux) for troubleshooting on linux.

```sh
pip install asyncping3
```

```python
>>> from asyncping3 import ping, verbose_ping
>>> anyio.run(ping,'example.com')  # Returns delay in seconds.
0.215697261510079666

>>> anyio.run(verbose_ping,'example.com')  # Ping 4 times in a row.
ping 'example.com' ... 215ms
ping 'example.com' ... 216ms
ping 'example.com' ... 219ms
ping 'example.com' ... 217ms
```

```sh
$ pping example.com  # Verbose ping.
ping 'example.com' ... 215ms
ping 'example.com' ... 216ms
ping 'example.com' ... 219ms
ping 'example.com' ... 217ms
```

## Installation

```sh
pip install asyncping3  # install asyncping3
pip install --upgrade asyncping3  # upgrade asyncping3
pip uninstall asyncping3  # uninstall asyncping3
```

## Functions

```python
>>> from ping3 import ping, verbose_ping

>>> ping('example.com')  # Returns delay in seconds.
0.215697261510079666  # `0.0` returned means the delay is lower than the precision of `time.time()`.

>>> ping('not.exist.com')  # If host unknown (cannot resolve), returns False.
False

>>> ping("224.0.0.0")  # If timed out (no reply), returns None.
None

>>> ping('example.com', timeout=10)  # Set timeout to 10 seconds. Default timeout is 4 for 4 seconds.
0.215697261510079666

>>> ping('example.com', unit='ms')  # Returns delay in milliseconds. Default unit is 's' for seconds.
215.9627876281738

>>> ping('example.com', src_addr='192.168.1.15')  # Set source ip address for multiple interfaces. Default src_addr is None for no binding.
0.215697261510079666

>>> ping('example.com', interface='eth0')  # LINUX ONLY. Set source interface for multiple network interfaces. Default interface is None for no binding.
0.215697261510079666

>>> ping('example.com', ttl=5)  # Set packet Time-To-Live to 5. The packet is discarded if it does not reach the target host after 5 jumps. Default ttl is 64.
None

>>> ping('example.com', size=56)  # Set ICMP packet payload to 56 bytes. The total ICMP packet size is 8 (header) + 56 (payload) = 64 bytes. Default size is 56.
0.215697261510079666

>>> verbose_ping('example.com')  # Ping 4 times in a row.
ping 'example.com' ... 215ms
ping 'example.com' ... 216ms
ping 'example.com' ... 219ms
ping 'example.com' ... 217ms

>>> verbose_ping('example.com', timeout=10)  # Set timeout to 10 seconds. Default timeout is 4 for 4 seconds.
ping 'example.com' ... 215ms
ping 'example.com' ... 216ms
ping 'example.com' ... 219ms
ping 'example.com' ... 217ms

>>> verbose_ping('example.com', count=6)  # Ping 6 times. Default count is 4.
ping 'example.com' ... 215ms
ping 'example.com' ... 216ms
ping 'example.com' ... 219ms
ping 'example.com' ... 217ms
ping 'example.com' ... 215ms
ping 'example.com' ... 216ms

>>> verbose_ping('example.com', count=0)  # Ping endlessly (0 means infinite loops). Using `ctrl + c` to stop manully.
ping 'example.com' ... 215ms
...

>>> verbose_ping('example.com', src_addr='192.168.1.15')  # Ping from source IP address for multiple interfaces. Default src_addr is None.
ping 'example.com' from '192.168.1.15' ... 215ms
ping 'example.com' from '192.168.1.15' ... 216ms
ping 'example.com' from '192.168.1.15' ... 219ms
ping 'example.com' from '192.168.1.15' ... 217ms

>>> verbose_ping('example.com', interface='wifi0')  # LINUX ONLY. Ping from network interface 'wifi0'. Default interface is None.
ping 'example.com' from '192.168.1.15' ... 215ms
ping 'example.com' from '192.168.1.15' ... 216ms
ping 'example.com' from '192.168.1.15' ... 219ms
ping 'example.com' from '192.168.1.15' ... 217ms

>>> verbose_ping('example.com', unit='s')  # Displays delay in seconds. Default unit is "ms" for milliseconds.
ping 'example.com' ... 1s
ping 'example.com' ... 2s
ping 'example.com' ... 1s
ping 'example.com' ... 1s

>>> verbose_ping('example.com', ttl=5)  # Set TTL to 5. Default is 64.
ping 'example.com' ... Timeout
ping 'example.com' ... Timeout
ping 'example.com' ... Timeout
ping 'example.com' ... Timeout

>>> verbose_ping('example.com', interval=5)  # Wait 5 seconds between each packet. Default is 0.
ping 'example.com' ... 215ms  # wait 5 secs
ping 'example.com' ... 216ms  # wait 5 secs
ping 'example.com' ... 219ms  # wait 5 secs
ping 'example.com' ... 217ms

>>> verbose_ping('example.com', size=56)  # Set ICMP payload to 56 bytes. Default size is 56.
ping 'example.com' ... 215ms
ping 'example.com' ... 216ms
ping 'example.com' ... 219ms
ping 'example.com' ... 217ms
```

### DEBUG mode

Show more info for developers.

```python
>>> import asyncping3
>>> asyncping3.DEBUG = True  # Default is False.

>>> asyncping3.ping("example.com")  # "ping()" prints received IP header and ICMP header.
[DEBUG] IP HEADER: {'version': 69, 'tos': 0, 'len': 14336, 'id': 8620, 'flags': 0, 'ttl': 51, 'protocol': 1, 'checksum': *, 'src_addr': *, 'dest_addr': *}
[DEBUG] ICMP HEADER: {'type': 0, 'code': 0, 'checksum': 8890, 'id': 21952, 'seq': 0}
0.215697261510079666

>>> asyncping3.ping("example.com", timeout=0.0001)
[DEBUG] Request timeout for ICMP packet. (Timeout = 0.0001s)
None

>>> asyncping3.ping("not.exist.com")
[DEBUG] Cannot resolve: Unknown host. (Host = not.exist.com)
False

>>> asyncping3.ping("example.com", ttl=1)
[DEBUG] Time exceeded: Time To Live expired.
None
```

### EXCEPTIONS mode

Raise exceptions when there are errors instead of return None

```python
>>> import asyncping3, anyio, functools
>>> asyncping3.EXCEPTIONS = True  # Default is False.
>>> def pia(*a, **k):
...    return anyio.run(functools.partial(asyncping3.ping, *a, **k))

>>> pia("example.com", timeout=0.0001))  # All Exceptions are subclasses of PingError
[... Traceback ...]
ping3.errors.Timeout: Request timeout for ICMP packet. (Timeout = 0.0001s)

>>> pia("not.exist.com")
[... Traceback ...]
ping3.errors.HostUnknown: Cannot resolve: Unknown host. (Host = not.exist.com)

>>> pia("example.com", ttl=1)  # Linux need root privilege to receive TTL expired. Windows cannot get TTL expired.
[... Traceback ...]
ping3.errors.TimeToLiveExpired: Time exceeded: Time To Live expired.

>>> try:
>>>     pia("example.com", ttl=1)
>>> except asyncping3.errors.TimeToLiveExpired as err:
>>>     print(err.ip_header["src_addr"])  # TimeToLiveExpired, DestinationUnreachable and DestinationHostUnreachable have ip_header and icmp_header attached.
1.2.3.4  # IP address where the TTL happened.

>>> help(ping3.errors)  # More info about exceptions.

>>> try:
>>>     pia("invalid.com")
>>> except ping3.errors.HostUnknown:  # Specific error is catched.
>>>     print("Host unknown error raised.")
>>> except ping3.errors.PingError:  # All ping3 errors are subclasses of `PingError`.
>>>     print("A ping error raised.")
```

## Command Line Execution

Execute `pping` from command-line.
Note: `pping` needs `root` privilege to send/receive packets. You may want to use `sudo pping`.

```sh
$ pping --help  # -h/--help. Command-line help message.
$ python -m asyncping3 --help  # Same as 'ping3'. 'ping3' is an alias for 'python -m ping3'

$ pping -v  # -v/--version. Show asyncping3 version number.
3.0.0

$ pping example.com  # Verbose ping.
ping 'example.com' ... 215ms
ping 'example.com' ... 216ms
ping 'example.com' ... 219ms
ping 'example.com' ... 217ms

$ pping example.com 8.8.8.8  # Verbose ping all the addresses in parallel.
ping 'example.com' ... 215ms
ping 'example.com' ... 217ms
ping '8.8.8.8' ... 5ms
ping 'example.com' ... 216ms
ping '8.8.8.8' ... 2ms
ping '8.8.8.8' ... 6ms
ping 'example.com' ... 219ms
ping '8.8.8.8' ... 5ms

$ pping --count 1 example.com  # -c/--count. How many pings should be sent. Default is 4.
ping 'example.com' ... 215ms

$ pping --count 0 example.com  # Ping endlessly (0 means infinite loops). Using `ctrl + c` to stop manully.
...

$ pping --timeout 10 example.com  # -t/--timeout. Set timeout to 10 seconds. Default is 4.
ping 'example.com' ... 215ms
ping 'example.com' ... 216ms
ping 'example.com' ... 219ms
ping 'example.com' ... 217ms

$ pping --ttl 5 example.com  # -T/--ttl. # Set TTL to 5. Default is 64.
ping 'example.com' ... Timeout
ping 'example.com' ... Timeout
ping 'example.com' ... Timeout
ping 'example.com' ... Timeout

$ pping --size 56 example.com  # -s/--size. Set ICMP packet payload to 56 bytes. Default is 56.
ping 'example.com' ... 215ms
ping 'example.com' ... 216ms
ping 'example.com' ... 219ms
ping 'example.com' ... 217ms

$ pping --interval 5 example.com  # -i/--interval. Wait 5 seconds between each packet. Default is 0.
ping 'example.com' ... 215ms  # wait 5 secs
ping 'example.com' ... 216ms  # wait 5 secs
ping 'example.com' ... 219ms  # wait 5 secs
ping 'example.com' ... 217ms

$ pping --interface eth0 example.com  # -I/--interface. LINUX ONLY. The gateway network interface to ping from. Default is None.
ping 'example.com' ... 215ms
ping 'example.com' ... 216ms
ping 'example.com' ... 219ms
ping 'example.com' ... 217ms

$ pping --src 192.168.1.15 example.com  # -S/--src. Ping from source IP address for multiple network interfaces. Default is None.
ping 'example.com' ... 215ms
ping 'example.com' ... 216ms
ping 'example.com' ... 219ms
ping 'example.com' ... 217ms

$ pping --exceptions --timeout 0.001 example.com  # -E/--exceptions. EXCPETIONS mode is on when this shows up.
[... Traceback ...]
asyncping.errors.Timeout: Request timeout for ICMP packet. (Timeout = 0.0001s)

$ pping --debug --timeout 0.001 example.com  # -D/--debug. DEBUG mode is on when this shows up.
[DEBUG] Request timeout for ICMP packet. (Timeout = 0.001s)
ping 'example.com' ... Timeout > 0.001s
[DEBUG] Request timeout for ICMP packet. (Timeout = 0.001s)
ping 'example.com' ... Timeout > 0.001s
[DEBUG] Request timeout for ICMP packet. (Timeout = 0.001s)
ping 'example.com' ... Timeout > 0.001s
[DEBUG] Request timeout for ICMP packet. (Timeout = 0.001s)
ping 'example.com' ... Timeout > 0.001s
```
