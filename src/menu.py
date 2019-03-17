#! /usr/bin/env python
from __future__ import print_function
from __future__ import absolute_import
import pygame
from . import media
import copy


class SortieMenu(Exception):
    pass


class ElemInterface(object):

    def __init__(self, pos=(0, 0), fonteH=16, centre=True, alpha_fond=50, imgFond=True, lectureSeule=False):

        self.pos = pos
        self.fonte = pygame.font.Font(media.cheminFichier(media.FONTE_DEFAUT, subdir='fonts'), fonteH)
        self.fonteH = fonteH
        self.interligne = 4
        self.couleur_texte = [255, 255, 255]
        self.couleur_texte_selec = [255, 0, 0]
        self.valeur = None
        self.alpha = 150
        self.hauteur = 0
        self.centre = centre

        self.modifiable = not lectureSeule

        self.bouton_validation = 1  # bouton souris pour valider les changements / la selection
        self.bouton_anulation = 3  # bouton souris pour annuler les changements / la selection

        # i.e. l'intervalle de temps au bout du quel une touche enfoncee
        # envoie un nouvel evenement de pression.
        self.repetition_clavier = 200, 100

        self.surface_dest = pygame.display.get_surface()

        if imgFond:
            # Ombre l'image de fond pour une meilleure lisibilite par contraste
            self.img_fond = self.surface_dest.convert_alpha()

            ombre = pygame.Surface(self.img_fond.get_size())
            ombre.fill((0, 0, 0))
            ombre.set_alpha(alpha_fond)

            self.img_fond.blit(ombre, (0, 0))

        else:
            self.img_fond = None

        self.x = self.pos[0]
        self.y = self.pos[1]

    @property
    def hauteur_ligne(self):
        return self.fonte.get_height()

    @property
    def ecart_ligne(self):
        return self.hauteur_ligne + self.interligne

    def mettre_a_jour(self, e):
        return False

    def affiche_ligne(self, surf_dest, texte, index_ligne=0, clr=None, centre=False, decalage=(0, 0)):

        if clr is None:
            clr = self.couleur_texte

        ren = self.fonte.render(texte, 1, clr)
        taille = ren.get_size()

        noir = pygame.Surface(taille)

        noir.fill((0, 0, 0))
        noir.set_alpha(self.alpha)

        pos_y = self.y + index_ligne * self.ecart_ligne

        if centre:
            coin_h_g = [self.x - ren.get_width() / 2, pos_y]
        else:
            coin_h_g = [self.x, pos_y]

        for i in 0, 1:
            coin_h_g[i] += decalage[i]

        surf_dest.blit(noir, coin_h_g)

        surf_dest.blit(ren, coin_h_g)

        return taille

    def __enter__(self):

        # Change le parametre de repetition des touches enfoncees,
        # et retabli la valeur preexistante en sortant.

        RepetitionExt = pygame.key.get_repeat()
        pygame.key.set_repeat(*self.repetition_clavier)
        self.repetition_clavier = RepetitionExt

    def __exit__(self, exc_type, exc_value, traceback):
        self.__enter__()
        pygame.event.clear()

    def boucle(self, action_func=None):

        clock = pygame.time.Clock()
        sortie_armee = False

        with self:

            while True:

                clock.tick(40)

                for e in pygame.event.get():

                    if e.type == pygame.QUIT:
                        pygame.quit()
                        return

                    if self.modifiable:
                        try:
                            if self.mettre_a_jour(e):
                                continue
                        except SortieMenu:
                            return self.valeur

                    if sortie_armee and e.type not in (pygame.MOUSEBUTTONUP, pygame.JOYBUTTONUP):
                        # Pour etre sur que la sortie du menu soit une action atomique.
                        sortie_armee = False

                    if (e.type == pygame.KEYDOWN and e.key == pygame.K_ESCAPE) or \
                            (e.type == pygame.MOUSEBUTTONUP and e.button == self.bouton_anulation):
                        # Sortie sans valider les changements / la selection
                        if (e.type not in (pygame.MOUSEBUTTONUP, pygame.JOYBUTTONUP)) ^ sortie_armee:
                            return

                    elif (e.type == pygame.KEYDOWN and e.key in (pygame.K_KP_ENTER, pygame.K_RETURN)) or \
                            (e.type == pygame.JOYBUTTONUP and e.button == 0) or \
                            (e.type == pygame.MOUSEBUTTONUP and e.button == self.bouton_validation):

                        # Sortie validant les changements / la selection
                        if (e.type not in (pygame.MOUSEBUTTONUP, pygame.JOYBUTTONUP)) ^ sortie_armee:
                            self.alafin()
                            return self.valeur
                    else:
                        sortie_armee = False

                    if action_func:
                        action_func(e)

                    if e.type == pygame.MOUSEBUTTONDOWN and e.button in (
                            self.bouton_validation, self.bouton_anulation) or \
                            e.type == pygame.JOYBUTTONDOWN and e.button in (0, 1):
                        sortie_armee = True

                self.surface_dest.blit(self.img_fond, (0, 0))

                self.affiche(self.surface_dest)

                pygame.display.flip()

    def alafin(self):
        pass


