import pygame
from . import menu
from . import media


def devinette(son_reussite=None, son_echec=None):
    ecran = pygame.display.get_surface()
    ecran.fill((0, 0, 0))

    import random
    while True:
        a = random.randrange(5, 40)
        b = random.randrange(2, 12)
        if a == 10 or b == 10:
            continue
        break

    resultat = a * b
    dim_ecran = ecran.get_size()

    question = f'Combien font {a} x {b} ?'

    init_menu = menu.BoiteTexte(legende=[question, '', ''],
                                pos=(dim_ecran[0] / 4, dim_ecran[1] / 2),
                                centre=True)

    try:
        reponse = int(init_menu.boucle())
    except:
        reponse = None

    if reponse != resultat:
        print(f'La bonne reponse est : {a} x {b} = {resultat}')
        if son_echec:
            media.charge_son(son_echec).play()
        return False
    else:
        if son_reussite:
            media.charge_son(son_reussite).play()
        return True


def devinette_sans_echec(*args, **kwargs):
    while not devinette(*args, **kwargs):
        pass
