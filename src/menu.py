#! /usr/bin/env python
from __future__ import print_function
from __future__ import absolute_import
import pygame
from . import media
import copy


class SortieMenu(Exception):
    pass


class ElemInterface:

    def __init__(self, pos=(0, 0), fonte_h=16, centre=True, alpha_fond=50, img_fond=True, lecture_seule=False):

        self.pos = pos
        self.fonte = pygame.font.Font(media.cheminFichier(media.FONTE_DEFAUT, subdir='fonts'), fonte_h)
        self.fonte_h = fonte_h
        self.interligne = 4
        self.couleur_texte = [255, 255, 255]
        self.couleur_texte_selec = [255, 0, 0]
        self.valeur = None
        self.alpha = 150
        self.hauteur = 0
        self.centre = centre

        self.modifiable = not lecture_seule

        self.bouton_validation = 1  # bouton souris pour valider les changements / la selection
        self.bouton_anulation = 3  # bouton souris pour annuler les changements / la selection

        # i.e. l'intervalle de temps au bout du quel une touche enfoncee
        # envoie un nouvel evenement de pression.
        self.repetition_clavier = 200, 100

        self.surface_dest = pygame.display.get_surface()

        if img_fond:
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

        repetition_ext = pygame.key.get_repeat()
        pygame.key.set_repeat(*self.repetition_clavier)
        self.repetition_clavier = repetition_ext

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
                            return self.alafin()

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
        return self.valeur


class InterfaceDeroulant:
    """
        propriete de defilement des champs d'un menu sous forme de liste dont la longeur excede la hauteur de l'ecran.
    """

    def __init__(self, options, legende, multi_selection=False, editable=True, force_liste=False):
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
        self.force_liste = force_liste

    @property
    def haut_index(self):
        """ index dans self.champs du premier element affiche en haut de l'ecran """
        return self._haut_index

    @haut_index.setter
    def haut_index(self, Val):
        nomb_champs = len(self.champs)
        nomb_champs_visibles = self.nombChampsVisibles()
        self._haut_index = min(max(0, Val), nomb_champs - nomb_champs_visibles)

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

            Increment = increment_pour_event(e, fleches_haut_bas=True)

            if Increment:
                self.haut_index = self.haut_index + Increment

            self.maj_selection(self.pos_index(pygame.mouse.get_pos()))

        elif e.type == pygame.MOUSEMOTION:
            # Positionnement absolu en suivant le curseur de la souris.
            self.maj_selection(self.pos_index(e.pos))
            # maj_valeur = True

        else:

            Increment = increment_pour_event(e, fleches_haut_bas=True)

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

                nomb_champs_visibles = self.nombChampsVisibles()

                if nomb_champs_visibles < len(self.champs):
                    ref_index = self.selection_index[-1]
                    self.haut_index = ref_index - nomb_champs_visibles // 2  # la selection se trouve au centre de l'ecran

        return maj_valeur

    def alafin(self):

        if not self.multi_selection and not self.force_liste:
            # Renvoie un seul index plutot qu'une liste
            if self.valeur:
                if isinstance(self.valeur, list):
                    return self.valeur[0]

            else:
                return None


class MenuOptions(InterfaceDeroulant, ElemInterface):
    """ Liste verticale d'options affichees en lignes de texte """

    def __init__(self, options, legende=(), pos=(0, 0), centre=True, force_liste=False, **kwargs):

        ElemInterface.__init__(self, pos, centre=centre, **kwargs)
        InterfaceDeroulant.__init__(self, options, legende, force_liste=force_liste)

        self.valeur = self.selection_index

        self.hauteur = len(self.champs) * self.fonte.get_height()

    def affiche(self, surf_dest):

        for i, ligne in enumerate(self.legende):
            self.affiche_ligne(surf_dest, ligne, i, centre=False)

        lignes_legende = len(self.legende)

        for j, option in enumerate(self.champs[self.haut_index:]):

            index = self.haut_index + j

            if index in self.selection_index:  # and len(self.champs) > 1:
                clr = self.couleur_texte_selec
            else:
                clr = self.couleur_texte

            self.affiche_ligne(surf_dest, option, lignes_legende + j, clr, centre=self.centre)


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