class InterfaceDeroulant(object):
    """
        propriete de defilement des champs d'un menu sous forme de liste dont la longeur excede la hauteur de l'ecran.
    """

    def __init__(self, options, legende, multi_selection=False, editable=True, forceListe=False):
        """
            forceListe : True: renvoie une liste d'index meme dans le cas multiselection = False
        """
        if isinstance(legende, str):
            self.legende = [legende]
        else:
            # on attend une liste
            self.legende = legende

        self.editable = editable
        self.champs = list(options)
        self._haut_index = 0  # index dans self.champs du premier element affiche en haut de l'ecran
        self.selection_index = [0]  # index des elements selectionnes
        self.multi_selection = multi_selection
        self.forceListe = forceListe

    @property
    def haut_index(self):
        """ index dans self.champs du premier element affiche en haut de l'ecran """
        return self._haut_index

    @haut_index.setter
    def haut_index(self, Val):
        nombChamps = len(self.champs)
        nombChampsVisibles = self.nombChampsVisibles()
        self._haut_index = min(max(0, Val), nombChamps - nombChampsVisibles)

    def pos_index(self, pos):
        return min(len(self.champs), max(0, int((pos[1] - self.pos[1]) / self.ecart_ligne) + self.haut_index - len(
            self.legende)))  # premiere lignes d'en-tete

    def nombChampsVisibles(self):
        return (self.surface_dest.get_height() - self.ecart_ligne * len(self.legende)) / self.ecart_ligne

    def maj_selection(self, novIndex):

        if not (self.multi_selection and pygame.key.get_mods() & pygame.KMOD_SHIFT):
            self.selection_index = []

        nombChamps = len(self.champs)
        novIndex %= nombChamps

        self.selection_index.append(novIndex)

    def mettre_a_jour(self, e):

        maj_valeur = False

        if e.type == pygame.MOUSEBUTTONDOWN and e.button in (4, 5):

            Increment = IncrementPourEvent(e, flechesHautBas=True)

            if Increment:
                self.haut_index = self.haut_index + Increment

            self.maj_selection(self.pos_index(pygame.mouse.get_pos()))

        elif e.type == pygame.MOUSEMOTION:
            # Positionnement absolu en suivant le curseur de la souris.
            self.maj_selection(self.pos_index(e.pos))
            # maj_valeur = True

        else:

            Increment = IncrementPourEvent(e, flechesHautBas=True)

            if Increment:

                if e.type == pygame.KEYDOWN and e.mod & pygame.KMOD_CTRL:
                    # aller directement au debut / fin de la liste
                    self.maj_selection(0 if Increment < 0 else -1)

                else:
                    self.maj_selection(self.selection_index[-1] + Increment)

                maj_valeur = True

            elif e.type == pygame.KEYDOWN:

                if e.key in (pygame.K_PAGEUP, pygame.K_HOME):
                    self.maj_selection(0)
                    maj_valeur = True

                elif e.key in (pygame.K_PAGEDOWN, pygame.K_END):
                    self.maj_selection(-1)
                    maj_valeur = True

                elif e.key == pygame.K_DELETE:
                    # index negatif pour signifier l'effacage
                    self.valeur = [-index - 1 for index in self.selection_index]
                    raise SortieMenu()

                elif e.key == pygame.K_INSERT:
                    # renommage
                    champ_selec = self.champs[self.selection_index[-1]]
                    editeur = BoiteTexte(legende=['Renommer :'], defaut=champ_selec)
                    val = editeur.boucle()
                    if val:
                        self.champs[self.selection_index[-1]] = val

                else:

                    keyName = pygame.key.name(e.key)

                    if e.mod & pygame.KMOD_CTRL and e.key == pygame.K_a:
                        # tout selectionne
                        self.selection_index = range(len(self.champs))
                        maj_valeur = True

                    elif len(keyName) == 1:
                        # Selectionne l'entree commencant par la touche pressee

                        numChamps = len(self.champs)

                        for index in range(1, numChamps):

                            indexMod = (self.selection_index[-1] + index) % numChamps

                            Champ = self.champs[indexMod]
                            if isinstance(Champ, (list, tuple)):
                                NomChamp = Champ[0]
                            else:
                                NomChamp = Champ

                            if NomChamp.lower().startswith(keyName):
                                self.maj_selection(indexMod)
                                maj_valeur = True
                                break

        if maj_valeur:

            if self.valeur != self.selection_index:
                self.valeur = list(set(self.selection_index))

                nombChampsVisibles = self.nombChampsVisibles()

                if nombChampsVisibles < len(self.champs):
                    ref_index = self.selection_index[-1]
                    self.haut_index = ref_index - nombChampsVisibles / 2  # la selection se trouve au centre de l'ecran

        return maj_valeur

    def alafin(self):

        if not self.multi_selection and not self.forceListe:
            # Renvoie un seul index plutot qu'une liste
            if self.valeur:
                if isinstance(self.valeur, list):
                    self.valeur = self.valeur[0]

            else:
                self.valeur = None


