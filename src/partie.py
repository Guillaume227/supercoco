#! /usr/bin/env python

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


def GetEcran(PleinEcran):
    if PleinEcran:
        Flags = pygame.FULLSCREEN | pygame.HWSURFACE | pygame.DOUBLEBUF
    else:
        Flags = pygame.DOUBLEBUF  # | pygame.NOFRAME

    titre = pygame.display.get_caption()
    pygame.display.quit()

    mode = pygame.display.set_mode(Partie.TailleEcran, Flags)
    pygame.display.set_caption(*titre)
    return mode


def RectFromPoints(Point1, Point2):
    P1, P2 = (min(Point1[0], Point2[0]), min(Point1[1], Point2[1])), \
             (max(Point1[0], Point2[0]), max(Point1[1], Point2[1]))

    return P1[0], P1[1], P2[0] - P1[0], P2[1] - P1[1]


def barycentre(Coords):
    """ Barycentre d'un ensemble de points (x,y)"""
    Bar = [0, 0]
    for Coors in Coords:
        Bar[0] += Coors[0]
        Bar[1] += Coors[1]

    NumPoints = float(len(Coords))
    Bar[0] /= NumPoints
    Bar[1] /= NumPoints

    return Bar


class Camera(object):

    def __init__(self, posCentre=(0, 0)):

        self.rect = pygame.display.get_surface().get_rect()
        self.rect_monde = None
        self.StillDim = 64

    def SetRectMonde(self, rect):
        self.rect_monde = rect
        self.rect.bottomleft = self.rect_monde.bottomleft

    def RelRect(self, actor):
        """ passage du referentiel monde au referentiel camera """
        if isinstance(actor, Rect):
            rect = actor
        else:
            rect = actor.rect
        return Rect(rect.x - self.rect.x, rect.y - self.rect.y, rect.w, rect.h)

    def AbsPoint(self, point):
        return point[0] + self.rect.x, point[1] + self.rect.y

    def RelPoint(self, point):
        return point[0] - self.rect.x, point[1] - self.rect.y

    def AbsRect_ip(self, rect):
        """ conversion de Rect du referentiel camera au referentiel absolu """
        rect.x += self.rect.x
        rect.y += self.rect.y

    def Deplace(self, dX, dY):
        self.rect.centerx += dX
        self.rect.centery += dY

    def maj(self, cible, revenirEnArriere=True):
        """mise a jour"""

        if cible[0] > self.rect.centerx + self.StillDim:
            self.rect.centerx = cible[0] - self.StillDim
        elif revenirEnArriere and cible[0] < self.rect.centerx - self.StillDim:
            self.rect.centerx = cible[0] + self.StillDim

        if cible[1] > self.rect.centery + self.StillDim:
            self.rect.centery = cible[1] - self.StillDim
        elif cible[1] < self.rect.centery - self.StillDim:
            self.rect.centery = cible[1] + self.StillDim

        self.rect.clamp_ip(self.rect_monde)


