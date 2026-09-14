import numpy as np
import matplotlib.pyplot as plt

files = [
    ("./qpe_swaproute_g1p3.npy", "Gross ($p=10^{-3}$)", "lightsalmon"),
    ("./qpe_swaprouting.npy", "Gross ($p=10^{-4}$)", "crimson"),
    ("./qpe_swaproute_g2p3.npy", "Two-Gross ($p=10^{-3}$)", "cornflowerblue"),
    ("./qpe_swaproute_g2p4.npy", "Two-Gross ($p=10^{-4}$)", "royalblue"),
]


def plot(fid_ax, fname, label, color):
    data = np.load(fname, allow_pickle=True).item()

    num_qubits = []
    fids = []
    # magic = []
    # entanglement = []

    for (_, n), datum in data.items():
        if n < 10:
            # skip artifacts
            continue
        num_qubits.append(n)
        fids.append(datum["Fidelity"])
        # magic.append(datum["TFidelity"])
        # entanglement.append(datum["InterFidelity"])

    fid_ax.loglog(num_qubits, fids, "o-", c=color, label=label)
    # fid_ax.loglog(num_qubits, magic, c=color, ls="-.")
    # fid_ax.loglog(num_qubits, entanglement, c=color, ls=":")


# _, (ax1, ax2) = plt.subplots(2, 1, figsize=(4, 6))
_, ax = plt.subplots(1, 1, figsize=(5, 4))
ax.set_ylim(bottom=1e-9, top=2)
ax.set_xlabel("num Ising qubits")
ax.set_ylabel("fidelity")
ax.grid()

for fname, label, color in files:
    plot(ax, fname, label, color)

plt.title("Different error models")
plt.legend(loc="best")
plt.tight_layout()
plt.show()
