#!/usr/bin/env python

import os
import socket
import struct
import time
import platform
import logging
import functools
import errno
import anyio
from importlib.metadata import version

from . import errors
from .enums import ICMP_DEFAULT_CODE, IcmpType, IcmpTimeExceededCode, IcmpDestinationUnreachableCode

DEBUG = False  # DEBUG: Show debug info for developers. (default False)
EXCEPTIONS = False  # EXCEPTIONS: Raise exception when delay is not available.
LOGGER = None  # LOGGER: Record logs into console or file. Logger object should have .debug() method.

IP_HEADER_FORMAT = "!BBHHHBBHII"
ICMP_HEADER_FORMAT = "!BBHHH"  # According to netinet/ip_icmp.h. !=network byte order(big-endian), B=unsigned char, H=unsigned short
ICMP_TIME_FORMAT = "!d"  # d=double
SOCKET_SO_BINDTODEVICE = 25  # socket.SO_BINDTODEVICE


def _debug(*args) -> None:
    """Print debug info to stdout if `asyncping3.DEBUG` is True.

    Args:
        *args (any): Usually are strings or objects that can be converted to str.
    """
    def get_logger():
        logger = logging.getLogger(__name__)
        logger.setLevel(logging.DEBUG)
        formatter = logging.Formatter('[%(levelname)s] %(message)s')
        cout_handler = logging.StreamHandler()
        cout_handler.setLevel(logging.DEBUG)
        cout_handler.setFormatter(formatter)
        logger.addHandler(cout_handler)
        v,_ = version("asyncping3")
        logger.debug("AsyncPing Version: {}".format(v))
        logger.debug("LOGGER: {}".format(logger))
        return logger

    if not DEBUG:
        return None
    global LOGGER
    LOGGER = LOGGER or get_logger()
    message = " ".join(str(item) for item in args)
    LOGGER.debug(message)


def _raise(err: Exception) -> None:
    """Raise exception if `asyncping3.EXCEPTIONS` is True.

    Args:
        err (Exception): Exception to be raised.

    Raise:
        Exception: Exception passed in args will be raised if `asyncping3.EXCEPTIONS` is True.
    """
    if EXCEPTIONS:
        raise err


def _func_logger(func):
    """Decorator that log function calls for debug

    Args:
        func (callable): Function to be decorated.

    Returns:
        callable: Decorated function.
    """
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        pargs = ", ".join(str(arg) for arg in args)
        kargs = str(kwargs) if kwargs else ""
        all_args = ", ".join((pargs, kargs)) if (pargs and kargs) else (pargs or kargs)
        _debug("Function called:", "{func.__name__}({})".format(all_args, func=func))
        func_return = func(*args, **kwargs)
        _debug("Function returned:", "{func.__name__} -> {rtrn}".format(func=func, rtrn=func_return))
        return func_return

    return wrapper


def _async_func_logger(func: callable) -> callable:
    """Decorator that log function calls for debug

    Args:
        func: Function to be decorated.

    Returns:
        Decorated function.
    """
    @functools.wraps(func)
    async def wrapper(*args, **kwargs):
        pargs = ", ".join("'{}'".format(arg) if isinstance(arg, str) else arg for arg in args)
        kargs = str(kwargs) if kwargs else ""
        all_args = ", ".join((pargs, kargs)) if (pargs and kargs) else (pargs or kargs)
        _debug("Function Called:", "{func.__name__}({})".format(all_args, func=func))
        func_return = await func(*args, **kwargs)
        _debug("Function Returned:", "{func.__name__} -> {rtrn}".format(func=func, rtrn=func_return))
        return func_return

    return wrapper