class MenuOptions(InterfaceDeroulant, ElemInterface):
    """ Liste verticale d'options affichees en lignes de texte """

    def __init__(self, options, legende=[], pos=(0, 0), centre=True, forceListe=False, **kwargs):

        ElemInterface.__init__(self, pos, centre=centre, **kwargs)
        InterfaceDeroulant.__init__(self, options, legende, forceListe=forceListe)

        self.valeur = self.selection_index

        self.hauteur = len(self.champs) * self.fonte.get_height()

    def affiche(self, surf_dest):

        for i, ligne in enumerate(self.legende):
            self.affiche_ligne(surf_dest, ligne, i, centre=False)

        lignesLegende = len(self.legende)

        for j, option in enumerate(self.champs[self.haut_index:]):

            index = self.haut_index + j

            if index in self.selection_index:  # and len(self.champs) > 1:
                clr = self.couleur_texte_selec
            else:
                clr = self.couleur_texte

            self.affiche_ligne(surf_dest, option, lignesLegende + j, clr, centre=self.centre)


class BoiteMessage(ElemInterface):

    def __init__(self, lignes=('',), pos=(0, 0), **kwargs):
        ElemInterface.__init__(self, pos=pos, **kwargs)
        self.lignes = lignes

    def affiche(self, surface):
        for i, ligne in enumerate(self.lignes):
            self.affiche_ligne(surface, ligne, i)


def nom_touche(val):
    if val == pygame.K_SPACE:
        return ' '
    else:
        caractere = pygame.key.name(val)

        if len(caractere) > 1:
            # le nom des touches du pave numerique sont entre [] e.g. [0]
            return caractere.replace('[', '').replace(']', '')

        return caractere


def convertisseur(vieilVal, novVal):
    if isinstance(vieilVal, bool):

        return novVal.lower() == 'oui'

    elif vieilVal is None:

        if novVal == '':
            return None
        elif novVal.lower() == 'none':
            return eval(novVal)
        else:
            return novVal

    elif isinstance(vieilVal, (tuple, list)):

        if novVal == '':
            novVal = type(vieilVal)()  # sequence vide

        else:

            valeurs = []

            for i, val in enumerate(novVal.replace(',', ' ').split()):

                if len(vieilVal) > 0:
                    if i >= len(vieilVal):
                        oldI = -1
                    else:
                        oldI = i

                    val = convertisseur(vieilVal[oldI], val)

                valeurs.append(val)

            novVal = valeurs

    valType = type(vieilVal)

    if isinstance(novVal, (list, tuple)):
        if valType not in [list, tuple]:
            # cas des vect2d.Vec
            return type(vieilVal)(*novVal)

    return type(vieilVal)(novVal)


