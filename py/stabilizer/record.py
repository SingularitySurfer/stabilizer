#!/usr/bin/python3
"""Record raw data from stream"""

import argparse
import asyncio
import miniconf
import socket
import csv

# import struct
# import socket
# from collections import namedtuple
# from dataclasses import dataclass

import numpy as np
import matplotlib.pyplot as plt
from scipy import signal

from stream import StabilizerStream, get_local_ip



async def main():
    parser = argparse.ArgumentParser(description="Record raw Stabilizer data")
    parser.add_argument(
        "--port", type=int, default=2345, help="Local port to listen on"
    )
    parser.add_argument(
        "--host", default="10.42.0.1", help="Local address to listen on"
    )
    parser.add_argument(
        "--channel",
        "-c",
        type=int,
        choices=[0, 1],
        default=0,
        help="The channel to operate on",
    )
    parser.add_argument(
        "--filename", type=str, default="raw.csv", help="File to safe the data in."
    )
    parser.add_argument(
        "--frames", type=int, default=1000, help="Nr frames to record"
    )
    args = parser.parse_args()

    transport, stream = await StabilizerStream.open((args.host, args.port))
    # Increase the OS UDP receive buffer size to 4 MiB so that latency
    # spikes don't impact much. Achieving 4 MiB may require increasing
    # the max allowed buffer size, e.g. via
    # `sudo sysctl net.core.rmem_max=26214400` but nowadays the default
    # max appears to be ~ 50 MiB already.
    sock = transport.get_extra_info("socket")
    if sock is not None:
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, 4 << 20)

    data = []
    file = open(args.filename, "w")
    writer = csv.writer(file)

    while not stream.queue.empty():
        stream.queue.get_nowait()
    await stream.queue.get()

    for _ in range(args.frames):
        frame = await stream.queue.get()
        data.extend(frame.to_si()["adc"][args.channel])

    for d in data:
        writer.writerow([d])
    
    print("done")

if __name__ == "__main__":
    data = asyncio.run(main())