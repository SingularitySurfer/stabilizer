#!/usr/bin/python3
"""Record a transfer function with Stabilizer using the signal generator and streaming"""

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

AMPLITUDE = 0.01
F_SAMPLE = 781250
PERIODS_PER_BIN = 10
MAX_FRAMES = 1000  # maximim nr frames per freq bin
SETTINGS_DELAY = 1e-2  # delay to wait for after updating miniconf settings


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
        help="The device prefix in MQTT",
    )
    parser.add_argument(
        "--bins", type=int, default=100, help="nr frequency bins to record"
    )
    parser.add_argument("--f_min", type=int, default=100, help="lowest frequency bin")
    parser.add_argument(
        "--f_max", type=int, default=100000, help="highest frequency bin"
    )
    parser.add_argument(
        "--filename", type=str, default="data.csv", help="File to safe the data in."
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
    ax.grid()
    plt.ion()

    file = open(args.filename, "w")
    writer = csv.writer(file)

    freqs = np.linspace(args.f_min, args.f_max, args.bins)
    first = True
    scale = 0.0
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
        # for d in data:
        #     writer.writerow([d])

        freqs, psd = signal.welch(data, F_SAMPLE, window="flattop", nperseg=len(data))
        # for d in psd:
        #     writer.writerow([10 * np.log10(d)])
        idx = (np.abs(freqs - f)).argmin()  # get closest index
        power = (
            10 * np.log10(psd[idx - 10 : idx + 10].max()) if idx > 3 else psd[idx]
        )  # still search in vicinity
        if first:
            scale = power
        power = power - scale
        print(f"frequency: {freqs[idx]} power: {power}")
        tf.append(power)
        ax.plot(f_run, tf)
        writer.writerow([power])
        data = []
        plt.pause(0.0001)
        first = False

    file.close()
    print("done")
    input()


if __name__ == "__main__":
    asyncio.run(main())