def convertisseur(vieil_val, nov_val):
    if isinstance(vieil_val, bool):

        return nov_val.lower() == 'oui'

    elif vieil_val is None:

        if nov_val == '':
            return None
        elif nov_val.lower() == 'none':
            return eval(nov_val)
        else:
            return nov_val

    elif isinstance(vieil_val, (tuple, list)):

        if nov_val == '':
            nov_val = type(vieil_val)()  # sequence vide

        else:

            valeurs = []

            for i, val in enumerate(nov_val.replace(',', ' ').split()):

                if len(vieil_val) > 0:
                    if i >= len(vieil_val):
                        oldI = -1
                    else:
                        oldI = i

                    val = convertisseur(vieil_val[oldI], val)

                valeurs.append(val)

            nov_val = valeurs

    val_type = type(vieil_val)

    if isinstance(nov_val, (list, tuple)):
        if val_type not in [list, tuple]:
            # cas des vect2d.Vec
            return type(vieil_val)(*nov_val)

    return type(vieil_val)(nov_val)


class ChampParent(ElemInterface):

    def __init__(self, valeur, legende=('',), AligneDroit=0, lecture_seule=False, valeur_multi=False, **kwargs):

        ElemInterface.__init__(self, **kwargs)

        self.legende = legende

        self.valeurInit = valeur
        if isinstance(self.valeur, (list, tuple)):
            self.valeur = copy.copy(self.valeurInit)
        else:
            self.valeur = valeur

        self.valeur_multi = self.valeur_multi_init = valeur_multi

        self.val_temp = None
        self.modifiable = not lecture_seule
        self.aligne_droit = AligneDroit
        self.curseur_pos = 0  # position depuis la droite

    def __str__(self):
        return self.__class__.__name__, self.legende[0]

    def est_modifie(self):
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

    def __valAff__(self):
        """ Convertit la valeur en caracteres a afficher """

        if self.val_temp is not None:
            val_aff = self.val_temp

        elif self.valeur is True:
            val_aff = 'Oui'

        elif self.valeur is False:
            val_aff = 'Non'
        # elif self.valeur is None:
        #    val_aff = ''

        elif isinstance(self.valeur, type):
            val_aff = self.valeur.__name__

        elif isinstance(self.valeur, (tuple, list)):
            val_aff = ', '.join('%.2f' % val if isinstance(val, float) else str(val) for val in self.valeur)

        elif isinstance(self.valeur, float):
            val_aff = '%.2f' % self.valeur

        else:
            val_aff = str(self.valeur)

        return val_aff

    def affiche(self, surface, index_decal=0):

        for i, ligne in enumerate(self.legende):
            if self.aligne_droit:
                ligne = ligne.rjust(self.aligne_droit)

            taille_l = self.affiche_ligne(surface, ligne, index_ligne=i + index_decal)[0]

        val_aff = self.__valAff__()

        if hasattr(self, 'choix'):
            val_aff = '<' + val_aff + '>'

        elif self.modifiable:
            # Ajout du curseur
            index = len(val_aff) - self.curseur_pos
            val_aff = val_aff[:index] + '|' + val_aff[index:]

        if self.valeur_multi:
            val_aff = '                           <diff>  ' + val_aff

        self.affiche_ligne(surface, val_aff, index_ligne=i + index_decal, decalage=[15 + taille_l, 0])