class ChampParent(ElemInterface):

    def __init__(self, valeur, legende=[''], AligneDroit=0, lectureSeule=False, valeur_multi=False, **kwargs):

        ElemInterface.__init__(self, **kwargs)

        self.legende = legende

        self.valeurInit = valeur
        if isinstance(self.valeur, (list, tuple)):
            self.valeur = copy.copy(self.valeurInit)
        else:
            self.valeur = valeur

        self.valeur_multi = self.valeur_multi_init = valeur_multi

        self.val_temp = None
        self.modifiable = not lectureSeule
        self.aligne_droit = AligneDroit
        self.curseur_pos = 0  # position depuis la droite

    def __str__(self):
        return self.__class__.__name__, self.legende[0]

    def EstModifie(self):
        return self.val_temp is not None or self.valeurInit != self.valeur or self.valeur_multi != self.valeur_multi_init

    def valide(self):

        if self.val_temp is not None:

            try:

                self.valeur = convertisseur(self.valeur, self.val_temp)
                self.valeur_multi = False
                self.val_temp = None

            except:
                print('echec de conversion', self.val_temp, self.valeur)
                import traceback
                traceback.print_exc()
                pass

    def alafin(self):
        pass

    def __valAff__(self):
        """ Convertit la valeur en caracteres a afficher """

        if self.val_temp is not None:
            valAff = self.val_temp

        elif self.valeur is True:
            valAff = 'Oui'

        elif self.valeur is False:
            valAff = 'Non'
        # elif self.valeur is None:
        #    valAff = ''

        elif isinstance(self.valeur, type):
            valAff = self.valeur.__name__

        elif isinstance(self.valeur, (tuple, list)):
            valAff = ', '.join('%.2f' % Val if isinstance(Val, float) else str(Val) for Val in self.valeur)

        elif isinstance(self.valeur, float):
            valAff = '%.2f' % self.valeur

        else:
            valAff = str(self.valeur)

        return valAff

    def affiche(self, surface, index_decal=0):

        for i, ligne in enumerate(self.legende):
            if self.aligne_droit:
                ligne = ligne.rjust(self.aligne_droit)

            tailleL = self.affiche_ligne(surface, ligne, index_ligne=i + index_decal)[0]

        valAff = self.__valAff__()

        if hasattr(self, 'choix'):
            valAff = '<' + valAff + '>'

        elif self.modifiable:
            # Ajout du curseur
            index = len(valAff) - self.curseur_pos
            valAff = valAff[:index] + '|' + valAff[index:]

        if self.valeur_multi:
            valAff = '                           <diff>  ' + valAff

        self.affiche_ligne(surface, valAff, index_ligne=i + index_decal, decalage=[15 + tailleL, 0])


def IncrementeUnReel(valeur, increment, minZero=.01, facteur=1.1):
    if valeur:
        valeur *= facteur if (increment == 1) ^ (valeur < 0) else 1. / facteur
        if abs(valeur) < minZero:
            return 0.
        return valeur
    else:
        return minZero * increment


class BoiteTexte(ChampParent):

    def __init__(self, legende='', defaut='', pos=(0, 0), centre=False, **kwargs):

        ChampParent.__init__(self, defaut, legende=legende, pos=pos, centre=centre, **kwargs)

    def mettre_a_jour(self, e):

        if not self.modifiable:
            return

        Increment = IncrementPourEvent(e, flechesHautBas=False)

        if Increment and e.type == pygame.MOUSEBUTTONDOWN:
            # Incrementation de valeurs numeriques a la molette

            if self.val_temp:
                self.valide()

            if isinstance(self.valeur, int):
                self.valeur += Increment
                self.valeur_multi = False

            elif isinstance(self.valeur, float):
                self.valeur = IncrementeUnReel(self.valeur, Increment)
                self.valeur_multi = False

            elif isinstance(self.valeur, (list, tuple)):

                for i, val in enumerate(self.valeur):

                    if isinstance(val, int):
                        self.valeur[i] += Increment
                        self.valeur_multi = False

                    elif isinstance(val, float):
                        self.valeur[i] = IncrementeUnReel(self.valeur[i], Increment)
                        self.valeur_multi = False

        elif e.type == pygame.KEYDOWN:

            novVal = None

            if e.key in (pygame.K_KP_ENTER, pygame.K_RETURN, pygame.K_UP, pygame.K_DOWN):
                # Validation de ce qu'entre l'utilisateur
                self.valide()

            if Increment:
                # Deplacement du curseur

                valAff = self.__valAff__()
                valAffLon = len(valAff)

                self.curseur_pos += Increment

                if e.mod & pygame.KMOD_CTRL:
                    # saute d'un separateur a l'autre ou bien en bout de chaine si aucun separateur n'est trouve.

                    indexGauche = valAffLon - 1 - self.curseur_pos

                    if Increment > 0:
                        # recherche depuis la droite, curseur se deplace vers la gauche.
                        indexes = [valAff.rfind(car, 0, indexGauche) for car in '., ']
                        indexes = [index for index in indexes if index > -1]

                        indexGauche = max(indexes) if indexes else 0

                    else:
                        # recherche depuis la gauche

                        indexes = [valAff.find(car, indexGauche) for car in '., ']
                        indexes = [index for index in indexes if index > -1]

                        indexGauche = min(indexes) if indexes else valAffLon - 1

                    self.curseur_pos = valAffLon - 1 - indexGauche

                if valAffLon:
                    self.curseur_pos %= valAffLon
                else:
                    self.curseur_pos = 0

            elif e.key == pygame.K_BACKSPACE:

                if e.mod & pygame.KMOD_CTRL:
                    # efface le champ entier.
                    novVal = ''
                else:
                    novVal = self.__valAff__()
                    DelIndex = len(novVal) - self.curseur_pos

                    novVal = novVal[:DelIndex - 1] + novVal[DelIndex:]


            elif e.key == pygame.K_DELETE:
                novVal = self.__valAff__()
                DelIndex = len(novVal) - self.curseur_pos
                self.curseur_pos -= 1
                self.curseur_pos = max(self.curseur_pos, 0)
                novVal = novVal[:DelIndex] + novVal[DelIndex + 1:]

            else:

                val = e.unicode

                if len(val) == 1:
                    # Maj = e.mod & ( pygame.KMOD_SHIFT | pygame.KMOD_CAPS )

                    # if Maj:
                    #    val = val.upper()

                    novVal = self.__valAff__()
                    index = len(novVal) - self.curseur_pos
                    novVal = novVal[:index] + val + novVal[index:]

            if novVal is not None:
                self.val_temp = novVal


