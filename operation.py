import stim

class Operation:
    def __init__(self):
        self.circuit = stim.Circuit()

    def tick(self):
        self.circuit.append("TICK")

    def reset_z(self, qubits):
        self.circuit.append("R", qubits)

    def cx(self, c_qubit, t_qubit):
        self.circuit.append("CX", [c_qubit, t_qubit])

    def measure_z(self, qubits):
        self.circuit.append("M", qubits)

    def h(self, qubits):
        self.circuit.append("H", qubits)

    def measure_z_check(self, ancilla, data_qubits):
        self.reset_z([ancilla])
        for data in data_qubits:
            self.cx(data, ancilla)
        self.measure_z([ancilla])

    def measure_x_check(self, ancilla, data_qubits):
        self.reset_z([ancilla])
        self.h([ancilla])
        for data in data_qubits:
            self.cx(ancilla, data)
        self.h([ancilla])
        self.measure_z([ancilla])

    def detector(self, offsets, timespace_coords):
        targets = []

        for offset in offsets:
            targets.append(stim.target_rec(offset))

        self.circuit.append("DETECTOR", targets, timespace_coords)

    def observable_include(self, offsets, observable_index = 0):
        targets = []

        for offset in offsets:
            targets.append(stim.target_rec(offset))

        self.circuit.append("OBSERVABLE_INCLUDE", targets, observable_index)
        

if __name__ == "__main__":
    from layout import SurfaceCodeLayout

    layout = SurfaceCodeLayout(distance=3)
    op = Operation()

    # sample
    ancilla = 10
    data_qubits = layout.z_check[ancilla]  # [1, 2, 4, 5]

    op.reset_z(data_qubits)
    op.measure_z_check(ancilla, data_qubits)

    print(op.circuit)

    sampler = op.circuit.compile_sampler()
    results = sampler.sample(shots=10)
    print(results)

    op = Operation()

    ancilla = 9
    data_qubits = layout.x_check[ancilla]

    op.reset_z(data_qubits)
    op.h(data_qubits)
    op.measure_x_check(ancilla, data_qubits)

    print(op.circuit)
    
    sampler = op.circuit.compile_sampler()
    results = sampler.sample(shots=10)
    print(results)