def incremente_un_reel(valeur, increment, minZero=.01, facteur=1.1):
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

        increment = increment_pour_event(e, fleches_haut_bas=False)

        if increment and e.type == pygame.MOUSEBUTTONDOWN:
            # Incrementation de valeurs numeriques a la molette

            if self.val_temp:
                self.valide()

            if isinstance(self.valeur, int):
                self.valeur += increment
                self.valeur_multi = False

            elif isinstance(self.valeur, float):
                self.valeur = incremente_un_reel(self.valeur, increment)
                self.valeur_multi = False

            elif isinstance(self.valeur, (list, tuple)):

                for i, val in enumerate(self.valeur):

                    if isinstance(val, int):
                        self.valeur[i] += increment
                        self.valeur_multi = False

                    elif isinstance(val, float):
                        self.valeur[i] = incremente_un_reel(self.valeur[i], increment)
                        self.valeur_multi = False

        elif e.type == pygame.KEYDOWN:

            nov_val = None

            if e.key in (pygame.K_KP_ENTER, pygame.K_RETURN, pygame.K_UP, pygame.K_DOWN):
                # Validation de ce qu'entre l'utilisateur
                self.valide()

            if increment:
                # Deplacement du curseur

                val_aff = self.__valAff__()
                val_aff_lon = len(val_aff)

                self.curseur_pos += increment

                if e.mod & pygame.KMOD_CTRL:
                    # saute d'un separateur a l'autre ou bien en bout de chaine si aucun separateur n'est trouve.

                    index_gauche = val_aff_lon - 1 - self.curseur_pos

                    if increment > 0:
                        # recherche depuis la droite, curseur se deplace vers la gauche.
                        indexes = [val_aff.rfind(car, 0, index_gauche) for car in '., ']
                        indexes = [index for index in indexes if index > -1]

                        index_gauche = max(indexes) if indexes else 0

                    else:
                        # recherche depuis la gauche

                        indexes = [val_aff.find(car, index_gauche) for car in '., ']
                        indexes = [index for index in indexes if index > -1]

                        index_gauche = min(indexes) if indexes else val_aff_lon - 1

                    self.curseur_pos = val_aff_lon - 1 - index_gauche

                if val_aff_lon:
                    self.curseur_pos %= val_aff_lon
                else:
                    self.curseur_pos = 0

            elif e.key == pygame.K_BACKSPACE:

                if e.mod & pygame.KMOD_CTRL:
                    # efface le champ entier.
                    nov_val = ''
                else:
                    nov_val = self.__valAff__()
                    DelIndex = len(nov_val) - self.curseur_pos

                    nov_val = nov_val[:DelIndex - 1] + nov_val[DelIndex:]

            elif e.key == pygame.K_DELETE:
                nov_val = self.__valAff__()
                DelIndex = len(nov_val) - self.curseur_pos
                self.curseur_pos -= 1
                self.curseur_pos = max(self.curseur_pos, 0)
                nov_val = nov_val[:DelIndex] + nov_val[DelIndex + 1:]

            else:

                val = e.unicode

                if len(val) == 1:
                    # Maj = e.mod & ( pygame.KMOD_SHIFT | pygame.KMOD_CAPS )

                    # if Maj:
                    #    val = val.upper()

                    nov_val = self.__valAff__()
                    index = len(nov_val) - self.curseur_pos
                    nov_val = nov_val[:index] + val + nov_val[index:]

            if nov_val is not None:
                self.val_temp = nov_val


class ChampChoix(ChampParent):

    def __init__(self, valeur, choix=(True, False), alpha_fond=100, **kwargs):

        ChampParent.__init__(self, valeur, alpha_fond=alpha_fond, **kwargs)
        self.choix = choix
        self.bouton_validation = 2  # bouton souris pour valider les changements / la selection

    def mettre_a_jour(self, e):

        if self.modifiable:

            if e.type == pygame.MOUSEBUTTONDOWN and e.button == 1:
                increment = 1
            else:
                increment = increment_pour_event(e)

            if increment:

                if self.valeur not in self.choix:
                    self.valeur = self.choix[0]
                    self.valeur_multi = False

                else:

                    if e.type == pygame.KEYDOWN and e.mod & pygame.KMOD_CTRL:
                        # aller directement au debut / fin de la liste
                        index = 0 if increment < 0 else -1
                    else:
                        index = self.choix.index(self.valeur) + increment

                    nomb_choix = len(self.choix)
                    self.valeur = self.choix[index % nomb_choix]
                    self.valeur_multi = False

            elif e.type == pygame.KEYDOWN:
                # Choix qui commence par la touche frappee

                val = e.unicode

                for premiere_lettre in val, val.lower():

                    for ch in self.choix:
                        if ch != self.valeur and str(ch).startswith(premiere_lettre):
                            self.valeur = ch
                            self.valeur_multi = False
                            break
                    else:
                        continue

                    break


