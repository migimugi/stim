from layout import SurfaceCodeLayout
from operation import Operation
from measurement_tracker import MeasurementTracker
from noise import Noise

class MemoryCircuitBuilder:
    def __init__(self, distance, rounds, p_data=0.0, p_measure=0.0):
        self.layout = SurfaceCodeLayout(distance)
        self.op = Operation()
        self.tracker = MeasurementTracker()
        self.rounds = rounds
        self.round_index = 0
        self.observable_index = 0
        self.noise = Noise(p_data, p_measure)

        for index, coord in enumerate(self.layout.location.coords):
            self.op.circuit.append("QUBIT_COORDS", [index], coord)

    def initialize_z(self):
        self.op.reset_z(self.layout.data_qubits)
        self.op.tick()

    def measure_round(self):
        self.noise.apply_data_noise(
            self.op.circuit,
            self.layout.data_qubits,
        )

        z_ancillas = list(self.layout.z_check)
        x_ancillas = list(self.layout.x_check)

        all_ancillas = z_ancillas + x_ancillas

        self.op.reset_z(all_ancillas)
        self.op.tick()

        self.op.h(x_ancillas)
        self.op.tick()

        x_order = [(-1, 1), (-1, -1), (1, 1), (1, -1)]
        z_order = [(-1, 1), (1, 1), (-1, -1), (1, -1)]

        for step in range(4):
            for ancilla, data_qubits in self.layout.z_check.items():
                ax, ay = self.layout.location.coord_at(ancilla)

                for data in data_qubits:
                    x, y = self.layout.location.coord_at(data)

                    if (x - ax, y - ay) == z_order[step]:
                        self.op.cx(data, ancilla)

            for ancilla, data_qubits in self.layout.x_check.items():
                ax, ay = self.layout.location.coord_at(ancilla)

                for data in data_qubits:
                    x, y = self.layout.location.coord_at(data)

                    if (x - ax, y - ay) == x_order[step]:
                        self.op.cx(ancilla, data)

            self.op.tick()

        self.op.h(x_ancillas)
        self.op.tick()

        self.noise.apply_measure_noise(
            self.op.circuit,
            all_ancillas
        )

        self.op.measure_z(all_ancillas)

        for ancilla in all_ancillas:
            self.tracker.register_measurement(self.round_index, ancilla)

        self.add_round_detectors()

        self.op.tick()
        self.round_index += 1

    def add_round_detectors(self):
        if self.round_index == 0:
            ancillas = list(self.layout.z_check)

        else:
            ancillas = (
                list(self.layout.z_check)
                + list(self.layout.x_check)
            )

        for ancilla in ancillas:
            current = self.tracker.offset(self.round_index, ancilla)
            offsets = [current]

            if self.round_index > 0:
                previous = self.tracker.offset(self.round_index - 1, ancilla)
                offsets.append(previous)

            x, y = self.layout.location.coord_at(ancilla)

            self.op.detector(offsets, [x, y, self.round_index])

    def finalize_z(self):
        self.noise.apply_measure_noise(
            self.op.circuit,
            self.layout.data_qubits
        )

        self.op.measure_z(self.layout.data_qubits)

        for data in self.layout.data_qubits:
            self.tracker.register_measurement(self.round_index, data)

        self.add_final_z_detectors()
        self.add_logical_z()
        self.op.tick()

    def add_final_z_detectors(self):
        last_round = self.round_index - 1
        final_round = self.round_index

        for ancilla, data_qubits in self.layout.z_check.items():
            offsets = [self.tracker.offset(last_round, ancilla)]

            for data in data_qubits:
                offsets.append(self.tracker.offset(final_round, data))

            x, y = self.layout.location.coord_at(ancilla)
            self.op.detector(offsets, [x, y, final_round])

    def add_logical_z(self):
        offsets = []

        for data in self.layout.logical_z:
            offsets.append(self.tracker.offset(self.round_index, data))

        self.op.observable_include(offsets, self.observable_index)
        self.observable_index += 1

    def build(self):
        self.initialize_z()

        for _ in range(self.rounds):
            self.measure_round()

        self.finalize_z()
        return self.op.circuit

if __name__ == "__main__":
    builder = MemoryCircuitBuilder(distance=3, rounds=2)
    circuit = builder.build()

    assert builder.round_index == 2
    assert builder.tracker.num_measurements == 25

    assert (
        builder.tracker.num_measurements
        == builder.op.circuit.num_measurements
    )

    assert builder.tracker.records[(0, 10)] == 0
    assert builder.tracker.records[(1, 10)] == 8

    assert builder.tracker.offset(0, 10) == -25
    assert builder.tracker.offset(1, 10) == -17

    for key, index in builder.tracker.records.items():
        print(f"{key} → 測定記録の{index}番")

    sampler = builder.op.circuit.compile_sampler()
    results = sampler.sample(shots=10)

    assert (results[:, :8] == results[:, 8:16]).all()

    circuit = builder.op.circuit

    assert circuit.num_detectors == 16

    circuit.detector_error_model()

    assert circuit.num_observables == 1

    detector_sampler = circuit.compile_detector_sampler()
    events, observable_flips = detector_sampler.sample(
        shots=10, separate_observables=True)

    assert events.shape == (10, 16)
    assert observable_flips.shape == (10, 1)
    assert not events.any()
    assert not observable_flips.any()

    print("検出イベント:")
    print(events.astype(int))

    print("論理反転:")
    print(observable_flips.astype(int))

    print("すべての確認に成功")