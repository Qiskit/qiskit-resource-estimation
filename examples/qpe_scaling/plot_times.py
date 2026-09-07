import numpy as np
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D

files = [
    ("./qpe_swaprouting.npy", "SWAP routing", "seagreen"),
    ("./qpe_telbest.npy", "Best-case teleportation routing", "royalblue"),
    # ("./qpe_telworst.npy", "Worst-case teleportation routing", "cornflowerblue"),
    # ("./qpe_swaprouting_ucx.npy", "U+CX, SWAP-route", "crimson"),
    ("./qpe_fullcompile.npy", "Qiskit", "crimson"),
]


def plot(time_ax, fid_ax, fname, label, color):
    data = np.load(fname, allow_pickle=True).item()

    num_qubits = []
    runtimes = []
    fids = []
    magic = []
    entanglement = []

    for (_, n), datum in data.items():
        if n < 10:
            # skip artifacts
            continue
        num_qubits.append(n)
        runtimes.append(datum["runtime"])
        fids.append(datum["Fidelity"])
        magic.append(datum["TFidelity"])
        entanglement.append(datum["InterFidelity"])

    fid_ax.loglog(num_qubits, fids, "o-", c=color, label=label)
    fid_ax.loglog(num_qubits, magic, c=color, ls="-.")
    fid_ax.loglog(num_qubits, entanglement, c=color, ls=":")
    time_ax.loglog(num_qubits, runtimes, c=color, label=label)


# _, (ax1, ax2) = plt.subplots(2, 1, figsize=(4, 6))
_, (ax1, ax2) = plt.subplots(1, 2, figsize=(10, 4))
ax1.set_xlabel("num Ising qubits")
ax1.set_ylabel("fidelity")
# ax1.set_ylim(top=2, bottom=1e-10)

custom_lines = [
    Line2D([0], [0], color="k", linestyle="--", label="Total fidelity"),
    Line2D([0], [0], color="k", linestyle="-.", label="Magic"),
    Line2D([0], [0], color="k", linestyle=":", label="Entanglement"),
]
ax1.grid()
ax1.legend(handles=custom_lines)

ax2.grid()
ax2.set_xlabel("num Ising qubits")
ax2.set_ylabel("runtime [s]")

for fname, label, color in files:
    plot(ax2, ax1, fname, label, color)

plt.legend(loc="best")
plt.tight_layout()
plt.show()
