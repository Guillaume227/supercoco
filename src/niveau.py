#! /usr/bin/env python

from . import media
from .media import charge_image

from . import elems
import pickle
import traceback
import os
from . import sauvegarde
import copyreg

suffixe = '.monde'


class Monde(sauvegarde.Phenixable):

    def __init__(self, nom='NouveauMonde'):

        self.tempsMax_ = 400

        self.musique_ = "maintheme.ogg"
        self.nomJoueur_ = 'mario'
        self.etat_joueur_ = None

        # dans le jeu d'origine, la brique la plus basse est coupee a sa moitie
        self.marge_bas_ = .5  # en ratio de media.TAILLE_BLOC

        self._image_fond = charge_image("background-2.png")
        self.parallaxe_ = False

        self.nom = nom

        self.Elements = []
        self.Elements.append(self.posDepart)

        # Le joueur a-t-il le droit de revenir sur ses pas ?
        self.revenir_en_arriere_ = False
        self.photos_ = []

    def __str__(self):
        return 'Monde %s' % getattr(self, 'nom', 'sans nom')

    @property
    def arriere_plan_(self):
        return self._image_fond.file_name

    @arriere_plan_.setter
    def arriere_plan_(self, val):
        self._image_fond = charge_image(val)

    @property
    def posDepart(self):
        if self.Elements:
            for elem in self.Elements:
                if isinstance(elem, elems.PositionDepart):
                    return elem

            print(self, 'position depart non trouvee')

        return elems.PositionDepart((16, 380))  # position par defaut

    def composition(self):
        """ Affiche la composition du monde """
        for elem in sorted(self.Elements, key=lambda x: x.__class__.__name__):
            print(elem)

    def Sauvegarde(self, renomme=False):

        nom_fichier = self.nom

        if renomme:

            nom_fichier = select_monde(defaut=nom_fichier)

            if not nom_fichier:
                return

        self.nom = nom_fichier

        file_path = media.cheminFichier(nom_fichier + suffixe, subdir=media.SAUVE_REP)

        try:
            with open(file_path, 'wb') as fichier_obj:

                try:
                    pickle.dump(self, fichier_obj, protocol=2)
                except:
                    traceback.print_exc()

            print(nom_fichier, 'sauvegarde')

        except:
            traceback.print_exc()
            return

        # sauvegarde reussie
        return True


def select_monde(defaut=None, choix_nouveau=True):
    from . import menu
    import pygame

    choix = media.liste_des_mondes() + ['*Nouveau*']

    ecran = pygame.display.get_surface()
    menu_choix = menu.MenuOptions(choix,
                                  legende=['Choisir un monde :'],
                                  pos=(ecran.get_width() / 2, 5),
                                  fonte_h=12,
                                  centre=False)

    monde_index = menu_choix.boucle()

    if monde_index is not None:

        nom_monde = choix[monde_index]

        if nom_monde == '*Nouveau*':
            while True:
                nom_monde = menu.ChampNomMonde(['Nom du niveau :'], defaut=defaut, pos=(40, 100), alpha_fond=200).boucle()
                if nom_monde in choix:
                    menu.BoiteMessage(['Le niveau %s existe deja !' % nom_monde, ' En choisir un autre.'],
                                      pos=(200, 100)).boucle()
                else:
                    break

        return nom_monde


def existe(file_name):
    if not file_name.endswith(suffixe):
        file_name += suffixe
    return os.path.exists(os.path.join(media.SAUVE_REP, file_name))


def Resauve():
    """ Ouvre et sauve tous les mondes existants.
        Utile pour la mise a jour de nouveaux parametres 
        selon les modifications du code intervenues depuis la sauvegarde precedente.  
    """

    import pygame
    pygame.init()
    pygame.display.set_mode((640, 480))

    for nom_monde in media.liste_des_mondes():
        print('Resauve', nom_monde)
        monde_obj = ouvrir(nom_monde)
        monde_obj.Sauvegarde(renomme=False)


def loads(file_obj):
    """ Code a activer si le nom d'un module ou d'une classe
        sauvegarde change.
    """

    def mapname(name):
        name = name.replace('code.', 'src.')
        return {'src.sprites': 'src.elems',
                'src.data': 'src.media',
                'src.level': 'src.niveau',
                'Level': 'Monde'}.get(name, name)
        # return name.replace('vieux_module', 'nouveau_module')

    def mapped_load_global(self):
        module = mapname(self.readline()[:-1])
        name = mapname(self.readline()[:-1])
        klass = self.find_class(module, name)
        self.append(klass)

    unpickler = pickle.Unpickler(file_obj)
    # unpickler.dispatch[pickle.GLOBAL] = mapped_load_global
    copyreg.dispatch_table[pickle.GLOBAL] = mapped_load_global
    return unpickler.load()


def ouvrir(file_name=''):

    if False:
        file_name = select_monde()

        if not file_name:
            return

    print('ouverture de', file_name)

    if not file_name.endswith(suffixe):
        file_name += suffixe

    file_path = os.path.join(media.SAUVE_REP, file_name)

    with open(file_path, 'rb') as file_obj:

        monde_obj = loads(file_obj)

        monde_obj.nom = file_name.split('.')[0]

        return monde_obj
