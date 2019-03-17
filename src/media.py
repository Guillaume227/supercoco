import os, pygame, sys

#data_py  = os.path.abspath(os.path.dirname(__file__))
data_py   = os.path.dirname( os.path.abspath(sys.argv[0]) )
MEDIA_REP = os.path.normpath(os.path.join(data_py, 'media'))
SAUVE_REP = os.path.join(MEDIA_REP, 'mondes')

FONTE_DEFAUT = "font.ttf"

_CacheImage = {}
_CacheSon   = {}
_CacheFonte = {}

TAILLE_BLOC = 32

def ListeDesMondes():
    return [ nomFichier.split('.')[0] for nomFichier in os.listdir( SAUVE_REP ) if nomFichier.endswith('.monde') ]

def VidangeCache():
    _CacheImage.clear()
    _CacheSon.clear()
    
def cheminFichier(nomFichier, subdir='', verifExiste=True):
    nomFichierLong = os.path.join(MEDIA_REP, subdir, nomFichier)
    if verifExiste and not os.path.exists(nomFichierLong):
        raise MediaManquantExc(nomFichierLong)
    
    return nomFichierLong


class MediaManquantExc(Exception):
    
    def __init__(self, nomFichier):
        self.nomFichier = nomFichier
        
    def __repr__(self):
        return '%s introuvable'%self.nomFichier
    
    __str__ = __repr__
    
class SurfacePersistante( pygame.Surface ):
    """Enrobage de la classe pygame.Surface pour la rendre persistable avec pickle"""
    def __setstate__(self,Dict):
        self.__init__(**Dict)

class SurfaceP( SurfacePersistante ):
    """ Enrobage d'une image pour persistance
        Ne sauvegardons que le nom du fichier.
    """
    def __init__( self, fileName, flip=False, scale=2 ):
        fileName = fileName.replace('nagefire', 'firenage')
        self.fileName = fileName
        self.flip     = flip
        
        Image = charge_image_no_cache(fileName,scale)
        if self.flip:
            Image = pygame.transform.flip(Image, 1, 0)
        pygame.Surface.__init__( self, Image.get_size(), 0, Image)

        self.blit(Image,(0,0))
        global _CacheImage
        if fileName not in _CacheImage:
            _CacheImage[(fileName,flip)] = self
    
    def __str__(self):
        return SurfacePersistante.__str__(self) + ' ' + self.fileName

    def __getstate__(self):
        return dict( fileName = self.fileName, flip=self.flip )
        
class SurfaceTexte( SurfacePersistante ):

    def __init__( self, message, police, taille=16, couleur=(0,0,0) ):
        self.police = police
        self.taille = taille
        self.couleur = couleur
        self.message = message
        
        self.image = charge_fonte(police, taille).render(message, 1, couleur)
        
        #pygame.Surface.__init__( self, image.get_size(), 0, image )

    def __getstate__(self):
        return dict( police = self.police,
                     taille = self.taille,
                     couleur = self.couleur,
                     message = self.message)


def charge_image_no_cache(filename,scale=1):
        
    fullfilename = cheminFichier(filename)
    
    try:
        
        image = pygame.image.load(fullfilename)
        image = pygame.transform.scale(image, (image.get_width()*scale, image.get_height()*scale))
        
    except pygame.error:
        import traceback
        traceback.print_exc()
            
    return image.convert_alpha()
    
def charge_image(nomFichier,flip=False,scale=2):
    
    if (nomFichier,flip) not in _CacheImage:
        
        _CacheImage[(nomFichier,flip)] = SurfaceP(nomFichier,flip,scale)

    return _CacheImage[(nomFichier,flip)]


class SonP( pygame.mixer.Sound ):

    def __init__( self, fileName, volume ):
        
        self.__safe_for_unpickling__ = True
        
        fileName = cheminFichier(fileName, subdir='sons')
        pygame.mixer.Sound.__init__(self, fileName)
        
        self.fileName = fileName
        self.volume = volume
        
        self.set_volume(volume)

        global _CacheSon
        if fileName not in _CacheSon:
            _CacheSon[fileName] = self
    
    def __str__(self):
        return pygame.mixer.Sound.__str__(self), self.fileName
    
    def __reduce__(self):
        return SonP, (self.fileName, self.volume)
    
    """
    def __getnewargs__(self):
        return self.fileName, self.volume
    """
    def __getstate__(self):
        return dict( fileName = self.fileName, volume = self.volume, __safe_for_unpickling__=True )
    """
    def __setstate__(self,Dict):
        self.__init__( **Dict )
        
    """


def charge_fonte_no_cache(nomFichier, taille=16):
        
    fullfilename = cheminFichier(nomFichier, subdir= 'fonts')

    return pygame.font.Font(fullfilename, taille)

           
def charge_fonte(nomFichier, taille):

    global _CacheFonte
    clef = (nomFichier,taille)
    if clef not in _CacheFonte:

        _CacheFonte[clef] = charge_fonte_no_cache(nomFichier, taille)
        
    return _CacheFonte[clef]

def charge_son_no_cache(nomFichier, volume=0.5):
    
    fullfilename = cheminFichier(nomFichier, subdir='sons')
    
    sound = pygame.mixer.Sound(fullfilename)
    sound.set_volume(volume)
           
    return sound
        
def charge_son(nomFichier, volume=0.5):

    global _CacheSon
    if nomFichier not in _CacheSon:

        _CacheSon[nomFichier] = SonP(nomFichier, volume)
        
    return _CacheSon[nomFichier]

def lire_musique(nomFichier, volume=0.5, loop=-1):
    nomFichier = cheminFichier(nomFichier, subdir='sons')
    
    pygame.mixer.music.load(nomFichier)
    pygame.mixer.music.set_volume(volume)
    pygame.mixer.music.play(loop)
    
def arret_musique():
    pygame.mixer.music.stop()
