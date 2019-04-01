from __future__ import absolute_import
import pygame, sys
from pygame.locals import *
from .media import cheminFichier, charge_image


class SautePlanche(Exception):
    """Signifie que l'on veut sauter la planche en cours d'affichage"""
    pass


def recadre_image(img_fond, img):
    l,h = img_fond.get_size()
    
    i_l, i_h = img.get_size()
    if i_l > i_h:
        i_l, i_h = l, int(l*i_h/i_l)
    else:
        i_l, i_h = int(h*i_l/i_h), h
        
    photo = pygame.transform.scale(img, (i_l, i_h))
    coin_haut_gauche = (l-i_l)/2, (h-i_h)/2
    
    return photo, coin_haut_gauche


def planche(text='', taille=16, centre=True, intro=True, extro=False, photo=None, duree=-1):
    
    ecran = pygame.display.get_surface()
    
    font = pygame.font.Font(cheminFichier("fonts/font.ttf"), taille)
    l, h = ecran.get_size()
    black = pygame.Surface((l, h))
    black.fill((0, 0, 0))
    
    intro = intro
    if intro:
        alpha = 255
    else:
        alpha = 0
        
    extro = False
    height = len(text)*(font.get_height()+3)
    image = pygame.Surface((l, height))
    
    if photo:
        img = charge_image("photos/"+photo)
        photo, photo_pos = recadre_image(ecran, img)
    
    for y, line in enumerate(text):
        ren = font.render(line.strip(), 1, (255, 255, 255))
        if centre:
            lineX = l/2.-ren.get_width()/2
        else:
            lineX = 5
                     
        image.blit(ren, (lineX, y*(font.get_height()+3)))
    
    horloge = pygame.time.Clock()
    temps = 0
    d_t = 10
    
    while True:
        
        #pygame.time.wait(10)
        horloge.tick(d_t) # 10 ms
        temps += d_t / 1000.
        
        if duree > 0 and temps >= duree:
            extro = True
        
        for e in pygame.event.get():
            
            if e.type == QUIT:
                sys.exit()
                
            elif e.type == KEYDOWN:
                if e.key == K_ESCAPE:
                    raise SautePlanche
                
                elif e.key in (K_SPACE, K_RETURN):
                    intro = False
                    if extro:
                        extro = True
                    else:
                        ecran.blit(black, (0, 0))
                    
            elif e.type == pygame.JOYBUTTONDOWN:
                if e.button == 3:
                    break
                else:
                    intro = False
                    if extro:
                        extro = True
                    else:
                        ecran.blit(black, (0, 0))
                        return
                
        if intro:
            if alpha > 0:
                alpha -= 25
                
        elif extro:
            if alpha < 255:
                alpha += 25
            else:
                break
        
        ecran.fill((0, 0, 0))
        if centre:
            ecran.blit(image, (0, (h-image.get_height())/2) )
        else:
            ecran.blit(image, (0, 0) )
            
        if photo:
            ecran.blit(photo, photo_pos)
        
        black.set_alpha(alpha)
        ecran.blit(black, (0, 0))
        
        pygame.display.flip()

    ecran.blit(black, (0, 0))
