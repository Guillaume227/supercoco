#! /usr/bin/env python

import pygame
import os

from src import pagedegarde


def main(plein_ecran=False):
    
    os.environ["SDL_VIDEO_CENTERED"] = "1"
    
    pygame.mixer.pre_init(44100, -16, 2, 1024)
    pygame.init()
        
    try:
        
        pygame.display.set_caption("  Super Coco")
        
        try:
            pygame.display.set_icon(pygame.image.load("media/coco.ico"))
        except:
            print("echec d'affichage de l'icone")

        pygame.joystick.init()
        if pygame.joystick.get_count() > 0:
            pygame.joystick.Joystick(0).init()
            print(f'{pygame.joystick.get_count()} manette(s) disponible(s)')

        pygame.mouse.set_visible(0)
        
        pagedegarde.Menu(plein_ecran=plein_ecran)
        
    finally:

        pygame.quit()
        pygame.joystick.quit()


if __name__ == '__main__':
    
    try:
        main()
    except:
        import traceback
        traceback.print_exc()
        
        input('Appuyez sur Entrer pour fermer')
