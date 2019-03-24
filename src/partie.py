from __future__ import print_function
from __future__ import absolute_import
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


def getModeEcran(plein_ecran):
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

    NumPoints = float(len(coords))
    bar[0] /= NumPoints
    bar[1] /= NumPoints

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

    def AbsPoint(self, point):
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

    def maj(self, cible, revenirEnArriere=True):
        """mise a jour"""

        if cible[0] > self.rect.centerx + self.still_dim:
            self.rect.centerx = cible[0] - self.still_dim
        elif revenirEnArriere and cible[0] < self.rect.centerx - self.still_dim:
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

        self.grilleRef = None
        self.selection_elem = []
        self.SelectionMotif = []

        self.couleur_selection = pygame.Color(0, 255, 0, 100)
        self._affiche_crible = False
        self.avec_photos = False
        self.clic_precedent = None

        ecran = pygame.display.get_surface()
        self.ecranH = ecran.get_height()
        self.ecranL = ecran.get_width()

        self._plein_ecran = True

        # mode pas a pas, i.e. action image par image, utile pour le deverolage
        self.pas_a_pas = None

        self.crible = None
        self.compte_a_rebours = 0

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
            fondH = self.niveau._image_fond.get_height()
            if fondH > self.TailleEcran[1]:
                rect_min.h = fondH

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
                self.init_niveau(nomNiveau=exc.monde, entree=exc.entree)

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

                self.init_niveau(nomNiveau=self.niveau.nom)

                self.lancer_intro_niveau()

            except InterruptionDePartie:
                print("Partie interrompue par le joueur")
                return

    def lancer_intro_niveau(self, affiche=True):
        # Ecran d'introduction du niveau

        media.arret_musique()

        ecran = pygame.display.get_surface()
        ecran.fill((0, 0, 0))

        if self.avec_photos and self.niveau.nom not in self.photos_deja_vues:
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

                    intercalaires.planche(photo=img, Extro=True)

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

    def show_end(self):
        pygame.time.wait(7500)
        pygame.display.flip()

    def affiche_fin_de_partie(self):
        media.lire_musique("smb_gameover.wav")
        intercalaires.planche([langues.Traduc(langues.Echec)])
        media.arret_musique()

    def init_niveau(self, nomNiveau='', entree=0, reinit=True):

        if reinit or not self.niveau:
            if niveau.Existe(nomNiveau):
                info = niveau.Ouvrir(nomNiveau)
                if info:
                    self.niveau = info
            else:
                self.niveau = niveau.Monde(nomNiveau)

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

    def place_joueur(self, entree):
        # Placement du joueur selon le point d'entree du niveau
        if entree == 0:
            # positionnement au debut du niveau
            self.perso.rect.bottomleft = self.niveau.posDepart.rect.bottomleft
            self.perso.insere()

        else:
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
        # est essentiel
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
                # Note : commandes de saut et de tirs sont percues comme evenments dans TraiterEvenements ci-dessous
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

            if not self.en_pause and (self.pas_a_pas is None or self.pas_a_pas):

                if self.pas_a_pas is True:
                    self.pas_a_pas = False

                self.horloge.tick(self.temps_boucle_ms)
                self.temps_discret += 1
                elems.Dessinable.index_temps = self.temps_discret

                self.camera.maj(self.perso.rect.center, self.niveau.revenir_en_arriere_)

                try:

                    # Boucle sur tous les elements du niveau
                    extraL = self.camera.rect.w / 2
                    extraH = 200
                    RectAction = self.camera.rect.move(-extraL, -extraH)
                    RectAction.w = RectAction.w + extraL
                    RectAction.h += 50 + extraH

                    # Elements actifs
                    for s in self.crible.intersecte(RectAction):

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
                L, H = self.camera.rect_monde.size
                le, he = self.TailleEcran
                # yrel    = 0

                if H != he:
                    # yrel = y/float(H-he)*(hi-he)
                    # yrel = max(0, min( hi-y, hi-he ) )
                    pass

                xrel = x / float(L - le) * (li - le)

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

    @property
    def plein_ecran(self):
        return self._plein_ecran

    @plein_ecran.setter
    def plein_ecran(self, val):
        """ Mode d'affichage plein Ecran / fenetre """

        self._plein_ecran = val
        getModeEcran(self._plein_ecran)
        pygame.mouse.set_visible(False)

    def traite_les_evenements(self):

        # Instructions des peripheriques
        for e in pygame.event.get():

            if e.type == QUIT:
                sys.exit()

            # Instructions au clavier
            if e.type == KEYDOWN:

                key = e.key
                if key == K_F1:
                    # Affiche l'aide
                    aide = """  
                                e : mode plein ecran

                                echap : interruption de la partie - retour au menu

                                """.splitlines()

                    intercalaires.planche(aide, taille=8, centre=False, Extro=False, Intro=False)

                elif key == K_SPACE:
                    # Mode pas a pas

                    if e.mod & pygame.KMOD_CTRL:
                        if self.pas_a_pas is None:
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

                elif key in [pygame.K_PRINT]:
                    self.imprime_ecran(vers_presse_papier=e.mod & pygame.KMOD_CTRL)

                elif key == K_b:
                    # change les boutons de la manette
                    # elems.ControlePerso.BoutonA_joy = 3
                    elems.ControlePerso.BoutonB_joy = 2

                    print('BoutonA', elems.ControlePerso.BoutonA_joy)
                    print('BoutonB', elems.ControlePerso.BoutonB_joy)

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

    def ordonne_elems(self, elems):
        return sorted(elems, key=self.elems.index)

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

    def imprime_ecran(self, vers_presse_papier=False):
        """ Sauvegarde l'image a l'ecran """
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

            cliche_rep = media.cheminFichier('cliches', verifExiste=False)
            if not os.path.exists(cliche_rep):
                os.mkdir(cliche_rep)

            nom_fichier = sauvegarde.SelectDansRepertoire(cliche_rep, Suffixe='', defaut=self.niveau.nom,
                                                         Legende="Sauver l'image d'ecran sous :",
                                                         choixNouveau=True, valideExistant=True, Effacable=True)

            if nom_fichier:
                nom_complet = os.path.join(cliche_rep, nom_fichier + '.png')
                print("sauvegarde d'ecran : %s" % nom_complet)
                pygame.image.save(surface, nom_complet)
