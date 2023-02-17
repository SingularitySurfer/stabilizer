#!/usr/bin/python3
# evaluate raw adc samples from text file
import numpy as np
import matplotlib.pyplot as plt

# first lines is startup prints
skip = 3000
no_samples = 10000

file = "2_driver_voltage.txt"

f = open(file, "r")
data = list(
    map(
        float,
        [s[7:] for s in f.readlines()[skip : no_samples + skip]],
    )
)
f.close()

std_dev = np.std(data)
print(f"std deviation: {std_dev}")
fig, ax = plt.subplots(1)
# fig.tight_layout()
# ax.plot(data)
# ax.grid()
# ax.set_xlim(0, no_samples)
# # ax.text(0.75, 0.1, f'standard deviation: {std_dev}', transform=ax.transAxes,
# #            verticalalignment='top', bbox=dict(facecolor='none', edgecolor='black', boxstyle='round'))
# ax.set_title("Time domain data")
# ax.set_xlabel("sample nr.")
# ax.set_ylabel("adc code")
ax.psd(data, Fs=1, NFFT=len(data))

plt.show()
input()
