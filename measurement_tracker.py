class MeasurementTracker:
    def __init__(self):
        self.records = {}
        self.num_measurements = 0

    def register_measurement(self, round_index, qubit):
        key = (round_index, qubit)
        if key in self.records:
            raise ValueError(f"測定キーが重複しています: {key}")
    
        self.records[key] = self.num_measurements
        self.num_measurements += 1

    def offset(self, round_index, qubit):
        key = (round_index, qubit)
        return self.records[key] - self.num_measurements

if __name__ == "__main__":
    tracker = MeasurementTracker()

    tracker.register_measurement(0, 10)  # 絶対番号0
    tracker.register_measurement(0, 11)  # 絶対番号1

    assert tracker.offset(0, 10) == -2
    assert tracker.offset(0, 11) == -1

    tracker.register_measurement(1, 10)  # 絶対番号2

    assert tracker.offset(0, 10) == -3
    assert tracker.offset(1, 10) == -1

    print("確認できました")