"""
Created on 16 Aug 2012

@author: Zarastro
"""

import pickle
import traceback
import os
import sys
from . import menu

rep_racine = os.path.dirname(os.path.abspath(sys.argv[0]))
DOSSIER_SAUVEGARDES = 'sauvegardes'
DOSSIER_IMAGES = 'images'
SAUVE_REP = os.path.normpath(os.path.join(rep_racine, DOSSIER_SAUVEGARDES))
IMAGE_REP = os.path.normpath(os.path.join(rep_racine, DOSSIER_IMAGES))
SUFF_PARTIE = '.par'
SUFF_RESEAU = '.res'

derniere_lancee = '__derniere_lancee__'
nouvelle_entree = '*Nouveau*'


def ListeRepertoire(repertoire, suffixe=''):
    return [fileName.split('.')[0] for fileName in os.listdir(repertoire) if not suffixe or fileName.endswith(suffixe)]


def SelectDansRepertoire(repertoire, suffixe='', defaut='', legende=None, choix_nouveau=True, valide_existant=True,
                         effacable=False):
    choix = ListeRepertoire(repertoire, suffixe)

    res = SelectObjet(defaut=defaut, legende=legende, liste=choix, choix_nouveau=choix_nouveau,
                      valide_existant=valide_existant, effacable=effacable)

    if res:
        selection, a_effacer = res

        for nom_fichier in a_effacer:
            Effacer(nom_fichier + suffixe, repertoire)

        return selection


def SelectObjet(defaut='', liste=(), legende=None, choix_nouveau=True, valide_existant=True, effacable=False):
    choix = list(liste)

    if choix_nouveau:
        choix = ['*Nouveau*'] + choix

    if not choix:
        menu.BoiteMessage(lignes=['Rien a choisir.'], pos=(40, 100), alpha_fond=200).boucle()
        return

    if legende is None:
        legende = 'Choisir :'

    menu_choix = menu.MenuOptions(choix, legende=[legende], pos=(5, 5), centre=False, force_liste=True)

    a_effacer = []

    while True:

        liste_d_index = menu_choix.boucle()

        if liste_d_index is None:
            return None, a_effacer

        else:

            while True:

                if all(Index < 0 for Index in liste_d_index):

                    mondes = [choix[-(Index + 1)] for Index in liste_d_index]

                    if effacable:
                        if menu.ChampChoix(False, legende=['Effacer %s ?' % (', '.join(mondes))],
                                           pos=(200, 100)).boucle():
                            for monde in mondes:
                                a_effacer.append(monde)
                                choix.remove(monde)

                            return None, a_effacer

                    break

                else:

                    mondes = [choix[Index] for Index in liste_d_index]

                    if len(liste_d_index) != 1 or any(Index < 0 for Index in liste_d_index):
                        # Trop de choix
                        break

                    monde = mondes[0]

                    if monde == nouvelle_entree:

                        monde = menu.ChampNomMonde(legende=['Nom du nouveau :'], defaut=defaut, pos=(40, 100),
                                                   alpha_fond=200).boucle()

                        if monde is None:
                            break

                    if valide_existant and monde in choix:

                        if menu.ChampChoix(False, legende=['%s existe deja.' % monde, " ecraser l'existant ?."],
                                           pos=(200, 100)).boucle():
                            return monde, a_effacer

                        elif choix[Index] == nouvelle_entree:
                            continue

                        else:
                            break

                    return monde, []


def Effacer(nom, sauve_dir):
    chemin_fichier = os.path.join(sauve_dir, nom)
    print('effacage de', chemin_fichier)
    os.remove(chemin_fichier)


def Sauvegarde(Obj, nom='', fonc_dialogue=None, suff='', sauve_dir='', copie=False, ablanc=False, throw=False,
               securite=True):
    nom_fichier = nom

    if fonc_dialogue is not None:

        nom_fichier = fonc_dialogue(defaut=nom_fichier, Legende='Sauver sous :')

        if not nom_fichier:
            return

    assert nom_fichier

    if not copie:
        Obj.nom = nom_fichier

    file_path = os.path.join(os.getcwd(), sauve_dir, nom_fichier + suff)

    if securite and fonc_dialogue is not None and not nom.startswith(derniere_lancee) and 'efface' not in nom and os.path.exists(
            file_path):
        if not menu.ChampChoix(False, legende=['%s existe deja.' % nom, " ecraser l'existant ?."],
                               pos=(200, 100)).boucle():
            return

    import pygame

    if isinstance(Obj, pygame.Surface):

        pygame.image.save(Obj, file_path)

    else:
        try:

            data_stream_str = pickle.dumps(Obj, protocol=2)

        except:
            if throw:
                raise
            else:
                traceback.print_exc()
                return False

        if ablanc:
            print('serialisation a blanc reussie pour : ', Obj)
        else:
            try:
                fichier_obj = open(file_path, 'wb')
                fichier_obj.write(data_stream_str)

                # sauvegarde reussie
                print('sauvegarde de', nom_fichier)
                return True

            except:
                if throw:
                    raise
                else:
                    traceback.print_exc()
                    return

            finally:
                fichier_obj.close()


