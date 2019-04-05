#! /usr/bin/env python

import sys

import pygame
from pygame.locals import *
import traceback
from . import crible
from . import intercalaires
from . import media
from . import elems
from . import ordonnet
from .elems import Perso, ControlePerso
import random
from . import langues

from .interruptions import MortJoueur, TransferMonde, InterruptionDePartie

from . import niveau
from .vect2d import Vec

try:
    from . import palette

    EDITABLE = True
except:
    EDITABLE = False


def get_mode_ecran(plein_ecran):
    if plein_ecran:
        flags = pygame.FULLSCREEN | pygame.HWSURFACE | pygame.DOUBLEBUF
    else:
        flags = pygame.DOUBLEBUF  # | pygame.NOFRAME

    titre = pygame.display.get_caption()
    pygame.display.quit()

    mode = pygame.display.set_mode(Partie.TailleEcran, flags)
    pygame.display.set_caption(*titre)
    return mode


def rect_from_points(pt1, pt2):
    p1, p2 = (min(pt1[0], pt2[0]), min(pt1[1], pt2[1])), \
             (max(pt1[0], pt2[0]), max(pt1[1], pt2[1]))

    return p1[0], p1[1], p2[0] - p1[0], p2[1] - p1[1]


def barycentre(coords):
    """ Barycentre d'un ensemble de points (x,y)"""
    bar = [0, 0]
    for coors in coords:
        bar[0] += coors[0]
        bar[1] += coors[1]

    num_points = len(coords)
    bar[0] /= num_points
    bar[1] /= num_points

    return bar


class Camera:

    def __init__(self, posCentre=(0, 0)):

        self.rect = pygame.display.get_surface().get_rect()
        self.rect_monde = None
        self.still_dim = 64

    def set_rect_monde(self, rect):
        self.rect_monde = rect
        self.rect.bottomleft = self.rect_monde.bottomleft

    def rel_rect(self, actor):
        """ passage du referentiel monde au referentiel camera """
        if isinstance(actor, Rect):
            rect = actor
        else:
            rect = actor.rect
        return Rect(rect.x - self.rect.x, rect.y - self.rect.y, rect.w, rect.h)

    def abs_point(self, point):
        return point[0] + self.rect.x, point[1] + self.rect.y

    def rel_point(self, point):
        return point[0] - self.rect.x, point[1] - self.rect.y

    def abs_rect_ip(self, rect):
        """ conversion de Rect du referentiel camera au referentiel absolu """
        rect.x += self.rect.x
        rect.y += self.rect.y

    def deplace(self, dX, dY):
        self.rect.centerx += dX
        self.rect.centery += dY

    def maj(self, cible, revenir_en_arriere=True):
        """mise a jour"""

        if cible[0] > self.rect.centerx + self.still_dim:
            self.rect.centerx = cible[0] - self.still_dim
        elif revenir_en_arriere and cible[0] < self.rect.centerx - self.still_dim:
            self.rect.centerx = cible[0] + self.still_dim

        if cible[1] > self.rect.centery + self.still_dim:
            self.rect.centery = cible[1] - self.still_dim
        elif cible[1] < self.rect.centery - self.still_dim:
            self.rect.centery = cible[1] + self.still_dim

        self.rect.clamp_ip(self.rect_monde)


