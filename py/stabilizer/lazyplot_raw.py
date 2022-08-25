from matplotlib import pyplot as plt
import csv
import argparse
import numpy as np

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
    # data = signal.detrend(data)
    _, ax = plt.subplots(2, 1)
    pxx, freqs = ax[1].psd(data, len(data), F_S)
    ax[1].set_xscale("log")
    ax[1].set_xlim(1, 400000)
    ax[0].set_xlabel("Sampler Nr.")
    ax[0].set_ylabel("Amplitude (V)")
    ax[0].set_title("Time domain data")
    ax[0].grid()
    ax[0].plot(data)
    ax[0].margins(0, 0.1)

    sum = 0
    nr_samples = 0
    for f, p in zip(freqs, pxx):
        if f < 20000.0:
            sum += p
            nr_samples += 1

    # 0.01 - 1 Hz -> ~1Hz bandwidth
    rms_noise = np.sqrt(sum/nr_samples)

    print(f"20000 Hz rms noise: {rms_noise}")
    
    plt.show()  #
    plt.tight_layout()


if __name__ == "__main__":
    main()
