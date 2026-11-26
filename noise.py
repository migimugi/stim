class Noise:
    def __init__(self, p_data, p_measure):
        self.p_data = p_data
        self.p_measure = p_measure

    def apply_data_noise(self, circuit, data_qubits):
        circuit.append("DEPOLARIZE1", data_qubits, self.p_data)

    def apply_measure_noise(self, circuit, qubits):
        circuit.append("X_ERROR", qubits, self.p_measure)

