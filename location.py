class Location:

    def __init__(self):
        self.coords = []

    def add(self, coord):
        if coord not in self.coords:
            self.coords.append(coord)

        return self.index_at(coord)

    def index_at(self, coord):
        return self.coords.index(coord)

    def coord_at(self, index):
        return self.coords[index]