def increment_pour_event(e, fleches_haut_bas=False):
    if e.type == pygame.KEYDOWN:

        if fleches_haut_bas and e.key in (pygame.K_UP, pygame.K_DOWN):
            return -1 if e.key == pygame.K_UP else 1

        elif not fleches_haut_bas and e.key in (pygame.K_LEFT, pygame.K_RIGHT):
            return -1 if e.key == pygame.K_RIGHT else 1

    elif e.type == pygame.MOUSEBUTTONDOWN and e.button in (4, 5):

        return -1 if e.button == 4 else 1

    elif e.type in (pygame.JOYHATMOTION, pygame.JOYAXISMOTION):

        value_y = None

        if e.type == pygame.JOYHATMOTION:
            value_y = -e.value[1]

        elif e.axis % 2:  # suppose que les axes verticaux sont impairs
            value_y = e.value

        if value_y:
            if round(value_y) == 1:
                return 1
            elif round(value_y) == -1:
                return -1


class ChampNomMonde(BoiteTexte):
    """ validation du nom des mondes """

    def mettre_a_jour(self, e):

        vieille_val = self.val_temp

        BoiteTexte.mettre_a_jour(self, e)

        if self.val_temp:
            for c in self.val_temp:
                if not (c.isalnum() or c in ' =-_'):
                    self.val_temp = vieille_val
                    break


def EditFields(item):
    import inspect

    props = [name for name, memberType in inspect.getmembers(type(item)) if isinstance(memberType, property)]

    stripped_props = set(propname.strip('_') for propname in props)

    memberVars = [arg for arg in vars(item) if arg.strip('_') not in stripped_props]

    return sorted(memberVars + props)


def getVal(elem, AttrName):
    valeur = getattr(elem, AttrName)
    if callable(valeur):
        import inspect
        if not inspect.isclass(valeur):
            valeur = valeur()

    return valeur


