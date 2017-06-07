#! /usr/bin/env python

from __future__ import absolute_import
from .elems import ControlePerso
from pygame.locals import *
from . import intercalaires
from . import media
from . import menu
import os
from . import partie
import pygame
import sys
import traceback
from . import langues

class ChangeLangueExc( Exception ):
    pass

class Menu(object):    
    """ Menu principal / page de garde du jeu """

    
    def __init__(self, pleinEcran=False):
        
        self.plein_ecran = pleinEcran
        self.boucle()
        
    @property
    def plein_ecran(self):
        return self._plein_ecran
    
    @plein_ecran.setter
    def plein_ecran(self, val):
        """ Mode d'affichage plein Ecran / fenetre """
        
        self._plein_ecran = val
        partie.GetEcran(self._plein_ecran)
        pygame.mouse.set_visible( False )
    
    
    def actions(self, e):
            
        if e.type == QUIT:
            pygame.quit()
            return
                    
        elif e.type == KEYDOWN:
            
            if e.key == pygame.K_e:    
                self.plein_ecran = not self.plein_ecran

                                    
    def InitMenuOptions(self):

        ecran = pygame.display.get_surface()
        ecran.fill((0,0,0))
        
        if not partie.Partie.Ombre:
            img_fond, coin_img = intercalaires.recadre_image( ecran, media.charge_image("Super Coco.jpg") )
            ecran.blit(img_fond, coin_img)
        
        if os.path.exists(media.cheminFichier('photos')):
            options = [ [langues.Traduc(langues.MENU_Lancer), self.LancerPartie],  ]
        else:
            options = [ [langues.Traduc(langues.MENU_Lancer), self.LancerPartie], ]
            
        options += [ [langues.Traduc(langues.MENU_Aide),           self.Aide],
                          [langues.Traduc(langues.MENU_Change_Langue),  self.ChangeLangue],
                          [langues.Traduc(langues.MENU_Quiter),         sys.exit], ]

        Menu = menu.MenuOptions( zip(*options)[0], pos=(ecran.get_size()[0]/2,360), centre=True )
        
        if partie.Partie.Ombre:
            Menu.couleur_texte_selec = (0, 0, 0)
            Menu.couleur_texte = (150, 0, 0)
        else:
            Menu.couleur_texte_selec = (255, 0, 0)
            Menu.couleur_texte = (255, 255, 255)

        return Menu, options
    
    def boucle(self):

        Menu, options = self.InitMenuOptions()
        
        while True:
            
            try:
                indexOption = Menu.boucle( self.actions )
                if indexOption is None:
                    break
                else:
                    options[indexOption][1]()    
                    
            except SystemExit:
                return
            
            except ChangeLangueExc:
                Menu, options = self.InitMenuOptions()
                
            except intercalaires.SautePlanche:
                pass
                            
            except:
                traceback.print_exc()
                break
                    
                
    def AllerAuNiveau( self, Niveau=None, ModeModifs=False ):
            
        if Niveau:
            self.LancerPartie(Niveau,ModeModifs=ModeModifs)

    def LancerPartieAvecPhotos(self, Niveau='1-1', ModeModifs=False):
        self.LancerPartie(Niveau, ModeModifs, AvecPhotos=True)
        
    def LancerPartie(self, Niveau='1-1', ModeModifs=False, AvecPhotos=False):
        
        Partie = partie.Partie()
        
        Partie.avec_photos = AvecPhotos
        
        if ModeModifs:
            Partie.SetModeModifs()
            
        Partie.boucle(Niveau)
        
        self._plein_ecran = Partie.plein_ecran
        
        pygame.mixer.music.stop()
        
    
    def Aide(self):
        
        intercalaires.planche([langues.Traduc(langues.MENU_Aide),
                                "",
                                langues.Traduc(langues.AIDE_Manette),
                                "",
                                langues.Traduc(langues.AIDE_Deplacement),
                                langues.Traduc(langues.AIDE_Saut)   + " : %s"%pygame.key.name(ControlePerso.BoutonA_key).upper(),
                                langues.Traduc(langues.AIDE_Course) + " : %s"%pygame.key.name(ControlePerso.BoutonB_key).upper(),
                                "",
                                "",
                                langues.Traduc(langues.AIDE_Retour),
                                langues.Traduc(langues.AIDE_PleinEcran),
                                ""], centre=False)

        return ""

    def ChangeLangue(self):
        langues.ChangeLangue()
        raise ChangeLangueExc()
