
EN = 'English'
FR = 'Francais'

Langue = FR

Monde = "MONDE"
Temps = "TEMPS"
Perdu = "C'EST PERDU !"
Echec = "FIN"
MENU_Lancer     = "Nouvelle Partie"
MENU_Aide       = "Aide"
MENU_A_Propos   = "A propos"
MENU_Quiter     = "Quiter"
MENU_Change_Langue = "English"

AIDE_Manette      = " Si vous avez une manette, branchez-la."
AIDE_Deplacement  = "Deplacement : fleches"
AIDE_Saut         = 'Saut'
AIDE_Course       = 'Course'
AIDE_Retour       = "Retour au menu : Echap"
AIDE_PleinEcran   = "Plein Ecran : E"

def ChangeLangue():
    global Langue
    if Langue == FR:
        Langue = EN
    else:
        Langue = FR


__Dico__ = { Monde : { EN:'WORLD'},
             Temps : { EN:'TIME'},
             Echec : { EN:'GAME OVER'},
             
             Perdu          : { EN:'YOU LOSE!'},
             MENU_Aide      : { EN : "Help" },
             MENU_Lancer    : { EN : "New Game" },
             MENU_A_Propos  : { EN : "About" }  ,
             MENU_Quiter    : { EN : "Quit" },
             MENU_Change_Langue : { EN : "Francais" },
             
             
             AIDE_Manette     : { EN :  " If you have a game pad, plug it in."},
            AIDE_Deplacement  : { EN :  "MOVE: arrows"},
            AIDE_Saut         : { EN :  'JUMP'},
            AIDE_Course       : { EN :  'RUN '},
            AIDE_Retour       : { EN :  "Back to menu: ESC" },
            AIDE_PleinEcran   : { EN :  "Full screen:  E" },
            }


def Traduc(Mot):
    
    if Langue == FR:
        return Mot
    else:
        return __Dico__[Mot][Langue]