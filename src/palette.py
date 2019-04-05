from .elems import Elements, Categories
from . import elems
from . import media
import os
import pygame
from . import menu

_Selection = None

RepertoiresVrac = ['decors Vrac', 'Cap Vrac']


def DecorsVrac(repertoire):
    vrac_dir = os.path.join(media.MEDIA_REP, repertoire)
    return [item for item in os.listdir(vrac_dir) if item.split('.')[-1] in ['png', 'gif', 'jpeg', 'jpg']]


def GetElements():
    Elems = Elements.copy()
    for Repertoire in RepertoiresVrac:
        Elems[Repertoire] = DecorsVrac(Repertoire)

    return Elems


ListElements = GetElements()


class Palette(menu.ElemInterface):

    def __init__(self, **kwargs):

        menu.ElemInterface.__init__(self, pos=(0, 0), alpha_fond=150, **kwargs)

        self.IndexSelection = [0, 0]

        self.dim_vignette = 32, 32
        self.dim_ecran = pygame.display.get_surface().get_size()

        self.IndexType = 0
        self.marge_HG = 0, 16
        self.nomb_vignettes = [(self.dim_ecran[i] - self.marge_HG[i]) // self.dim_vignette[i] for i in (0, 1)]
        coin_HG = [(self.dim_ecran[i] - self.nomb_vignettes[i] * self.dim_vignette[i]) // 2 for i in (0, 1)]
        self.coin_HG = [max(self.marge_HG[i], coin_HG[i]) for i in (0, 1)]

        self.grilles = [[[None for _ in range(self.nomb_vignettes[1])] for _ in range(self.nomb_vignettes[0])] for _
                        in Categories]

        self.emplit_grille()

    def emplit_grille(self):

        for cat_index, categorie in enumerate(Categories):

            for i, elem in enumerate(ListElements[categorie]):

                li = i % self.nomb_vignettes[1]
                col = 1 + i // self.nomb_vignettes[1]

                if isinstance(elem, str):
                    elem_name = elem
                    image = os.path.join(media.MEDIA_REP, categorie, elem)

                else:
                    elem_name = elem.__name__
                    if hasattr(elem, 'nomImages'):
                        image = elem.nomImages[0]
                    else:
                        image = None

                if image:
                    # Retaille
                    image_obj = pygame.transform.scale(media.charge_image(image), self.dim_vignette)
                else:
                    image_obj = None

                self.grilles[cat_index][col][li] = elem, image_obj, elem_name

        for cat_index, _categorie in enumerate(Categories):
            for CatIndex2, _categorie in enumerate(Categories):
                self.grilles[cat_index][0][CatIndex2] = self.grilles[CatIndex2][1][0]

    def index_pour_pos(self, pos):
        """ index col, index ligne"""
        return [(pos[i] - self.coin_HG[i]) // self.dim_vignette[i] for i in (0, 1)]

    def pos_pour_index(self, index):
        """ index col, index ligne"""
        return [index[i] * self.dim_vignette[i] + self.coin_HG[i] for i in (0, 1)]

    @property
    def valeur(self):
        val = self.grilles[self.IndexType][self.IndexSelection[0]][self.IndexSelection[1]]
        if val is not None:
            return val[0]

    @valeur.setter
    def valeur(self, val):
        pass

    def affiche(self, surface):

        for colIndex, col in enumerate(self.grilles[self.IndexType]):
            for liIndex, elem in enumerate(col):
                if elem:
                    elem, image, _nom = elem

                    if image:
                        pos = self.pos_pour_index((colIndex, liIndex))
                        surface.blit(image, pos)

        etiquette = Categories[self.IndexType]

        if self.IndexSelection[0] != 0:

            val = self.grilles[self.IndexType][self.IndexSelection[0]][self.IndexSelection[1]]
            if val:
                etiquette += ' : ' + val[2]

                # Marque la selection d'une ombre
        Rect = pygame.Rect(self.pos_pour_index(self.IndexSelection), self.dim_vignette)
        pygame.draw.rect(surface, pygame.Color(0, 255, 0, 100), Rect, 1)

        self.affiche_ligne(surface, etiquette)

    def mettre_a_jour(self, e):

        if e.type == pygame.MOUSEMOTION:

            pos = pygame.mouse.get_pos()
            self.IndexSelection = self.index_pour_pos(pos)

        elif e.type == pygame.KEYDOWN:

            if e.key == pygame.K_UP:
                self.IndexSelection[1] -= 1
            elif e.key == pygame.K_DOWN:
                self.IndexSelection[1] += 1
            elif e.key == pygame.K_LEFT:
                self.IndexSelection[0] -= 1
            elif e.key == pygame.K_RIGHT:
                self.IndexSelection[0] += 1

        if self.IndexSelection[0] == 0:
            cat_index = min(max(0, self.IndexSelection[1]), len(Categories) - 1)
            if self.IndexType != cat_index:
                self.IndexType = cat_index

            self.IndexSelection[1] = self.IndexType

        else:
            self.IndexSelection[1] %= len(ListElements[Categories[self.IndexType]])

        for i in 0, 1:
            self.IndexSelection[i] %= self.nomb_vignettes[i]


def Selecte():
    selection = Palette().boucle()

    pygame.event.clear()

    if selection:
        if isinstance(selection, str):
            sel = elems.Dessinable(pos=None, images=[selection])
        else:
            sel = selection(pos=None)

        sel.efface()
        return sel


def EditFields(item):
    return sorted([AttrName for AttrName in dir(item) if AttrName.endswith('_') and not AttrName.startswith('_')])


class EditeurElem(menu.EditeurElem):

    def alafin(self):

        # Verifie que les photos existent (pas de coquille dans le nom)
        for AttrName, champ in self.champs:

            if AttrName == 'photos_':
                for val in champ.valeur:
                    try:
                        media.charge_image('photos/' + val)
                    except:
                        print('manque la photo', val)

        menu.EditeurElem.alafin(self)


def Editor(*items):
    if EditFields(items[0]):
        choix_champs = dict(nomJoueur_=['coco', 'mario'], surprise_=[None] + ListElements['Surprises'])
        editeur = EditeurElem(items, fonte_h=10, choixPourChamps=choix_champs, filtre_=True)

        editeur.boucle()
        pygame.event.clear()

        return editeur.modifie
