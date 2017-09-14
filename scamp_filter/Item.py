class Atom:
    def __init__(self, nr, x, y, neg=False):
        self.nr = nr
        self.x = x
        self.y = y
        self.neg = neg

    def __str__(self):
        return ('-' if self.neg else '') + '([' + str(self.nr) + '] ' + str(self.x) + ' ' + str(self.y) + ')'

    def __repr__(self):
        return self.__str__()

    def val(self):
        return self.x, self.y, self.neg

    def __eq__(self, other):
        return self.nr == other.nr and self.x == other.x and self.y == other.y

    def __hash__(self):
        return hash((self.nr, self.x, self.y))


class Item:
    def __init__(self, scale, x, y, neg=False):
        self.scale = scale
        self.x = x
        self.y = y
        self.neg = neg

    def __str__(self):
        return ('-' if self.neg else '') + '(' + str(self.scale) + ' ' + str(self.x) + ' ' + str(self.y) + ')'

    def __repr__(self):
        return self.__str__()

    def __eq__(self, other):
        return self.x == other.x and self.y == other.y and self.scale == other.scale

    def __lt__(self, other):
        if self.scale < other.scale:
            return True
        if self.scale == other.scale:
            if self.x < other.x:
                return True
            if self.x == other.x:
                if self.y < other.y:
                    return True
        return False

    def __neg__(self):
        return Item(self.scale, self.x, self.y, not self.neg)

    def __hash__(self):
        return hash((self.scale, self.x, self.y, self.neg))

    def __len__(self):
        return abs(self.x) + abs(self.y) + abs(self.scale) + self.neg