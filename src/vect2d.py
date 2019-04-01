from __future__ import print_function
from math import sqrt, cos, sin

Rotateurs = {}


def Rot(rad, Arron=3):
    arronRad = round(rad, Arron)
    Rotateur = Rotateurs.get(arronRad)

    if not Rotateur:
        Rotateur = (cos(rad), sin(rad)), (-sin(rad), cos(rad))
        Rotateurs[arronRad] = Rotateur

    return Rotateur


class Rectang:
    """ GrandCote / PetitCote = 2."""

    def __init__(self, Centre, Orient, GrandCote):

        self.vX = Orient.normale() * GrandCote
        self.vY = Orient * GrandCote / 2.
        self.orig = Centre - self.v1 / 2. - self.v2 / 2.

    def Sommets(self):
        return [self.orig,
                self.orig + self.vX,
                self.orig + self.vX + self.vY,
                self.orig + self.vY]

    def PaveLimite(self):
        coord_x, coord_y = zip(*self.Sommets())
        return (min(coord_x), min(coord_y)), (max(coord_x), max(coord_y))

    def Interse(self, Autre):

        (Ax1, Ay1), (Ax2, Ay2) = Autre.PaveLimite()
        (Sx1, Sy1), (Sx2, Sy2) = self.PaveLimite()

        if Ax1 >= Sx2 or Sx1 >= Ax2 or Sy2 <= Ay1 or Ay2 <= Sy1:
            return False

        Aorig = Autre.orig - self.orig
        Aorig = Vec(Aorig * self.vX, Aorig * self.vY)
        AvX = Vec(Autre.vX * self.vX, Autre.vX * self.vY)
        AvY = Vec(Autre.vY * self.vX, Autre.vY * self.vY)

        for p1, p2 in ((Aorig, Aorig + Autre.vX),
                       (Aorig + Autre.vX, Aorig + Autre.vX + Autre.vY),
                       (Aorig + Autre.vY + Autre.vX, Aorig + Autre.vY),
                       (Aorig + Autre.vY, Aorig,)):

            for q1, q2 in ((0, 0), (1, 0)), ((0, 0), (0, 1)), ((1, 0), (1, 1)), ((0, 1), (1, 1)):
                return True  # Faux - A continuer


