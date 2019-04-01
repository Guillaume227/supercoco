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
        return self._image_fond.fileName

    @arriere_plan_.setter
    def arriere_plan_(self, val):
        self._image_fond = charge_image(val)

    @property
    def posDepart(self):
        if self.Elements:
            for Elem in self.Elements:
                if isinstance(Elem, elems.PositionDepart):
                    return Elem

            print(self, 'position depart non trouvee')

        return elems.PositionDepart((16, 380))  # position par defaut

    def composition(self):
        """ Affiche la composition du monde """
        for Elem in sorted(self.Elements, key=lambda x: x.__class__.__name__):
            print(Elem)

    def Sauvegarde(self, renomme=False):

        nomFichier = self.nom

        if renomme:

            nomFichier = SelectMonde(defaut=nomFichier)

            if not nomFichier:
                return

        self.nom = nomFichier

        filePath = media.cheminFichier(nomFichier + suffixe, subdir=media.SAUVE_REP)

        try:
            fichierObj = open(filePath, 'wb')
        except:
            traceback.print_exc()
            return

        try:
            pickle.dump(self, fichierObj, protocol=2)
        except:
            traceback.print_exc()

        print
        nomFichier, 'sauvegarde'

        fichierObj.close()

        # sauvegarde reussie
        return True


def SelectMonde(defaut=None, choixNouveau=True):
    from . import menu
    import pygame

    choix = media.ListeDesMondes() + ['*Nouveau*']

    ecran = pygame.display.get_surface()
    menuChoix = menu.MenuOptions(choix,
                                 legende=['Choisir un monde :'],
                                 pos=(ecran.get_width() / 2, 5),
                                 fonte_h=12,
                                 centre=False)

    MondeIndex = menuChoix.boucle()

    if MondeIndex is not None:

        Nom = choix[MondeIndex]

        if Nom == '*Nouveau*':
            while True:
                Nom = menu.ChampNomMonde(['Nom du niveau :'], defaut=defaut, pos=(40, 100), alpha_fond=200).boucle()
                if Nom in choix:
                    menu.BoiteMessage(['Le niveau %s existe deja !' % Nom, ' En choisir un autre.'],
                                      pos=(200, 100)).boucle()
                else:
                    break

        return Nom


def Existe(fileName):
    if not fileName.endswith(suffixe):
        fileName += suffixe
    return os.path.exists(os.path.join(media.SAUVE_REP, fileName))


def Resauve():
    """ Ouvre et sauve tous les mondes existants.
        Utile pour la mise a jour de nouveaux parametres 
        selon les modifications du code intervenues depuis la sauvegarde precedente.  
    """

    import pygame
    pygame.init()
    pygame.display.set_mode((640, 480))

    for nom_monde in media.ListeDesMondes():
        print
        'Resauve', nom_monde
        mondeObj = Ouvrir(nom_monde)
        mondeObj.Sauvegarde(renomme=False)


def loads(fileObj):
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

    unpickler = pickle.Unpickler(fileObj)
    # unpickler.dispatch[pickle.GLOBAL] = mapped_load_global
    copyreg.dispatch_table[pickle.GLOBAL] = mapped_load_global
    return unpickler.load()


def Ouvrir(fileName=''):
    print('Ouvrir', fileName)

    fileName = SelectMonde()

    if not fileName:
        return

    if not fileName.endswith(suffixe):
        fileName += suffixe

    filePath = os.path.join(media.SAUVE_REP, fileName)

    fileObj = open(filePath, 'rb')

    MondeObj = loads(fileObj)

    MondeObj.nom = fileName.split('.')[0]

    fileObj.close()

    return MondeObj
