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
from . import intermede


class ChangeLangueExc(Exception):
    pass


class Menu:
    """ Menu principal / page de garde du jeu """

    def __init__(self, plein_ecran):

        self.plein_ecran = plein_ecran
        self.boucle()

    @property
    def plein_ecran(self):
        return self._plein_ecran

    @plein_ecran.setter
    def plein_ecran(self, val):
        """ Mode d'affichage plein Ecran / fenetre """

        self._plein_ecran = val
        partie.get_mode_ecran(self._plein_ecran)
        pygame.mouse.set_visible(False)

    def actions(self, e):

        if e.type == QUIT:
            pygame.quit()
            return

        elif e.type == KEYDOWN:
            if e.key == pygame.K_e:
                self.plein_ecran = not self.plein_ecran

            elif e.key == pygame.K_n:
                from . import niveau
                file_name = niveau.select_monde()

                if not file_name:
                    return

                self.lancer_partie(file_name, mode_modifs=e.mod & pygame.KMOD_ALT)

    def init_menu_options(self):

        ecran = pygame.display.get_surface()
        ecran.fill((0, 0, 0))

        if not partie.Partie.Ombre:
            img_fond, coin_img = intercalaires.recadre_image(ecran, media.charge_image("Super Coco.jpg"))
            ecran.blit(img_fond, coin_img)

        if os.path.exists(media.cheminFichier('photos')) and False:
            options = [[langues.Traduc(langues.MENU_Lancer), self.lancer_partie_avec_photos], ]
        else:
            options = [[langues.Traduc(langues.MENU_Lancer), self.lancer_partie], ]

        options += [[langues.Traduc(langues.MENU_Aide), self.aide],
                    [langues.Traduc(langues.MENU_Change_Langue), self.change_langue],
                    [langues.Traduc(langues.MENU_Quiter), sys.exit], ]

        init_menu = menu.MenuOptions(next(zip(*options)),
                                     pos=(ecran.get_size()[0] / 2, 360),
                                     centre=True)

        if partie.Partie.Ombre:
            init_menu.couleur_texte_selec = (0, 0, 0)
            init_menu.couleur_texte = (150, 0, 0)
        else:
            init_menu.couleur_texte_selec = (255, 0, 0)
            init_menu.couleur_texte = (255, 255, 255)

        return init_menu, options

    def boucle(self):

        intermede.devinette_sans_echec()

        init_menu, options = self.init_menu_options()

        while True:

            try:
                index_option = init_menu.boucle(self.actions)
                if index_option is None:
                    break
                else:
                    options[index_option][1]()

            except SystemExit:
                return

            except ChangeLangueExc:
                init_menu, options = self.init_menu_options()

            except intercalaires.SautePlanche:
                pass

            except:
                traceback.print_exc()
                break

    def aller_au_niveau(self, niveau=None, mode_modifs=False):
        if niveau:
            self.lancer_partie(niveau, mode_modifs=mode_modifs)

    def lancer_partie_avec_photos(self, niveau='1-1', mode_modifs=False):
        self.lancer_partie(niveau=niveau, mode_modifs=mode_modifs, avec_photos=True)

    def lancer_partie(self, niveau='1-1', mode_modifs=False, avec_photos=False):

        partie.get_mode_ecran(True)
        partie_obj = partie.Partie()

        partie_obj.avec_photos = avec_photos

        if mode_modifs:
            partie_obj.set_mode_modifs()

        partie_obj.boucle(niveau)

        self._plein_ecran = partie_obj.plein_ecran

        pygame.mixer.music.stop()

    def aide(self):

        intercalaires.planche([langues.Traduc(langues.MENU_Aide),
                               "",
                               langues.Traduc(langues.AIDE_Manette),
                               "",
                               langues.Traduc(langues.AIDE_Deplacement),
                               langues.Traduc(langues.AIDE_Saut) + " : %s" % pygame.key.name(
                                   ControlePerso.BoutonA_key).upper(),
                               langues.Traduc(langues.AIDE_Course) + " : %s" % pygame.key.name(
                                   ControlePerso.BoutonB_key).upper(),
                               "",
                               "",
                               langues.Traduc(langues.AIDE_Retour),
                               langues.Traduc(langues.AIDE_PleinEcran),
                               ""], centre=False)

        return ""

    def change_langue(self):
        langues.ChangeLangue()
        raise ChangeLangueExc()
