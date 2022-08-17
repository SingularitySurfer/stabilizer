from matplotlib import pyplot as plt
import csv
import argparse
from scipy import signal

F_S = 781250


def main():
    parser = argparse.ArgumentParser(description="Record raw Stabilizer data")
    parser.add_argument(
        "--filename", type=str, default="data.csv", help="File to safe the data in."
    )
    args = parser.parse_args()
    f = open(args.filename, "r")
    reader = csv.reader(f)
    data = []
    for i, row in enumerate(reader):
        data.append(float(row[0]))
    data = signal.detrend(data)
    fig, ax = plt.subplots(2, 1)
    ax[1].psd(data, len(data), F_S)
    ax[1].set_xscale("log")
    ax[1].set_xlim(1, 400000)
    ax[0].set_xlabel("Sampler Nr.")
    ax[0].set_ylabel("Amplitude (V)")
    ax[0].set_title("Rec_data")
    ax[0].grid()
    ax[0].plot(data)
    plt.show()  #
    plt.tight_layout()


if __name__ == "__main__":
    main()
