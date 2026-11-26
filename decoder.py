import numpy as np
import pymatching
import matplotlib.pyplot as plt
from pathlib import Path

from memory import MemoryCircuitBuilder

def evaluate_memory(distance, rounds, p_data, p_measure, shots):

    builder = MemoryCircuitBuilder(
        distance=distance,
        rounds=rounds,
        p_data=p_data,
        p_measure=p_measure
    )

    circuit = builder.build()

    sampler = circuit.compile_detector_sampler()
    events, observable_flips = sampler.sample(
        shots=shots,
        separate_observables=True
    )

    error_model = circuit.detector_error_model(
        decompose_errors=True
    )

    matcher = pymatching.Matching.from_detector_error_model(
        error_model
    )

    predictions = matcher.decode_batch(events)

    # 今回はオブザーバブルが1個なので、0列目を使う
    actual = observable_flips[:, 0]
    predicted = predictions[:, 0]

    failures = actual != predicted

    num_before = np.count_nonzero(actual)
    num_after = np.count_nonzero(failures)

    return num_before, num_after

if __name__ == "__main__":
    shots = 100000
    rounds = 3

    p_data_list = [0.005, 0.01, 0.02, 0.03, 0.05, 0.07, 0.1]
    distance_list = [3, 5, 7]

    fig, ax = plt.subplots()

    for distance in distance_list:
        logical_rates = []

        for p_data in p_data_list:

            num_before, num_after = evaluate_memory(
                distance=distance,
                rounds=rounds,
                p_data=p_data,
                p_measure=p_data,
                shots=shots,
            )

            logical_rate = num_after / shots
            logical_rates.append(logical_rate)

            print(
                f"d={distance}, p={p_data}: "
                f"{num_after}/{shots} = {logical_rate}"
            )

        rates = np.array(logical_rates)
        plotted_rates = np.where(rates > 0, rates, np.nan)

        ax.plot(
            p_data_list,
            plotted_rates,
            marker="o",
            label=f"d={distance}",
        )

    ax.set_xscale("log")
    ax.set_yscale("log")

    ax.set_xlabel("Noise parameter p (p_data = p_measure = p)")
    ax.set_ylabel("Logical Z readout failure rate per shot")
    ax.set_title(f"Z memory: {rounds} rounds, data and measurement noise")

    ax.legend()
    ax.grid(True, which="both", alpha=0.3)

    fig.tight_layout()

    # decoder.pyと同じstimフォルダに保存する
    path = Path(__file__).resolve().with_name("logical_error_rate_with_measurement_noise.png")
    fig.savefig(path, dpi=200)

    plt.show()