def checksum(source: bytes) -> int:
    """Calculates the checksum of the input bytes.

    RFC1071: https://tools.ietf.org/html/rfc1071
    RFC792: https://tools.ietf.org/html/rfc792

    Args:
        source (Bytes): The input to be calculated.

    Returns:
        int: Calculated checksum.
    """
    BITS = 16  # 16-bit long
    carry = 1 << BITS  # 0x10000
    result = sum(source[::2]) + (sum(source[1::2]) << (BITS // 2))  # Even bytes (odd indexes) shift 1 byte to the left.
    while result >= carry:  # Ones' complement sum.
        result = sum(divmod(result, carry))  # Each carry add to right most bit.
    return ~result & ((1 << BITS) - 1)  # Ensure 16-bit


def read_icmp_header(raw: bytes) -> dict:
    """Get information from raw ICMP header data.

    Args:
        raw (Bytes): Raw data of ICMP header.

    Returns:
        dict: A map contains the infos from the raw header.
    """
    icmp_header_keys = ('type', 'code', 'checksum', 'id', 'seq')
    return dict(zip(icmp_header_keys, struct.unpack(ICMP_HEADER_FORMAT, raw)))


def read_ip_header(raw: bytes) -> dict:
    """Get information from raw IP header data.

    Args:
        raw (Bytes): Raw data of IP header.

    Returns:
        dict: A map contains the infos from the raw header.
    """
    def stringify_ip(ip: int) -> str:
        return ".".join(str(ip >> offset & 0xff) for offset in (24, 16, 8, 0))  # str(ipaddress.ip_address(ip))

    ip_header_keys = ('version', 'tos', 'len', 'id', 'flags', 'ttl', 'protocol', 'checksum', 'src_addr', 'dest_addr')
    ip_header = dict(zip(ip_header_keys, struct.unpack(IP_HEADER_FORMAT, raw)))
    ip_header['src_addr'] = stringify_ip(ip_header['src_addr'])
    ip_header['dest_addr'] = stringify_ip(ip_header['dest_addr'])
    return ip_header


@_async_func_logger
async def send_one_ping(sock: socket.socket, dest_addr: str, icmp_id: int, seq: int, size: int) -> None:
    """Sends one ping to the given destination.

    ICMP Header (bits): type (8), code (8), checksum (16), id (16), sequence (16)
    ICMP Payload: time (double), data
    ICMP Wikipedia: https://en.wikipedia.org/wiki/Internet_Control_Message_Protocol

    Args:
        sock (socket.socket): Socket.
        dest_addr (str): The destination address, can be an IP address or a domain name. Ex. "192.168.1.1"/"example.com"
        icmp_id (int): ICMP packet id. Calculated from Process ID and Thread ID.
        seq (int): ICMP packet sequence, usually increases from 0 in the same process.
        size (int): The ICMP packet payload size in bytes. Note this is only for the payload part.

    Raises:
        HostUnkown: If destination address is a domain name and cannot resolved.
    """
    _debug("Destination address: '{}'".format(dest_addr))
    try:
        dest_addr = (await anyio.getaddrinfo(dest_addr, 0, family=socket.AF_INET))[0][4][0]
    except socket.gaierror as err:
        raise errors.HostUnknown(dest_addr=dest_addr) from err
    _debug("Destination IP address:", dest_addr)
    pseudo_checksum = 0  # Pseudo checksum is used to calculate the real checksum.
    icmp_header = struct.pack(ICMP_HEADER_FORMAT, IcmpType.ECHO_REQUEST, ICMP_DEFAULT_CODE, pseudo_checksum, icmp_id, seq)
    padding = (size - struct.calcsize(ICMP_TIME_FORMAT)) * "Q"  # Using double to store current time.
    icmp_payload = struct.pack(ICMP_TIME_FORMAT, time.time()) + padding.encode()
    real_checksum = checksum(icmp_header + icmp_payload)  # Calculates the checksum on the dummy header and the icmp_payload.
    # Don't know why I need socket.htons() on real_checksum since ICMP_HEADER_FORMAT already in Network Bytes Order (big-endian)
    icmp_header = struct.pack(ICMP_HEADER_FORMAT, IcmpType.ECHO_REQUEST, ICMP_DEFAULT_CODE, socket.htons(real_checksum), icmp_id, seq)  # Put real checksum into ICMP header.
    _debug("Sent ICMP header:", read_icmp_header(icmp_header))
    _debug("Sent ICMP payload:", icmp_payload)
    packet = icmp_header + icmp_payload
    await anyio.wait_socket_writable(sock)
    sock.sendto(packet, (dest_addr, 0))  # addr = (ip, port). Port is 0 respectively the OS default behavior will be used.


@_async_func_logger
async def receive_one_ping(sock: socket, icmp_id: int, seq: int, timeout: int) -> float:
    """Receives the ping from the socket.

    IP Header (bits): version (8), type of service (8), length (16), id (16), flags (16), time to live (8), protocol (8), checksum (16), source ip (32), destination ip (32).
    ICMP Packet (bytes): IP Header (20), ICMP Header (8), ICMP Payload (*).
    Ping Wikipedia: https://en.wikipedia.org/wiki/Ping_(networking_utility)
    ToS (Type of Service) in IP header for ICMP is 0. Protocol in IP header for ICMP is 1.

    Args:
        sock (socket.socket): The same socket used for send the ping.
        icmp_id (int): ICMP packet id. Sent packet id should be identical with received packet id.
        seq (int): ICMP packet sequence. Sent packet sequence should be identical with received packet sequence.
        timeout (int): Timeout in seconds.

    Returns:
        float | None: The delay in seconds or None on timeout.

    Raises:
        TimeToLiveExpired: If the Time-To-Live in IP Header is not large enough for destination.
        TimeExceeded: If time exceeded but Time-To-Live does not expired.
        DestinationHostUnreachable: If the destination host is unreachable.
        DestinationUnreachable: If the destination is unreachable.
    """
    has_ip_header = (os.name != 'posix') or (platform.system() == 'Darwin') or (sock.type == socket.SOCK_RAW)  # No IP Header when unprivileged on Linux.
    if has_ip_header:
        ip_header_slice = slice(0, struct.calcsize(IP_HEADER_FORMAT))  # [0:20]
        icmp_header_slice = slice(ip_header_slice.stop, ip_header_slice.stop + struct.calcsize(ICMP_HEADER_FORMAT))  # [20:28]
    else:
        _debug("Unprivileged on Linux")
        icmp_header_slice = slice(0, struct.calcsize(ICMP_HEADER_FORMAT))  # [0:8]
    timeout_time = time.time() + timeout  # Exactly time when timeout.
    _debug("Timeout time: {} ({})".format(time.ctime(timeout_time), timeout_time))
    with anyio.fail_after(timeout):
        while True:
            await anyio.wait_socket_readable(sock)
            time_recv = time.time()
            recv_data, addr = sock.recvfrom(1024)
            _debug("Received time: {} ({}))".format(time.ctime(time_recv), time_recv))
            if has_ip_header:
                ip_header_raw = recv_data[ip_header_slice]
                ip_header = read_ip_header(ip_header_raw)
                _debug("Received IP Header:", ip_header)
            else:
                ip_header = None
            icmp_header_raw, icmp_payload_raw = recv_data[icmp_header_slice], recv_data[icmp_header_slice.stop:]
            icmp_header = read_icmp_header(icmp_header_raw)
            _debug("Received ICMP Header:", icmp_header)
            _debug("Received ICMP Payload:", icmp_payload_raw)
            if not has_ip_header:  #  When unprivileged on Linux, ICMP ID is rewrited by kernel.
                icmp_id = sock.getsockname()[1]  # According to https://stackoverflow.com/a/14023878/4528364
            if icmp_header['id'] and icmp_header['id'] != icmp_id:  # ECHO_REPLY should match the ID field.
                _debug("ICMP ID dismatch. Packet filtered out.")
                continue
            if icmp_header['type'] == IcmpType.ECHO_REQUEST:  # filters out the ECHO_REQUEST itself.
                _debug("ECHO_REQUEST received. Packet filtered out.")
                continue
            if icmp_header['type'] == IcmpType.TIME_EXCEEDED:  # TIME_EXCEEDED has no icmp_id and icmp_seq. Usually they are 0.
                if icmp_header['code'] == IcmpTimeExceededCode.TTL_EXPIRED:
                    raise errors.TimeToLiveExpired()  # Some router does not report TTL expired and then timeout shows.
                raise errors.TimeExceeded()
            if icmp_header['type'] == IcmpType.DESTINATION_UNREACHABLE:  # DESTINATION_UNREACHABLE has no icmp_id and icmp_seq. Usually they are 0.
                if icmp_header['code'] == IcmpDestinationUnreachableCode.DESTINATION_HOST_UNREACHABLE:
                    raise errors.DestinationHostUnreachable()
                raise errors.DestinationUnreachable()
            if icmp_header['id'] != icmp_id:  # ECHO_REPLY should match the ICMP ID field.
                _debug("ICMP ID dismatch. Packet filtered out.")
                continue
            if icmp_header['seq'] != seq:  # ECHO_REPLY should match the ICMP SEQ field.
                _debug("IMCP SEQ dismatch. Packet filtered out.")
                continue
            if icmp_header['type'] == IcmpType.ECHO_REPLY:
                time_sent = struct.unpack(ICMP_TIME_FORMAT, icmp_payload_raw[0:struct.calcsize(ICMP_TIME_FORMAT)])[0]
                _debug("Received sent time: {} ({})".format(time.ctime(time_sent), time_sent))
                return time_recv - time_sent
        _debug("Ignored ICMP packet:", icmp_header)

_seq_id = 0

@_async_func_logger
async def ping(dest_addr: str, timeout: int = 4, unit: str = "s", src_addr: str = None, ttl: int = None, seq: int = 0, size: int = 56, interface: str = None) -> float:
    """
    Send one ping to destination address with the given timeout.

    Args:
        dest_addr (str): The destination address, can be an IP address or a domain name. Ex. "192.168.1.1"/"example.com"
        timeout (int): Time to wait for a response, in seconds. Default is 4s, same as Windows CMD. (default 4)
        unit (str): The unit of returned value. "s" for seconds, "ms" for milliseconds. (default "s")
        src_addr (str): The IP address to ping from. This is for multiple network interfaces. Ex. "192.168.1.20". (default "")
        interface (str): LINUX ONLY. The gateway network interface to ping from. Ex. "wlan0". (default "")
        ttl (int | None): The Time-To-Live of the outgoing packet. Default is None, which means using OS default ttl -- 64 onLinux and macOS, and 128 on Windows. (default None)
        seq (int): ICMP packet sequence, usually increases from 0 in the same process. (default 0)
        size (int): The ICMP packet payload size in bytes. If the input of this is less than the bytes of a double format (usually 8), the size of ICMP packet payload is 8 bytes to hold a time. The max should be the router_MTU(Usually 1480) - IP_Header(20) - ICMP_Header(8). Default is 56, same as in macOS. (default 56)

    Returns:
        float | None | False: The delay in seconds/milliseconds, False on error and None on timeout.

    Raises:
        PingError: Any PingError will raise again if `asyncping3.EXCEPTIONS` is True.
    """
    global _seq_id

    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_RAW, socket.IPPROTO_ICMP)
    except PermissionError as err:
        if err.errno == errno.EPERM:  # [Errno 1] Operation not permitted
            _debug("`{}` when create socket.SOCK_RAW, using socket.SOCK_DGRAM instead.".format(err))
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_ICMP)
        else:
            raise err
    with sock:
        if ttl:
            try:  # IPPROTO_IP is for Windows and BSD Linux.
                if sock.getsockopt(socket.IPPROTO_IP, socket.IP_TTL):
                    sock.setsockopt(socket.IPPROTO_IP, socket.IP_TTL, ttl)
            except OSError as err:
                _debug("Set Socket Option `IP_TTL` in `IPPROTO_IP` Failed: {}".format(err))
            try:
                if sock.getsockopt(socket.SOL_IP, socket.IP_TTL):
                    sock.setsockopt(socket.SOL_IP, socket.IP_TTL, ttl)
            except OSError as err:
                _debug("Set Socket Option `IP_TTL` in `SOL_IP` Failed: {}".format(err))
        if interface:
            sock.setsockopt(socket.SOL_SOCKET, SOCKET_SO_BINDTODEVICE, interface.encode())  # packets will be sent from specified interface.
            _debug("Socket Interface Binded:", interface)
        if src_addr:
            sock.bind((src_addr, 0))  # only packets send to src_addr are received.
            _debug("Socket Source Address Binded:", src_addr)
        process_id = os.getpid()  # If ping() run under different process, thread_id may be identical.
        icmp_id = (((process_id << 5) | _seq_id) ^ (process_id >> 11)) & 0xffff  # to avoid icmp_id collision.
        _seq_id += 1
        try:
            await send_one_ping(sock=sock, dest_addr=dest_addr, icmp_id=icmp_id, seq=seq, size=size)
            try:
                delay = await receive_one_ping(sock=sock, icmp_id=icmp_id, seq=seq, timeout=timeout)  # in seconds
            except TimeoutError:
                raise errors.Timeout(timeout=timeout) from None
        except errors.HostUnknown as err:  # Unsolved
            _debug(err)
            _raise(err)
            return False
        except errors.PingError as err:
            _debug(err)
            _raise(err)
            return None
        except errors.PingError as err:
            _debug(err)
            _raise(err)
            return False
        if delay is None:
            return None
        if unit == "ms":
            delay *= 1000  # in milliseconds
        return delay


