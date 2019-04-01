"""
Created on 16 Aug 2012

@author: Zarastro
"""
from __future__ import print_function
from __future__ import absolute_import

import pickle
import os
import sys
from . import menu

nouvelle_entree = '*Nouveau*'


def ListeRepertoire(Repertoire, Suffixe=''):
    return [fileName.split('.')[0] for fileName in os.listdir(Repertoire) if not Suffixe or fileName.endswith(Suffixe)]


def SelectDansRepertoire(Repertoire, Suffixe='', defaut='', Legende=None, choixNouveau=True, valideExistant=True,
                         Effacable=False):
    Choix = ListeRepertoire(Repertoire, Suffixe)

    Res = SelectObjet(defaut=defaut, legende=Legende, liste=Choix, choixNouveau=choixNouveau,
                      valideExistant=valideExistant, Effacable=Effacable)

    if Res:
        Selection, _ = Res

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


def loads(fileObj):
    unpickler = pickle.Unpickler(fileObj)
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

    with open(chemin_fichier, 'rb') as f;
        monde_obj = loads(f)
        monde_obj.nom = nom.split('.')[0]
        return monde_obj
