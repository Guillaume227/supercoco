'''
Created on 20 Feb 2014

@author: Guiche
'''

'''
Created on 16 Aug 2012

@author: Zarastro
'''

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


def ListeRepertoire(Repertoire, Suffixe=''):
    return [fileName.split('.')[0] for fileName in os.listdir(Repertoire) if not Suffixe or fileName.endswith(Suffixe)]


def SelectDansRepertoire(Repertoire, Suffixe='', defaut='', Legende=None, choixNouveau=True, valideExistant=True,
                         Effacable=False):
    Choix = ListeRepertoire(Repertoire, Suffixe)

    Res = SelectObjet(defaut=defaut, legende=Legende, liste=Choix, choixNouveau=choixNouveau,
                      valideExistant=valideExistant, Effacable=Effacable)

    if Res:

        Selection, AEffacer = Res

        for NomFichier in AEffacer:
            Effacer(NomFichier + Suffixe, Repertoire)

        return Selection


def SelectObjet(defaut='', liste=[], legende=None, choixNouveau=True, valideExistant=True, Effacable=False):
    choix = list(liste)

    if choixNouveau:
        choix = ['*Nouveau*'] + choix

    if not choix:
        menu.BoiteMessage(lignes=['Rien a choisir.'], pos=(40, 100), alpha_fond=200).boucle()
        return

    if legende is None:
        legende = 'Choisir :'
    else:
        legende = Legende

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

                    if Effacable:
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

                    if valideExistant and monde in choix:

                        if menu.ChampChoix(False, legende=['%s existe deja.' % monde, " ecraser l'existant ?."],
                                           pos=(200, 100)).boucle():
                            return monde, a_effacer

                        elif choix[Index] == nouvelle_entree:
                            continue

                        else:
                            break

                    return monde, []


def Effacer(nom, sauve_dir):
    fichier = os.path.join(sauve_dir, nom)
    print
    'effacage de', fichier
    os.remove(fichier)


def Sauvegarde(Obj, nom='', FoncDialogue=False, suff='', sauve_dir='', copie=False, ablanc=False, throw=False,
               securite=True):
    nomFichier = nom

    if FoncDialogue:

        nomFichier = FoncDialogue(defaut=nomFichier, Legende='Sauver sous :')

        if not nomFichier:
            return

    assert nomFichier

    if not copie:
        Obj.nom = nomFichier

    filePath = os.path.join(os.getcwd(), sauve_dir, nomFichier + suff)

    if securite and not FoncDialogue and not nom.startswith(derniere_lancee) and 'efface' not in nom and os.path.exists(
            filePath):
        if not menu.ChampChoix(False, legende=['%s existe deja.' % nom, " ecraser l'existant ?."],
                               pos=(200, 100)).boucle():
            return

    import pygame

    if isinstance(Obj, pygame.Surface):

        pygame.image.save(Obj, filePath)

    else:
        try:

            dataStreamStr = pickle.dumps(Obj, protocol=2)

        except:
            if throw:
                raise
            else:
                traceback.print_exc()
                return False

        if ablanc:
            print
            'serialisation a blanc reussie pour : ', Obj

        else:

            try:

                fichierObj = open(filePath, 'wb')
                fichierObj.write(dataStreamStr)

                # sauvegarde reussie
                print
                'sauvegarde de', nomFichier
                return True

            except:
                if throw:
                    raise
                else:
                    traceback.print_exc()
                    return

            finally:
                fichierObj.close()


def loads(fileObj):
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

    unpickler = pickle.Unpickler(fileObj)
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


class Phenixable(object):
    """ Interface de serialisation
        pour prendre en compte automatiquement
        l'ajout, le renommage ou le retrait d'attributs.
    """
    __exc__state__ = []  # liste des attributs a exclure de la serialisation

    __attr_renomme__ = {}  # attributs a renommer. { vieux_nom : nouv_nom, ... }

    __attr_reinit__ = []  # attributs a reinitialiser. [ nom, ... ]

    def __setstate__(self, Dict):
        """ Deserialisation des elements.
        
            comparaison des attributs deserialises avec ceux aue l'on trouve dans une nouvelle instance de cette classe.
            
            Les attributs manquants dans l'ancienne version sont ajoutes avec la valeur par defaut.
            Les attributs manquants dans la nouvelle version sont juges obsoletes et sont elimines.
            
        """
        # print 'setstate',self.__class__.__name__
        self.__dict__ = Dict

        classe = type(self)
        nomClasse = classe.__module__ + '.' + classe.__name__

        try:

            newObj = classe()

        except Exception:
            print
            'Probleme pour instancier', nomClasse
            traceback.print_exc()
            return

        # Renommage d'attributs
        for argName in self.__attr_renomme__:
            if argName in self.__dict__:
                novArgName = self.__attr_renomme__[argName]
                self.__dict__[novArgName] = self.__dict__.pop(argName)

        # Reinitialization d'attributs
        for argName in self.__attr_reinit__:
            if argName in self.__dict__ and hasattr(newObj, argName):
                novVal = getattr(newObj, argName)
                ancVal = self.__dict__[argName]
                if novVal != ancVal:
                    print
                    'reinit', argName, ancVal, '->', novVal
                self.__dict__[argName] = novVal

        keys = list(self.__dict__.keys())

        # Ajout de nouveaux attributs trouves dans une nouvelle instanciation de la classe
        novAttrs = []
        for argName in newObj.__dict__:
            if argName not in self.__dict__:
                self.__dict__[argName] = newObj.__dict__[argName]
                novAttrs.append(argName)

        for argName in novAttrs:
            if argName not in self.__exc__state__:
                print
                nomClasse, self, '  ajout : ', argName

        # Retrait d'attributs (ceux qui ne sont pas trouves dans une nouvelle instanciation de la classe)
        for argName in keys:

            # Conversion des sauvegardees comme instances en leur type.

            # Elimination des attributs trouves dans une l'ancienne version mais pas dans la nouvelle.
            if argName not in newObj.__dict__:
                print
                nomClasse, self, 'retrait : ', argName
                self.__dict__.pop(argName)

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

    print
    print
    'Resauve mondes de', dossier

    for fichier in os.listdir(dossier):

        if fichier not in ['.svn']:

            print

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
