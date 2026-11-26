from location import Location


class SurfaceCodeLayout:
    def __init__(self, distance):
        self.distance = distance
        self.location = Location()
        self.data_qubits = []
        self.ancilla_qubits = []
        self.x_check = {}
        self.z_check = {}
        self.logical_z = []

        # データビットの配置
        for j in range(self.distance):
            for i in range(self.distance):
                index = self.location.add((2 * i, 2 * j))
                self.data_qubits.append(index)

        # アンシラの配置(内部)
        for j in range(self.distance - 1):
            for i in range(self.distance - 1):
                index = self.location.add((2 * i + 1, 2 * j + 1))
                self.ancilla_qubits.append(index)

                data_coords = [
                    (2 * i, 2 * j),
                    (2 * i + 2, 2 * j),
                    (2 * i, 2 * j + 2),
                    (2 * i + 2, 2 * j + 2),
                ]
                data_indices = []

                for coord in data_coords:
                    data_indices.append(self.location.index_at(coord))

                if (i + j) % 2 == 0:
                    self.x_check[index] = data_indices

                else:
                    self.z_check[index] = data_indices

        # アンシラの配置(境界)
        for i in range(self.distance - 1):
            if i % 2 == 0:
                index = self.location.add((2 * i + 1, -1))
                self.ancilla_qubits.append(index)

                data_coords = [(2 * i, 0), (2 * i + 2, 0)]
                data_indices = []

                for coord in data_coords:
                    data_indices.append(self.location.index_at(coord))

                self.z_check[index] = data_indices

            if i % 2 == 1:
                index = self.location.add((2 * i + 1, 2 * self.distance - 1))
                self.ancilla_qubits.append(index)

                data_coords = [
                    (2 * i, 2 * self.distance - 2),
                    (2 * i + 2, 2 * self.distance - 2),
                ]
                data_indices = []

                for coord in data_coords:
                    data_indices.append(self.location.index_at(coord))

                self.z_check[index] = data_indices

        for j in range(self.distance - 1):
            if j % 2 == 1:
                index = self.location.add((-1, 2 * j + 1))
                self.ancilla_qubits.append(index)

                data_coords = [(0, 2 * j), (0, 2 * j + 2)]
                data_indices = []

                for coord in data_coords:
                    data_indices.append(self.location.index_at(coord))

                self.x_check[index] = data_indices

            if j % 2 == 0:
                index = self.location.add((2 * self.distance - 1, 2 * j + 1))
                self.ancilla_qubits.append(index)

                data_coords = [
                    (2 * self.distance - 2, 2 * j),
                    (2 * self.distance - 2, 2 * j + 2),
                ]
                data_indices = []

                for coord in data_coords:
                    data_indices.append(self.location.index_at(coord))

                self.x_check[index] = data_indices

        for j in range(self.distance):
            index = self.location.index_at((0, 2 * j))
            self.logical_z.append(index)



if __name__ == "__main__":
    layout = SurfaceCodeLayout(distance=3)

    assert len(layout.data_qubits) == 9

    for index in layout.data_qubits:
        print(index, layout.location.coord_at(index))