class Partie:
    Ombre = False
    TailleEcran = 640, 480

    def __init__(self):

        self.en_pause = False
        self.jouer_musique = True
        self._affiche_stats = False
        self.phase_decompte = False
        self.photos_deja_vues = set()
        self.mode_modifs = False
        self.grille_ref = None
        self.selection_elem = []
        self.SelectionMotif = []
        self.monde_modifie = False
        self.couleur_selection = pygame.Color(0, 255, 0, 100)
        self._affiche_crible = False
        self.avec_photos = False
        self.clic_precedent = None

        ecran = pygame.display.get_surface()
        self.ecranH = ecran.get_height()
        self.ecranL = ecran.get_width()

        self._plein_ecran = False

        # mode pas a pas, i.e. action image par image, utile pour le deverolage
        self.pas_a_pas = None

        self.crible = None

        self._sauvegarde_possible = True

        self.son_pause = media.charge_son("smb_pause.wav")

        self.points = 0

        self.horloge = pygame.time.Clock()

        self.police = pygame.font.Font(media.cheminFichier("fonts/font.ttf"), 16 * self.ecranH // self.TailleEcran[0])
        elems.Legende.font = pygame.font.Font(media.cheminFichier("fonts/font.ttf"), 10)

        self.mini_pieces = [media.charge_image('piecette%d.png' % i) for i in (1, 3, 2, 1, 1)]

        self.temps_boucle_ms = 60  # millisecondes

        self.niveau = None

    def retaille_monde(self):
        """ Calcule les dimensions du rectangle contenant tous les elements du niveau"""
        rect = self.niveau.Elements[0].rect.copy()

        rect.unionall_ip([elem.rect for elem in self.niveau.Elements])

        rect_min = pygame.Rect((0, 0), self.TailleEcran)

        if self.niveau.parallaxe_:
            print('taille image_fond', self.niveau._image_fond.get_size())
            fond_h = self.niveau._image_fond.get_height()
            if fond_h > self.TailleEcran[1]:
                rect_min.h = fond_h

        rect_min.left = rect.left
        rect_min.right = rect.right

        # rectMin.bottomleft = rect.bottomleft
        rect.union_ip(rect_min)
        rect.bottom -= self.niveau.marge_bas_ * media.TAILLE_BLOC

        self.camera.set_rect_monde(rect)

        if self._affiche_stats:
            print('Dimensions du Monde', self.niveau.nom, self.camera.rect_monde)
            for elem in self.niveau.Elements:
                if elem.rect.left <= self.camera.rect_monde.left:
                    print('Gauche', elem)
                elif elem.rect.right >= self.camera.rect_monde.right:
                    print('Droite', elem)
                elif elem.rect.bottom >= self.camera.rect_monde.bottom:
                    pass  # print 'Bas', elem
                elif elem.rect.top <= self.camera.rect_monde.top:
                    print('Haut', elem)

    def boucle(self, nom_niveau):

        self.perso = None

        self.compte_a_rebours = 0
        self.temps_discret = 0

        self.camera = Camera()

        self.init_niveau(nom_niveau)

        self.lancer_intro_niveau()

        while True:

            try:

                self.boucle_niveau()

            except TransferMonde as exc:
                # perso a fini le niveau, poursuit vers le niveau suivant
                if exc.decompte:
                    self.points += self.perso.points

                self.perso.efface()
                self.init_niveau(nom_niveau=exc.monde, entree=exc.entree)

                self.lancer_intro_niveau(affiche=exc.decompte)

                self.phase_decompte = False

            except MortJoueur:

                self.ecran_de_mort()

                self.compte_a_rebours = 0

                if self.perso.vies <= 0:
                    self.affiche_fin_de_partie()
                    return

                # reset player
                self.perso = Perso((0, 0), vies=self.perso.vies)

                self.init_niveau(nom_niveau=self.niveau.nom)

                self.lancer_intro_niveau()

            except InterruptionDePartie:
                print("Partie interrompue par le joueur")
                return

    def lancer_intro_niveau(self, affiche=True):
        # Ecran d'introduction du niveau

        media.arret_musique()

        ecran = pygame.display.get_surface()
        ecran.fill((0, 0, 0))

        if self.avec_photos and self.niveau.nom not in self.PhotosDejaVues and not self.mode_modifs:
            sons = ["smb_coin.wav",
                    "smb_powerup.wav",
                    "1up.ogg",
                    "son_harricot.wav", ]

            sons_obj = [media.charge_son(son) for son in sons]

            son_cococouda = media.charge_son("the A-team theme.ogg")

            est_cococouda = False

            self.photos_deja_vues.add(self.niveau.nom)
            for img in self.niveau.photos_:

                try:

                    if self.niveau.nom == '1-1 bis' and not est_cococouda:
                        est_cococouda = True
                        son_cococouda.play()

                    elif not est_cococouda:
                        sons_obj[random.randint(0, len(sons) - 1)].play()

                    intercalaires.planche(photo=img, extro=True)

                except intercalaires.SautePlanche:
                    break

                except media.MediaManquantExc as exc:
                    print(exc)

            if est_cococouda:
                son_cococouda.stop()

        if affiche:
            ecran = pygame.display.get_surface()

            ecran.fill((0, 0, 0))

            self.affiche_stats()

            ecran_l, ecran_h = ecran.get_size()
            centre_x, centre_y = ecran_l / 2, ecran_h / 2
            ren = self.police.render(langues.Traduc(langues.Monde) + " " + self.niveau.nom.split("=")[0], 1,
                                     (255, 255, 255))
            ecran.blit(ren, (centre_x - ren.get_width() / 2, centre_y - 60))
            ecran.blit(self.perso.image, (centre_x - ren.get_width() / 2, centre_y - 10))
            ren = self.police.render("x  %d" % self.perso.vies, 1, (255, 255, 255))
            ecran.blit(ren, (centre_x * 1.1 - ren.get_width() / 2, centre_y))

        pygame.display.flip()
        if self.mode_modifs or not affiche:
            pause = 500
        else:
            pause = 2500

        pygame.time.wait(pause)
        if self.niveau.musique_:
            media.lire_musique(self.niveau.musique_)

    def ecran_de_mort(self):

        self.affiche_voile_d_ombre(100)
        ecran = pygame.display.get_surface()

        ren = self.police.render(langues.Traduc(langues.Perdu), 1, (255, 255, 255))
        ecran.blit(ren, (320 - ren.get_width() / 2, 235))
        self.affiche_stats()
        pygame.display.flip()
        pygame.time.wait(2500)

    def ecran_de_fin(self):
        pygame.time.wait(7500)
        pygame.display.flip()

    def affiche_fin_de_partie(self):
        media.lire_musique("smb_gameover.wav")
        intercalaires.planche([langues.Traduc(langues.Echec)])
        media.arret_musique()

    def init_niveau(self, nom_niveau='', entree=0, reinit=True):

        if reinit or not self.niveau:
            if niveau.existe(nom_niveau):
                info = niveau.ouvrir(nom_niveau)
                if info:
                    self.niveau = info
            else:
                self.niveau = niveau.Monde(nom_niveau)

        if self.perso is None:
            self.perso = Perso((0, 0))

        self.perso.nom = self.niveau.nomJoueur_
        if self.niveau.etat_joueur_ is not None and self.niveau.etat_joueur_ != '':
            self.perso.etat = self.niveau.etat_joueur_

        self.retaille_monde()

        if self.compte_a_rebours <= 0:
            self.compte_a_rebours = self.niveau.tempsMax_

        self.elems = ordonnet.Ordonnet()

        self.crible = crible.Crible(40)

        elems.Dessinable._crible = self.crible
        elems.Dessinable.groupe = self.elems
        elems.Dessinable.partie = self
        elems.Dessinable.joueur = self.perso

        for Elem in self.niveau.Elements:
            Elem.insere()

        self.place_joueur(entree)

        self.camera.maj(self.perso.rect.center)

        self._sauvegarde_possible = self.mode_modifs

    def place_joueur(self, entree):
        # Placement du joueur selon le point d'entree du niveau
        if entree == 0:
            # positionnement au debut du niveau
            self.perso.rect.bottomleft = self.niveau.posDepart.rect.bottomleft
            if not self.mode_modifs:
                self.perso.insere()

        elif not self.mode_modifs:
            # numero de tuyeau
            self.perso.rect.bottomleft = self.niveau.posDepart.rect.bottomleft
            for Elem in self.niveau.Elements:
                if isinstance(Elem, elems.Tuyeau):
                    if Elem.numero_ == entree:
                        self.perso.efface()
                        Elem.joueur = self.perso
                        break
            else:
                raise Exception("Point d'entree numero %d introuvable dans le monde %s" % (entree, self.niveau.nom))

            Elem.perso = self.perso

    def affiche_elems_niveau(self):

        # for s in self.crible.Intersecte(self.camera.rect):
        # l'ordre d'affichage des elements selon leur position dans self.elems
        # est essentielcccc
        elems = self.crible.intersecte(self.camera.rect)
        ecran = pygame.display.get_surface()
        for elem in self.ordonne_elems(elems):
            try:
                elem.affiche(ecran, self.camera)
            except:
                traceback.print_exc()
                print(elem, elem.rect)

    def boucle_niveau(self):

        avertissement = self.niveau.tempsMax_ <= 100
        transfer_monde_exc = None
        son_decompte = media.charge_son("decompte.ogg")
        mort_joueur_exc = None

        pygame.event.clear()

        while True:

            if not self.perso.auto_pilote:
                # Note : commandes de saut et de tirs sont percues comme evenements dans TraiterEvenements ci-dessous
                self.perso.Controle.capte()

            try:
                self.traite_les_evenements()

            except (SystemExit, InterruptionDePartie):
                raise

            except:
                traceback.print_exc()

            if self._affiche_crible:
                pass
                # self.crible.Integrite()
                # self.elems.integrite()

            if not self.en_pause and not self.mode_modifs and (self.pas_a_pas is None or self.pas_a_pas):

                self._sauvegarde_possible = False

                if self.pas_a_pas is True and not pygame.key.get_pressed()[K_SPACE]:
                    self.pas_a_pas = False

                self.horloge.tick(self.temps_boucle_ms)
                self.temps_discret += 1
                elems.Dessinable.index_temps = self.temps_discret

                self.camera.maj(self.perso.rect.center, self.niveau.revenir_en_arriere_)

                try:

                    # Boucle sur tous les elements du niveau
                    extra_l = self.camera.rect.w / 2
                    extra_h = 200
                    rect_action = self.camera.rect.move(-extra_l, -extra_h)
                    rect_action.w = rect_action.w + extra_l
                    rect_action.h += 50 + extra_h

                    # Elements actifs
                    for s in self.crible.intersecte(rect_action):

                        if s.vivant():

                            if hasattr(s, 'maj'):
                                s.maj()

                            if s.rect.colliderect(self.camera.rect):

                                s.hors_champ = False
                                if hasattr(s, 'action_in_camera'):
                                    s.action_in_camera(self.perso, self.camera)

                            else:
                                s.horschamp(self.perso, self.camera)
                                s.hors_champ = True

                except MortJoueur as exc:
                    mort_joueur_exc = exc

                except TransferMonde as exc:

                    transfer_monde_exc = exc
                    media.arret_musique()

                    # Pas de decompte pour les sous-niveaux

                    if exc.decompte:

                        self.phase_decompte = True
                        self.temps_restant = self.compte_a_rebours

                        son_decompte.play(loops=-1)

                    else:
                        raise exc

                if self.phase_decompte:

                    if self.compte_a_rebours > 0:

                        if self.compte_a_rebours > 400:
                            self.compte_a_rebours -= self.compte_a_rebours / 50
                        else:
                            self.compte_a_rebours -= 1

                        self.points += 50

                        if self.compte_a_rebours <= 0:
                            son_decompte.stop()

                    elif self.compte_a_rebours <= -20:

                        if transfer_monde_exc:

                            if not pygame.mixer.get_busy():
                                # Attend la fin de la musiquette pour passer au monde suivant
                                raise transfer_monde_exc
                            else:
                                print('Attente de la fin de la musiquette')

                    else:
                        # Compte a rebours negatif en attendant de passer au niveau suivant.
                        self.compte_a_rebours -= self.temps_boucle_ms * .001

                else:
                    # pas en phase decompte

                    if self.perso.vivant():

                        self.compte_a_rebours -= self.temps_boucle_ms * .001

                        if self.compte_a_rebours <= 100 and not avertissement:
                            # Compte a rebours lorsque le temps descend sous 100
                            avertissement = True
                            media.charge_son("smb_warning.wav").play()

                        if not self.niveau.revenir_en_arriere_ and self.perso.rect.left < self.camera.rect.left:
                            # Empeche mario de revenir en arriere si le niveau l'interdit
                            self.perso.rect.clamp_ip(self.camera.rect)
                            self.perso.deplace()

                        if self.perso.rect.right > self.camera.rect_monde.right or \
                                self.perso.rect.left < self.camera.rect_monde.left:
                            # Empeche mario de sortir des limites horizontales du monde.
                            self.perso.rect.clamp_ip(self.camera.rect_monde)
                            self.perso.deplace()

                        if self.compte_a_rebours <= 0:

                            # Compte a rebours ecoule
                            if not self.perso.invincible:
                                self.perso.tue()

            # Affichage du decors de fond
            image_fond = self.niveau._image_fond

            if self.niveau.parallaxe_:
                # Le niveau defile plus ou moins vite que le fond d'ecran
                x, y = self.camera.rect.topleft
                li, _hi = image_fond.get_size()
                longueur, hauteur = self.camera.rect_monde.size
                le, he = self.TailleEcran
                # yrel    = 0

                if hauteur != he:
                    # yrel = y/(H-he)*(hi-he)
                    # yrel = max(0, min( hi-y, hi-he ) )
                    pass

                xrel = x / (longueur - le) * (li - le)

                area = pygame.Rect(xrel, y, le, he)
                area.clamp_ip(image_fond.get_rect())
                # print xrel, yrel

            else:
                area = None

            ecran = pygame.display.get_surface()

            ecran.blit(image_fond, (0, 0), area=area)

            self.affiche_elems_niveau()
            self.affiche_stats()

            if self._affiche_crible:
                self.affiche_crible()

            # Mode Modifications
            if self.mode_modifs:

                mods = pygame.key.get_mods()

                # Deplacement de la camera avec les fleches clavier

                dX = 0
                dY = 0

                if self.perso.Controle.Haut:
                    dY -= 1
                if self.perso.Controle.Bas:
                    dY += 1
                if self.perso.Controle.Gauche:
                    dX -= 1
                if self.perso.Controle.Droite:
                    dX += 1

                if mods & pygame.KMOD_ALT:
                    if mods & pygame.KMOD_SHIFT:
                        # Deplacement de la selection

                        dP = dX, dY
                        if dX or dY:
                            for elem in self.selection_elem:
                                elem.deplace(dP, mode_modifs=True)
                                self.monde_modifie = True

                else:
                    if mods & pygame.KMOD_CTRL:
                        # Deplacement de la camera avec la souris

                        # Boutton3Presse = pygame.mouse.get_pressed()[2]
                        pos_souris = pygame.mouse.get_pos()
                        marge_souris = 20

                        derive = 1
                        if 0 < pos_souris[1] < marge_souris:
                            dY -= derive
                        if self.TailleEcran[1] - 1 > pos_souris[1] > self.TailleEcran[1] - marge_souris:
                            dY += derive
                        if 0 < pos_souris[0] < marge_souris:
                            dX -= derive
                        if self.TailleEcran[0] - 1 > pos_souris[0] > self.TailleEcran[0] - marge_souris:
                            dX += derive

                    if dX or dY:

                        derive = 4
                        if self.perso.Controle.BoutonB:
                            derive *= 2

                        dX *= derive
                        dY *= derive

                        self.camera.deplace(dX, dY)

                pos_souris = pygame.mouse.get_pos()

                mouse_button_state = pygame.mouse.get_pressed()

                mods = pygame.key.get_mods()

                temp_select = []
                if self.clic_precedent and mouse_button_state[0]:
                    # Dessinons le Carre de selection
                    clic_prec_rel = self.camera.rel_point(self.clic_precedent)
                    rect_select = Rect(rect_from_points(clic_prec_rel, pos_souris))
                    pygame.draw.rect(ecran, self.couleur_selection, rect_select, 1)

                    temp_select = self.select_elem(clic_prec_rel, pos_souris)
                    # if mods & pygame.KMOD_CTRL:
                    # Dessine tous les elements qui sont exactement un des ensembles 
                    # TempSelect et selection_elem
                    elements = set(temp_select).symmetric_difference(self.selection_elem)

                    for elem in elements:
                        pygame.draw.rect(ecran, self.couleur_selection, self.camera.rel_rect(elem), 1)

                # Dessinons la selection
                elif self.selection_elem:

                    extra_offset = self.mouve_select_offset(pos_souris)

                    for elem in self.selection_elem:
                        if extra_offset and (mods & pygame.KMOD_CTRL or not elem.vivant()):
                            # Ombre l'endroit de collage potentiel
                            ImageOmbree = elem.image.convert()
                            ImageOmbree.set_alpha(100)
                            ecran.blit(ImageOmbree, self.camera.rel_rect(elem.rect.move(*extra_offset)).topleft)
                        else:
                            # Souligne la bordure des elements selectionnes
                            pygame.draw.rect(ecran, self.couleur_selection, self.camera.rel_rect(elem), 1)

                if self.grille_ref:
                    # Dessine grille magnetique
                    pygame.draw.rect(ecran, pygame.Color(0, 255, 255, 100), self.camera.rel_rect(self.grille_ref.rect),
                                     3)

            if self.en_pause:
                self.affiche_voile_d_ombre(100)

                self.affiche_texte("PAUSE", pos=(self.TailleEcran[0] / 2, self.TailleEcran[1] / 2))

            if self.Ombre:
                self.affiche_voile_d_ombre(200)

            pygame.display.flip()

            if mort_joueur_exc:
                # permet l'affichage de la derniere toile avant le gel de la mise a jour
                raise mort_joueur_exc

    def affiche_texte(self, texte, pos, centre=(True, True), couleur=(255, 255, 255)):
        """affiche du texte a l'ecran"""
        texte_img = self.police.render(texte, 2, (255, 255, 255))

        coin_haut_gauche = list(pos)
        txt_dim = texte_img.get_size()
        ecran = pygame.display.get_surface()

        for i in 0, 1:

            if centre[i]:
                coin_haut_gauche[i] -= txt_dim[i] / 2

            elif pos[i] < 0:
                coin_haut_gauche[i] += self.TailleEcran[i] - txt_dim[i]

        ecran.blit(texte_img, coin_haut_gauche)

        return txt_dim

    def affiche_voile_d_ombre(self, alpha=100):
        ombre = pygame.Surface(self.TailleEcran)
        ombre.fill((0, 0, 0))
        ombre.set_alpha(alpha)
        ecran = pygame.display.get_surface()
        ecran.blit(ombre, (0, 0))
        return ombre

    def sauvegarde_possible(self):
        return self.mode_modifs and self._sauvegarde_possible

    @property
    def plein_ecran(self):
        return self._plein_ecran

    @plein_ecran.setter
    def plein_ecran(self, val):
        """ Mode d'affichage plein Ecran / fenetre """

        self._plein_ecran = val
        get_mode_ecran(self._plein_ecran)
        pygame.mouse.set_visible(False)

    def traite_les_evenements(self):

        # Instructions des peripheriques 
        for e in pygame.event.get():

            if e.type == QUIT:
                if not self.sauvegarde_possible() or self.valide_modifs():
                    sys.exit()

            # Instructions au clavier
            if e.type == KEYDOWN:

                key = e.key
                if key == K_F1:
                    # Affiche l'aide
                    aide = """  m ou l : passage en / sortie du mode modifs
                                e : mode plein ecran
                                i : perso invincible / vulnerable
                                u : transformation du perso
                                t : affiche la composition du monde
                                n : change le nom du perso (coco <-> mario)

                                echap : interruption de la partie - retour au menu

                                En Mode Modifs:

                                Clic Gauche [+ deplacement souris] : Boite de Selection
                                Clic Gauche + MAJ : ajoute / retranche a la selection
                                Clic Droit sur un element : edition des parametres d'un element
                                Clic Droit sur l'image de fond : edition des parametres de niveau
                            
                                Clic Droit + CTRL : colle une copie de la selection
                                Molette souris : changement de l'ordre du plan de la selection (vers le premier ou l'arriere plan)

                                CTRL + deplacement souris vers les bords : deplacement de la camera
                                ALT + Deplacement Souris : deplacement de la selection
                                ALT + fleches : deplacement pixel par pixel de la selection
                                ALT + MAJ + fleches : deplacement continu de la selection 

                                G : (de)selection de l'element de reference du mode grille (pour alignement facile)
                                En mode grille : CTRL + bouton droit souris enfonce pour coller rapidement de nouveaux elements
                                Touche Effacer : effacte la selection

                                CTRL + A : selectionne tout le niveau

                                d : recentre le niveau sur la position de depart

                                r : re-initialisation de la selection (perte possible d'info)

                                CTRL + S : sauvegarde du niveau
                                CTRL + MAJ + S : sauvegarder sous
                                CTRL + O : ouvrir un niveau

                                CTRL + Espace : mode pas-a-pas Espace en mode pas-a-pas : avance de pas en pas.
                                """.splitlines()

                    intercalaires.planche(aide, taille=8, centre=False, extro=False, intro=False)

                elif key == K_SPACE:
                    # Mode pas a pas

                    if e.mod & pygame.KMOD_CTRL:
                        if self.pas_a_pas is None:
                            print('mode pas a pas active')
                            self.pas_a_pas = False
                        else:
                            self.pas_a_pas = None
                    elif self.pas_a_pas is False:
                        self.pas_a_pas = True

                    # Mise en pause
                    else:
                        self.bascule_en_pause()

                elif key == K_ESCAPE:
                    # Sortie du jeu
                    media.arret_musique()
                    pygame.mixer.stop()

                    if not self.sauvegarde_possible() or self.valide_modifs():
                        raise InterruptionDePartie

                elif key == K_e:
                    self.plein_ecran = not self.plein_ecran

                elif key == K_i:
                    self.perso.invincible = not self.perso.invincible
                    print('perso invincible:', self.perso.invincible)

                elif key in (ControlePerso.BoutonA_key, ControlePerso.BoutonB_key):
                    if not self.en_pause and not self.phase_decompte:
                        if key == ControlePerso.BoutonA_key:
                            self.perso.Controle.BoutonA_evenement = True
                        else:
                            self.perso.Controle.BoutonB_evenement = True

                elif key == K_F2:
                    # Mode musique / silencieux
                    self.jouer_musique = not self.jouer_musique
                    if self.jouer_musique:
                        pygame.mixer.music.unpause()
                    else:
                        pygame.mixer.music.pause()

                elif key in [pygame.K_PRINT, pygame.K_INSERT] or (
                        EDITABLE and key == pygame.K_v and not e.mod & pygame.KMOD_CTRL):
                    self.imprime_ecran(vers_presse_papier=e.mod & pygame.KMOD_CTRL)

                elif key == K_b:
                    # change les boutons de la manette
                    # elems.ControlePerso.BoutonA_joy = 3
                    elems.ControlePerso.BoutonB_joy = 2

                    print('BoutonA', elems.ControlePerso.BoutonA_joy)
                    print('BoutonB', elems.ControlePerso.BoutonB_joy)

                elif e.mod & pygame.KMOD_CTRL:

                    if key == K_w:
                        import profileur
                        profileur.Bascule()

                    elif key == K_v:
                        self.perso.vies += 1

                    elif key == K_y:
                        self._affiche_stats = not self._affiche_stats

                    elif key == K_i:
                        # Invincibilite
                        self.perso.invincible = not self.perso.invincible

                        if self.perso.invincible:
                            print('perso invincible')
                        else:
                            print('perso vulnerable')

                    elif key == K_t:

                        self.compte_a_rebours += 100

                    elif key == K_k:
                        # Composition du monde
                        print()
                        print('Dans le niveau')
                        self.niveau.composition()

                        print()
                        print('Dans le crible')
                        for elem in self.crible.Tous():
                            print(elem)

                        print()
                        print('Dans le groupe')
                        for elem in self.elems:
                            print(elem)

                        print()

                    elif key in [K_l, K_m]:
                        if e.mod & pygame.KMOD_CTRL:
                            self.set_mode_modifs()

                    elif key == K_u:
                        if e.mod & pygame.KMOD_CTRL:
                            if e.mod & pygame.KMOD_SHIFT:
                                self.perso.blesse()
                            else:
                                self.perso.metamorphe()

                if self.mode_modifs:
                    from . import menu
                    GaucheDroite = {K_LEFT: -1, K_RIGHT: 1}
                    HautBas = {K_UP: -1, K_DOWN: 1}
                    if key in GaucheDroite or key in HautBas:

                        if e.mod & pygame.KMOD_ALT and not e.mod & pygame.KMOD_CTRL:
                            # Deplacement fin de la selection pixel par pixel
                            dP = GaucheDroite.get(key, 0), HautBas.get(key, 0)
                            if dP[0] or dP[1]:
                                for elem in self.selection_elem:
                                    elem.deplace(dP, mode_modifs=True)
                                    self.monde_modifie = True

                    elif key == K_DELETE:
                        for elem in self.selection_elem:
                            self.monde_modifie = True

                            if elem.vivant():
                                elem.efface()

                        self.selection_elem = []

                    if key == K_d:
                        # Retour au point de depart
                        self.camera.maj(self.niveau.posDepart.rect.center)

                    elif key == K_r:
                        # Reinitialisation des elements selectionnes 
                        for SelIndex, elem in enumerate(self.selection_elem):

                            nov_elem = type(elem)(elem.rect.topleft)
                            nov_elem.insere(index=elem.index())
                            elem.efface()

                            print('Re-init de ', elem)
                            if hasattr(elem, 'surprise_'):
                                surprise = elem.surprise_
                                if surprise:
                                    nov_elem.surprise_ = type(surprise)()
                                    nov_elem.surprise_.efface()

                            self.selection_elem[SelIndex] = nov_elem
                            self.monde_modifie = True

                    elif key == K_p:
                        # Affichage de la palette d'elements
                        from . import palette
                        elem = palette.Selecte()

                        if elem:
                            self.selection_elem = [elem]

                    elif key == K_f:
                        self._affiche_crible = not self._affiche_crible
                        print('affiche crible', self._affiche_crible)

                    elif key == K_v:
                        if e.mod & pygame.KMOD_CTRL:
                            self.colle_selection(pygame.mouse.get_pos())

                    elif key == K_g:
                        # (Des)Active la grille d'alignement
                        if self.selection_elem:
                            if self.grille_ref == self.selection_elem[0]:
                                self.grille_ref = None
                            else:
                                self.grille_ref = self.selection_elem[0]

                        else:
                            self.grille_ref = None

                    elif key == K_a:
                        if e.mod & pygame.KMOD_CTRL:

                            # Selectionner tout les elements du meme type que la selection...                     
                            if self.selection_elem:

                                if e.mod & pygame.KMOD_SHIFT:
                                    # ... parmis les elements du niveau
                                    population = self.elems
                                else:
                                    # ... parmis les elements visibles a l'ecran                                                
                                    population = self.select_elem((0, 0), self.TailleEcran)

                                selection = list(self.selection_elem)
                                population_par_type = {}
                                for elem in population:
                                    population_par_type.setdefault(type(elem), set()).add(elem)

                                select_types = set([type(Elem) for Elem in selection])

                                self.selection_elem = set(self.selection_elem)
                                for ElemType in select_types:
                                    NovSel = population_par_type.get(ElemType)
                                    if NovSel:
                                        print('Selection de %d %s' % (len(NovSel), ElemType))
                                        self.selection_elem.maj(NovSel)

                                self.selection_elem = list(self.selection_elem)

                            else:
                                # Selectionner tout
                                self.selection_elem = list(self.elems)

                    elif key == K_s:

                        if e.mod & pygame.KMOD_CTRL:
                            # sauvegarde du niveau

                            if not self.sauvegarde_possible():
                                # Afaire monde imodifiable
                                menu.BoiteMessage(['Sauvegarde en cours de partie impossible']).boucle()

                            else:
                                prompt = e.mod & pygame.KMOD_SHIFT

                                self.niveau.Elements = tuple(self.elems)
                                assert self.perso not in self.niveau.Elements

                                if self.niveau.Sauvegarde(renomme=prompt):
                                    self.monde_modifie = False

                        elif self.selection_elem:
                            print()
                            print("%d elements selectiones :" % len(self.selection_elem))
                            for elem in sorted(self.selection_elem):
                                print(elem)

                    elif key == K_o:

                        if e.mod & pygame.KMOD_CTRL:
                            # Ouvrons un niveau sauvegarde
                            if self.valide_modifs():

                                prompt = e.mod & pygame.KMOD_SHIFT
                                if prompt:
                                    nom_niveau = ''
                                else:
                                    nom_niveau = self.niveau.nom

                                nouv_level = niveau.ouvrir(nom_niveau)

                                if nouv_level:
                                    self.selection_elem = []
                                    media.VidangeCache()

                                    self.niveau = nouv_level

                                    self.perso.efface(strict=False)
                                    self.perso = None

                                    self.compte_a_rebours = 0

                                    self.init_niveau()

                                    self.monde_modifie = False

                                    return True

            elif e.type == pygame.JOYBUTTONDOWN:
                if not self.en_pause and e.button == ControlePerso.BoutonA_joy:
                    # Saut du perso joueur
                    self.perso.saute()

                elif not self.en_pause and e.button == ControlePerso.BoutonB_joy:
                    self.perso.tire()

                elif e.button == 3:
                    # mise en pause
                    self.bascule_en_pause()

                else:
                    pass

            elif self.mode_modifs:
                #
                # Edition du niveau
                #

                mods = pygame.key.get_mods()

                if e.type == pygame.MOUSEMOTION:

                    if self.selection_elem:

                        if pygame.mouse.get_pressed()[2] and self.grille_ref:
                            self.colle_selection(pygame.mouse.get_pos())

                        elif pygame.mouse.get_pressed()[0]:
                            pass

                        elif mods & pygame.KMOD_ALT:

                            # Deplace elements existants

                            self.monde_modifie = True

                            # Mode alignement sur grille

                            pos_rel = self.mouve_select_offset(e.pos)
                            if pos_rel:
                                for elem in self.selection_elem:
                                    elem.deplace(pos_rel, mode_modifs=True)

                elif e.type == pygame.MOUSEBUTTONUP:

                    if e.button == 1:

                        if self.clic_precedent is not None:

                            # Rectangle de selection
                            nouvel_selection = self.select_elem(self.camera.rel_point(self.clic_precedent), e.pos)

                            if nouvel_selection:

                                if mods & pygame.KMOD_SHIFT:
                                    for elem in nouvel_selection:
                                        if elem in self.selection_elem:
                                            self.selection_elem.remove(elem)
                                        else:
                                            self.selection_elem.append(elem)

                                elif self.perso in nouvel_selection:
                                    # Joueur dans la selection - ne selectionnons que lui
                                    self.selection_elem = [self.perso]

                                elif Vec(self.camera.rel_point(self.clic_precedent)) - Vec(e.pos) < 2:
                                    # Double click (clic suffisament proches)
                                    # selectionnons seulement l'element au premier plan

                                    nouvel_selection = self.ordonne_elems(nouvel_selection)

                                    self.selection_elem.append(nouvel_selection[-1])

                                else:

                                    for elem in nouvel_selection:
                                        if elem not in self.selection_elem:
                                            self.selection_elem.append(elem)

                                # if self.grilleRef is None and not self.selection_elem[0].vivant():
                                #    self.grilleRef = self.selection_elem[0]

                        self.clic_precedent = None

                elif e.type == pygame.MOUSEBUTTONDOWN:

                    if e.button == 3:

                        if self.selection_elem and (mods & pygame.KMOD_CTRL or not self.selection_elem[0].vivant()):
                            # Copier/Coller de la selection
                            self.colle_selection(e.pos)

                        else:

                            edit_elems = []

                            clic_elems = self.ordonne_elems(self.select_elem(e.pos, e.pos))

                            if self.selection_elem:

                                if clic_elems and clic_elems[-1] in self.selection_elem:
                                    edit_elems = [Elem for Elem in self.selection_elem if
                                                  isinstance(Elem, type(clic_elems[-1]))]
                                    self.selection_elem = edit_elems
                                else:
                                    # Deselection
                                    self.selection_elem = []

                            elif clic_elems:
                                edit_elems = [clic_elems[-1]]

                            else:
                                edit_elems = [self.niveau]

                                self.selection_elem = []

                            if edit_elems:
                                from . import palette

                                self.affiche_voile_d_ombre()

                                if palette.Editor(*edit_elems):
                                    self.monde_modifie = True

                    elif e.button == 1:

                        if not mods & pygame.KMOD_SHIFT:
                            self.selection_elem = []

                        # premier jalon d'une selection
                        self.clic_precedent = self.camera.abs_point(e.pos)

                    elif e.button in (4, 5):
                        #
                        # Change l'ordre des elements des differents plans
                        #
                        if self.selection_elem:
                            #
                            # Change le plan des elements de la  selection : vers devant ou vers l'arriere
                            #
                            en_avant = e.button == 4
                            select = self.selection_elem[0]
                            nouv_elems = self.elems

                            if en_avant:
                                index_gen = range(nouv_elems.index(select), len(nouv_elems))

                            else:
                                index_gen = reversed(range(0, nouv_elems.index(select)))

                            for index in index_gen:
                                elem = nouv_elems[index]
                                if elem != select and elem.rect.colliderect(select):
                                    break
                            else:
                                index = None

                            if en_avant:
                                if index is None:
                                    # tout devant
                                    nouv_elems.deplace(select)
                                else:
                                    nouv_elems.deplace(select, nouvelIndex=index + 1)

                            else:
                                if index is None:
                                    index = 0  # tout en arriere

                                nouv_elems.deplace(select, nouvelIndex=index)

    def ordonne_elems(self, elements):
        return sorted(elements, key=self.elems.index)

    def colle_selection(self, pos):
        # Copier/Coller de la selection dont le barycentre se deplace a pos
        import copy
        if not self.selection_elem:
            return

        extra_offset = self.mouve_select_offset(pos)

        if extra_offset:

            # collage d'element                     
            try:

                # Colle les elements de la selection
                for ElemIndex, Elem in enumerate(self.selection_elem):

                    self.monde_modifie = True
                    nov_elem = copy.deepcopy(Elem)

                    # En mode Grille, n'ajoutons que si l'espace est libre

                    if Elem.vivant():
                        # Si l'element existe deja dans le niveau,
                        # ajoutons le nouvel element dans le meme plan
                        nov_elem.insere(index=Elem.index())

                    else:
                        # Nouvel element, au premier plan.
                        nov_elem.insere()

                    nov_elem.deplace(mouve=extra_offset, mode_modifs=True)

                    self.selection_elem[ElemIndex] = nov_elem

            except:
                traceback.print_exc()

    def mouve_select_offset(self, pos):
        """ Calcule le deplacement du barycentre des centres des elements selectionnes aux coords pos 
            pos : dans le referentiel camera
        """
        # Alignement sur la position de l'element grilleRef dont le rect definit une grille de reference

        # Passage du referentiel camera au referentiel absolu                    
        nouv_coords = Vec(pos) + self.camera.rect.topleft

        if self.grille_ref:
            ref_rect = self.grille_ref.rect

            coords_ref_grille = nouv_coords - ref_rect.center

            grille = ref_rect.w, ref_rect.h

            coords_ref_grille = [round(coords_ref_grille[i] / grille[i], 0) * grille[i] for i in (0, 1)]

            nouv_coords = Vec(ref_rect.center) + coords_ref_grille

        bary = barycentre([Elem.rect.center for Elem in self.selection_elem])

        deplacement = nouv_coords - bary

        mods = pygame.key.get_mods()
        verif_intersection = mods & pygame.KMOD_SHIFT

        if verif_intersection:
            # Verifie que l'on ne se cogne a aucun element visible a l'ecran
            for Elem in self.selection_elem:
                tentative_rect = self.camera.rel_rect(Elem.rect.move(*deplacement))
                sels = self.select_elem(tentative_rect.topleft, tentative_rect.bottomright)
                if sels:
                    return None

        return deplacement

    def valide_modifs(self):
        # A faire
        if self.monde_modifie:
            from . import menu
            if 0 == menu.MenuOptions(options=['Oui', 'Non'], legende=['Abandonner les modifs ?'], pos=(200, 100),
                                     alpha_fond=150).boucle():
                self.monde_modifie = False
                return True
            else:
                return False

        else:
            return True

    def select_elem(self, pt1, pt2):
        """ Point1 et Point2 sont dans le referentiel camera (relatif) """

        selection_rect = Rect(rect_from_points(pt1, pt2))

        # Passage du referentiel camera au referentiel absolu
        self.camera.abs_rect_ip(selection_rect)
        selection = self.crible.intersecte(selection_rect)

        return selection

    def set_mode_modifs(self):
        if not EDITABLE:
            self.mode_modifs = False

        else:
            if self.sauvegarde_possible():
                if self.valide_modifs():
                    self.mode_modifs = False
                    self.init_niveau(reinit=False)

                else:
                    return
            else:
                self.mode_modifs = not self.mode_modifs

            if self.mode_modifs:

                pygame.mixer.music.pause()

            else:
                if not self.en_pause:
                    pygame.mixer.music.unpause()

                self.retaille_monde()

        pygame.mouse.set_visible(self.mode_modifs)

    def bascule_en_pause(self):
        self.en_pause = not self.en_pause

        if self.en_pause:
            self.son_pause.play()
            pygame.mixer.music.pause()
        else:
            pygame.mixer.music.unpause()

    def affiche_crible(self):

        if self.selection_elem:
            rects = [elem.rect for elem in self.selection_elem]
        else:
            rects = [self.camera.rect]

        ecran = pygame.display.get_surface()
        for rect in rects:
            for rect_coor in self.crible.rects(rect):
                pygame.draw.rect(ecran, (250, 150, 50), self.camera.rel_rect(Rect(*rect_coor)), 1)

    def affiche_stats(self):

        ecran = pygame.display.get_surface()
        ecran_l, ecran_h = self.TailleEcran
        marge_cote = self.ecranL / ecran_l * 50

        police_h = self.police.get_height() * 20 / 16
        marge_h = self.ecranH / ecran_h * 10

        # Nom du perso
        texte_dim = self.affiche_texte(self.perso.nom.upper(), pos=(marge_cote, marge_h), centre=(False, False))
        self.affiche_texte("%05d" % (self.points + self.perso.points),
                           pos=(-ecran_l + marge_cote + texte_dim[0], marge_h + police_h), centre=(False, False))

        # Nombre de pieces
        self.affiche_texte("x%02d" % self.perso.boursePieces, pos=(marge_cote + 100, marge_h + police_h),
                           centre=(False, False))

        ecran.blit(self.mini_pieces[int(self.temps_discret / 9) % len(self.mini_pieces)],
                   (marge_cote + 86, marge_h + police_h - 3))

        # Nom du monde
        ancre_monde = self.TailleEcran[0] / 2 - 100
        self.affiche_texte(langues.Traduc(langues.Monde), pos=(-ancre_monde, marge_h), centre=(False, False))
        self.affiche_texte(self.niveau.nom.split('=')[0], pos=(-ancre_monde, marge_h + police_h), centre=(False, False))

        # Temps ecoule
        self.affiche_texte(langues.Traduc(langues.Temps), pos=(-marge_cote, marge_h), centre=(False, False))
        self.affiche_texte("%d" % max(0, self.compte_a_rebours), pos=(-marge_cote, marge_h + police_h),
                           centre=(False, False))

        if self.mode_modifs:
            # Coordonnees absolues de la souris
            pos = pygame.mouse.get_pos()
            pos_abs = self.camera.abs_point(pos)

            self.affiche_texte("%d,%d" % (pos_abs[0], pos_abs[1]),
                               pos=(ecran_l / 2, - 2 * police_h - 5),
                               centre=(True, False))
            if self.clic_precedent:
                self.affiche_texte("%d,%d" % (pos_abs[0] - self.clic_precedent[0], pos_abs[1] - self.clic_precedent[1]),
                                   pos=(ecran_l / 2, - police_h - 5), centre=(True, False))

        if self.mode_modifs or self._affiche_stats:
            self.affiche_texte("IPS : %d" % self.horloge.get_fps(), pos=(-1, -1), centre=(False, False))

            if len(self.selection_elem) == 1:
                elem = self.selection_elem[0]
            else:
                elem = self.perso

            for i, (legende, tuplet) in enumerate(
                    [('  v', elem.speed), ('h_g', elem.rect.topleft), ('b_d', elem.rect.bottomright),
                     ('lxh', elem.rect.size)]):
                self.affiche_texte("%s: %s" % (legende, tuplet), pos=(1, (i + 4) * police_h), centre=(False, False))

    def imprime_ecran(self, vers_presse_papier=False):
        """ Sauvegarde l'image a l'ecran
        NomModule = 'win32clipboard'
        try:
            win32clipboard = __import__(NomModule)
        except ImportError:
            print "Erreur: Imprime ecran necessite l'installation de %s"%NomModule
            return
         
        win32clipboard.OpenClipboard()
        win32clipboard.EmptyClipboard()
        win32clipboard.SetClipboardData(win32clipboard.CF_BITMAP, data)
        win32clipboard.CloseClipboard()
        """
        surface = pygame.display.get_surface().copy()

        if vers_presse_papier:
            pygame.scrap.init()
            pygame.scrap.set_mode(pygame.SCRAP_CLIPBOARD)
            image_data = pygame.image.tostring(surface, "RGBA")
            pygame.scrap.put(pygame.SCRAP_BMP, image_data)

        else:
            # vers fichier
            import os
            from . import sauvegarde

            cliche_rep = media.cheminFichier('cliches', verif_existe=False)
            if not os.path.exists(cliche_rep):
                os.mkdir(cliche_rep)

            nom_fichier = sauvegarde.SelectDansRepertoire(cliche_rep, suffixe='', defaut=self.niveau.nom,
                                                          legende="Sauver l'image d'ecran sous :",
                                                          choix_nouveau=True, valide_existant=True, effacable=True)

            if nom_fichier:
                nom_complet = os.path.join(cliche_rep, nom_fichier + '.png')
                print("sauvegarde d'ecran : %s" % nom_complet)
                pygame.image.save(surface, nom_complet)
