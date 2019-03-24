from __future__ import print_function
from pygame import Rect


class Crible(dict):
    """ Pavage (carres) uniforme du plan de cote self.pas. """

    def __init__(self, pas):
        super(Crible, self).__init__()
        self.pas = pas
        self.elem_a_paves = {}

    def extremas(self):
        """ Coordonnees des paves extremes du crible """
        xs, ys = zip(*self.keys())
        return min(xs), min(ys), max(xs), max(ys)

    def coords(self, arg):

        """Recherche dans le crible
            arg peut etre:
             - un couple (point haut, point bas) definissant un rectangle
             - un rectangle pygame.Rect
             
            Si ajout est True, ajoute les paves qui n'ont pas deja ete frequentes.

            
            Renvoie la liste des paves intersectes par arg.
        """

        if isinstance(arg, Rect):
            p1, p2 = arg.topleft, arg.bottomright

        elif isinstance(arg, slice):

            if isinstance(arg.stop, (float, int)):
                rayon = arg.stop
                x0, y0 = arg.start
                p1 = x0 - rayon, y0 - rayon
                p2 = x0 + rayon, y0 + rayon
            else:
                p1, p2 = arg.start, arg.stop
                if not (p1 or p2):
                    return self.values()

                elif not p1 or not p2:
                    raise ValueError('Point manquant')

        elif len(arg) == 3:
            p1 = arg[0], arg[1].start
            p2 = arg[1].stop, arg[2]

        elif isinstance(arg[1], slice):
            rayon = arg[1].stop
            x0, y0 = arg[0], arg[1].start
            p1 = x0 - rayon, y0 - rayon
            p2 = x0 + rayon, y0 + rayon

        else:
            p1, p2 = arg

        x1, y1 = p1
        x2, y2 = p2

        xb, xh = sorted((x1, x2))
        yb, yh = sorted((y1, y2))

        xb, yb, xh, yh = [int(coor) // self.pas for coor in (xb, yb, xh, yh)]

        if xb == xb * self.pas:
            xb -= 1
        if yb == yb * self.pas:
            yb -= 1

        return xb, yb, xh, yh

    def paves(self, arg, ajout=False):
        xb, yb, xh, yh = self.coords(arg)
        if ajout:
            return [self.setdefault((x, y), set()) for x in range(xb, xh + 1) for y in range(yb, yh + 1)]
        else:
            return [self[(x, y)] for x in range(xb, xh + 1) for y in range(yb, yh + 1) if (x, y) in self]

    def rects(self, arg):
        xb, yb, xh, yh = self.coords(arg)
        pas = self.pas
        return [(x * pas, y * pas, pas, pas) for x in range(xb, xh + 1) for y in range(yb, yh + 1) if (x, y) in self]

    def intersecte(self, rect, obj=None):
        """Assumes rect is a pygame.rect
            and criblable items have a rect member
        """
        res = set()
        for Ens in self.paves(rect):
            res.update(Elem for Elem in Ens if Elem is not obj and rect.colliderect(Elem.rect))

        return res

    def insere(self, arg, obj, loc_info=None):

        if loc_info is None:
            paves = self.paves(arg, ajout=True)
        else:
            paves = loc_info

        self.elem_a_paves[obj] = list(paves)

        for pave in paves:
            pave.add(obj)

    def retire(self, obj, strict=True):

        if strict:
            paves = self.elem_a_paves.pop(obj)
        else:
            paves = self.elem_a_paves.pop(obj, [])

        for ens in paves:
            ens.discard(obj)

    def deplace(self, dest, obj, strict=True):

        self.retire(obj, strict=strict)
        self.insere(dest, obj)

    def afficher(self, surface):
        import pygame
        couleur = (100, 100, 150)
        pas = self.pas
        for x0, y0 in self:
            pygame.draw.rect(surface, couleur, Rect(x0 * pas, y0 * pas, pas, pas), 1)

    def tous(self):
        """ Tous les elements du crible """
        res = set()
        [res.update(ens) for ens in self.values()]
        return res

    def vidange(self):
        for ens in self.values():
            ens.clear()

        self.elem_a_paves.clear()

    def verif_integrite(self):
        for ens in iter(self):
            for obj in ens:
                assert ens in self.elem_a_paves[obj]

    def verif_integrite_2(self):
        for x, y in self:
            for a, b in self:
                if (x - a) ** 2 + (y - b) ** 2 > 2:
                    intersection = self[x, y].intersection(self[a, b])
                    if intersection:
                        print(intersection)
                        raise ValueError(f'Crible incoherent, {len(intersection)} duplication(s) {x},{y} et {a},{b}')
