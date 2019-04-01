from __future__ import print_function
from __future__ import absolute_import
from .media import charge_image, charge_son, TAILLE_BLOC
from .vect2d import Vec
from . import interruptions
import math
from . import media
import pygame
import random
import traceback
import functools

HAUT = 0
DROITE = 1
BAS = 2
GAUCHE = 3
TRAVERSE = 4

Signe_Direction = {DROITE: 1, GAUCHE: -1}

_CoteReciproque = {HAUT: BAS, BAS: HAUT,
                   GAUCHE: DROITE, DROITE: GAUCHE,
                   TRAVERSE: TRAVERSE}


class IgnoreCollision(Exception):
    pass


def TriChocsFunc(mid):
    def f(*args):

        if args[0][0] != args[1][0]:
            return args[0][0] - args[1][0]

        elif args[0][1] != args[1][1]:
            return args[0][1] - args[1][1]

        else:
            dists = []

            for i in 0, 1:

                if mid > args[i][2].rect.right:
                    dists.append(mid - args[i][2].rect.right)

                elif mid < args[i][2].rect.left:
                    dists.append(args[i][2].rect.left - mid)

                else:
                    dists.append(0)

            return dists[0] - dists[1]

    return f


class Dessinable:
    groupe = None
    penetrable = None
    _crible = None
    index_temps = 0
    images_synchro = True

    miroir = True  # Vrai si l'objet change de sens lorsqu'il change de direction

    freq = 8  # nombres d'affichages entre chaque changement d'image de l'animation
    gravite = .3
    v_Y_max = 5  # vitesse verticale max
    rebond = False  # Si nombre entier : rebond absolu, si True, rebond proportionnel a la chute

    @staticmethod
    def image_rpr(self):
        return media.charge_image(self.nomImages[0])

    def __init__(self, pos=None, images=None, versGauche=True, index=None):

        self.hors_champ = False

        self._vers_gauche = versGauche

        if images is None and hasattr(self, 'nomImages'):
            images = self.nomImages

        if images is None:
            self.image = None
            self.rect = None
            self.images = None

        else:
            if isinstance(images[0], str):
                if not hasattr(self, 'nomImages'):
                    self.nomImages = images

                self.set_images(images, versGauche)

            else:
                self.images = [images] * 2

            self.image = self.images[self._vers_gauche][0]

            if pos is None:
                self.rect = self.image.get_rect()
            else:
                self.rect = self.image.get_rect(topleft=pos)

        self.frame = 0

        self.visible_ = True

        if self.penetrable:
            self._penetrable = list(self.penetrable)  # copie l'attribut de classe
        else:
            self._penetrable = []

        if self.groupe is not None and self.rect is not None and pos is not None:
            self.insere(index)

        self.posInit = pos

        self.speed = Vec(0, 0)
        self.vitesse_base = Vec(0, 0)
        self.inamovible_ = False

    def index(self):
        return self.groupe.index(self)

    def set_images(self, images, versGauche=True):
        if self.miroir:
            self.images = [[charge_image(imgName, flip=flip) for imgName in images] for flip in
                           (versGauche, not versGauche)]
        else:
            self.images = [[charge_image(imgName) for imgName in images]] * 2

    @property
    def rebord_(self):
        """ Determine si les creatures ont une notion du rebord de l'element pour eviter de passer par dessus bord """
        return getattr(self, '_rebord', False)

    @rebord_.setter
    def rebord_(self, val):
        self._rebord = val

    @property
    def cotesRect(self):
        return self.rect.top, self.rect.right, self.rect.bottom, self.rect.left

    @cotesRect.setter
    def cotesRect(self, xxx_todo_changeme):
        (cote, val) = xxx_todo_changeme
        if cote == HAUT:
            self.rect.top = val
        elif cote == BAS:
            self.rect.bottom = val
        elif cote == GAUCHE:
            self.rect.left = val
        else:
            assert cote == DROITE
            self.rect.right = val

    @property
    def vers_gauche_(self):
        return self._vers_gauche

    @vers_gauche_.setter
    def vers_gauche_(self, val):
        if val != self._vers_gauche:
            self._vers_gauche = val
            if self.image is not None and self.images:
                imgIndex = self.images[not val].index(self.image)
                self.image = self.images[val][imgIndex]

    def rafraichit_image(self):
        images = self.images[self._vers_gauche]
        if self.images_synchro:
            self.image = images[self.index_temps // self.freq % len(images)]
        else:
            self.image = images[self.frame // self.freq % len(images)]

    def __repr__(self):
        return self.__str__()

    def __str__(self):
        return '%s %s' % (self.__class__.__name__, self.rect)
        # return '%s %s'%(self.image.fileName.split('.')[0],self.rect)

    def affiche(self, surf, camera, mode_modifs=False, centre=None, alpha=None):

        if self.image:

            if self.visible_:
                if alpha is not None:
                    image = self.image.convert()
                    image.set_alpha(alpha)
                else:
                    image = self.image

            elif mode_modifs:
                image = self.image.convert()
                image.set_alpha(100)

            else:
                image = None

            if image:

                if centre is None:
                    rect = self.rect
                else:
                    rect = self.rect.copy()
                    rect.center = centre

                RelRect = camera.rel_rect(rect)

                try:
                    surf.blit(image, RelRect)
                except:
                    traceback.print_exc()

        if mode_modifs and self.rebord_:
            dessus = RelRect.top + 1
            pygame.draw.line(surf, (250, 150, 30), (RelRect.left, dessus), (RelRect.right, dessus), 3)

    def horschamp(self, joueur, camera):
        if self.rect.top > camera.rect_monde.bottom:
            self.efface()

    def insere(self, index=None):

        self.groupe.insere(self, index)
        self._crible.insere(self.rect, self)

    def repos_init(self):
        self.posInit = self.rect.topleft

    def vivant(self):
        return self in self.groupe

    def efface(self, strict=True):
        if self.groupe and self.vivant():
            self.groupe.ote(self)
            self._crible.retire(self, strict)

    def tue(self, side=None, points=True):
        self.efface()

    def deplace(self, mouve=None, mode_modifs=False, strict=True):
        if mouve:
            self.rect.move_ip(*mouve)

        if mode_modifs:
            self.repos_init()

        if getattr(self, '_crible', False):
            self._crible.deplace(self.rect, self, strict=strict)

    def mouve(self, collision=True):

        v_x, v_y = deplacement = tuple(self.speed + self.vitesse_base)

        chocs_by_side = {}

        if not collision:
            self.rect.move_ip(*deplacement)

        else:

            mouv_rect = self.rect.union(self.rect.move(*deplacement))

            obstacles = self._crible.intersecte(mouv_rect, self)

            if abs(v_x) >= abs(v_y):
                if v_y:
                    ordre_index = 0, 1
                else:
                    ordre_index = 0,

            else:
                if v_x:
                    ordre_index = 1, 0
                else:
                    ordre_index = 1,

            for Index in ordre_index:

                mouv = [0, 0]
                mouv[Index] = deplacement[Index]
                self.rect.move_ip(*mouv)

                if collision and obstacles:

                    sides = list(chocs_by_side.keys())
                    for side in sides:

                        # Trie les chocs dans l'ordre des premiers touches
                        if side != TRAVERSE:
                            chocs_by_side.pop(side)

                    chocs = tuple(obstacle.collisione(mouv, self.rect) for obstacle in obstacles if
                                  obstacle._penetrable and self.rect.colliderect(obstacle.rect))
                    [chocs_by_side.setdefault(choc[0], []).append(choc[1:]) for choc in chocs if choc is not None]

                    num_chocs = len(chocs_by_side)

                    # Deux rectangles precedement disjoints ne peuvent
                    # s'intersecter par plus de deux cotes au cours d'un deplacement
                    assert num_chocs <= 1 or (num_chocs == 2 and TRAVERSE in chocs_by_side)

                    for side, chocs in chocs_by_side.items():

                        if side in (BAS, HAUT):
                            chocs = sorted(chocs, key=functools.cmp_to_key(TriChocsFunc(self.rect.centerx)))

                        elif side == TRAVERSE:
                            chocs = chocs_by_side[side]

                        else:
                            # DROITE, GAUCHE
                            print('chocs', chocs)
                            # TODO: sort chocs with right comparison func
                            #chocs = sorted(chocs)

                        for _dist, penetrable, obj in chocs:

                            try:

                                if isinstance(self, Personnage):
                                    if hasattr(obj, 'effet_joueur') and self.vivant():
                                        # choc n'a pas le meme sens vu depuis la creature.

                                        obj.effet_joueur(self, _CoteReciproque.get(side))

                                elif isinstance(obj, Personnage):
                                    if hasattr(self, 'effet_joueur') and obj.vivant():
                                        self.effet_joueur(obj, side=side)

                                if self.vivant():
                                    if hasattr(self, 'on_collision'):
                                        self.on_collision(side, obj)

                                    if hasattr(obj, 'on_collision_passive'):
                                        obj.on_collision_passive(_CoteReciproque[side], self)

                            except IgnoreCollision:
                                continue

                            if side == TRAVERSE:
                                continue

                            if not penetrable and not self._penetrable[side]:
                                # Choc contre un obstacle impenetrable.

                                if (side == HAUT or side == BAS) and isinstance(self,
                                                                                Personnage) and self.taille > 0 and len(
                                    chocs) == 1:
                                    # Pour que le grand perso passe plus facilement entre deux briques.
                                    # NB: en lieu de cette logique, on pourrait directement retrecir la largeur de son rect

                                    if side == HAUT:
                                        tolX = 2
                                    else:
                                        tolX = 1

                                    dist_gauche = obj.rect.right - self.rect.left
                                    dist_droite = obj.rect.left - self.rect.right

                                    if dist_gauche <= tolX:
                                        self.rect.move_ip((dist_gauche, 0))
                                        continue
                                    elif dist_droite >= -tolX:
                                        self.rect.move_ip((dist_droite, 0))
                                        continue

                                if side == HAUT:

                                    if isinstance(self, Ebranlable) and self.speed[1] < 0:

                                        pass
                                        """
                                        if isinstance( obj, Mechant ) :
                                            obj.tue()
                                        elif isinstance( obj, AutoMobile ):
                                            obj.speed[1] = self.speed[1] / 2
                                            self.rect.top += self.speed[1]
                                            obj.rect.bottom += self.speed[1]
                                            obj.deplace()
                                        """
                                    elif not isinstance(self, Poutrelle):

                                        # pour qu'une poutrelle ne fasse pas demi-tour lorsqu'on lui saute dessus
                                        self.speed[1] = 1
                                        self.rect.top = obj.rect.bottom

                                elif side == BAS:

                                    if not isinstance(obj, (EnemiInterface, PlatformeQ)) and not self.inamovible_:
                                        self.vitesse_base = Vec(obj.speed)

                                    if self.speed[1] > 0:
                                        if self.rebond:
                                            if isinstance(self.rebond, bool):
                                                pass
                                            else:

                                                self.speed[1] = self.rebond

                                            self.speed[1] *= -1

                                        else:
                                            self.speed[1] = 1

                                    self.rect.bottom = obj.rect.top

                                    if obj.rebord_ and getattr(self, 'marche_bas_', False):
                                        # si le prochain mouvement conduit au dessus d'un trou, faire marche arriere
                                        # (par exemple, pour que les mechants ne tombent pas dans un trou
                                        # si l'objet definit un rebord)
                                        if deplacement[0] != 0:
                                            rect_pas = self.rect.copy()
                                            rect_pas.h = self.marche_bas_
                                            rect_pas.top = self.rect.bottom

                                            if deplacement[0] > 0:
                                                rect_pas.left = self.rect.right
                                            else:
                                                rect_pas.right = self.rect.left

                                            if not any([not Elem.penetrable_haut_ for Elem in
                                                        self._crible.intersecte(rect_pas, self)]):
                                                # Aucun element n'offre un appui - faire demi-tour
                                                self.speed[0] *= -1

                                else:
                                    # Choc a gauche ou a droite

                                    if getattr(self, 'marche_haut_', False) and not isinstance(obj, EnemiInterface):
                                        # Monte la marche si elle est moins haute que self.marche_haut_
                                        rect_pas = self.rect.copy()

                                        rect_pas.bottom = rect_pas.bottom - self.marche_haut_

                                        if not any(
                                                [not Elem.penetrable_haut_ or not Elem.penetrable_traverse_ for Elem in
                                                 self._crible.intersecte(rect_pas, self)]):
                                            # Monte la marche
                                            self.rect.bottom = obj.rect.top
                                            self.deplace()
                                            return

                                    # Fait demi-tour
                                    self.speed[0] *= -1

                                    if side == DROITE:
                                        self.rect.right = obj.rect.left
                                    else:
                                        assert side == GAUCHE
                                        self.rect.left = obj.rect.right

                                break

        if self.gravite:
            # Gravite
            gravite = self.gravite
            vmax = self.v_Y_max

            if TRAVERSE in chocs_by_side and isinstance(chocs_by_side[TRAVERSE][0][2], MilieuAquatique):
                gravite /= 3.
                vmax /= 3.

            if self.speed[1] < vmax:
                self.speed[1] += gravite
            else:
                self.speed[1] = vmax

        if self.vivant():
            self.deplace()

    def collisione(self, speed, rect1):
        """
            side, penetration, bloquant, self
            
            side : cote de self par ou Rect1 entre en collision
            penetration : distance de penetration de Rect1 dans self.rect
            bloquant : si le contact est bloquant par ce cote la
        """
        tx = ty = None

        sx, sy = speed

        sy = int(sy)

        traverse_x = False
        traverse_y = False
        """

        """
        if sx > 0:

            dx = rect1.right - self.rect.left

            if dx > 0:
                if dx <= sx:
                    tx = (sx - dx) / sx
                else:
                    traverse_x = dx

        elif sx < 0:

            dx = self.rect.right - rect1.left

            if dx > 0:
                if dx <= -sx:
                    tx = (-sx - dx) / -sx
                else:
                    traverse_x = dx

        if sy > 0:

            dy = rect1.bottom - self.rect.top

            if dy > 0:
                if dy <= sy:
                    ty = (sy - dy) / sy
                else:
                    traverse_y = dy

        elif sy < 0:

            dy = self.rect.bottom - rect1.top

            if dy > 0:
                if dy <= -sy:
                    ty = (-sy - dy) / -sy
                else:
                    traverse_y = dy

        penetrables = self._penetrable
        if len(penetrables) < 5:
            penetrables.append(False)

        if tx is None and ty is None:

            if traverse_x or traverse_y or self.rect.colliderect(rect1):
                # Recouvrement
                return TRAVERSE, None, None, self
                # return TRAVERSE, None, penetrables[TRAVERSE], self

            else:
                # Pas de Collision
                return None

        elif tx is None or (ty is not None and ty <= tx):

            if sy < 0:
                return HAUT, -dy, penetrables[BAS] or penetrables[TRAVERSE], self

            else:
                return BAS, -dy, penetrables[HAUT] or penetrables[TRAVERSE], self

        else:
            assert tx >= 0

            if sx < 0:
                return GAUCHE, -dx, penetrables[DROITE] or penetrables[TRAVERSE], self

            else:

                return DROITE, -dx, penetrables[GAUCHE] or penetrables[TRAVERSE], self


def penetrable_getter(cote):
    def fget(obj):
        if obj._penetrable:

            if len(obj._penetrable) == 4:
                # Afaire : retirer ce code lorsque tous les elements sont
                # reinitialises de sorte qu'ils aient un tableau penetrable de taille 5
                obj._penetrable.append(any(obj._penetrable))

            return obj._penetrable[cote]
        else:
            return True

    return fget


def penetrable_setter(cote):
    def fset(obj, val):
        if not obj._penetrable:
            if obj.penetrable:
                obj._penetrable = list(obj.penetrable)
            else:
                obj._penetrable = [True] * 5

            obj.insere()

        obj._penetrable[cote] = val

    return fset


for i, cote in enumerate('haut droite bas gauche traverse'.split()):
    setattr(Dessinable, 'penetrable_%s_' % cote, property(fget=penetrable_getter(i), fset=penetrable_setter(i)))


class Collidable(Dessinable):
    penetrable = True, True, True, True, True


class CollidableBloc(Dessinable):
    penetrable = False, False, False, False, False


class BlocBase(CollidableBloc):
    son_bris = "smb_breakblock.wav"

    def __init__(self, pos=None):
        CollidableBloc.__init__(self, pos)
        self.incassable_ = True
        self._visible = True

    def casser(self, cote=None):

        charge_son(self.son_bris).play()

        sousRect = self.image.get_rect().copy()
        sousRect.h /= 2
        sousRect.w /= 2
        origTopLeft = Vec(self.rect.topleft)
        imgL, imgH = sousRect.w, sousRect.h

        for i in 0, 1:
            for j in 0, 1:
                sousImg = self.image.subsurface(sousRect.move(imgL * i, imgH * j))
                Morceau(origTopLeft + (imgL * i, imgH * j), images=[sousImg], vX=2 if i else -2,
                        impulsion=-12 if j else -18)

        if cote == BAS:
            # Tue les mechants qui se trouvent juste au dessus de la brique
            for elem in self._crible.intersecte(self.rect.move(0, -2), self):
                if isinstance(elem, Mechant):
                    elem.tue()

        self.efface()

    def effet_joueur(self, joueur, side):

        if side == BAS:

            if joueur.etat > 0 and not (hasattr(self, 'surprise_') and self.surprise_) and not self.incassable_:
                self.casser(side)
                joueur.points += 50

            else:
                joueur.son_bosse.play()

                if hasattr(self, 'declenche'):
                    self.declenche(joueur)


class Intouchable:

    def effet_joueur(self, joueur, side):
        joueur.blesse()


class AutoMobile(CollidableBloc):
    freq = 8

    marche_bas_ = 1
    marche_haut_ = 0  # franchissement d'une marche de tant de pixels vers le haut

    def __init__(self, pos=None, images=None):
        Dessinable.__init__(self, pos, images=images)

    def maj(self):

        if self.speed[0]:
            self._vers_gauche = self.speed[0] < 0

        self.rafraichit_image()

        if self.speed:
            self.mouve()

    def marche_erratique(self):
        """marche aleatoire horizontale"""

        tirage = random.random()
        if self.speed[0] == 0:
            # se met en marche
            if tirage > .95:
                self.speed[0] = self.v_X

        elif tirage > .98:
            # s'arrete
            self.speed[0] = 0

        if tirage > .99:
            # change de direction
            self.speed[0] *= -1

        self._vers_gauche = self.speed[0] < 0

        if self.speed[0]:
            self.rafraichit_image()

        if self.speed:
            self.mouve()


class PositionDepart(Dessinable):
    """Marqueur de la position initiale du joueur dans le niveau"""

    nomImages = ["mariogd1.png"]

    def __init__(self, pos=None):
        Dessinable.__init__(self, pos)
        self.visible_ = False


class Personnage:
    marche_bas_ = 0
    marche_haut_ = 5


class Perso(Dessinable, Personnage):
    """ Personage de mario """
    penetrable = False, False, False, False, False

    gravite = .6
    freq = 6
    v_Y_max = 8

    POINTS_ECRASE = 100, 200, 400, 500, 800, 1000, 2000, 4000, 5000, 8000

    def __init__(self, pos=None, vies=3):

        self._nom = 'mario'

        self.init_images()

        Dessinable.__init__(self, pos, versGauche=False)

        self.vies = vies
        self.auto_pilote = False

        self.en_saut = False  # booleen ou bien la valeur de la vitesse horizontale au moment de l'appel du saut.
        self.en_rebond = False

        self.chute = False

        self.mourant = False
        self.pas_de_course = False

        self._accroupi = False
        self._glissade = 0
        self._agrippe = False

        self.sous_l_eau = 0
        self.brasse_compteur = 0

        self.serie_ecrasement = 0

        self.__etat = 0  # 0=petit, 1=grand, 2=tireur

        self._surpuissant = 0  # effet de l'etoile

        self.decompte_tir = 0
        self.decompte_touche = 0
        self.decompte_kamea = 0
        self.pouvoir_kamea = False
        self.volte_face = 0
        self.en_transformation = 0
        self.temps_transfo = 45

        self._boursePieces = 0
        self.points = 0

        self.invincible = False

        self.son_mort = charge_son("smb_mariodie.wav")
        self.jump_sound = charge_son("smb_jump-small.wav")
        self.son_tape = charge_son("smb_kick.wav")
        self.son_grandit = charge_son("smb_powerup.wav")
        self.son_rapetit = charge_son("smb_pipe.wav")
        self.son_cococouda = charge_son("tamtatam8bit.ogg")
        self.son_choc = charge_son("smb_kick.wav")

        self.son_nage = charge_son("smb_stomp.wav")
        self.son_bosse = charge_son("smb_bump.wav")
        self.son_vie = charge_son("1up.wav")

        self.Controle = ControlePerso()

    def init_images(self):

        self.nomImagePerdu = "%sdie.png" % self._nom
        self.couleur = 0

        if self._nom == 'coco':

            NomCouleurs = [self._nom]
            nomImagesKamea = ["cococoudakamea%d.png" % i for i in (1, 2, 3, 4, 5)]

            self.images_kamea = [[charge_image(img, flip=flip) for img in nomImagesKamea] for flip in (False, True)]

            """
            self.toutes_images = [ Images_petit, Images_grand ]
            Images             = [ ImageType1, ImageType2, ... ]
            ImageType1         =  [ ImageType1_vers_gauche, ImageType2_vers_gauche ]
            
            d.s.q : ImageCourante = Images[Taille][Couleur][Direction]
            Couleur = Normal/Tire/CocoCouda/CocoCoudaSlip
            """
            self.toutes_images = []

            for nomCouleur in NomCouleurs:

                self.nomImages = [nomCouleur + "%d.png" % i for i in (1, 2, 3, 4, 5, 6, 6, 8, 9)]

                self.nomImages += [nomCouleur + "nage%d.png" % i for i in range(1, 7)]

                images_petit = [[charge_image(imgName, flip=flip) for imgName in self.nomImages] for flip in
                                (False, True)]

                SequenceImgGrand = range(1, 10)
                self.toutes_images = [[images_petit], []]

                for racine in 'cocogd', 'cocogdfire', 'cococoudaslip', 'cococouda':
                    nomImagesGrand = [racine + "%d.png" % i for i in SequenceImgGrand]

                    nomImagesGrand += [racine + "nage%d.png" % i for i in range(1, 7)]

                    nomImagesGrand += ["cocomoyen.png", racine + "-tire.png"]

                    images_grand = [[charge_image(img, flip=flip) for img in nomImagesGrand] for flip in (False, True)]

                    self.toutes_images[1].append(images_grand)

        else:
            # mario

            nomImagesKamea = ["mario-tire-kamea%d.png" % i for i in (1, 2, 3, 4, 5)]

            self.images_kamea = [[charge_image(img, flip=flip) for img in nomImagesKamea] for flip in (False, True)]

            self.toutes_images = []

            for taille in 0, 1:

                self.toutes_images.append([])

                for coul_num, couleur in enumerate(['', 'rouge', 'blanc', 'noir']):

                    self.toutes_images[taille].append([])

                    nomCouleur = self._nom + couleur

                    if taille == 1:
                        SequenceImage = range(1, 10)
                        nomCouleur += 'gd'
                    else:
                        SequenceImage = 1, 2, 3, 4, 5, 6, 6, 8, 9

                    nomImages = [nomCouleur + f"{i}.png" for i in SequenceImage]
                    nomImages += [nomCouleur + f"nage{i}.png" for i in range(1, 7)]

                    if taille == 1:
                        nomImages += [self._nom + "moyen.png", nomCouleur + "-tire.png"]
                    elif coul_num == 0:
                        self.nomImages = nomImages

                    imgs = [[charge_image(nomImg, flip=flip) for nomImg in nomImages] for flip in (False, True)]

                    self.toutes_images[taille][coul_num] = imgs

    def Reinit(self):
        self.auto_pilote = False
        self.surpuissant = None
        self.en_saut = False
        self.accroupi = False
        self._vers_gauche = False
        self.Controle.Reset()
        self.rafraichit_image(au_repos=True)

    @property
    def boursePieces(self):
        return self._boursePieces

    @boursePieces.setter
    def boursePieces(self, val):
        self._boursePieces = val
        if self._boursePieces >= 100:
            self._boursePieces -= 100
            self.incremente_vie(legende=False)

    def incremente_vie(self, legende=True):
        self.vies += 1
        self.son_vie.play()
        Legende(self.rect.move(0, -15).topleft, '1VIE')

    @property
    def nom(self):
        return self._nom

    @nom.setter
    def nom(self, val):
        if val != self._nom:
            self._nom = val
            self.init_images()
            self.rafraichit_image()

    @property
    def taille(self):
        if self.__etat == 0:
            return 0
        else:
            return 1

    @property
    def couleur_(self):
        return self.couleur

    @couleur_.setter
    def couleur_(self, val):
        self.couleur = val
        self.rafraichit_image()

    @property
    def etat(self):
        return self.__etat

    @etat.setter
    def etat(self, val):

        print('etat', val, type(val))
        assert val >= 0

        if self.__etat != val:
            self.__etat = val
            self.rafraichit_image()

        if self.__etat < 2:
            self.pouvoir_kamea = False

    nom_ = nom  # pour affichage dans l'editeur
    etat_ = etat

    def metamorphe(self, touche=False):

        self.en_transformation = self.temps_transfo

        etat_avant = self.etat

        if touche:
            self.accroupi = False
            self.etat = 0

        elif self.etat < 2:
            self.etat = self.etat + 1

        if self.etat == 2:
            if etat_avant == 1:
                self.couleur = 1
        else:
            self.couleur = 0

        if self.nom == 'coco' and self.etat == 2 and etat_avant == 2:
            self.son_cococouda.play()
            self.couleur = -1

        elif self.etat >= 1:
            self.son_grandit.play()
            self.accroupi = False

        else:
            self.son_rapetit.play()


    def recadre_image(self, insere=False):
        if self.image and self.rect.size != self.image.get_size():

            midbottom = self.rect.midbottom
            self.rect.h = self.image.get_height()
            self.rect.midbottom = midbottom

            if insere:
                self.rect.w = self.image.get_width()
                self.deplace(strict=False)

    def rafraichit_image(self, au_repos=True):

        if self.decompte_kamea > 0:
            numImgs = len(self.images_kamea[0])
            index = (self.decompte_kamea // self.freq) % numImgs

            self.image = self.images_kamea[self._vers_gauche][numImgs - 1 - index]
            self.recadre_image()

            return

        if self.en_transformation:
            freq = 4
            if self.etat >= 2:
                # Change de couleur

                images = self.toutes_images[self.taille]
                couleur = self.en_transformation // freq % len(images)

            else:
                # Change de taille
                taille = self.en_transformation // freq % 3

                if taille == 2:
                    self.image = self.toutes_images[1][self.couleur][self._vers_gauche][-2]  # image moyen
                else:
                    if self.taille == 1:
                        taille = 1 - taille  # sequence 'petit moyen grand' ou 'grand moyen petit'
                    self.image = self.toutes_images[taille][self.couleur][self._vers_gauche][0]

                return

        elif self.surpuissant:
            couleur = self._surpuissant // self.freq % len(self.toutes_images[self.taille])

        else:
            couleur = self.couleur

        self.images = self.toutes_images[self.taille][couleur]

        if self.decompte_touche > 0 and self.decompte_touche % 2:
            self.image = None

        elif self.decompte_tir > 0:
            if self.sous_l_eau and self.en_saut:
                self.image = self.images[self._vers_gauche][11 + self.frame // self.freq % 2]
            else:
                self.image = self.images[self._vers_gauche][-1]

        elif not self.chute:

            if self.agrippe is not False:

                if not au_repos:
                    self.frame += 1

                img_index = 8 - (self.frame // self.freq % 2)

            elif self.volte_face:
                # Se retourne
                img_index = 5

            elif self.accroupi:
                img_index = 6

            elif self.en_saut:

                if self.sous_l_eau:

                    self.frame += 1

                    if self.brasse_compteur == 0 or self.brasse_compteur > 20:
                        img_index = 9 + self.frame // self.freq % 2

                    elif self.brasse_compteur > 10:
                        img_index = 13 + self.frame // self.freq % 2

                    else:  # if self.brasse_compteur > 0:
                        img_index = 11 + self.frame // self.freq % 2

                else:
                    img_index = 4

            elif au_repos:

                img_index = 0

            else:
                # Marche / Course
                self.frame += 1

                freq = self.freq
                if self.pas_de_course:
                    freq //= 2

                img_index = self.frame // freq % 3 + 1

            self.image = self.images[self._vers_gauche][img_index]

        if self.image and not self.agrippe:
            self.recadre_image()

    def efface(self, strict=True):
        self.Reinit()
        Dessinable.efface(self, strict=strict)

    def blesse(self):
        if not self.invincible and not self.surpuissant and self.decompte_touche <= 0:

            self.decompte_kamea = 0
            self.decompte_tir = 0
            self.decompte_touche = 160

            if self.etat <= 0:
                self.tue()
            else:
                self.metamorphe(touche=True)
                self.son_tape.play()

    def tue(self, side=None, saut_de_face=True):
        if not self.mourant:
            if not self.invincible:

                pygame.mixer.stop()
                pygame.mixer.music.stop()

                self.son_mort.play()
                self.mourant = True
                self.vies -= 1

                pd = SautDeLaMort(self.rect.center, images=[charge_image(self.nomImagePerdu)])

                if not saut_de_face:
                    pd.visible_ = False
                self.efface()

    def on_collision(self, side, sprite):

        if side == HAUT:
            if not sprite._penetrable[BAS]:
                self.son_bosse.play()

        elif side == BAS:

            if not sprite.penetrable_haut_ or not sprite.penetrable_traverse_:
                if not isinstance(sprite, Mechant):
                    self.en_saut = False
                    self.serie_ecrasement = 0

                self.en_rebond = False

                self.agrippe = False

        elif side in (DROITE, GAUCHE):
            if sprite.penetrable and not sprite.penetrable[_CoteReciproque[side]]:
                self.en_rebond = False

    def saute(self, impulsion_extra=1):

        if not self.auto_pilote:

            if self.sous_l_eau or not (self.chute or self.en_saut):

                self.agrippe = False

                if self.sous_l_eau > 30:
                    # Suffisament immerge
                    if self.brasse_compteur > 20:
                        return
                    self.brasse_compteur = 24
                    self.speed[1] = -5.4 * impulsion_extra
                    self.son_nage.play()

                else:
                    if self.speed[0] == 0:
                        self.speed[1] = -9.4 * impulsion_extra
                    elif abs(self.speed[0]) <= 3:
                        self.speed[1] = -9.6 * impulsion_extra
                    else:
                        self.speed[1] = -10 * impulsion_extra

                    self.jump_sound.play()

                self.en_saut = True

                self.mouve()

    def tire(self):

        if not self.auto_pilote:

            if self.en_transformation <= 0 and self.decompte_tir <= 0 and self.etat >= 2 and not self.accroupi \
                    and Boulette.NombBoulettes < Boulette.MaxBoulettes:

                if self.pouvoir_kamea:
                    self.decompte_kamea = len(self.images_kamea[0]) * self.freq
                    self.speed[0] = 0

                else:

                    self.decompte_tir = 10

                    if self._vers_gauche:
                        pos_x = self.rect.left
                    else:
                        pos_x = self.rect.right

                    pos_y = self.rect.top + 30

                    boulette = Boulette((pos_x, pos_y))
                    if self._vers_gauche:
                        boulette.rect.left -= boulette.rect.w

                        boulette.deplace()

                    boulette.speed = Vec(9, 1)

                    if self._vers_gauche:
                        boulette.speed[0] *= -1

    @property
    def agrippe(self):
        return self._agrippe

    @agrippe.setter
    def agrippe(self, val):
        if val != self._agrippe:
            self._agrippe = val

            if val is not False:
                self.en_saut = False
                self.chute = False
                self.vitesse_base *= 0

            elif self.auto_pilote:
                self.Controle.Reset()
                self.Controle.Droite = 100

    @property
    def accroupi(self):
        return self._accroupi

    @accroupi.setter
    def accroupi(self, val):

        if val != self._accroupi:

            if self._accroupi:
                # Se releve
                novH = self.toutes_images[self.taille][self.couleur][0][0].get_height()
                self._glissade = False
            else:
                # S'accroupit
                novH = self.toutes_images[self.taille][self.couleur][0][6].get_height()

            self.rect.top += self.rect.h - novH
            self.rect.h = novH

            self.deplace()

            self._accroupi = val

    @property
    def surpuissant(self):
        return self._surpuissant > 0

    @surpuissant.setter
    def surpuissant(self, val):

        if val:
            self._surpuissant = val.duree
            self._etoile = val
        elif hasattr(self, '_etoile'):
            self._etoile.son.stop()
            pygame.mixer.music.rewind()
            pygame.mixer.music.play()

    def maj(self):

        if self._surpuissant > 0:
            self._surpuissant -= 1
            if self._surpuissant == 0:
                self.surpuissant = None

        if self.brasse_compteur > 0:
            self.brasse_compteur -= 1

        if self.volte_face > 0:
            self.volte_face -= 1

        if self.decompte_touche > 0:
            self.decompte_touche -= 1

        if self.decompte_tir > 0:
            self.decompte_tir -= 1

        if self.en_transformation:

            self.en_transformation -= 1
            self.rafraichit_image(au_repos=True)
            self.recadre_image(insere=not self.en_transformation)

            return

        elif self.decompte_kamea:

            self.decompte_kamea -= 1
            # Immobilite pendant le kamea
            self.speed *= 0

            if self.decompte_kamea == self.freq - 1:

                if self._vers_gauche:
                    bdf = BouleDeFeu(self.rect.topleft)
                    bdf.deplace((-bdf.image.get_width(), 0))
                    bdf.vers_gauche_ = True
                    bdf.speed[0] *= -1
                else:
                    BouleDeFeu(self.rect.topright)

            au_repos = True

        else:

            # Genere des bulles de respiration sous l'eau
            if self.sous_l_eau > self.rect.h + 15:
                if random.random() > .98 or self.brasse_compteur == 23:
                    Bulle(self.rect.midtop)

            if not self.auto_pilote:

                if self.Controle.BoutonA_evenement:
                    self.Controle.BoutonA_evenement = False
                    # Saut
                    self.saute()

                if self.Controle.BoutonB_evenement:
                    self.Controle.BoutonB_evenement = False
                    # tire boule de feu
                    self.tire()

            if self._agrippe is not False:
                # Perso est agrippe a quelque chose
                dx = 0
                dy = 0

                if self.Controle.Haut:
                    dy = -3
                    if self.rect.top <= self._agrippe:
                        dy = 0

                elif self.Controle.Bas:
                    dy = 3

                # Change de cote
                if self.Controle.Droite and not self._vers_gauche:
                    self._vers_gauche = True
                    dx = self.rect.w - 5

                elif self.Controle.Gauche and self._vers_gauche:
                    self._vers_gauche = False
                    dx = -self.rect.w + 5

                self.speed[0] = dx
                self.speed[1] = dy

                au_repos = dy == 0

            else:

                if self.en_saut and not self.en_rebond and not self.sous_l_eau and self.Controle.BoutonA:
                    # Anti-gravite
                    extra_saut = .3
                    if abs(self.speed[0]) > 3:
                        extra_saut += .05
                    elif abs(self.speed[0]) > 0:
                        extra_saut += .02

                    self.speed[1] -= extra_saut

                self.chute = False
                if abs(self.speed[1]) > 2.5 and not self.en_saut:
                    if self.sous_l_eau:
                        self.en_saut = True
                    else:
                        self.chute = True

                if self.Controle.BoutonB and not self.sous_l_eau:
                    self.pas_de_course += 1
                else:
                    self.pas_de_course = 0

                x_incre = 3

                dx = 0

                if self.Controle.Gauche:

                    if self.Controle.Gauche < 20:
                        dx = -1
                    else:
                        dx = -x_incre

                    if self.pas_de_course and not self._vers_gauche:
                        self.volte_face = self.freq

                    self._vers_gauche = True

                elif self.Controle.Droite:

                    if self.Controle.Droite < 20:
                        dx = 1
                    else:
                        dx = x_incre

                    if self.pas_de_course and self._vers_gauche:
                        self.volte_face = self.freq

                    self._vers_gauche = False

                if self.etat > 0 and self.Controle.Bas > 0 and not (self.sous_l_eau and self.en_saut):
                    if not self.accroupi:
                        self.accroupi = True

                        if dx != 0:
                            self._glissade = TAILLE_BLOC  # glisse un bloc

                        if self.pas_de_course:
                            self._glissade *= 3  # glisse trois blocs

                else:
                    self.accroupi = False

                if self.pas_de_course > 10:
                    if self.pas_de_course < 50 or (self.en_saut and abs(self.speed[0]) < 6):
                        dx *= 1.5
                    else:
                        dx *= 2

                if self.accroupi and not self.en_saut:
                    if self._glissade:
                        self._glissade -= abs(dx)
                        self._glissade = max(self._glissade, 0)
                    else:
                        dx = 0

                au_repos = dx == 0

                self.speed[0] = dx

        self.rafraichit_image(au_repos=au_repos)

        self.sous_l_eau = 0

        self.mouve()

        if not self.sous_l_eau:
            self.brasse_compteur = 0

    def engrange_points(self, points, pos, duree=40):
        """ajoute les points et les affiche"""
        self.points += points
        Legende(pos, points, compteur=duree)

    def horschamp(self, joueur, camera):
        if self.rect.top >= camera.rect_monde.bottom:
            # mario tombe dans un trou
            if self.invincible:
                # saute hors du trou en mode invincible
                dy = camera.rect_monde.bottom - self.rect.bottom
                self.deplace((0, dy))
                self.en_saut = False
                self.chute = False
                self.saute(2)
            else:
                self.tue(saut_de_face=False)


class ControlePerso:
    BoutonA_key = pygame.K_c
    BoutonB_key = pygame.K_x

    BoutonA_joy = 0
    BoutonB_joy = 2 #1

    def __init__(self):

        pygame.joystick.init()
        if pygame.joystick.get_count() > 0:
            print(f'get_init: {pygame.joystick.get_init()}')
            self.joystick = pygame.joystick.Joystick(0)
            self.joystick.init()
            self.bouton_croix = self.joystick.get_numhats() > 0
            print(f'manette active ; numhats: {self.joystick.get_numhats()}')
        else:
            self.joystick = None
            self.bouton_croix = False

        self.Reset()

    def Reset(self):

        self.BoutonA = False  # BoutonA enfonce
        self.BoutonB = False  # BoutonB enfonce

        self.BoutonA_evenement = False  # BoutonA presse (ne l'etait pas avant)
        self.BoutonB_evenement = False  # BoutonB presse (ne l'etait pas avant)

        self.Haut = False
        self.Bas = False
        self.Gauche = False
        self.Droite = False

    @property
    def controles(self):
        return self.Haut, self.Droite, self.Bas, self.Gauche

    def capte(self):

        keys = pygame.key.get_pressed()

        self.BoutonA = keys[self.BoutonA_key] or (self.joystick and self.joystick.get_button(self.BoutonA_joy))
        self.BoutonB = keys[self.BoutonB_key] or (self.joystick and self.joystick.get_button(self.BoutonB_joy))

        bouton_croix = self.joystick.get_hat(0) if self.bouton_croix else (0, 0)

        axisVal = 0

        self.BoutonA_evenement = False
        self.BoutonB_evenement = False

        if self.joystick:
            axisVal = self.joystick.get_axis(1)

        if keys[pygame.K_UP] or bouton_croix[1] > 0 or axisVal < -.5:
            self.Haut += 1
        else:
            self.Haut = 0

        if keys[pygame.K_DOWN] or bouton_croix[1] < 0 or axisVal > .5:
            self.Bas += 1
        else:
            self.Bas = 0

        if self.joystick:
            axisVal = self.joystick.get_axis(0)

        if keys[pygame.K_RIGHT] or bouton_croix[0] > 0 or axisVal > .8:
            self.Droite += 1
            # self.Gauche = 0
        else:
            self.Droite = 0

        if keys[pygame.K_LEFT] or bouton_croix[0] < 0 or axisVal < -.8:
            self.Gauche += 1
            # self.Droite = 0
        else:
            pass
            self.Gauche = 0


class PersoNonJoueur(Perso):
    nomImages = ["coco1.png"]
    penetrable = True, True, False, True, True
    impulsionY = 5

    def __init__(self, pos=None, **kwargs):
        # Garcon / fille
        Perso.__init__(self, pos, **kwargs)
        self.invincible = True
        self.nom = 'coco'
        self.oisif = 20
        if random.randint(0, 1):
            # Fille
            nom_images = ["Aurorepetite%d.png" % i for i in (1, 2)] * 4
            self.toutes_images = [
                [[[charge_image(imgName, flip=flip) for imgName in nom_images] for flip in (False, True)]]]
            self.rect = self.toutes_images[0][0][0][0].get_rect()

    def action_in_camera(self, joueur, camera):

        dist_x = joueur.rect.centerx - self.rect.centerx

        if abs(dist_x) > 220 + 30 * random.random():

            self.Controle.Reset()

            self.Controle.BoutonB = self.Controle.BoutonB or abs(dist_x) > 280 + 40 * random.random()

            if dist_x > 0:
                self.Controle.Droite = 100
            else:
                self.Controle.Gauche = 100

        else:

            self.Controle.BoutonB = False

            self.oisif -= 1

            if self.oisif < 0:

                self.Controle.Reset()

                self.oisif = int(15 + 30 * random.random())
                alea = random.randint(-1, 1)

                if alea > 0:
                    self.Controle.Droite = 100

                elif alea < 0:
                    self.Controle.Gauche = 100

                else:
                    pass
                    # saut ?


class Princesse(AutoMobile, Personnage):
    penetrable = True, True, False, True, True

    nomImages = ["aurore%d.png" % i for i in (1, 2)]

    def __init__(self, pos=None):
        Dessinable.__init__(self, pos)
        self.reveillee = False
        self.distance_perso_ = 33
        self.distance_reveil_ = 300
        self.etat = 1
        self.taille = 0

    def incremente_vie(self, legende=True):
        self.joueur.son_vie.play()
        Legende(self.rect.move(0, -15).topleft, '1VIE')

    def action_in_camera(self, joueur, camera):

        dist_x = joueur.rect.centerx - self.rect.centerx
        if not self.reveillee and abs(dist_x) < self.distance_reveil_:
            self.reveillee = True

        if self.reveillee:

            if abs(dist_x) > self.distance_perso_:

                if abs(dist_x) > 3 * self.distance_perso_:

                    vitesse = abs(joueur.speed[0]) + 1
                else:
                    vitesse = 2

                self.speed[0] = vitesse

                if dist_x <= 0:
                    self.speed[0] *= -1

            elif abs(dist_x) < joueur.rect.w:
                self.speed[0] = -2 if dist_x > 0 else 2
            else:
                self.speed[0] = 0
                self._vers_gauche = dist_x < 0

    def rafraichit_image(self):

        images = self.images[self._vers_gauche]
        self.image = images[self.frame // self.freq % len(images)]

        if self.speed[0]:
            self.frame += 1


class Figurant(Dessinable, Personnage):
    penetrable = True, True, False, True, True

    nomImages = ['Perso/Vincent%d.png' % i for i in (1, 2)]

    def __init__(self, pos=None):
        Dessinable.__init__(self, pos)
        self.periode_ovation_ = 150
        self.duree_ovation_ = 50
        self.compteur_ovation = self.periode_ovation_
        self._nom = self.nomImages[0].split('/')[-1].split('.')[0][:-1]
        self.frame = 0

    @property
    def nom_(self):
        return self._nom

    @nom_.setter
    def nom_(self, val):
        self._nom = val
        nom_images = ['Perso/%s%d.png' % (val, i) for i in (1, 2)]
        self.set_images(nom_images)

        self.image = self.images[self._vers_gauche][0]

        mid_bottom = self.rect.midbottom
        self.rect = self.image.get_rect()
        self.rect.midbottom = mid_bottom

    def action_in_camera(self, joueur, camera):

        distX = joueur.rect.centerx - self.rect.centerx

        self._vers_gauche = distX < 0

        self.compteur_ovation -= 1

        repositionne = False

        if self.compteur_ovation <= 0:
            self.compteur_ovation = self.periode_ovation_
            self.frame = 0
            repositionne = True

        elif self.compteur_ovation == self.duree_ovation_:
            self.frame = 1
            midbottom = self.rect.midbottom
            repositionne = True

        self.image = self.images[self._vers_gauche][self.frame]

        if repositionne:
            midbottom = self.rect.midbottom
            self.rect = self.image.get_rect()
            self.rect.midbottom = midbottom


class Flotant(Dessinable):

    def __init__(self, pos=None):
        Dessinable.__init__(self, pos)
        self.compteur_flote = 0

    def maj(self):
        self.compteur_flote -= 1

        if self.compteur_flote <= 0:
            self.compteur_flote = 20
            self.speed[0] = round(2 * random.random() - 1, 0)


class Bulle(Flotant):
    gravite = -2
    nomImages = ['bulle.png']

    def __init__(self, pos=None):
        Flotant.__init__(self, pos)
        self.speed[1] = -2

    def maj(self):

        collisions = self._crible.intersecte(self.rect, self)
        for elem in collisions:
            if isinstance(elem, MilieuAquatique) and elem.rect.top < self.rect.top:
                break
        else:
            self.efface()
            return

        Flotant.maj(self)
        self.deplace(self.speed)


class FleurDeFeu(Collidable):
    """fleur qui donne le pouvoir des boulettes de feu"""
    nomImages = ["fireflower%d.png" % i for i in (1, 2, 3, 4)]
    freq = 6
    points = 1000

    def effet_joueur(self, joueur, side):
        # joueur.son_choc.play()

        joueur.metamorphe()
        joueur.engrange_points(self.points, self.rect.topleft)

        self.efface()

    def maj(self):
        self.rafraichit_image()


class Chapeau(Collidable):
    nomImages = ["chapeau.png"]
    points = 8000

    def effet_joueur(self, joueur, side):
        # joueur.Controle.Reset()
        # joueur.auto_pilote = True
        # joueur.Controle.Droite = 100
        imgs = ["Cocopingouin%d.png" % i for i in (1, 2, 3, 4, 5, 6, 7)]
        imgs = [[charge_image(img, flip=flip) for img in imgs] for flip in (False, True)]
        joueur.toutes_images[joueur.taille][joueur.couleur] = imgs
        joueur.enTransformation = joueur.temps_transfo
        joueur.invincible = True
        joueur.son_grandit.play()
        joueur.marche_haut_ = 20  # pour qu'il puisse prendre la marche de l'eglise.

        joueur.rafraichit_image()
        self.efface()


class Bague(Collidable):
    nomImages = ["bague%d.png" % i for i in (1, 2, 3, 4, 5)]
    points = 10000
    freq = 16

    def action_in_camera(self, joueur, camera):
        self.rafraichit_image()

    def effet_joueur(self, joueur, side):
        joueur.Controle.Reset()
        joueur.auto_pilote = True
        joueur.Controle.Droite = 100
        joueur.invincible = True

        if joueur.etat != 1:
            joueur.etat = 1
            joueur.enTransformation = 45

        joueur.son_vie.play()

        joueur.engrange_points(self.points, self.rect.move(0, -15).topleft)

        self.efface()


class SurpriseMouvante:
    penetrable = False, False, False, False, True
    impulsionY = 0
    impulsionX = 0

    miroir = False
    marche_bas_ = 0
    marche_haut_ = 0

    def horschamp(self, joueur, camera):
        self.efface()


class CoeurMultiColore(Flotant, SurpriseMouvante):
    penetrable = True, True, False, True, True
    rebond = True

    images_synchro = False

    nomImages = ["Coeur%d.png" % i for i in (1, 2, 3, 4, 5, 6, 7)]
    gravite = .1
    v_Y_max = 3
    impulsionY = 6

    # ChocRecessif

    def __init__(self, pos=(0, 0), duree=300):
        Flotant.__init__(self, pos)
        self.eclatable_ = True
        self.duree_ = duree

    def tue(self, side=None):
        self.efface()
        ExploPouff(self.rect.center)

    def effet_joueur(self, joueur, side):
        if self.eclatable_:
            self.tue()

        if isinstance(joueur, Perso) and not isinstance(joueur, PersoNonJoueur):
            joueur.pouvoir_kamea = False
            if joueur.etat != 1 and not joueur.en_transformation:
                joueur.etat = 1
                joueur.couleur = 0
                joueur.en_transformation = joueur.temps_transfo

    def maj(self):

        self.frame += 1

        if self.duree_ >= 0:
            self.duree_ -= 1
            if self.duree_ == 0:
                self.tue()

        Flotant.maj(self)
        self.mouve()
        if not hasattr(self, 'couleur_'):
            self.rafraichit_image()


class Coeur(CoeurMultiColore):
    rebond = 8

    def __init__(self, pos=(0, 0), duree=300):
        CoeurMultiColore.__init__(self, pos, duree)
        self.couleur_ = 1

    @property
    def couleur_(self):
        return self.images[0].index(self.image) + 1

    @couleur_.setter
    def couleur_(self, val):
        self.image = self.images[0][val - 1]


class CoeurPiece(CoeurMultiColore):
    nomImages = ["Coeurpiece%d.png" % i for i in (1, 2, 3)]


class Choppe(SurpriseMouvante, FleurDeFeu, AutoMobile):
    nomImages = ["Pintbeer.png", "Pintbeer2.png"]


class ChampiTaille(SurpriseMouvante, AutoMobile):
    """ Champignon de taille """

    nomImages = ["champi-taille.png"]
    points = 1000
    impulsionX = 2

    def effet_joueur(self, joueur, side):

        if joueur.etat <= 0:
            joueur.metamorphe()
        else:
            joueur.son_choc.play()

        joueur.engrange_points(self.points, self.rect.move(0, -15).topleft)

        self.efface()


class CocoNinja(Collidable):
    nomImages = ["coconinja.png"]
    points = 777

    def effet_joueur(self, joueur, side):
        if joueur.etat != 2:
            joueur.etat = 2
            joueur.enTransformation = joueur.temps_transfo

        joueur.couleur = -1

        media.charge_son("hadoken.ogg").play()

        joueur.pouvoir_kamea = True
        joueur.engrange_points(self.points, self.rect.move(0, -15).topleft)

        self.efface()


class Etoile(SurpriseMouvante, AutoMobile):
    penetrable = True, True, False, True, False
    nomImages = ["etoile%s.png" % i for i in (1, 2, 3, 4)]
    points = 1000
    impulsionY = 7
    impulsionX = 2
    rebond = 7
    duree = 500

    def maj(self):
        self.rafraichit_image()
        self.mouve()

    def effet_joueur(self, joueur, side):
        self.tue()
        pygame.mixer.music.stop()
        self.son = charge_son("etoile.wav")
        self.son.play(loops=-1)

        joueur.points += self.points
        joueur.surpuissant = self


class Burger(ChampiTaille):
    nomImages = ["burger.png"]


class ChampiVert(SurpriseMouvante, AutoMobile):
    """ Champignon de vie """
    nomImages = ["mushroom-green.png"]
    impulsionX = 2

    def effet_joueur(self, joueur, side):
        self.tue()
        joueur.incremente_vie()


class ChampiCoco(ChampiVert):
    nomImages = ["mushroomcoco%d.png" % i for i in (1, 2, 3, 4, 5, 6)]
    impulsionY = 6
    impulsionX = 0
    rebond = True

    def __init__(self, **kwargs):
        self.transfere_monde_ = "cap-1"
        super(ChampiCoco, self).__init__(**kwargs)

    def tue(self, side=None):

        Legende(self.rect.move(0, -15).topleft, 'COCO !!!', compteur=150, vX=-1)
        self.image = None

    def effet_joueur(self, joueur, side):
        if not hasattr(self, 'chrono'):
            self.chrono = joueur.temps_transfo + 20
            joueur.enTransformation = joueur.temps_transfo
            media.charge_son("behave.ogg").play()
            joueur.nom = "coco"
            joueur.etat = 1
            joueur.auto_pilote = True
            joueur.Controle.Reset()
            self.tue()

    def maj(self):

        if self.image:
            self.rafraichit_image()
            self.mouve()

        if hasattr(self, 'chrono'):
            self.chrono -= 1
            if self.chrono < 0:
                self.efface()
                # pygame.time.wait(3000)
                raise interruptions.TransferMonde(self.transfere_monde_, decompte=True)


class ExploBoulette(Dessinable):
    nomImages = ["exploboulette%d.png" % i for i in (1, 2, 3)]
    duree_detonation = 6

    def __init__(self, pos=None):

        Dessinable.__init__(self, pos)
        self.compteur = self.duree_detonation
        if pos is not None:
            self.rect = self.image.get_rect(center=pos)
        self.temps = self.duree_detonation

    def maj(self):
        self.compteur -= 1

        if self.compteur < 0:
            self.efface()
        elif self.compteur < self.temps / 3:
            self.image = self.images[0][2]
        elif self.compteur < self.temps * 2 / 3:
            self.image = self.images[0][1]
        else:
            self.image = self.images[0][0]

        centre = self.rect.center
        self.rect = self.image.get_rect()
        self.rect.center = centre


class FeuDArtifice(ExploBoulette):
    son_explo = "smb_fireworks.wav"
    points = 500
    duree_detonation = 18

    def maj(self):
        if self.temps == self.compteur:
            charge_son(self.son_explo).play()
            self.partie.points += self.points

        ExploBoulette.maj(self)


class ExploFiente(ExploBoulette):
    nomImages = ["fiente_explo%d.png" % i for i in (1, 2, 3)]


class Panneau(Dessinable):
    """Affiches defilantes"""
    penetrable = False, True, True, True, True

    nomImages = ["cadrejcdecaux.png"]
    cadre = [50, 100]
    taillePied = 55

    def __init__(self, pos=(0, 0)):
        Dessinable.__init__(self, pos)
        self.image1_ = 'slub1.png'
        self.image2_ = 'monster1.png'
        self.fraction = 0
        self.sens_ = 1

        self.cadre[0] = self.image.get_width() - 16  # Soustrait l'epaisseur du cadre * 2
        self.cadre[1] = self.image.get_height() - self.taillePied  # Soustrait l'epaisseur du cadre + taille du pied

        self.periode_ = 200
        self.compteur = self.periode_
        self.vitesse_defilement_ = 50

    def maj(self):

        if self.compteur <= 0:
            self.compteur = self.periode_
            self.sens_ *= -1

        if self.compteur <= self.vitesse_defilement_:
            pas = self.cadre[1] / self.vitesse_defilement_

            self.fraction += self.sens_ * pas

            # if self.fraction >= self.cadre[1]:
            #    self.fraction = self.cadre[1]

        self.compteur -= 1

    def affiche(self, surf, camera, mode_modifs=False, centre=None, alpha=None):

        cadre_rect = camera.rel_rect(self.rect.move((8, 8)))

        cadre_rect.size = self.cadre
        # Dessine les affiches

        cadre_rect1 = cadre_rect.copy()
        cadre_rect1.topleft = 0, 0
        cadre_rect1.h = self.fraction
        cadre_rect1.move_ip((0, self.cadre[1] - self.fraction))

        cadre_rect2 = cadre_rect.copy()
        cadre_rect2.topleft = 0, 0
        cadre_rect2.h = self.cadre[1] - self.fraction
        cadre_rect2.move((0, self.fraction))

        pos1 = cadre_rect
        pos2 = cadre_rect.move((0, self.fraction))

        for img, dest_rect, pos in (self.image1_, cadre_rect1, pos1), (self.image2_, cadre_rect2, pos2):
            if self.compteur <= self.vitesse_defilement_ and False:
                print('Rects', dest_rect, cadre_rect, self.cadre)
            if dest_rect.h:
                img = charge_image('photos/' + img)
                img = pygame.transform.scale(img, self.cadre)
                surf.blit(img.subsurface(dest_rect), pos)

        # Dessine le cadre
        Dessinable.affiche(self, surf, camera, mode_modifs=mode_modifs, centre=centre, alpha=alpha)


class PanneauLarge(Panneau):
    nomImages = ["cadrejcdecauxgrand.png"]
    cadre = [50, 100]
    taillePied = 140


class Generateur(Collidable):
    """ generateur d'objets """

    nomImages = ["platform-q1.png"]

    def __init__(self, pos=None):
        Dessinable.__init__(self, pos)
        self.delai_ = 50
        self.active_ = True

        self.aleatoire_ = False
        self.periode_ = 20
        self.max_ = -1
        self.nombre_genere = 0
        self.compteur = 0
        self.objet_ = 'Coeur'
        self.visible_ = False
        self.impulsion_ = 0, 0

    def action_in_camera(self, joueur, camera):

        if self.delai_ > 0:
            self.delai_ -= 1
        else:

            if self.active_:

                self.compteur -= 1

                if self.compteur <= 0 and (self.max_ < 0 or self.nombre_genere < self.max_):
                    self.nombre_genere += 1
                    obj = globals()[self.objet_](pos=(0, 0))
                    obj.rect.center = self.rect.center
                    obj.deplace()
                    obj.speed = Vec(self.impulsion_)
                    self.compteur = self.periode_
                    if self.aleatoire_:
                        self.compteur *= random.random()

    def effet_joueur(self, joueur, camera):
        # active au toucher
        self.active_ = True


class ExploPouff(Dessinable):
    nomImages = ["exp2-%d.png" % i for i in range(1, 4)]

    def __init__(self, pos=None):

        Dessinable.__init__(self, pos)

        if pos is not None:
            self.rect = self.image.get_rect(center=pos)

        self.timer = 0

    def maj(self):
        self.timer += 1
        if self.timer < 12:
            self.image = self.images[0][self.timer // 4 % 3]
        else:
            self.efface()


class Morceau(Dessinable):
    speed = Vec(1, 0)

    def __init__(self, pos, images, vX, impulsion):
        Dessinable.__init__(self, pos, images)
        self.inertie = impulsion
        self._vX = vX
        self.compteur = 0

    def maj(self):
        self.compteur += 1
        self.rect.move_ip(self._vX, self.inertie)
        self.inertie += 1

        if self.compteur >= 100:
            self.efface()


class Ebranlable:
    """ Bloc a declenchement"""

    def __init__(self, surprise=None, num_fois=1, deplacement=None):

        self.posOrg = None
        self.dx = 0
        self.dy = 0
        self.surprise_ = surprise
        self.incassable_ = False
        self.nombreSurprises_ = num_fois

    def maj(self):
        self.declenche_maj()

    def declenche_maj(self):

        if self.posOrg is not None:

            self.mouve()

            if self.rect.topleft[1] >= self.posOrg[1]:
                self.rect.topleft = self.posOrg
                self.posOrg = None
                self.speed[0] = 0
                self.speed[1] = 0
                self.deplace()

            else:
                self.speed[1] = 1

    def declenche(self, sprite):

        self.visible_ = True

        if self.nombreSurprises_ != 0 and self.posOrg is None:

            # declenches apres un choc par en dessous
            self.posOrg = self.rect.topleft

            self.speed[1] = -self.rect.h / 3

            if self.nombreSurprises_ > 0:
                self.nombreSurprises_ -= 1

            if self.nombreSurprises_ == 0:
                self.images = [[charge_image("platform-air.png")] * len(self.images[0])] * 2
                self.image = self.images[0][0]
                self.incassable_ = True

            if self.surprise_:
                # poussage de la surprise
                if issubclass(self.surprise_, Piece):
                    piece = PiecePrise(self.rect.midtop)
                    piece.rect.left -= 5
                    if isinstance(sprite, Perso):
                        sprite.points += self.surprise_.points
                        sprite.boursePieces += 1

                else:
                    surprise = self.surprise_

                    if isinstance(sprite, Perso):
                        if sprite.etat > 0 and self.surprise_ == Burger:
                            surprise = Choppe
                        elif sprite.etat > 0 and self.surprise_ == ChampiTaille:
                            surprise = FleurDeFeu

                    Apparition(pos=self.rect.topleft, boite=self.rect, surprise=surprise, index=self.index() - 1)

    def affiche(self, surf, camera, mode_modifs=False):
        Dessinable.affiche(self, surf, camera, mode_modifs=mode_modifs)

        if mode_modifs:
            if self.surprise_:
                # img = media.charge_image(self.surprise_.nomImages[0])
                img = self.surprise_.image_rpr(self.surprise_)
                img = pygame.transform.scale(img, (Vec(img.get_size()) / 1.5).ent())
                img.set_alpha(200)
                surf.blit(img, camera.rel_rect(self))

    def on_collision(self, side, sprite):

        if side == HAUT:

            if hasattr(sprite, 'blesse'):
                sprite.blesse()

            elif isinstance(sprite, Mechant):
                # Tue un mechant qui se trouvait au dessus
                sprite.tue()

            elif isinstance(sprite, (AutoMobile, Personnage)):
                # donne une impulsion - change la direction d'un element (champignon par ex.).
                sprite.rect.bottom = self.rect.top
                sprite.deplace()
                if sprite.rect.centerx < self.rect.centerx:
                    if sprite.speed[0] > 0:
                        sprite.speed[0] *= -1
                else:
                    if sprite.speed[0] < 0:
                        sprite.speed[0] *= -1

                sprite.speed[1] += -3


class Apparition(Collidable):

    def __init__(self, boite, surprise=None, duree=60, cote=1, **kwargs):

        self.surprise_ = surprise()
        self.surprise_.efface()

        Dessinable.__init__(self, images=[self.surprise_.image], **kwargs)

        self.visible_ = True

        self.rect = boite.copy()

        self.imgRect = self.surprise_.image.get_rect()
        centerx = self.rect.centerx
        self.rect.w = self.imgRect.w
        self.rect.centerx = centerx
        self.rect.h = 0
        self.deplace()
        self.boite = self.imgRect.copy()
        self.boite.h = 0
        self.cote = cote

        self.image = None
        son = getattr(surprise, 'son_apparition_', 'smb_powerup_appears.wav')

        charge_son(son).play()

        self.pas = self.imgRect.h

        if duree:
            self.pas /= duree
            self.pas = int(max(self.pas, 1))

    def effet_joueur(self, joueur, side):
        if hasattr(self.surprise_, 'effet_joueur'):
            self.surprise_.rect.center = self.rect.center
            self.surprise_.insere()
            self.surprise_.effet_joueur(joueur, side)
            self.efface()

    def maj(self):

        self.rect.top -= self.pas
        self.rect.h += self.pas
        self.deplace()

        self.boite.h = min(self.boite.h + self.pas, self.imgRect.h)

        if self.imgRect.h <= self.boite.h:
            # Largage de la surprise
            self.surprise_.rect.center = self.rect.center

            self.surprise_.insere()

            if isinstance(self.surprise_, SurpriseMouvante):
                self.surprise_.speed[0] = self.surprise_.impulsionX * self.cote

                self.surprise_.speed[1] -= self.surprise_.impulsionY

            self.efface()

        else:
            self.boite.clip(self.imgRect)
            self.surprise_.rafraichit_image()

            self.image = self.surprise_.image.subsurface(self.boite)


class SolRoche(BlocBase):
    _rebord = True
    nomImages = ["roche.png"]


class RocheBlanche(SolRoche):
    nomImages = ["roche-blanche.png"]


class PaveParisien(SolRoche):
    nomImages = ["plateforme-briques-paris.png"]


class SolRocheBleu(SolRoche):
    nomImages = ["roche-bleu.png"]


class SolRocheGris(SolRoche):
    nomImages = ["roche-gris.png"]


class Sables(SolRoche):
    nomImages = ["roche-sable.png"]


class Corail(SolRoche):
    nomImages = ["corail.png"]


class Algues(BlocBase):
    _rebord = True
    nomImages = ["algues.png"]


class RocheSousMarine(SolRoche):
    nomImages = ["fond-sous-marin.png"]


class PlatformeBriques(Ebranlable, BlocBase):
    nomImages = ["plateforme-briques.png"]

    def __init__(self, pos=None):
        BlocBase.__init__(self, pos)
        Ebranlable.__init__(self)
        self.incassable_ = False


class PlatformeBiseau(BlocBase):
    nomImages = ["platform-biseau.png"]


class PlatformeQ(Ebranlable, BlocBase):
    nomImages = ["platform-q%s.png" % i for i in (1, 2, 3)]
    freq = 39

    def __init__(self, pos=None, num_fois=1):

        BlocBase.__init__(self, pos)
        Ebranlable.__init__(self, num_fois=num_fois)

        self.surprise_ = ChampiTaille

        self.inamovible_ = True

    def rafraichit_image(self):
        images = self.images[self._vers_gauche]
        self.image = images[self.index_temps // self.freq % len(images)]

    @property
    def visible_(self):
        return self._visible

    @visible_.setter
    def visible_(self, val):
        """ lorsque le bloc question est invisible,
            il n'apparait que lorsqu'il est cogne par le bas
        """
        self._visible = val
        if self._visible:
            self._penetrable = list(self.penetrable)
        else:
            self._penetrable = [True, True, False, True, False]
            print(self.penetrable_haut_)
            print(self.penetrable_droite_)
            print(self.penetrable_bas_)
            print(self.penetrable_gauche_)
            print(self.penetrable_traverse_)

    def action_in_camera(self, joueur, camera):
        self.rafraichit_image()
        self.declenche_maj()


class PlatformeQRouge(PlatformeQ):
    nomImages = ["platformcoco-q%s.png" % i for i in (1, 2, 3)]


class Briques(PlatformeBriques):
    nomImages = ["briques.png"]


class BriquesBleu(PlatformeBriques):
    nomImages = ["briques-bleu.png"]


class Pierres(CollidableBloc):
    nomImages = ["gray1.png"]


class PlatformeHerbe(Collidable):
    nomImages = ["grass-middle.png"]
    penetrable = False, True, True, True, False


class PlatformeHerbeGauche(PlatformeHerbe):
    _rebord = True
    nomImages = ["grass-1.png"]


class PlatformeHerbeDroite(PlatformeHerbe):
    _rebord = True
    nomImages = ["grass-2.png"]


class PinCime(PlatformeHerbe):
    _rebord = True
    nomImages = ["Pincime.png"]


class PinCimeCourte(PlatformeHerbe):
    nomImages = ["Pincime2.png"]


class PinTroncGrand(Dessinable):
    nomImages = ["Pintroncgd.png"]


class PinTronc(Dessinable):
    nomImages = ["Pintroncpt.png"]


class Passage:

    def __init__(self):
        self.monde_suivant_ = ''
        self.sortie_ = 0

    def affiche(self, surf, camera, mode_modifs=False, centre=None, alpha=None):

        if self.monde_suivant_:
            font_size = 10
            font = pygame.font.Font(media.cheminFichier("fonts/font.ttf"), font_size)

            for idx, txt in enumerate(['vers', str(self.monde_suivant_), '%d' % self.sortie_]):
                imgTexte = font.render(txt, 1, (255, 255, 255))
                rect = imgTexte.get_rect()
                rect.center = self.rect.center
                rect.move_ip(0, font_size * idx - 1)

                surf.blit(imgTexte, camera.rel_rect(rect))


class Tuyeau(CollidableBloc, Passage):
    nomImages = ["pipe.png"]

    vertical = True

    def __init__(self, pos=None):
        Dessinable.__init__(self, pos)
        Passage.__init__(self)

        self.numero_ = 1
        self._perso = None
        self.imgPerso = None
        self.rayon_absorbtion_ = 10
        self.son_absorbtion_ = "smb_pipe.wav"
        self.sortie_en_cours = False

    @property
    def perso(self):
        return self._perso

    @perso.setter
    def perso(self, val):
        self._perso = val
        self._perso.rect.center = self.rect.center
        self._perso.cotesRect = (self.cote_entree, self.cotesRect[self.cote_entree])
        self.rectPerso = self._perso.rect.copy()

    @property
    def cote_entree(self):
        if self.vertical:
            if self._vers_gauche:
                return HAUT
            else:
                return BAS

        else:
            if self._vers_gauche:
                return GAUCHE
            else:
                return DROITE

    def effet_joueur(self, joueur, side):

        if not self._perso:
            cote_entree = self.cote_entree
            # if not self.vertical:
            #    print 'cote_entree', self.cote_entree, side
            if self.monde_suivant_ and side == cote_entree and ( \
                            (side in (HAUT, BAS) and abs(
                                joueur.rect.centerx - self.rect.centerx) < self.rayon_absorbtion_) \
                            or (side in (DROITE, GAUCHE) and abs(
                        joueur.rect.bottom - self.rect.bottom) < self.rayon_absorbtion_)) \
                    and joueur.Controle.controles[_CoteReciproque[side]]:
                # Absorption par le tuyeau vers un autre monde

                charge_son(self.son_absorbtion_).play()
                joueur.efface()
                joueur.accroupi = False
                self.imgPerso = joueur.images[joueur._vers_gauche][0]
                self.rectPerso = joueur.rect.copy()

                if not self.vertical:
                    self.rectPerso.bottom = self.rect.bottom

                self.rectPersoInit = self.rectPerso.copy()

    def maj(self):

        dPos = 5

        if self._perso:
            # Sortie du tuyeau

            if self.sortie_en_cours:

                if not self.rect.colliderect(self.rectPerso):

                    self._perso.cotesRect = (_CoteReciproque[self.cote_entree], self.cotesRect[self.cote_entree])
                    self._perso.insere()

                    self._perso = None
                    self.imgPerso = None
                    self.rectPerso = None

                    self.sortie_en_cours = False

                elif self.index_temps % 5 == 0:

                    mouve = [[0, -dPos], [dPos, 0], [0, dPos], [-dPos, 0]]

                    self.rectPerso.move_ip(mouve[self.cote_entree])


            else:
                charge_son(self.son_absorbtion_).play()
                self.sortie_en_cours = True
                self.imgPerso = self._perso.image


        elif self.imgPerso:
            # Rentree dans le tuyeau

            if self.rectPerso.w == 0 or self.rectPerso.h == 0:
                raise interruptions.TransferMonde(self.monde_suivant_, self.sortie_)

            elif self.index_temps % 5 == 0:
                mouve = [[0, dPos], [-dPos, 0], [0, -dPos], [dPos, 0]]

                self.rectPerso.move_ip(mouve[self.cote_entree])
                self.rectPerso = self.rectPerso.clip(self.rectPersoInit)

    def affiche(self, surf, camera, mode_modifs=False, centre=None, alpha=None):

        if self.imgPerso:
            area = self.rectPerso.copy()
            area.topleft = 0, 0

            if hasattr(self, 'rectPersoInit'):
                if self.rectPerso.right < self.rectPersoInit.right:
                    area.left = self.rectPersoInit.right - self.rectPerso.right

            surf.blit(self.imgPerso, camera.rel_rect(self.rectPerso), area)

        Dessinable.affiche(self, surf, camera, mode_modifs, centre, alpha)

        if mode_modifs:
            font = pygame.font.Font(media.cheminFichier("fonts/font.ttf"), 10)

            imgTexte = font.render('Entree %d' % self.numero_, 1, (255, 255, 255))
            rect = imgTexte.get_rect()
            rect.midtop = self.rect.center
            rect.move_ip(0, -20)
            surf.blit(imgTexte, camera.rel_rect(rect))

            Passage.affiche(self, surf, camera, mode_modifs, centre, alpha)


class TuyeauGrand(Tuyeau):
    nomImages = ["pipe-big.png"]


class TuyeauCourt(Tuyeau):
    nomImages = ["tuyeau-court.png"]


class TuyeauMini(Tuyeau):
    nomImages = ["tuyeau-mini.png"]


class Tuyeau_Tube(CollidableBloc):
    nomImages = ["tuyeau-tube.png"]


class Tuyeau_Bouche(Tuyeau):
    vertical = False
    nomImages = ["tuyeau-bouche.png"]


class Tuyeau_Jointure(Tuyeau):
    vertical = False
    nomImages = ["tuyeau-jointure.png"]


class Cloture(Dessinable):
    nomImages = ["fence.png"]


class Arbre1(Dessinable):
    nomImages = ["tree-1.png"]


class Arbre2(Dessinable):
    nomImages = ["tree-2.png"]


class Flag(Dessinable):
    nomImages = ["flagpole.png"]


class Chateau(Dessinable):
    nomImages = ["castle.png"]

    OrdreDesFeux = ((0, 100), (-80, 80), (80, 80), (0, 50), (100, 120), (-100, 120))

    def action_in_camera(self, joueur, camera):

        if self.partie.phase_decompte and self.partie.compte_a_rebours <= 0:

            if hasattr(self, 'fanion'):

                if not self.hisse:

                    self.yFanion += 1

                    if self.yFanion >= self.fanion.get_height():
                        self.hisse = True
                        self.yFanion = self.fanion.get_height()

                        nomb_feux = int(self.partie.temps_restant) % 10
                        if nomb_feux in (1, 3, 6):
                            self.nomb_feux = nomb_feux
                        else:
                            self.nomb_feux = 0
                        # self.nomb_feux = 6
                        self.feu = None
                        self.compteur_feu = 0
            else:

                self.hisse = False
                self.yFanion = 0
                self.fanion = charge_image("drapeau-etoile.png")

            if self.hisse and self.nomb_feux > 0:

                if self.feu:

                    if not self.feu.vivant():
                        self.nomb_feux -= 1
                        self.feu = None

                elif self.compteur_feu > 0:
                    self.compteur_feu -= 1

                else:
                    pos = list(self.rect.midtop)

                    for i in 0, 1:
                        pos[i] -= self.OrdreDesFeux[self.nomb_feux - 1][i]

                    # print 'Pos Feu', pos, self.nomb_feux
                    self.feu = FeuDArtifice(pos)

                    self.compteur_feu = FeuDArtifice.duree_detonation

    def affiche(self, surf, camera, mode_modifs=False, centre=None, alpha=None):

        if hasattr(self, 'fanion'):
            # Hissage du drapeau

            relRect = camera.rel_rect(self.rect)
            pos = list(relRect.midtop)
            pos[1] -= self.yFanion
            pos[0] -= self.fanion.get_width() // 2
            surf.blit(self.fanion, pos)

        Dessinable.affiche(self, surf, camera, mode_modifs, centre, alpha)


class ChateauGrand(Dessinable):
    nomImages = ["castle-big.png"]


class Chaine(Dessinable):
    nomImages = ["chain.png"]


class Buisson(Dessinable):
    nomImages = ["bush-1.png"]


class BuissonSimple(Dessinable):
    nomImages = ["buisson-simple.png"]


class BuissonDouble(Dessinable):
    nomImages = ["buisson-double.png"]


class Pont(Dessinable):
    nomImages = ["bridge.png"]


class Nuage(Dessinable):
    nomImages = ["cloud.png"]


class NuageDouble(Nuage):
    nomImages = ["dobbelclouds.png"]


class NuageTriple(Nuage):
    nomImages = ["nuage-triple.png"]


class ProjectileInterface:

    def effet_joueur(self, joueur, side):
        joueur.blesse()
        self.tue()


class MilieuAquatique(Collidable):

    def effet_joueur(self, joueur, side):
        if joueur.couleur == -1:
            joueur.couleur = -2  # coco couda en culotte
        joueur.sous_l_eau = max(joueur.sous_l_eau, joueur.rect.bottom - self.rect.top)


class PleineEau(MilieuAquatique):
    nomImages = ["pleine-eau.png"]


class PeuDEau(MilieuAquatique):
    nomImages = ["peu-d-eau.png"]


class Vaguelettes(PleineEau):
    nomImages = ["vaguelettes.png"]


class Firebowser(Collidable, ProjectileInterface):
    nomImages = ["bowser-fireball1.png"]

    def __init__(self, pos=None):

        Collidable.__init__(self, pos)

        self.baseY = self.rect.centerx
        self.speed = Vec(-2.9, 0.5)

    def on_collision(self, side, sprite):
        if side == HAUT:
            sprite.rect.right = self.rect.left
            sprite.speed[1] = 2
        elif side == BAS:
            sprite.rect.right = self.rect.left

    def maj(self):
        if self.rect.centerx & self.baseY + 64:
            self.speed[1] *= -1
        if self.rect.centerx & self.baseY - 64:
            self.speed[1] *= -1
        self.mouve()


class AllerRetourable:

    def __init__(self):

        self.debattement_ = 100, 100
        self.vitesse_ = Vec(0, 1)

    def maj(self):

        vitesseRef = self.vitesse_

        for i in 0, 1:

            if self.speed[i] == 0 and self.vitesse_[i]:
                self.speed[i] = self.vitesse_[i]

            if self.debattement_[i] > 0:
                if self.rect.topleft[i] > self.posInit[i] + self.debattement_[i]:
                    self.speed[i] = -vitesseRef[i]

                elif self.rect.topleft[i] < self.posInit[i]:
                    self.speed[i] = vitesseRef[i]

            else:
                if self.rect.topleft[i] < self.posInit[i] + self.debattement_[i]:
                    self.speed[i] = vitesseRef[i]

                elif self.rect.topleft[i] > self.posInit[i]:
                    self.speed[i] = -vitesseRef[i]

        if self.speed[0] < 0:
            self._vers_gauche = True
        elif self.speed[0] > 0:
            self._vers_gauche = False

        self.rafraichit_image()

        if self.speed:
            self.mouve()

    def on_collision(self, side, sprite):

        if side == HAUT or side == BAS:
            self.speed[1] *= -1

    def affiche(self, surf, camera, mode_modifs=False, centre=None, alpha=None):

        if mode_modifs:

            # Affiche le rectangle correspondant au domaine balaye par le mouvement
            rect = self.rect.copy()
            rect.topleft = self.posInit

            mouve = [0, 0]

            for i in 0, 1:
                if self.vitesse_[i]:
                    mouve[i] = self.debattement_[i]
                    mouve[1 - i] = 0
                    rect.union_ip(rect.move(mouve))

            rect = camera.rel_rect(rect)
            black = pygame.Surface((rect.w, rect.h))
            black.fill((0, 0, 0))
            black.set_alpha(100)

            surf.blit(black, rect.topleft)

        Dessinable.affiche(self, surf, camera, mode_modifs, centre, alpha)


class Poutrelle(AllerRetourable, CollidableBloc):
    nomImages = ["moving-platform.png"]
    gravite = None

    def __init__(self, pos=None):
        Dessinable.__init__(self, pos)
        AllerRetourable.__init__(self)

    def on_collision(self, side, sprite):

        if side in (HAUT, TRAVERSE):
            # sprite.speed[0] = self.speed[0]
            # sprite.rect.bottom = self.rect.top + self.speed[1]

            sprite.deplace(mouve=self.speed)

        elif side == BAS:
            sprite.rect.top = self.rect.bottom
            if not (isinstance(sprite, Perso) and sprite.en_saut):
                sprite.tue()


class PoutrelleLongue(Poutrelle):
    nomImages = ["moving-platformlong.png"]


class Coline(Dessinable):
    nomImages = ["hill.png"]


class Phare(Dessinable):
    nomImages = ["Pharegd.png"]


class Dune(Dessinable):
    nomImages = ["dune.png"]


class MotteDeTerre(Dessinable):
    nomImages = ["grass-texture.png"]


class Mur(Dessinable):
    nomImages = ["wall-1.png"]


class Lave(Collidable):
    nomImages = ["lava.png"]

    def effet_joueur(self, joueur, side):
        joueur.efface()


class Tremplin(Collidable):
    nomImages = ["spring%d.png" % i for i in (1, 2, 3)]

    penetrable = False, True, False, True, False

    def __init__(self, pos=None):

        Collidable.__init__(self, pos)
        self.son_grand_saut_ = "smb_jump-super.wav"
        self.son_petit_saut_ = 'smb_jump-small.wav'
        self.intensite_saut_ = 15
        self.spring_time = 0

    def on_collision_passive(self, side, sprite):

        if side == HAUT:

            if not self.spring_time and not sprite.penetrable_bas_:
                self.spring_time = 12

    def on_collision(self, side, sprite):

        if side == HAUT:

            if self.spring_time <= 8:

                sprite.speed[1] = -self.intensite_saut_

                if isinstance(sprite, Perso):
                    if sprite.Controle.BoutonA:
                        charge_son(self.son_grand_saut_).play()
                        sprite.speed[1] -= 5.4
                    else:
                        charge_son(self.son_petit_saut_).play()

                    sprite.en_saut = True
                    sprite.en_rebond = True

                else:
                    charge_son(self.son_petit_saut_).play()

    def maj(self):

        self.mouve()

        if self.spring_time > 0:

            self.spring_time -= 1

            if 8 >= self.spring_time > 4:
                novImg = self.images[0][2]

            elif self.spring_time == 0:
                novImg = self.images[0][0]

            else:
                novImg = self.images[0][1]

            H = self.image.get_height()
            novH = novImg.get_height()

            if H != novH:

                self.speed[1] = H - novH

                bas = self.rect.bottom
                self.mouve()
                self.speed[1] = 1
                postMouvH = bas - self.rect.top

                if postMouvH >= novH:
                    # pas d'obstacle a l'expansion du tremplin
                    self.rect.h = novH
                    self.image = novImg

                else:
                    # obstacle a l'expansion - garde la position contracte
                    self.spring_time += 1

                # preserve la position du bas du tremplin
                self.rect.bottom = bas
                self.deplace()


class Ephemere(Dessinable):

    def __init__(self, pos, images, compteur):
        Dessinable.__init__(self, pos, images=images)
        self.compteur = compteur

    def maj(self):
        if self.compteur <= 0:
            self.efface()
        self.compteur -= 1


class EnemiInterface:
    pass


class Boulette(Collidable):
    penetrable = False, True, False, True, True
    nomImages = ["boulette%d.png" % i for i in range(1, 5)]
    freq = 3
    rebond = 4
    # gravite = 2.1
    NombBoulettes = 0
    MaxBoulettes = 2

    def __init__(self, pos=None):

        self.shoot_sound = charge_son("fireball.ogg")
        self.shoot_sound.play()
        Boulette.NombBoulettes += 1
        assert Boulette.NombBoulettes <= Boulette.MaxBoulettes

        Collidable.__init__(self, pos)

    def maj(self):

        self.rafraichit_image()
        self.mouve()

    def tue(self, side=None):
        Boulette.NombBoulettes -= 1
        self.efface()

        if self.speed[0] > 0:
            centrex = self.rect.right
        else:
            centrex = self.rect.left

        ExploBoulette(pos=(centrex, self.rect.centery))

    def on_collision(self, side, sprite):

        if not isinstance(sprite, (Perso, Boulette)):  # Afaire - enqueter sur les boulettes fantome
            assert sprite is not self

        if isinstance(sprite, EnemiInterface):
            sprite.tue(side=_CoteReciproque[side])
            self.tue()

        elif side in [DROITE, GAUCHE, TRAVERSE]:
            penetrables = list(sprite._penetrable)

            if len(penetrables) == 4:
                # A enlever quand tous les elements des mondes sauvegardes
                # auront ete reinitialise avec un vecteur _penetrable de 5 elements
                penetrables.append(any(penetrables))

            if not isinstance(sprite, (Perso, Boulette)) and not penetrables[_CoteReciproque[side]] and sprite.visible_:
                self.tue()
                # print 'boulette efface contre', sprite

    def horschamp(self, joueur, camera):
        # nique la boulette si elle sort de l'ecran
        Boulette.NombBoulettes -= 1
        self.efface(strict=False)


class BouleDeFeu(Collidable):
    """ Enorme boule de feu """

    nomImages = ['bouledefeu%d.png' % i for i in (1, 2)]
    son_flame = "flame.wav"
    gravite = None

    def __init__(self, pos=None, versGauche=False):

        Collidable.__init__(self, pos, versGauche=versGauche)
        self.speed[0] = 8
        if versGauche:
            self.speed[0] *= -1

        self.compteur = 0
        charge_son(self.son_flame).play()

    def maj(self):
        self.compteur += 1

        if self.compteur == 10:
            self.image = self.images[self._vers_gauche][1]

        self.mouve()

    def on_collision(self, side, sprite):

        if isinstance(sprite, EnemiInterface):
            sprite.tue()

        elif isinstance(sprite, BlocBase):
            if not sprite.incassable_:
                sprite.casser()
            elif hasattr(sprite, 'declenche'):
                sprite.declenche(self)

    def horschamp(self, joueur, camera):
        # nique la boule si elle sort de l'ecran
        self.efface(strict=False)


class FleurCarnivore(Collidable, Intouchable, EnemiInterface):
    nomImages = ["flower%d.png" % i for i in (1, 2)]
    freq = 12
    gravite = 0

    dist_inhibition = 2 * media.TAILLE_BLOC

    def __init__(self, pos=None):

        Collidable.__init__(self, pos)

        self.speed = Vec(0, -1)

        self.tempsCachee_ = 150  # temps que la fleur reste cachee
        self.cacheeChrono = 0

    def maj(self):
        # Rentre et sort du pot

        if self.cacheeChrono > 0:
            # reste cachee en bas
            self.cacheeChrono -= 1
        else:
            if self.rect.top <= self.posInit[1] - self.rect.h:
                self.speed[1] *= -1
            elif self.rect.top > self.posInit[1]:
                self.rect.top = self.posInit[1] + 1
                self.cacheeChrono = self.tempsCachee_
                self.speed[1] *= -1

            self.rafraichit_image()
            self.mouve(collision=False)

    def action_in_camera(self, joueur, camera):
        if self.cacheeChrono == 1 and ((Vec(joueur.rect.center) - self.rect.center) < self.dist_inhibition):
            # Reste cachee si le perso est a proximite
            self.cacheeChrono += 1

    def blesse(self):
        self.tue()

    def affiche(self, surf, camera, mode_modifs=False, centre=None, alpha=None):

        Dessinable.affiche(self, surf, camera, mode_modifs=mode_modifs, centre=centre, alpha=alpha)

        if mode_modifs:
            img = self.image.convert()
            img.set_alpha(100)
            rect = self.rect.copy()
            rect.bottom = self.posInit[1]
            surf.blit(img, camera.rel_rect(rect))


class FleurCarnivore2(FleurCarnivore):
    pass


class Sautable:
    son_ecrase = "smb_stomp.wav"

    def effet_joueur(self, joueur, side):

        if self.vivant():

            if joueur.rect.bottom < self.rect.top + 10 and joueur.speed[1] >= 0:

                self.ecrase()

                if joueur.serie_ecrasement >= len(Perso.POINTS_ECRASE):
                    # gagne une vie
                    joueur.incremente_vie()

                else:
                    if joueur.serie_ecrasement == 0 or isinstance(self, BouletDeCanon):
                        points = self.points
                    else:
                        points = joueur.POINTS_ECRASE[joueur.serie_ecrasement]

                    joueur.engrange_points(points, self.rect.move(0, -15).topleft)

                joueur.serie_ecrasement += 1

                # Rebond sur le mechant
                joueur.speed[1] = -5
                if joueur.Controle.BoutonA:
                    # Rebondit plus haut si le bouton de saut est presse
                    joueur.speed[1] -= 2.7

                joueur.rect.bottom = self.rect.top - 1

            elif joueur.surpuissant:
                self.tue()

            else:
                joueur.blesse()
                raise IgnoreCollision

    def ecrase(self):
        charge_son(self.son_ecrase).play()
        self.tue(points=False)


class Ecriteau(Dessinable):

    def __init__(self, pos=(0, 0)):

        self._image = None
        self._taille = 16
        self._couleur = 0, 0, 0
        self._police = 'font.ttf'
        self.rect = pygame.Rect(0, 0, 0, 0)
        Dessinable.__init__(self, pos)
        self.message_ = 'XXXX YYYYY'

    @property
    def taille_(self):
        return self._taille

    @taille_.setter
    def taille_(self, val):
        self._taille = val
        self.message_ = self.message_

    @property
    def police_(self):
        return self._police

    @police_.setter
    def police_(self, val):
        self._police = val
        self.message_ = self.message_

    @property
    def couleur_(self):
        return self._couleur

    @couleur_.setter
    def couleur_(self, val):
        self._couleur = val
        self.message_ = self.message_

    @property
    def message_(self):
        return self._message

    @message_.setter
    def message_(self, val):

        self._message = val
        self._image = media.SurfaceTexte(self._message, self.police_, self._taille, self.couleur_)

        self.rect = self.image.get_rect()

        if self.posInit is not None:
            self.rect.topleft = self.posInit

    @property
    def image(self):
        if self._image:
            return self._image.image

    @image.setter
    def image(self, val):
        self._image = None


class Legende(Dessinable):
    """Affichage flottant des points
        par exemple lorsque l'on ecrase un enemi
    """

    # variable de classe self.font doit etre intialisee statiquement avant tout instanciation.

    def __init__(self, pos=None, texte='', compteur=40, vX=-2):
        Couleur = (255, 255, 255)
        img = self.font.render(str(texte), 1, Couleur)
        Dessinable.__init__(self, pos, [img])
        self.compteur = compteur
        self.rectRel = None
        self.vX = vX

    def action_in_camera(self, joueur, camera):
        self.compteur -= 1
        if self.compteur <= 0:
            self.efface()
        else:
            self.rect.move_ip(0, self.vX)
            self.rectRel = camera.rel_rect(self.rect)

    def affiche(self, surf, camera, mode_modifs=False, centre=None, alpha=None):
        if self.rectRel:
            surf.blit(self.image, self.rectRel)


class Mechant(AutoMobile, EnemiInterface):
    v_X = -1
    carapace = None
    capsule = None
    carcasse = None
    points = 100

    def __init__(self, pos=None, images=None):

        AutoMobile.__init__(self, pos, images)

        self.speed[0] = self.v_X
        self.son_efface_ = "smb_kick.wav"

    def blesse(self):
        self.tue()

    def tue(self, side=None, points=True):

        charge_son(self.son_efface_).play()

        if self.carcasse:
            img = charge_image(self.carcasse)
        else:
            img = pygame.transform.flip(self.image, True, True)

        if side in (DROITE, GAUCHE):
            vX = 3 * -Signe_Direction[side]
        else:
            vX = self.speed[0]

        Morceau(self.rect.topleft, images=[img], vX=vX, impulsion=-5)

        if points:
            self.joueur.engrange_points(self.points, pos=self.rect.move(0, -15).topleft)

        self.efface()

    def effet_joueur(self, joueur, side):

        if self.vivant():

            if joueur.surpuissant:
                self.tue()
            else:
                joueur.blesse()

            raise IgnoreCollision


class EcureuilNuageux(Sautable, Mechant, AllerRetourable):
    """Ecureuil qui balance des crabes depuis son nuage"""

    gravite = None
    nomImages = ['ecureuil%d.png' % i for i in (1, 2, 3, 4)]

    affiche = AllerRetourable.affiche

    def __init__(self, pos=None):
        Mechant.__init__(self, pos)
        AllerRetourable.__init__(self)
        self.frequence_de_tir_ = 200
        self.frequence_cligne_ = 100
        self.DeltaX = 0
        self.projectile_ = Crabe.__name__

        self.debattement_ = 1000, 0
        self.vitesse_ = Vec(1, 0)
        self.retour = False

    def maj(self):
        pass

    def horschamp(self, joueur, camera):
        if self.retour:
            self.efface()

    def action_in_camera(self, joueur, camera):

        num = self.index_temps % self.frequence_de_tir_

        if self.retour:
            self.mouve()
            if self.rect.left <= self.posInit[0]:
                self.retour = False
                self.speed[0] = 0

        elif self.rect.right >= self.posInit[0] + self.debattement_[0]:
            # Ne depasse pas l'absisce max.    
            self.speed[0] = -5
            self.retour = True

        else:
            if num < 50:
                imgIndex = 1

            else:

                if num == 50:
                    # Projection de projectiles
                    ClasseProjectile = globals()[self.projectile_]
                    if hasattr(ClasseProjectile, 'capsule') and ClasseProjectile.capsule:
                        Capsule(pos=self.rect.topright, Contenu=ClasseProjectile)
                    else:
                        ClasseProjectile(pos=self.rect.topright)

                num = self.index_temps % self.frequence_cligne_
                if num < 10:
                    imgIndex = 2
                elif num < 20:
                    imgIndex = 3
                else:
                    imgIndex = 0

            self.image = self.images[self._vers_gauche][imgIndex]

            if num == 50:
                self.DeltaX = random.randint(-1, 1) * 100

            self.speed[0] = 0

            distJoueur = joueur.rect.centerx - self.rect.centerx
            if distJoueur > 350:
                # ratrape le joueur
                self.speed[0] = abs(joueur.speed[0]) + 2
            else:
                # Deplacement        
                dx = joueur.rect.centerx + self.DeltaX - self.rect.centerx

                if abs(dx) > 50:

                    vmax = max(abs(joueur.speed[0]), 3)

                    if dx > 0:
                        dx = vmax
                    else:
                        dx = -vmax

                    self.speed[0] = dx

            if self.speed[0]:
                self.mouve()


class NuageGentil(EcureuilNuageux):
    nomImages = ['nuage_actif.png'] * 4


class Capsule(Mechant):
    """ Capsule lancable par un enemi perche dans un nuage
        et qui libere un enemi en touchant un obstacle.
    """

    freq = 3
    gravite = .6

    def __init__(self, pos=None, Contenu=None):
        Mechant.__init__(self, pos, Contenu.capsule)
        self.contenu = Contenu

    def on_collision(self, side, sprite):
        if side == BAS:
            # Libere le contenu
            self.efface()
            projectile = self.contenu((0, 0))
            projectile.rect.centerx = self.rect.centerx
            projectile.rect.bottom = sprite.rect.top
            projectile.deplace()


class BeteAquatique:
    """Bete qui doit rester sous l'eau"""

    def on_collision(self, side, sprite):
        if isinstance(sprite, Vaguelettes):
            self.speed[1] = 1


class Oisson(Mechant, BeteAquatique):
    """ Oiseau-poisson """

    # penetrable = True, True, True, True, True
    nomImages = ["oisson%d.png" % i for i in (1, 2)]
    gravite = None
    freq = 40

    def __init__(self, pos=None):
        Mechant.__init__(self, pos)
        self.speed[0] = -1

    def maj(self):

        instant = self.index_temps % self.freq
        if instant == 0:
            self.speed[1] = [-1, 1][random.randint(0, 1)]

        elif instant == 2:
            self.speed[1] = 0

        Mechant.maj(self)


class OissonGris(Oisson):
    nomImages = ["oisson-gris%d.png" % i for i in (1, 2)]


class Calmar(Mechant, BeteAquatique):
    gravite = None

    nomImages = ["calamar%d.png" % i for i in (1, 2)]

    freq = 12

    def __init__(self, pos=None):

        Mechant.__init__(self, pos)
        self.speed = Vec(0, 1)
        self.retracte = False
        self.tempsRetraction_ = 12
        self.compteur = 0

    def maj(self):

        self.image = self.images[0][self.retracte]
        top = self.rect.top
        rect = self.image.get_rect()
        rect.top = top

    def action_in_camera(self, joueur, camera):

        DiffPos = Vec(joueur.rect.center) - self.rect.center

        self.compteur -= 1

        if self.retracte:

            if self.compteur <= 0:
                self.retracte = False
                self.compteur = 2 * self.tempsRetraction_
                # Plus retracte, se laisse tomber
                self.speed[0] = 0
                self.speed[1] = 1

        else:

            if self.compteur <= 0 and DiffPos[1] < 0:
                # Perso est au dessus - nage vers lui
                self.retracte = True
                self.compteur = self.tempsRetraction_

                if DiffPos[1] < 0:
                    # nage vers le haut
                    self.speed[0] = 3
                    if DiffPos[0] < 0:
                        self.speed[0] *= -1

                    self.speed[1] = -3

        self.mouve()


class Pigeon(Sautable, Mechant):
    """ pigeon des villes """

    nomImagesVol = ["pigeon%d.png" % i for i in (1, 2)]
    nomImages = ["pigeonmarche%d.png" % i for i in (1, 2)]

    v_X = 1

    def __init__(self, pos=None):
        Mechant.__init__(self, pos)
        self.vole_ = False
        self.rayon_joueur_ = 200
        self.dist_envol_ = 100

    @property
    def vole_(self):
        return self._vole

    @vole_.setter
    def vole_(self, val):

        if val:
            self.set_images(self.nomImagesVol)

        else:
            self.set_images(self.nomImages)
            self.speed[0] = 1 if self.speed[0] > 0 else -1
            self.speed[1] = 1

        self._vole = val

    def on_collision(self, side, sprite):
        if self.vole_:
            if side == BAS:
                self.vole_ = False

    def effet_joueur(self, joueur, side):

        if side == HAUT:
            Sautable.effet_joueur(self, joueur, side)
        else:
            charge_son(self.son_ecrase).play()
            self.tue()

    def action_in_camera(self, joueur, camera):
        """ s'envole a l'approche du joueur """
        distX = joueur.rect.centerx - self.rect.centerx
        if self._vole:

            self.speed[1] -= self.gravite

            alea = random.random()

            if abs(distX) > self.rayon_joueur_ or not camera.rect.contains(self.rect):

                if self.speed[0] * distX < 0:
                    # revient vers le joueur
                    self.speed[0] *= -1

                self.speed[1] = 0

            else:

                dist_y = joueur.rect.top - self.rect.bottom

                if dist_y > 60 * (1 + .2 * alea):

                    if dist_y > 150 * (1 + .2 * alea):
                        # Descend vers le joueur
                        self.speed[1] = 3
                    else:
                        # arrete de monter si l'on est suffisament au dessus du joueur
                        self.speed[1] = 0
                        self.speed[0] = 2 if self.speed[0] > 0 else -2

                else:
                    # monte pour s'eloigner du joueur
                    self.speed[1] = -2

            if alea > .99:
                # Fiente

                fiente = Fiente()
                if self.vers_gauche_:
                    fiente.rect.topright = self.rect.bottomleft
                else:
                    fiente.rect.topleft = self.rect.bottomright
                fiente.deplace()
                fiente.speed[1] = 1
        else:

            if abs(distX) < self.dist_envol_:
                # s'envole si le joueur se rapproche
                self.vole_ = True
                self.speed[0] = 4
                if distX > 0:
                    self.speed[0] *= -1
                self.speed[1] = -3

            else:
                self.marche_erratique()

    def tue(self, side=None, points=True):

        Mechant.tue(self, side=side, points=points)

        explo = ["pigeonexplose%d.png" % i for i in (1, 2)]
        anim = Animation(pos=None, images=explo, durees=[10, 20], vers_gauche=self._vers_gauche)
        anim.rect.center = self.rect.center
        anim.deplace()


class Fiente(Collidable, Intouchable):
    """fiente lachee par les  pigeons"""

    nomImages = ['fiente.png']

    def maj(self):
        self.mouve()

    def on_collision(self, side, sprite):
        self.tue()

    def tue(self, side=None):
        self.efface()

        ExploFiente(pos=self.rect.center)


class Carapace(AutoMobile, Sautable, EnemiInterface):
    """ e.g. carapace de tortue """

    nomImages = ['Pharegd.png']  # afaire
    points = 0
    marche_haut_ = 0
    marche_bas_ = 0

    POINTS_DEGOMMAGE = 500, 800, 1000, 2000, 4000, 5000, 8000

    def __init__(self, pos=None, images=None, parent=None):
        AutoMobile.__init__(self, pos, images)
        self.son_choc = charge_son("smb_bump.wav")
        self.son_tape = charge_son('smb_kick.wav')
        self.tempsCache_ = 300
        self.cacheChrono = self.tempsCache_
        self.parent = parent
        self.serie_degommage = 0

    def maj(self):

        if self.speed[0] == 0 and 0 <= self.speed[1] < 2:
            # la tortue ne ressort que d'une carapace immobile
            self.cacheChrono -= 1

            if self.cacheChrono <= 0:
                self.efface()
                self.parent.rect.bottomleft = self.rect.bottomleft
                self.parent.insere()

            elif self.cacheChrono < 100:
                self.image = self.images[0][1]
        else:
            self.resurectionChrono = self.tempsCache_

        self.mouve()

    def effet_joueur(self, joueur, side):

        self.image = self.images[0][0]

        if joueur.surpuissant:
            self.tue()

        if self.speed[0]:
            # la carapace est en mouvement

            if side == HAUT:
                # le joueur rebondit dessus, elle s'arrete

                self.son_tape.play()
                self.speed[0] = 0
                self.serie_degommage = 0

                joueur.speed[1] = -6
                joueur.rect.bottom = self.rect.top - 1


            else:
                # le joueur est touche

                joueur.blesse()
                raise IgnoreCollision

        else:
            # la carapace est a l'arret
            self.son_tape.play()
            self.speed[0] = 7
            if joueur.rect.centerx < self.rect.centerx:
                self.rect.left = joueur.rect.right + 10
            else:
                self.rect.right = joueur.rect.left - 10
                self.speed[0] *= -1

    def on_collision(self, side, sprite):

        if self.speed[0]:

            if isinstance(sprite, Carapace):
                self.son_tape.play()
                sprite.tue()
                self.tue()

            elif isinstance(sprite, EnemiInterface):

                self.son_tape.play()

                affiche_points = self.serie_degommage == 0
                sprite.tue(points=affiche_points)
                self.serie_degommage += 1
                if not affiche_points:
                    if self.serie_degommage >= len(self.POINTS_DEGOMMAGE):
                        self.joueur.incremente_vie()
                    else:
                        points = self.POINTS_DEGOMMAGE[self.serie_degommage]
                        self.joueur.engrange_points(points, self.rect.move(0, -15).topleft)

                self.speed[0] *= -1  # annule le changement de cote du a la collision

            elif isinstance(sprite, Perso):
                if side in (GAUCHE, DROITE):
                    self.speed[0] *= -1  # annule le changement de cote du a la collision

            elif side in (DROITE, GAUCHE):
                # La carapace se cogne de cote
                if not self.hors_champ:
                    self.son_choc.play()

    def tue(self, side=None, points=True):

        img = pygame.transform.flip(self.image, True, True)
        Morceau(self.rect.topleft, images=[img], vX=self.speed[0], impulsion=-5)

        self.efface()


class Tortue(Sautable, Mechant):
    nomImages = ["monster%d.png" % i for i in range(1, 3)]
    marche_bas_ = 0
    carapace = 'monster3.png', 'monster4.png'
    points = 200

    def ecrase(self):
        charge_son(self.son_efface_).play()

        Dep = Carapace(self.rect.topleft, images=[charge_image(img) for img in self.carapace], parent=self)

        Dep.rect.bottom = self.rect.bottom

        self.efface()

    def tue(self, side=None, points=True):
        self.image = charge_image(self.carapace[0])
        Mechant.tue(self, side=side, points=points)


class TortueRouge(Tortue):
    nomImages = ["monster-red%d.png" % i for i in range(1, 3)]
    carapace = 'monster-red3.png', 'monster-red4.png'
    marche_bas_ = 3


class TortueRougeSansAiles(TortueRouge):
    """ Tortue une fois ecrasee qui a perdue ses ailes.
        Elle tombe des plateformes, contrairement a la tortue rouge
        """
    marche_bas_ = 0


class TortueSansAiles(Tortue):
    pass


class TortueAiles(AllerRetourable, Sautable, Mechant):
    """ tortue ailee qui perd ses ailes lorsqu'on lui saute dessus. """
    nomImages = ["monster%d-aile.png" % i for i in range(1, 3)]
    freq = 12

    gravite = None

    def __init__(self, pos=None):
        Mechant.__init__(self, pos)
        AllerRetourable.__init__(self)

    def ecrase(self):
        charge_son(self.son_ecrase).play()
        self.efface()
        # devient une Tortue sans ailes
        tortue = eval(self.__class__.__name__[:-5] + 'SansAiles')(self.rect.topleft)
        tortue._vers_gauche = self._vers_gauche


class TortueRougeAiles(TortueAiles):
    """ tortue ailee qui perd ses ailes lorsqu'on lui saute dessus. """
    nomImages = ["monster-red%d-aile.png" % i for i in (1, 2)]


class Slub(Sautable, Mechant):
    nomImages = ["slub%d.png" % i for i in (1, 2)]

    v_X = -1

    def ecrase(self):
        charge_son(self.son_ecrase).play()
        # img = pygame.transform.scale(self.image, (self.image.get_width(), self.image.get_height()/2))
        img = charge_image("slub3.png")  # Image aplatie
        boom = Animation(self.rect.center, [img], durees=[36])
        boom.rect.bottom = self.rect.bottom
        boom.deplace()
        self.efface()


class Crane(Sautable, Mechant):
    nomImages = ["crane%d.png" % i for i in (1, 2)]
    carcasse = "crane3.png"


class TeteDeMort(Sautable, Mechant):
    nomImages = ["tetedemort%d.png" % i for i in (1, 2, 3, 4)]
    carcasse = "tetedemort5.png"


class RatNoir(Sautable, Mechant):
    nomImages = ["rat%d.png" % i for i in (1, 2)]
    points = 100
    v_X = 3

    def maj(self):
        self.marche_erratique()


class Crabe(Mechant):
    nomImages = ["crabe%d.png" % i for i in (1, 2, 3)]
    carcasse = 'crabe4.png'

    v_X = -2


class Herisson(Mechant):
    nomImages = ['herisson%d.png' % i for i in (1, 2)]
    capsule = ['herisson%d.png' % i for i in (3, 4)]


class Squidge(Sautable, Mechant):
    nomImages = ["squidge%d.png" % i for i in (1, 2)]
    nomImages_boom = ["squidge2.png", "squidge3.png", "exp1.png", "exp2.png", "exp3.png"]

    freq = 12

    def action_in_camera(self, joueur, camera):
        if not random.randrange(70):
            BaddieShot(self.rect.center, joueur.rect.centerx)


class Animation(Dessinable):
    freq = 4

    def __init__(self, pos, images, durees, centre=False, vers_gauche=True):

        Dessinable.__init__(self, pos, images=images)

        self._vers_gauche = vers_gauche
        self.rect = self.image.get_rect(center=pos)
        self.durees = durees
        self.centre = centre
        self.timer = 0

    def maj(self):

        # numImages = len( self.images[0] )

        for img, duree in zip(self.images[self._vers_gauche], self.durees):

            if self.timer <= duree:
                self.image = img
                if self.centre:
                    center = self.rect.center
                    self.rect = img.get_rect()
                    self.rect.center = center
                break

        else:
            self.efface()

        self.timer += 1


class PortailMonde(Dessinable, Passage):
    """ Portail qui declenche le passage a un autre monde """

    penetrable = True, True, True, True, True
    nomImages = ['portail-monde.png']

    def __init__(self, pos=None):

        Dessinable.__init__(self, pos)
        Passage.__init__(self)
        self.active = False
        self.chrono_ = 10
        self.decompte_ = True

    def effet_joueur(self, joueur, side):
        if self.monde_suivant_ and abs(joueur.rect.centerx - self.rect.centerx) <= 2 and abs(
                joueur.rect.bottom - self.rect.bottom) <= 2:
            joueur.efface()
            self.active = True

    def maj(self):

        if self.active and self.chrono_ >= 0:
            self.chrono_ -= 1

        if self.chrono_ == 0:
            raise interruptions.TransferMonde(self.monde_suivant_, decompte=self.decompte_)

    def affiche(self, surf, camera, mode_modifs=False, centre=None, alpha=None):
        Dessinable.affiche(self, surf, camera, mode_modifs, centre, alpha)

        if mode_modifs:
            # pygame.draw.line(surf,(250,150,30), relRect.midtop, relRect.midbottom, 3)
            Passage.affiche(self, surf, camera, mode_modifs, centre, alpha)


class BaddieShot(Collidable, ProjectileInterface):
    nomImages = ["shot.png"]

    def __init__(self, pos=None, target=(0, 0)):
        Collidable.__init__(self, pos)
        self.rect = self.image.get_rect(center=pos)

        self.x, self.y = self.rect.center
        x = self.x - target[0]
        y = self.y - target[1]
        angle = math.atan2(y, x)
        self.angle = int(270.0 - (angle * 180) / math.pi)

    def maj(self):
        self.rect.center = (self.x, self.y)
        speed = 3
        self.x += math.sin(math.radians(self.angle)) * speed
        self.y += math.cos(math.radians(self.angle)) * speed


# ____________________________________________________________________________

class Canon(CollidableBloc):
    nomImages = ["cannon1.png"]

    def __init__(self, pos=None):

        CollidableBloc.__init__(self, pos)
        self.tire_gauche_ = True
        self.tire_droite_ = True
        self.recharge_ = 20
        self.frequence_de_tir_ = 135
        self.son_tir_ = 'smb_fireworks.wav'

    def action_in_camera(self, joueur, camera):

        if not random.randrange(self.frequence_de_tir_):

            charge_son(self.son_tir_).play()
            joueur_x = joueur.rect.centerx
            cote_droit = joueur_x > self.rect.centerx
            if (cote_droit and self.tire_droite_) or (not cote_droit and self.tire_gauche_):
                BouletDeCanon(self.rect.topleft, target=joueur.rect.centerx)


class CanonGrand(Canon):
    nomImages = ["cannonbig1.png"]


class CanonPetit(Canon):
    nomImages = ["smallcannon1.png"]


class BouletDeCanon(Sautable, CollidableBloc):
    nomImages = ["cannonbullet1.png"]
    son_ecrase = "smb_kick.wav"
    points = 100

    def __init__(self, pos=None, target=0):
        """ target : vers ou part le coup """

        # pos[1] += 5 # ajuste la position de sortie du boulet pour qu'il soit dans l'axe du fut

        CollidableBloc.__init__(self, pos, versGauche=True)

        self.speed = Vec(4.5, 0)
        self.rect.h -= 2
        self._vers_gauche = pos[0] > target
        if self._vers_gauche:
            self.speed[0] *= -1

        self.inertie = 0
        self.tombe = False
        self.rafraichit_image()

    def maj(self):

        self.deplace(self.speed)  # AFaire - ne tue pas le joueur si ce dernier est touche alors qu'immobile

        if self.tombe:

            if self.speed[1] < 10:
                self.speed[1] += 1

    def horschamp(self, joueur, camera):
        self.efface()

    def tue(self, side=None, points=True):

        self.tombe = True
        self.speed[0] = 0


class Piece(Collidable):
    nomImages = ["piece%s.png" % i for i in (1, 2, 3)]

    points = 200
    freq = 20

    def __init__(self, pos=None):
        Collidable.__init__(self, pos)

        self.coin_sound = charge_son("smb_coin.wav")

    def maj(self):
        self.rafraichit_image()

    def blesse(self):
        self.tue()

    def tue(self, side=None):
        pygame.time.wait(10)
        self.coin_sound.play()
        self.efface()
        # ExploPouff(self.rect.center)

    def effet_joueur(self, joueur, side):
        self.tue()
        joueur.boursePieces += 1
        joueur.points += self.points


class PieceBleue(Piece):
    nomImages = ["piece-bleu%s.png" % i for i in (1, 2, 3)]


class PiecePrise(Dessinable):
    nomImages = ["coin%s.png" % i for i in (1, 2, 3, 4)]
    points = 200

    def __init__(self, pos=None):

        Dessinable.__init__(self, pos)
        self.coin_sound = charge_son("smb_coin.wav")
        self.speedY = -4
        self.coin_sound.play()
        self.rect.bottom -= 50
        self.compteur = 0

    def maj(self):

        self.compteur += 1

        self.speedY += .3
        self.rect.top += self.speedY

        if self.compteur >= 25:
            self.efface()
            Legende(self.rect.bottomleft, self.points)
        else:
            self.image = self.images[0][self.compteur // 3 % 3]

        # Recentre les images qui n'ont pas toute la meme largeur
        centerx = self.rect.centerx
        self.rect.w = self.image.get_width()
        self.rect.centerx = centerx


class SautDeLaMort(Dessinable):
    """ Animation 'saute en l'air' a la mort du joueur """

    def __init__(self, pos, images):
        Dessinable.__init__(self, pos, images=images)
        self.timer = 0
        self.rect.center = pos
        self.inertie = -11

    def maj(self):
        # Saute en l'air

        if self.timer >= 10:
            self.rect.move_ip(0, self.inertie)
            self.inertie += .5

        self.timer += 1

    def horschamp(self, joueur, camera):
        self.efface()
        raise interruptions.MortJoueur()


class MatDrapeau(Collidable):
    # Declencheur de fin de niveau (i.e. le mat du drapeau)
    nomImages = ["flagpole.png"]

    def __init__(self, pos=None):
        Collidable.__init__(self, pos)

        self.image_drapeau_ = "drapeau.png"
        self._vers_gauche = True
        self.pos_drapeau_ = 0  # position initiale du drapeau tout en haut du mat
        self.son_but_ = "goal.ogg"
        self.declenche_fin_niveau_ = True
        self.est_declenche = False
        self.posJoueur = None

    def effet_joueur(self, joueur, side):

        if (joueur.Controle.Haut or self.declenche_fin_niveau_) and joueur.rect.bottom >= self.rect.top:

            if joueur.agrippe is False:

                joueur.agrippe = self.rect.top

                if joueur._vers_gauche:
                    dx = self.rect.centerx - joueur.rect.left - 5
                else:
                    dx = self.rect.centerx - joueur.rect.right + 5

                joueur.deplace((dx, 0))

        if self.declenche_fin_niveau_:

            joueur.deplace((0, -2))

            self.declenche_fin_niveau_ = False
            self.est_declenche = 30

            media.arret_musique()
            charge_son(self.son_but_).play()

            joueur.Controle.Reset()
            self.surpuissant = None
            joueur.auto_pilote = True
            joueur.Controle.Bas = 100

        elif self.est_declenche:

            max_pos_drapeau = self.rect.h - charge_image(self.image_drapeau_).get_height() - 20

            if joueur.rect.bottom < self.rect.bottom - 10:

                if joueur.agrippe:

                    if self.pos_drapeau_ < max_pos_drapeau:
                        self.pos_drapeau_ = int(self.pos_drapeau_ + joueur.speed[1])

                        if self.pos_drapeau_ >= max_pos_drapeau:
                            # Drapeau est descendu tout en bas du mat.
                            self.pos_drapeau_ = max_pos_drapeau

                else:
                    joueur.Controle.Droite = 100

            elif joueur.agrippe:

                if joueur.Controle.Bas:
                    joueur.Controle.Droite = 100
                    joueur.Controle.Bas = 0

                elif self.est_declenche <= 1:
                    joueur.agrippe = False

                    points = int(round(5000 * self.pos_drapeau_ / max_pos_drapeau, -2))  # arrondi a la centaine
                    if points > 0:
                        joueur.engrange_points(points, pos=self.rect.move(0, -100).bottomright, duree=90)

                else:
                    self.est_declenche -= 1

            else:
                joueur.Controle.Droite = 100

    def affiche(self, surf, camera, mode_modifs=False, centre=None, alpha=None):

        Dessinable.affiche(self, surf, camera, mode_modifs=mode_modifs)
        img_drapeau = charge_image(self.image_drapeau_, flip=not self._vers_gauche)
        rect_drapeau = img_drapeau.get_rect()
        rect_drapeau.top = self.pos_drapeau_ + 16 + self.rect.top

        if self._vers_gauche:
            rect_drapeau.right = self.rect.centerx - 3
        else:
            rect_drapeau.left = self.rect.centerx + 3

        surf.blit(img_drapeau, camera.rel_rect(rect_drapeau))


Elements = dict(
    Surprises=[ChampiTaille, ChampiVert, Burger, Choppe, Piece, PieceBleue, FleurDeFeu, Bague, Etoile, PersoNonJoueur,
               Coeur, CoeurPiece, CoeurMultiColore, Chapeau, ChampiCoco, CocoNinja],

    Decor=[Coline, BuissonSimple, BuissonDouble, Buisson, Arbre1, Arbre2, Cloture,
           Nuage, NuageDouble, NuageTriple, Chateau, ChateauGrand, Mur, Pont, Lave, ],

    CapFerret=[Dune, Sables, EcureuilNuageux, Calmar, Crabe, Oisson, OissonGris, Vaguelettes, PleineEau, PeuDEau,
               PinCime,
               PinCimeCourte, PinTronc, PinTroncGrand, Phare, Corail, Algues, RocheSousMarine, Herisson],

    Paris=[Pigeon, RatNoir, PaveParisien, Crane, TeteDeMort],

    Blocs=[PlatformeQ, PlatformeQRouge, SolRoche, SolRocheBleu, SolRocheGris, Pierres, Briques, BriquesBleu,
           PlatformeBiseau, PlatformeBriques, Sables, RocheBlanche,
           MotteDeTerre, PlatformeHerbe, PlatformeHerbeGauche, PlatformeHerbeDroite],

    Mechants=[Slub, Tortue, TortueRouge, TortueAiles, TortueRougeAiles, FleurCarnivore,
              Canon, CanonPetit, CanonGrand, Calmar, Crabe, EcureuilNuageux, Herisson, Oisson, OissonGris, Pigeon,
              RatNoir],

    Accessoires=[Tuyeau, TuyeauCourt, TuyeauGrand, TuyeauMini, Tuyeau_Jointure, Tuyeau_Tube, Tuyeau_Bouche,
                 Poutrelle, PoutrelleLongue, Tremplin, MatDrapeau, PortailMonde, Coeur, Panneau, PanneauLarge,
                 Generateur, Ecriteau],

    Divers=[Figurant, PositionDepart, PersoNonJoueur, Princesse, NuageGentil])

Categories = tuple(Elements.keys())