def loads(file_obj):
    """ Deserialisation prennant en compte le changement d'un nom de module.
    """

    def mapname(name):
        return {'Mobile': 'EtreAnime',
                }.get(name, name)
        # return name.replace('vieux_module', 'nouveau_module')

    def mapped_load_global(self):
        module = mapname(self.readline()[:-1])
        name = mapname(self.readline()[:-1])
        klass = self.find_class(module, name)
        self.append(klass)

    unpickler = pickle.Unpickler(file_obj)
    unpickler.dispatch[pickle.GLOBAL] = mapped_load_global
    return unpickler.load()


def ouvrir_monde(nom, dossier='', suffixe=''):
    if dossier:
        chemin_fichier = os.path.join(dossier, nom)
    else:
        chemin_fichier = nom

    if suffixe:
        chemin_fichier += suffixe

    nom = os.path.basename(chemin_fichier)
    print('Ouverture  de', nom)

    with open(chemin_fichier, 'rb') as f:
        monde_obj = loads(f)
        monde_obj.nom = nom.split('.')[0]
        return monde_obj


class Phenixable:
    """ Interface de serialisation
        pour prendre en compte automatiquement
        l'ajout, le renommage ou le retrait d'attributs.
    """
    __exc__state__ = []  # liste des attributs a exclure de la serialisation

    __attr_renomme__ = {}  # attributs a renommer. { vieux_nom : nouv_nom, ... }

    __attr_reinit__ = []  # attributs a reinitialiser. [ nom, ... ]

    def __setstate__(self, dict_vals):
        """ Deserialisation des elements.
        
            comparaison des attributs deserialises avec ceux aue l'on trouve dans une nouvelle instance de cette classe.
            
            Les attributs manquants dans l'ancienne version sont ajoutes avec la valeur par defaut.
            Les attributs manquants dans la nouvelle version sont juges obsoletes et sont elimines.
            
        """
        # print 'setstate',self.__class__.__name__
        self.__dict__ = dict_vals

        classe = type(self)
        nom_classe = classe.__module__ + '.' + classe.__name__

        try:

            new_obj = classe()

        except Exception:
            print('Probleme pour instancier', nom_classe)
            traceback.print_exc()
            return

        # Renommage d'attributs
        for arg_name in self.__attr_renomme__:
            if arg_name in self.__dict__:
                nov_arg_name = self.__attr_renomme__[arg_name]
                self.__dict__[nov_arg_name] = self.__dict__.pop(arg_name)

        # Reinitialization d'attributs
        for arg_name in self.__attr_reinit__:
            if arg_name in self.__dict__ and hasattr(new_obj, arg_name):
                nov_val = getattr(new_obj, arg_name)
                anc_val = self.__dict__[arg_name]
                if nov_val != anc_val:
                    print('reinit', arg_name, anc_val, '->', nov_val)
                self.__dict__[arg_name] = nov_val

        keys = list(self.__dict__.keys())

        # Ajout de nouveaux attributs trouves dans une nouvelle instanciation de la classe
        nov_attrs = []
        for arg_name in new_obj.__dict__:
            if arg_name not in self.__dict__:
                self.__dict__[arg_name] = new_obj.__dict__[arg_name]
                nov_attrs.append(arg_name)

        for arg_name in nov_attrs:
            if arg_name not in self.__exc__state__:
                print(nom_classe, self, '  ajout : ', arg_name)

        # Retrait d'attributs (ceux qui ne sont pas trouves dans une nouvelle instanciation de la classe)
        for arg_name in keys:

            # Conversion des sauvegardees comme instances en leur type.

            # Elimination des attributs trouves dans une l'ancienne version mais pas dans la nouvelle.
            if arg_name not in new_obj.__dict__:
                print(nom_classe, self, 'retrait : ', arg_name)
                self.__dict__.pop(arg_name)

    def __getstate__(self):

        dico = self.__dict__.copy()

        for attri in self.__exc__state__:

            if attri in dico:
                dico.pop(attri)

        return dico


class SauvegardeAutoExc(Exception):
    """ Exception qui prend une copie d'un objet en le serialisant a sa creation
        pour pouvoir le reinstancier plus tard.
    """

    def __init__(self, Obj):
        self.__donnees = pickle.dumps(Obj, protocol=2)

    def Ressuscite(self):
        return loads(self.__donnees)


def Resauve(dossier, suff='', bavard=True, ecrase=False):
    """ Resauve tous les objets serialises trouve dans un certain dossier.
        suff : filtre les fichiers par suffixe.
    """

    print()
    print('Resauve mondes de', dossier)

    for fichier in os.listdir(dossier):

        if fichier not in ['.svn']:

            print()

            if not suff or fichier.endswith(suff):
                Obj = Ouvrir(nom=fichier, dossier=dossier)
                Sauvegarde(Obj=Obj, nom=fichier, sauve_dir=dossier, ablanc=not ecrase, securite=False, throw=True)


def main():
    # Resauvegarde toutes les parties (pour rafraichir les attributs manquants/obsoletes)
    dossier = os.path.join(os.path.dirname(os.path.dirname(__file__)), DOSSIER_SAUVEGARDES)
    Resauve(dossier=dossier, ecrase=True)


# this calls the 'main' function when this script is executed
if __name__ == '__main__':
    main()
