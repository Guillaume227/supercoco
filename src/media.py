import os, pygame, sys

# data_py  = os.path.abspath(os.path.dirname(__file__))
data_py = os.path.dirname(os.path.abspath(sys.argv[0]))
MEDIA_REP = os.path.normpath(os.path.join(data_py, 'media'))
SAUVE_REP = os.path.join(MEDIA_REP, 'mondes')

FONTE_DEFAUT = "font.ttf"

_CacheImage = {}
_CacheSon = {}
_CacheFonte = {}

TAILLE_BLOC = 32


def liste_des_mondes():
    return [nom_fichier.split('.')[0] for nom_fichier in os.listdir(SAUVE_REP) if nom_fichier.endswith('.monde')]


def vidange_cache():
    _CacheImage.clear()
    _CacheSon.clear()


def cheminFichier(nom_fichier, subdir='', verif_existe=True):
    nom_fichier_long = os.path.join(MEDIA_REP, subdir, nom_fichier)
    if verif_existe and not os.path.exists(nom_fichier_long):
        raise MediaManquantExc(nom_fichier_long)

    return nom_fichier_long


class MediaManquantExc(Exception):

    def __init__(self, nom_fichier):
        self.nom_fichier = nom_fichier

    def __repr__(self):
        return '%s introuvable' % self.nom_fichier

    __str__ = __repr__


class SurfacePersistante(pygame.Surface):
    """Enrobage de la classe pygame.Surface pour la rendre persistable avec pickle"""

    def __setstate__(self, dico):
        self.__init__(**dico)


class SurfaceP(SurfacePersistante):
    """ Enrobage d'une image pour persistance
        Ne sauvegardons que le nom du fichier.
    """

    def __init__(self, fileName, flip=False, scale=2):

        fileName = fileName.replace('nagefire', 'firenage')
        self.file_name = fileName
        self.flip = flip

        image = charge_image_no_cache(fileName, scale)

        if self.flip:
            image = pygame.transform.flip(image, 1, 0)

        pygame.Surface.__init__(self, image.get_size(), 0, image)

        self.blit(image, (0, 0))
        global _CacheImage
        if fileName not in _CacheImage:
            _CacheImage[(fileName, flip)] = self

    def __str__(self):
        return SurfacePersistante.__str__(self) + ' ' + self.file_name

    def __getstate__(self):
        return dict(fileName=self.file_name, flip=self.flip)


class SurfaceTexte(SurfacePersistante):

    def __init__(self, message, police, taille=16, couleur=(0, 0, 0)):
        super(SurfaceTexte, self).__init__()
        self.police = police
        self.taille = taille
        self.couleur = couleur
        self.message = message

        self.image = charge_fonte(police, taille).render(message, 1, couleur)

        # pygame.Surface.__init__( self, image.get_size(), 0, image )

    def __getstate__(self):
        return dict(police=self.police,
                    taille=self.taille,
                    couleur=self.couleur,
                    message=self.message)


def charge_image_no_cache(nom_fichier, scale=1):
    chemin_fichier = cheminFichier(nom_fichier)
    try:
        image = pygame.image.load(chemin_fichier)
        if scale != 1:
            image = pygame.transform.scale(image, (image.get_width() * scale, image.get_height() * scale))
        return image.convert_alpha()

    except pygame.error:
        import traceback
        traceback.print_exc()


def charge_image(nom_fichier, flip=False, scale=2):
    if (nom_fichier, flip) not in _CacheImage:
        _CacheImage[(nom_fichier, flip)] = SurfaceP(nom_fichier, flip, scale)

    return _CacheImage[(nom_fichier, flip)]


class SonP(pygame.mixer.Sound):

    def __init__(self, file_name, volume):

        self.__safe_for_unpickling__ = True

        file_name = cheminFichier(file_name, subdir='sons')
        pygame.mixer.Sound.__init__(self, file_name)

        self.fileName = file_name
        self.volume = volume

        self.set_volume(volume)

        global _CacheSon
        if file_name not in _CacheSon:
            _CacheSon[file_name] = self

    def __str__(self):
        return pygame.mixer.Sound.__str__(self), self.fileName

    def __reduce__(self):
        return SonP, (self.fileName, self.volume)

    """
    def __getnewargs__(self):
        return self.fileName, self.volume
    """

    def __getstate__(self):
        return dict(fileName=self.fileName, volume=self.volume, __safe_for_unpickling__=True)

    """
    def __setstate__(self,Dict):
        self.__init__( **Dict )
        
    """


def charge_fonte_no_cache(nom_fichier, taille=16):
    fullfilename = cheminFichier(nom_fichier, subdir='fonts')

    return pygame.font.Font(fullfilename, taille)


def charge_fonte(nom_fichier, taille):
    global _CacheFonte
    clef = (nom_fichier, taille)
    if clef not in _CacheFonte:
        _CacheFonte[clef] = charge_fonte_no_cache(nom_fichier, taille)

    return _CacheFonte[clef]


def charge_son_no_cache(nom_fichier, volume=0.5):
    fullfilename = cheminFichier(nom_fichier, subdir='sons')

    sound = pygame.mixer.Sound(fullfilename)
    sound.set_volume(volume)

    return sound


def charge_son(nom_fichier, volume=0.5):
    global _CacheSon
    if nom_fichier not in _CacheSon:
        _CacheSon[nom_fichier] = SonP(nom_fichier, volume)

    return _CacheSon[nom_fichier]


def lire_musique(nom_fichier, volume=0.5, loop=-1):
    nom_fichier = cheminFichier(nom_fichier, subdir='sons')

    pygame.mixer.music.load(nom_fichier)
    pygame.mixer.music.set_volume(volume)
    pygame.mixer.music.play(loop)


def arret_musique():
    pygame.mixer.music.stop()
