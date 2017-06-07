'''
Created on 16 Aug 2012

@author: Zarastro
'''
from __future__ import print_function
from __future__ import absolute_import

import pickle 
import os
import sys
from . import menu

nouvelle_entree = '*Nouveau*'

def ListeRepertoire(Repertoire, Suffixe=''):
    return [ fileName.split('.')[0] for fileName in os.listdir(Repertoire) if not Suffixe or fileName.endswith(Suffixe) ]


def SelectDansRepertoire(Repertoire, Suffixe='', defaut='', Legende=None, choixNouveau=True, valideExistant=True, Effacable=False):

    Choix = ListeRepertoire(Repertoire, Suffixe) 

    Res = SelectObjet(defaut=defaut, Legende=Legende, liste=Choix, choixNouveau=choixNouveau, valideExistant=valideExistant, Effacable=Effacable)

    if Res:
        
        Selection, _ = Res
            
        return Selection
    

def SelectObjet(defaut='', liste=[], Legende=None, choixNouveau=True, valideExistant=True, Effacable=False):

    choix = list(liste)
    
    if choixNouveau:
        choix = ['*Nouveau*'] + choix 
    
    if not choix:
        menu.BoiteMessage( lignes=['Rien a choisir.'], pos=(40,100), alpha_fond=200).boucle()
        return
        
    if Legende is None:
        legende = 'Choisir :'
    else:
        legende = Legende
        
    menuChoix = menu.MenuOptions( choix, legende=[legende], pos=(5,5), centre=False, forceListe=True )
    
    AEffacer = []
    
    while True:
        
        Liste_d_Index = menuChoix.boucle()
            
        if Liste_d_Index is None:
            return None, AEffacer
        
        else:
        
            while True:
                
                if all(Index < 0 for Index in Liste_d_Index):
                    
                    Mondes = [ choix[-(Index+1)] for Index in Liste_d_Index ]
                    
                    if Effacable:
                        if menu.ChampChoix(False, legende=['Effacer %s ?'%(', '.join(Mondes))], pos=(200,100)).boucle():
                            for Monde in Mondes:
                                AEffacer.append( Monde )
                                choix.remove( Monde )
                                
                            return None, AEffacer
                    
                    break
                
                else:
                    
                    Mondes = [ choix[Index] for Index in Liste_d_Index ]
                    
                    if len(Liste_d_Index) != 1 or any(Index < 0 for Index in Liste_d_Index):
                        # Trop de choix
                        break
                    
                    Monde = Mondes[0]
                     
                    if Monde == nouvelle_entree:
                    
                        Monde = menu.ChampNomMonde( legende=['Nom du nouveau :'], defaut=defaut, pos=(40,100), alpha_fond=200).boucle()
                        
                        if Monde is None:
                            break
                    
                    
                    if valideExistant and Monde in choix:
                    
                        if menu.ChampChoix(False, legende=['%s existe deja.'%Monde," ecraser l'existant ?."], pos=(200,100)).boucle():
                            return Monde, AEffacer
                       
                        elif choix[Index] == nouvelle_entree:
                            continue
                       
                        else:
                            break
                            
                    return Monde, []
    
    

def loads(fileObj):
    
    unpickler = pickle.Unpickler(fileObj)
    return unpickler.load()


def Ouvrir(nom, dossier='', suffixe=''):

    if dossier:
        filePath = os.path.join(dossier, nom)
    else:
        filePath = nom
        
    if suffixe:
        filePath += suffixe 
        
    nom = os.path.basename(filePath)
    print('Ouverture  de', nom)
    
    fileObj = open( filePath, 'rb' )
    
    Obj = loads(fileObj)
    
    Obj.nom = nom.split('.')[0]
    
    fileObj.close()
    
    return Obj
    
    