@_async_func_logger
async def verbose_ping(dest_addr: str, count: int = 4, interval: float = 0, *args, **kwargs):
    """
    Send pings to destination address with the given timeout and display the result.

    Args:
        dest_addr (str): The destination address. Ex. "192.168.1.1"/"example.com"
        count (int): How many pings should be sent. 0 means infinite loops until manually stopped. Default is 4, same as Windows CMD. (default 4)
        interval (float): How many seconds between two packets. Default is 0, which means send the next packet as soon as the previous one responsed. (default 0)
        *args and **kwargs (any): And all the other arguments available in ping() except `seq`.

    Output:
        Formatted ping results printed.
    """
    timeout = kwargs.get("timeout")
    src = kwargs.get("src_addr")
    unit = kwargs.setdefault("unit", "ms")
    i = 0
    while i < count or count == 0:
        if interval > 0 and i > 0:
            await anyio.sleep(interval)
        output_text = "ping '{}'".format(dest_addr)
        output_text += " from '{}'".format(src) if src else ""
        output_text += " ... "
        delay = await ping(dest_addr, seq=i, *args, **kwargs)
        print(output_text, end="")
        if delay is None:
            print("Timeout > {}s".format(timeout) if timeout else "Timeout")
        elif delay is False:
            print("Error")
        else:
            print("{value}{unit}".format(value=int(delay), unit=unit))
        i += 1
