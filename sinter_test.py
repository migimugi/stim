from pathlib import Path

import matplotlib.pyplot as plt
import sinter

from memory import MemoryCircuitBuilder


if __name__ == "__main__":
    output_dir = Path(__file__).resolve().parent
    circuit_dir = output_dir / "circuits"
    circuit_dir.mkdir(exist_ok=True)

    rounds = 3
    shots = 100_000
    distances = [3, 5, 7]
    noise_rates = [0.005, 0.01, 0.02, 0.03, 0.05, 0.07, 0.1]

    tasks = []

    for distance in distances:
        for p in noise_rates:
            builder = MemoryCircuitBuilder(
                distance=distance,
                rounds=rounds,
                p_data=p,
                p_measure=p,
            )
            circuit = builder.build()

            # 評価に使う回路を.stimファイルとして保存
            circuit_path = circuit_dir / (
                f"memory_z_d{distance}_r{rounds}_p{p}.stim"
            )
            circuit.to_file(circuit_path)

            # sinterに評価条件を渡す
            tasks.append(
                sinter.Task(
                    circuit=circuit,
                    json_metadata={
                        "d": distance,
                        "rounds": rounds,
                        "p": p,
                    },
                )
            )

    # サンプリングとデコードを行い、結果を保存
    stats = sinter.collect(
        num_workers=2,
        tasks=tasks,
        decoders=["pymatching"],
        max_shots=shots,
        save_resume_filepath=output_dir / "sinter_results.csv",
        print_progress=True,
    )

    fig, ax = plt.subplots()

    sinter.plot_error_rate(
        ax=ax,
        stats=stats,
        x_func=lambda stat: stat.json_metadata["p"],
        group_func=lambda stat: f"d={stat.json_metadata['d']}",
    )

    ax.set_xscale("log")
    ax.set_yscale("log")
    ax.set_xlabel("Noise parameter p (p_data = p_measure = p)")
    ax.set_ylabel("Logical Z readout failure rate per shot")
    ax.set_title(f"Z memory: {rounds} rounds")
    ax.grid(True, which="both", alpha=0.3)
    ax.legend()

    fig.tight_layout()
    fig.savefig(output_dir / "sinter_error_rate.pdf")
    plt.show()