class ChampChoix(ChampParent):

    def __init__(self, valeur, choix=[True, False], alpha_fond=100, **kwargs):

        ChampParent.__init__(self, valeur, alpha_fond=alpha_fond, **kwargs)
        self.choix = choix
        self.bouton_validation = 2  # bouton souris pour valider les changements / la selection

    def mettre_a_jour(self, e):

        if self.modifiable:

            if e.type == pygame.MOUSEBUTTONDOWN and e.button == 1:
                Increment = 1
            else:
                Increment = IncrementPourEvent(e)

            if Increment:

                if self.valeur not in self.choix:
                    self.valeur = self.choix[0]
                    self.valeur_multi = False

                else:

                    if e.type == pygame.KEYDOWN and e.mod & pygame.KMOD_CTRL:
                        # aller directement au debut / fin de la liste
                        Index = 0 if Increment < 0 else -1
                    else:
                        Index = self.choix.index(self.valeur) + Increment

                    nombChoix = len(self.choix)
                    self.valeur = self.choix[Index % nombChoix]
                    self.valeur_multi = False


            elif e.type == pygame.KEYDOWN:
                # Choix qui commence par la touche frappee

                val = e.unicode

                for premiereLettre in val, val.lower():

                    for ch in self.choix:
                        if ch != self.valeur and str(ch).startswith(premiereLettre):
                            self.valeur = ch
                            self.valeur_multi = False
                            break
                    else:
                        continue

                    break


def IncrementPourEvent(e, flechesHautBas=False):
    if e.type == pygame.KEYDOWN:

        if flechesHautBas and e.key in (pygame.K_UP, pygame.K_DOWN):
            return -1 if e.key == pygame.K_UP else 1

        elif not flechesHautBas and e.key in (pygame.K_LEFT, pygame.K_RIGHT):
            return -1 if e.key == pygame.K_RIGHT else 1

    elif e.type == pygame.MOUSEBUTTONDOWN and e.button in (4, 5):

        return -1 if e.button == 4 else 1

    elif e.type in (pygame.JOYHATMOTION, pygame.JOYAXISMOTION):

        valueY = None

        if e.type == pygame.JOYHATMOTION:
            valueY = -e.value[1]

        elif e.axis % 2:  # suppose que les axes verticaux sont impairs
            valueY = e.value

        if valueY:
            if round(valueY) == 1:
                return 1
            elif round(valueY) == -1:
                return -1


class ChampNomMonde(BoiteTexte):
    """ validation du nom des mondes """

    def mettre_a_jour(self, e):

        vieilleVal = self.val_temp

        BoiteTexte.mettre_a_jour(self, e)

        if self.val_temp:
            for c in self.val_temp:
                if not (c.isalnum() or c in ' =-_'):
                    self.val_temp = vieilleVal
                    break