class Partie(object):
    Ombre = False
    TailleEcran = 640, 480

    def __init__(self):

        self.EnPause = False
        self.JouerMusique = True
        self.affiche_stats = False
        self.phase_decompte = False
        self.PhotosDejaVues = set()

        self.grilleRef = None
        self.SelectionElem = []
        self.SelectionMotif = []

        self.couleur_selection = pygame.Color(0, 255, 0, 100)
        self.affiche_crible = False
        self.avec_photos = False
        self.Clic_Precedent = None

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

        self.tempsBoucleMs = 60  # millisecondes

        self.niveau = None

    def RetailleMonde(self):
        """ Calcule les dimensions du rectangle contenant tous les elements du niveau"""
        rect = self.niveau.Elements[0].rect.copy()

        rect.unionall_ip([Elem.rect for Elem in self.niveau.Elements])

        rectMin = pygame.Rect((0, 0), self.TailleEcran)

        if self.niveau.parallaxe_:
            print('taille image_fond', self.niveau._image_fond.get_size())
            fondH = self.niveau._image_fond.get_height()
            if fondH > self.TailleEcran[1]:
                rectMin.h = fondH

        rectMin.left = rect.left
        rectMin.right = rect.right

        # rectMin.bottomleft = rect.bottomleft
        rect.union_ip(rectMin)
        rect.bottom -= self.niveau.marge_bas_ * media.TAILLE_BLOC

        self.camera.SetRectMonde(rect)

        if self.affiche_stats:
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

        self.Init_Niveau(nom_niveau)

        self.Intro_Niveau()

        while True:

            try:

                self.Boucle_Niveau()

            except TransferMonde as exc:
                # perso a fini le niveau, poursuit vers le niveau suivant
                if exc.decompte:
                    self.points += self.perso.points

                self.perso.efface()
                self.Init_Niveau(nomNiveau=exc.monde, entree=exc.entree)

                self.Intro_Niveau(affiche=exc.decompte)

                self.phase_decompte = False

            except MortJoueur:

                self.ecran_de_mort()

                self.compte_a_rebours = 0

                if self.perso.vies <= 0:
                    self.FinDePartie()
                    return

                # reset player
                self.perso = Perso((0, 0), vies=self.perso.vies)

                self.Init_Niveau(nomNiveau=self.niveau.nom)

                self.Intro_Niveau()

            except InterruptionDePartie:
                print("Partie interrompue par le joueur")
                return

    def Intro_Niveau(self, affiche=True):
        # Ecran d'introduction du niveau

        media.arret_musique()

        ecran = pygame.display.get_surface()
        ecran.fill((0, 0, 0))

        if self.avec_photos and self.niveau.nom not in self.PhotosDejaVues:
            sons = ["smb_coin.wav",
                    "smb_powerup.wav",
                    "1up.ogg",
                    "son_harricot.wav", ]

            sons_obj = [media.charge_son(son) for son in sons]

            sonCocoCouda = media.charge_son("the A-team theme.ogg")

            Cococouda = False

            self.PhotosDejaVues.add(self.niveau.nom)
            for img in self.niveau.photos_:

                try:

                    if self.niveau.nom == '1-1 bis' and not Cococouda:
                        Cococouda = True
                        sonCocoCouda.play()

                    elif not Cococouda:
                        sons_obj[random.randint(0, len(sons) - 1)].play()

                    intercalaires.planche(photo=img, Extro=True)

                except intercalaires.SautePlanche:
                    break

                except media.MediaManquantExc as exc:
                    print(exc)

            if Cococouda:
                sonCocoCouda.stop()

        if affiche:
            ecran = pygame.display.get_surface()

            ecran.fill((0, 0, 0))

            self.Affiche_Stats()

            ecranL, ecranH = ecran.get_size()
            centreX, centreY = ecranL / 2, ecranH / 2
            ren = self.police.render(langues.Traduc(langues.Monde) + " " + self.niveau.nom.split("=")[0], 1,
                                     (255, 255, 255))
            ecran.blit(ren, (centreX - ren.get_width() / 2, centreY - 60))
            ecran.blit(self.perso.image, (centreX - ren.get_width() / 2, centreY - 10))
            ren = self.police.render("x  %d" % self.perso.vies, 1, (255, 255, 255))
            ecran.blit(ren, (centreX * 1.1 - ren.get_width() / 2, centreY))

        pygame.display.flip()
        pause = 2500

        pygame.time.wait(pause)
        if self.niveau.musique_:
            media.lire_musique(self.niveau.musique_)

    def ecran_de_mort(self):

        self.VoileDOmbre(100)
        ecran = pygame.display.get_surface()

        ren = self.police.render(langues.Traduc(langues.Perdu), 1, (255, 255, 255))
        ecran.blit(ren, (320 - ren.get_width() / 2, 235))
        self.Affiche_Stats()
        pygame.display.flip()
        pygame.time.wait(2500)

    def show_end(self):

        pygame.time.wait(7500)
        pygame.display.flip()

    def FinDePartie(self):
        media.lire_musique("smb_gameover.wav")
        intercalaires.planche([langues.Traduc(langues.Echec)])
        media.arret_musique()

    def Init_Niveau(self, nomNiveau='', entree=0, reinit=True):

        if reinit or not self.niveau:
            if niveau.Existe(nomNiveau):
                Info = niveau.Ouvrir(nomNiveau)
                if Info:
                    self.niveau = Info
            else:
                self.niveau = niveau.Monde(nomNiveau)

        if self.perso is None:
            self.perso = Perso((0, 0))

        self.perso.nom = self.niveau.nomJoueur_
        if self.niveau.etat_joueur_ is not None:
            self.perso.etat = self.niveau.etat_joueur_

        self.RetailleMonde()

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

    def Affiche_Elems_Niveau(self):

        # for s in self.crible.Intersecte(self.camera.rect):
        # l'ordre d'affichage des elements selon leur position dans self.elems
        # est essentiel
        elems = self.crible.Intersecte(self.camera.rect)
        ecran = pygame.display.get_surface()
        for elem in self.OrdonneElems(elems):
            try:
                elem.affiche(ecran, self.camera)
            except:
                traceback.print_exc()
                print(elem, elem.rect)

    def Boucle_Niveau(self):

        avertissement = self.niveau.tempsMax_ <= 100
        transferMondeExc = None
        son_decompte = media.charge_son("decompte.ogg")
        MortJoueurExc = None

        pygame.event.clear()

        while True:

            if not self.perso.auto_pilote:
                # Note : commandes de saut et de tirs sont percues comme evenments dans TraiterEvenements ci-dessous
                self.perso.Controle.capte()

            try:
                self.TraiterEvenements()

            except (SystemExit, InterruptionDePartie):
                raise

            except:
                traceback.print_exc()

            if self.affiche_crible:
                pass
                # self.crible.Integrite()
                # self.elems.integrite()

            if not self.EnPause and (self.pas_a_pas is None or self.pas_a_pas):

                if self.pas_a_pas is True:
                    self.pas_a_pas = False

                self.horloge.tick(self.tempsBoucleMs)
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
                    for s in self.crible.Intersecte(RectAction):

                        if s.vivant():

                            if hasattr(s, 'maj'):
                                s.maj()

                            if s.rect.colliderect(self.camera.rect):

                                s.hors_champ = False
                                if hasattr(s, 'ActionInCamera'):
                                    s.ActionInCamera(self.perso, self.camera)

                            else:
                                s.horschamp(self.perso, self.camera)
                                s.hors_champ = True


                except MortJoueur as exc:
                    MortJoueurExc = exc

                except TransferMonde as exc:

                    transferMondeExc = exc
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

                        if transferMondeExc:

                            if not pygame.mixer.get_busy():
                                # Attend la fin de la musiquette pour passer au monde suivant
                                raise transferMondeExc
                            else:
                                print('Attente de la fin de la musiquette')

                    else:
                        # Compte a rebours negatif en attendant de passer au niveau suivant.
                        self.compte_a_rebours -= self.tempsBoucleMs * .001

                else:
                    # pas en phase decompte

                    if self.perso.vivant():

                        self.compte_a_rebours -= self.tempsBoucleMs * .001

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

            self.Affiche_Elems_Niveau()
            self.Affiche_Stats()

            if self.affiche_crible:
                self.AfficheCrible()

            if self.EnPause:
                self.VoileDOmbre(100)

                self.affiche_texte("PAUSE", pos=(self.TailleEcran[0] / 2, self.TailleEcran[1] / 2))

            if self.Ombre:
                self.VoileDOmbre(200)

            pygame.display.flip()

            if MortJoueurExc:
                # permet l'affichage de la derniere toile avant le gel de la mise a jour
                raise MortJoueurExc

    def affiche_texte(self, texte, pos, centre=(True, True), couleur=(255, 255, 255)):
        """affiche du texte a l'ecran"""
        texteImg = self.police.render(texte, 2, (255, 255, 255))

        CoinHautGauche = list(pos)
        txtDim = texteImg.get_size()
        ecran = pygame.display.get_surface()

        for i in 0, 1:

            if centre[i]:
                CoinHautGauche[i] -= txtDim[i] / 2

            elif pos[i] < 0:
                CoinHautGauche[i] += self.TailleEcran[i] - txtDim[i]

        ecran.blit(texteImg, CoinHautGauche)

        return txtDim

    def VoileDOmbre(self, alpha=100):
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
        GetEcran(self._plein_ecran)
        pygame.mouse.set_visible(False)

    def TraiterEvenements(self):

        # Instructions des peripheriques
        for e in pygame.event.get():

            if e.type == QUIT:
                sys.exit()

            # Instructions au clavier
            if e.type == KEYDOWN:

                key = e.key
                if key == K_F1:
                    # Affiche l'aide
                    Aide = """  
                                e : mode plein ecran

                                echap : interruption de la partie - retour au menu

                                """.splitlines()

                    intercalaires.planche(Aide, taille=8, centre=False, Extro=False, Intro=False)

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
                        self.Bascule_Pause()

                elif key == K_ESCAPE:
                    # Sortie du jeu
                    media.arret_musique()
                    pygame.mixer.stop()

                    raise InterruptionDePartie

                elif key == K_e:

                    self.plein_ecran = not self.plein_ecran

                elif key in (ControlePerso.BoutonA_key, ControlePerso.BoutonB_key):
                    if not self.EnPause and not self.phase_decompte:
                        if key == ControlePerso.BoutonA_key:
                            self.perso.Controle.BoutonA_evenement = True
                        else:
                            self.perso.Controle.BoutonB_evenement = True

                elif key == K_F2:
                    # Mode musique / silencieux
                    self.JouerMusique = not self.JouerMusique
                    if self.JouerMusique:
                        pygame.mixer.music.unpause()
                    else:
                        pygame.mixer.music.pause()

                elif key in [pygame.K_PRINT]:
                    self.ImprimeEcran(versPressePapier=e.mod & pygame.KMOD_CTRL)

                elif key == K_b:
                    # change les boutons de la manette
                    # elems.ControlePerso.BoutonA_joy = 3
                    elems.ControlePerso.BoutonB_joy = 2

                    print('BoutonA', elems.ControlePerso.BoutonA_joy)
                    print('BoutonB', elems.ControlePerso.BoutonB_joy)


            elif e.type == pygame.JOYBUTTONDOWN:
                if not self.EnPause and e.button == ControlePerso.BoutonA_joy:
                    # Saut du perso joueur
                    self.perso.saute()

                elif not self.EnPause and e.button == ControlePerso.BoutonB_joy:
                    self.perso.tire()

                elif e.button == 3:
                    # mise en pause
                    self.Bascule_Pause()

                else:
                    pass
                    # print 'bouton manette', e.button

    def OrdonneElems(self, Elems):
        return sorted(Elems, key=self.elems.index)

    def Bascule_Pause(self):
        self.EnPause = not self.EnPause

        if self.EnPause:
            self.son_pause.play()
            pygame.mixer.music.pause()
        else:
            pygame.mixer.music.unpause()

    def AfficheCrible(self):

        if self.SelectionElem:
            Rects = [elem.rect for elem in self.SelectionElem]
        else:
            Rects = [self.camera.rect]

        ecran = pygame.display.get_surface()
        for rect in Rects:
            for rectCoor in self.crible.Rects(rect):
                pygame.draw.rect(ecran, (250, 150, 50), self.camera.RelRect(Rect(*rectCoor)), 1)

    def Affiche_Stats(self):

        ecran = pygame.display.get_surface()
        EcranL, EcranH = self.TailleEcran
        MargeCote = self.ecranL / EcranL * 50

        PoliceH = self.police.get_height() * 20 / 16
        MargeH = self.ecranH / EcranH * 10

        # Nom du perso
        texteDim = self.affiche_texte(self.perso.nom.upper(), pos=(MargeCote, MargeH), centre=(False, False))
        self.affiche_texte("%05d" % (self.points + self.perso.points),
                           pos=(-EcranL + MargeCote + texteDim[0], MargeH + PoliceH), centre=(False, False))

        # Nombre de pieces
        self.affiche_texte("x%02d" % self.perso.boursePieces, pos=(MargeCote + 100, MargeH + PoliceH),
                           centre=(False, False))

        ecran.blit(self.mini_pieces[int(self.temps_discret / 9) % len(self.mini_pieces)],
                   (MargeCote + 86, MargeH + PoliceH - 3))

        # Nom du monde
        AncreMonde = self.TailleEcran[0] / 2 - 100
        self.affiche_texte(langues.Traduc(langues.Monde), pos=(-AncreMonde, MargeH), centre=(False, False))
        self.affiche_texte(self.niveau.nom.split('=')[0], pos=(-AncreMonde, MargeH + PoliceH), centre=(False, False))

        # Temps ecoule
        self.affiche_texte(langues.Traduc(langues.Temps), pos=(-MargeCote, MargeH), centre=(False, False))
        self.affiche_texte("%d" % max(0, self.compte_a_rebours), pos=(-MargeCote, MargeH + PoliceH),
                           centre=(False, False))

    def ImprimeEcran(self, versPressePapier=False):
        """ Sauvegarde l'image a l'ecran """
        Surface = pygame.display.get_surface().copy()

        if versPressePapier:
            pygame.scrap.init()
            pygame.scrap.set_mode(pygame.SCRAP_CLIPBOARD)
            image_data = pygame.image.tostring(Surface, "RGBA")
            pygame.scrap.put(pygame.SCRAP_BMP, image_data)

        else:
            # vers fichier
            import os
            from . import sauvegarde

            Cliche_REP = media.cheminFichier('cliches', verifExiste=False)
            if not os.path.exists(Cliche_REP):
                os.mkdir(Cliche_REP)

            NomFichier = sauvegarde.SelectDansRepertoire(Cliche_REP, Suffixe='', defaut=self.niveau.nom,
                                                         Legende="Sauver l'image d'ecran sous :",
                                                         choixNouveau=True, valideExistant=True, Effacable=True)

            if NomFichier:
                NomComplet = os.path.join(Cliche_REP, NomFichier + '.png')
                print("sauvegarde d'ecran : %s" % NomComplet)
                pygame.image.save(Surface, NomComplet)
