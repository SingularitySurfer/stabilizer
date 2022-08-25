#!/usr/bin/python3
"""log swept sine experiments"""

import argparse
from curses import window
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.mlab as mlab
from scipy import signal

T = 0.1
f1 = 100
f2 = 100000

def main():
    parser = argparse.ArgumentParser(description="Record raw Stabilizer data")
    parser.add_argument(
        "--port", type=int, default=2345, help="Local port to listen on"
    )
    args = parser.parse_args()

    x = np.linspace(0, 0.1, 100000)
    y = np.sin((2*np.pi*f1*T / np.log(f2/f1)) * np.exp(np.log(f2/f1)*x / T)-1)

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
