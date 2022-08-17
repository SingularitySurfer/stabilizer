#!/usr/bin/python3
"""Record a transfer function with Stabilizer using the signal generator and streaming"""

import argparse
import asyncio
from time import sleep
from xml.etree.ElementPath import find
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

F_MIN = 10
F_MAX = 10000
POINTS = 10
AMPLITUDE = 1
F_SAMPLE = 781250
PERIODS_PER_BIN = 10
MAX_FRAMES = 1000  # maximim nr frames per freq bin
SETTINGS_DELAY = 1e-2 # delay to wait for after updating miniconf settings


async def main():
    parser = argparse.ArgumentParser(
        description="Record a Stabilizer Transfer Function"
    )
    parser.add_argument(
        "--port", type=int, default=2345, help="Local port to listen on"
    )
    parser.add_argument(
        "--host", default="10.42.0.1", help="Local address to listen on"
    )
    parser.add_argument("--broker", default="10.42.0.1", help="MQTT broker")
    parser.add_argument(
        "--channel",
        "-c",
        type=int,
        choices=[0, 1],
        default=0,
        help="The channel to operate on",
    )
    parser.add_argument(
        "--prefix",
        "-p",
        type=str,
        default="dt/sinara/dual-iir/04-91-62-d9-83-19",
        help="The device prefix in MQTT, wildcards allowed as "
        "long as the match is unique (%(default)s)",
    )
    parser.add_argument(
        "--bins", type=int, default=100, help="nr frequency bins to record"
    )
    parser.add_argument(
        "--f_min", type=int, default=100, help="lowest frequency bin"
    )
    parser.add_argument(
        "--f_max", type=int, default=1000, help="highest frequency bin"
    )
    args = parser.parse_args()

    conf = await miniconf.Miniconf.create(args.prefix, args.broker)
    transport, stream = await StabilizerStream.open((args.host, args.port))
    # Increase the OS UDP receive buffer size to 4 MiB so that latency
    # spikes don't impact much. Achieving 4 MiB may require increasing
    # the max allowed buffer size, e.g. via
    # `sudo sysctl net.core.rmem_max=26214400` but nowadays the default
    # max appears to be ~ 50 MiB already.
    sock = transport.get_extra_info("socket")
    if sock is not None:
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, 4 << 20)

    await conf.command(
        "stream_target",
        {"ip": get_local_ip(args.broker), "port": args.port},
        retain=False,
    )
    await conf.command(f"signal_generator/{args.channel}/amplitude", AMPLITUDE)

    data = []
    tf = []
    f_run = []

    fig, ax = plt.subplots()
    plt.ion()

    file = open("data.csv", "w")
    writer = csv.writer(file)

    freqs = np.linspace(args.f_min, args.f_max, args.bins)
    for f in freqs:
        print(f)
        f_run.append(f)
        await conf.command(f"signal_generator/{args.channel}/frequency", int(f))
        await asyncio.sleep(SETTINGS_DELAY)
        while not stream.queue.empty():
            stream.queue.get_nowait()
        await stream.queue.get()

        n_bin_samples = int(
            PERIODS_PER_BIN * (F_SAMPLE / f)
        )  # calc nr samples per freq pin
        for _ in range(MAX_FRAMES):
            frame = await stream.queue.get()
            data.extend(frame.to_si()["adc"][args.channel])
            # if len(data) > n_bin_samples:
            #     break
        # ax.plot(data)
        # plt.psd(data, len(data), F_SAMPLE)
        freqs, psd = signal.welch(data, F_SAMPLE, nperseg=len(data))
        idx = (np.abs(freqs - f)).argmin() # get closest index
        power = 10 * np.log10(psd[idx])
        print(f"frequency: {freqs[idx]} power: {power}")
        tf.append(power)
        ax.plot(f_run, tf)
        writer.writerow([power])
        data = []
        plt.pause(0.0001)

    file.close()
    print("done")
    input()

def find_nearest(array, value):
    array = np.asarray(array)
    idx = (np.abs(array - value)).argmin()
    return array[idx]

if __name__ == "__main__":
    asyncio.run(main())
