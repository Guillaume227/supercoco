#! /usr/bin/env python

import media
from media import charge_image

import elems
import pickle
import os

suffixe = '.monde'

class Monde(object):

    def __init__(self,nom='NouveauMonde'):
                        
        self.tempsMax_ = 400
        
        self.musique_       = "maintheme.ogg"
        self.nomJoueur_     = 'mario'
        self.etat_joueur_   = None
        
        # dans le jeu d'origine, la brique la plus basse est coupee a sa moitie
        self.marge_bas_  = .5 # en ratio de media.TAILLE_BLOC
        
        self._image_fond = charge_image("background-2.png")
        self.parallaxe_  = False
        
        self.nom = nom
        
        self.Elements = []
        self.Elements.append(self.posDepart)
        
        # Le joueur a-t-il le droit de revenir sur ses pas ?
        self.revenir_en_arriere_ = False
        self.photos_ = []

    def __str__( self ):
        return 'Monde %s'% getattr( self, 'nom', 'sans nom' )
    
    @property
    def arriere_plan_( self ):
        return self._image_fond.fileName

    @arriere_plan_.setter
    def arriere_plan_( self, val ):
        self._image_fond = charge_image(val)
    
    @property
    def posDepart(self):
        if self.Elements:
            for Elem in self.Elements:
                if isinstance(Elem, elems.PositionDepart):
                    return Elem
                
            print self, 'position depart non trouvee' 
            
        return elems.PositionDepart((16,380)) # position par defaut
          
    
    def composition(self):
        """ Affiche la composition du monde """
        for Elem in sorted( self.Elements, key = lambda x: x.__class__.__name__ ):
            print Elem
    


def Existe(fileName):
    if not fileName.endswith(suffixe):
        fileName += suffixe
    return os.path.exists(os.path.join(media.SAUVE_REP,fileName))


def loads(fileObj):
    """ Code a activer si le nom d'un module ou d'une classe
        sauvegarde change.
    """
    def mapname(name):
        name = name.replace('code.','src.')
        return {'src.sprites':'src.elems',
                'src.data':'src.media',
                'src.level':'src.niveau',
                'Level':'Monde'}.get(name, name)
        #return name.replace('vieux_module', 'nouveau_module')

    def mapped_load_global(self):
        module = mapname(self.readline()[:-1])
        name = mapname(self.readline()[:-1])
        klass = self.find_class(module, name)
        self.append(klass)

    unpickler = pickle.Unpickler(fileObj)
    unpickler.dispatch[pickle.GLOBAL] = mapped_load_global
    return unpickler.load()

def Ouvrir(fileName=''):

    print 'Ouvrir', fileName
            
    if not fileName.endswith(suffixe):
        fileName += suffixe
            
    filePath = os.path.join(media.SAUVE_REP, fileName)

    fileObj = open( filePath, 'rb' )

    MondeObj = loads(fileObj)
    
    MondeObj.nom = fileName.split('.')[0]
    
    fileObj.close()
    
    return MondeObj

 
    