class EditeurElem(ElemInterface, InterfaceDeroulant):

    def __init__(self, elems, pos=(10, 10), attributs=None, choixPourChamps={}, filtre_=False, **kwargs):

        ElemInterface.__init__(self, pos=pos, **kwargs)

        self.elems = list(elems)

        self.modifie = False

        legende = 'Edition de '

        if len(elems) == 1:
            legende += '%s' % str(self.elems[-1])
        else:
            legende += '%d  %s' % (len(self.elems), type(self.elems[-1]).__name__)

        lignes_legende = [legende]
        self.bouton_validation = 2  # bouton souris pour valider les changements / la selection

        ref_elem = self.elems[0]

        if attributs is None:
            if hasattr(self.elems[0], '_champs_description_'):
                attr_editables = self.elems[0]._champs_description_
            else:
                attr_editables = EditFields(ref_elem)
        else:
            attr_editables = attributs

        self.choix_pour_champs = choixPourChamps

        nom_champs = []
        for AttrName in attr_editables:
            AttrName = AttrName.strip('_')

            nom_champs.append(AttrName)

        legend_long = [self.fonte.render(NomChamp, 1, self.couleur_texte).get_width() for NomChamp in nom_champs]
        max_l = max(legend_long)

        extra_args = dict(imgFond=False)

        ecart_ligne = self.ecart_ligne

        champs = []

        num_lignes_legende = len(lignes_legende)

        for i, (AttrName, NomChamp, LongChamp) in enumerate(zip(attr_editables, nom_champs, legend_long)):

            if filtre_ and AttrName[-1] != '_':
                continue

            valeur = getVal(self.elems[0], AttrName)

            valeur_multi = any(valeur != getVal(Elem, AttrName) for Elem in self.elems[1:])

            pos = self.pos[0] + max_l - LongChamp, self.pos[1] + (i + num_lignes_legende) * ecart_ligne

            extra_args['pos'] = pos
            extra_args['legende'] = [NomChamp]
            extra_args['lectureSeule'] = AttrName.endswith('__')
            extra_args['valeur_multi'] = valeur_multi
            extra_args['fonteH'] = self.fonteH

            if AttrName in self.choix_pour_champs:
                champ = ChampChoix(valeur, choix=self.choix_pour_champs[AttrName], **extra_args)

            elif hasattr(type(valeur), 'EnsembleValeurs'):
                champ = ChampChoix(valeur, choix=type(valeur).EnsembleValeurs, **extra_args)

            elif isinstance(valeur, bool):
                champ = ChampChoix(valeur, **extra_args)

            else:
                champ = BoiteTexte(defaut=valeur, **extra_args)

            champs.append((AttrName, champ))

        InterfaceDeroulant.__init__(self, champs, lignes_legende)

    def alafin(self):

        if len(self.elems) > 1:
            mods = pygame.key.get_mods()
            uniformiser = mods & pygame.KMOD_CTRL
        else:
            uniformiser = False

        attr_modifies = set()

        if uniformiser:
            print()
            print(f'Uniformisation de {len(self.elems)} {type(self.elems[0])}')

        else:

            for attr_name, champ in self.champs:

                if not champ.valeur_multi:
                    if any(champ.valeur != getVal(Elem, attr_name) for Elem in self.elems):
                        attr_modifies.add(attr_name)

            if attr_modifies and len(self.elems) > 1:
                print('Champs Modifies :', '\n'.join(attr_modifies))

        for attr_name, champ in self.champs:

            if uniformiser or attr_name in attr_modifies:

                for elem in self.elems:

                    vieilVal = getattr(elem, attr_name)
                    novVal = champ.valeur

                    if vieilVal != novVal:

                        print('Modif %s.%s %s ->' % (elem, attr_name, vieilVal))

                        if not hasattr(type(novVal), 'EnsembleValeurs'):
                            try:
                                novVal = copy.copy(novVal)
                            except:
                                pass

                        setattr(elem, attr_name, novVal)

                        print(getattr(elem, attr_name))

                        self.modifie = True

    def affiche(self, surface):

        for i, ligne in enumerate(self.legende):
            self.affiche_ligne(surface, ligne, i)

        for j, (_AttrName, champ) in enumerate(self.champs[self.haut_index:]):

            index = self.haut_index + j

            if index in self.selection_index:
                champ.couleur_texte = self.couleur_texte_selec
                if self.modifiable and champ.modifiable is None:
                    champ.modifiable = True
            else:
                champ.couleur_texte = self.couleur_texte
                if champ.modifiable:
                    champ.modifiable = None

            champ.affiche(surface, index_decal=-self.haut_index)

    def mettre_a_jour(self, e):

        if InterfaceDeroulant.mettre_a_jour(self, e):
            return True

        elif self.modifiable:

            increment = increment_pour_event(e, fleches_haut_bas=True)

            fonc_sous_champ = self.champs[self.selection_index[-1]][1].mettre_a_jour

            if increment:

                mods = pygame.key.get_mods()

                if mods & pygame.KMOD_CTRL or pygame.mouse.get_pressed()[1]:
                    # l'evenement s'applique au sous champ plutot qu'au defilement de la selection des sous-champs.
                    return fonc_sous_champ(e)

                else:
                    return False

            else:
                return fonc_sous_champ(e)

        return False