class Vec(list):
    """Vecteur en deux dimensions """

    def __init__(self, *args):
        lenarg = len(args)
        if not lenarg:
            list.__init__(self, (0, 0))
        elif lenarg > 1:
            list.__init__(self, args)
        elif isinstance(args[0], (tuple, list, Vec)):
            if len(args[0]) == 1:
                val = args[0][0]
                list.__init__(self, (val, val))
            else:
                list.__init__(self, args[0])
        else:
            list.__init__(self, (args[0], args[0]))

    @property
    def nor(self):
        return sqrt(self[0] ** 2 + self[1] ** 2)

    @nor.setter
    def nor(self, value):
        self *= value / self.nor

    @property
    def nor2(self):
        return self[0] ** 2 + self[1] ** 2

    def unite(self, Long=1.):
        """ Vecteur unite ou de longueur specifie """
        fact = Long / self.nor
        return type(self)(self[0] * fact, self[1] * fact)

    def tr(self):
        """transpose"""
        return type(self)(self[1], self[0])

    def itr(self):
        """transpose"""
        self[0], self[1] = self[1], self[0]

    def normale(self):
        """normale suivant une rotation directe"""
        return type(self)(self[1], -self[0])

    def Angle(self, vec2, angle):
        prod = self.unite() ^ vec2.unite()
        if prod <= sin(angle):
            return prod
        else:
            return False

    def __repr__(self):
        return '%s,%s' % tuple(str(round(x, 1) if isinstance(x, float) else x) for x in self)

    def __add__(self, other):
        return type(self)(self[0] + other[0], self[1] + other[1])

    def __radd__(self, other):
        return self + other

    def __sub__(self, other):
        return type(self)(self[0] - other[0], self[1] - other[1])

    def __rsub__(self, other):
        return type(self)(other[0] - self[0], other[1] - self[1])

    def __mul__(self, a):
        """ produit scalaire ou par un scalaire """
        if isinstance(a, (int, float)):
            return type(self)(self[0] * a, self[1] * a)
        else:
            return self[0] * a[0] + self[1] * a[1]

    def __rmul__(self, a):
        return self[0] * a, self[1] * a

    def __div__(self, a):
        """ division par un scalaire """
        return type(self)(self[0] / a, self[1] / a)

    def __rdiv__(self, a):
        return self[0] / a, self[1] / a

    def __lt__(self, a):
        return abs(self[0]) < a and abs(self[1]) < a

    def __gt__(self, a):
        return abs(self[0]) > a and abs(self[1]) > a

    def __abs__(self):
        return abs(self[0]), abs(self[1])

    def __neg__(self):
        return type(self)(-self[0], -self[1])

    def __iadd__(self, other):
        self[0] += other[0]
        self[1] += other[1]
        return self

    def __isub__(self, other):
        self[0] -= other[0]
        self[1] -= other[1]
        return self

    def __imul__(self, a):
        if isinstance(a, (int, float)):
            self[0] *= a
            self[1] *= a
        else:
            # produit par une matrice
            self[0] = self[0] * a[0][0] + self[1] * a[0][1]
            self[1] = self[0] * a[1][0] + self[1] * a[1][1]

        return self

    def __idiv__(self, a):
        self[0] /= a
        self[1] /= a

        return self

    def __mod__(self, arg):
        # rotation
        if isinstance(arg, (int, float)):
            a = Rot(arg)
        else:  # a is a matrix
            a = arg
        return type(self)([self[0] * a[i][0] + self[1] * a[i][1] for i in (0, 1)])

    def __imod__(self, arg):
        if isinstance(arg, (int, float)):
            a = Rot(arg)
        else:
            a = arg
        self[0] = self[0] * a[0][0] + self[1] * a[0][1]
        self[1] = self[0] * a[1][0] + self[1] * a[1][1]
        return self

    def __xor__(self, other):
        """ produit vectoriel """
        return self[0] * other[1] - self[1] * other[0]

    def __pow__(self, other):
        return self[0] ** other, self[1] ** other

    def ent(self):
        return type(self)(int(self[0]), int(self[1]))

    def ient(self):
        self[0] = int(self[0])
        self[1] = int(self[1])
        return self

    def maxabs(self, val):
        self[0] = max(-val, min(self[0], val))
        self[1] = max(-val, min(self[1], val))

    def __nonzero__(self):
        return any(self)

    def inside(self, c1, c2):
        if (self[0] >= c1[0] and self[0] <= c2[0]) or \
                (self[0] >= c2[0] and self[0] <= c1[0]):
            if (self[1] >= c1[1] and self[1] <= c2[1]) or \
                    (self[1] >= c2[1] and self[1] <= c1[1]):
                return True
        return False


def pp(arg, noReturn=True, indent=0):
    """ pretty printing """

    Indentation = ' ' * indent
    """
    if isinstance( arg, datetime.date ):
        out =  Indentation + arg.strftime('%a %d %b %y')
    """
    if isinstance(arg, (list, set, tuple)):

        if isinstance(arg, set):
            arg2 = sorted(arg)

        if len(arg) > 3:
            out = ''
            for a in arg2:
                out += Indentation + '%s\n' % pp(a, noReturn=False)
        else:
            subList = [pp(a, noReturn=False) for a in arg2]
            if subList and '\n' in subList[0]:
                joinStr = '\n'
            else:
                joinStr = ', '

            out = Indentation + joinStr.join(subList)

    elif isinstance(arg, dict):
        out = ''
        maxKeyLength = max([len(str(k)) for k in arg.keys() + ['']]) + 1
        for Key in sorted(arg.keys()):

            KeyLine = Indentation + '%%%ds:' % maxKeyLength % str(Key)
            out += KeyLine
            Lines = pp(arg[Key], noReturn=False, indent=indent + maxKeyLength + 2)
            if len(Lines.split('\n')) > 1:
                out += '\n' + Lines
            else:
                out += ' ' + Lines.strip()
            out += '\n'
    else:
        if noReturn:
            import pprint
            pprint.pprint(arg, indent=indent)
            return
        else:
            return Indentation + str(arg)

    if noReturn:
        print(out)
    else:
        return out
