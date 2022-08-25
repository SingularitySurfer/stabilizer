#!/usr/bin/python3
"""log swept sine experiments"""

import argparse
from curses import window
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.mlab as mlab
from scipy import signal


def main():
    parser = argparse.ArgumentParser(description="Record raw Stabilizer data")
    parser.add_argument(
        "--port", type=int, default=2345, help="Local port to listen on"
    )
    args = parser.parse_args()

    x = np.arange(0, 20000, 1)
    acc = np.uint32(50000)
    eps = np.uint32(37)
    y = []
    for i, xx in enumerate(x):
        y.append(np.sin(np.float64(acc)*(2**-22)*np.pi))
        accl = acc * (np.uint32(1<<16) + eps)
        acc = accl >> 16
        print(acc)

    fig, ax = plt.subplots(2, 1)
    ax[1].psd(y, len(y), 1, window=mlab.window_none)
    ax[1].set_xscale("log")
    # ax[1].set_xlim(1, 400000)
    ax[0].set_xlabel("Sampler Nr.")
    ax[0].set_ylabel("Amplitude (V)")
    ax[0].set_title("Time domain data")
    ax[0].grid()
    ax[0].plot(y)
    plt.show()  #
    plt.tight_layout()
    input()

if __name__ == "__main__":
    main()
