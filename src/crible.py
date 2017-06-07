from __future__ import print_function
from pygame import Rect


class Crible( dict ):
    ''' Pavage (carres) uniforme du plan de cote self.pas. '''
  
    def __init__( self, pas ):
        self.pas = pas
        self.ElemAPaves = {}
 
    def extremas(self):
        ''' Coordonnees des paves extremes du crible '''
        Xs,Ys = zip(*self.keys())
        return min(Xs),min(Ys),max(Xs),max(Ys)
  

    def Coords( self, arg ):

        ''' Recherche dans le crible
            arg peut etre:
             - un couple (point haut, point bas) definissant un rectangle
             - un rectangle pygame.Rect
             
            Si Ajout est True, ajoute les paves qui n'ont pas deja ete frequentes.

            
            Renvoie la liste des paves intersectes par arg.
        '''
        
        if isinstance(arg,Rect):
            p1, p2 = arg.topleft, arg.bottomright
            
        elif isinstance(arg,slice):
 
            if isinstance( arg.stop, (float,int)):
                rayon = arg.stop
                x0,y0 = arg.start
                p1 = x0-rayon, y0-rayon
                p2 = x0+rayon, y0+rayon
            else:
                p1,p2 = arg.start,arg.stop
                if not (p1 or p2):
                    return self.iteritems()
                        
                elif not p1 or not p2:
                    raise ValueError( 'Point manquant' )
 
        elif len(arg) == 3:
            p1 = arg[0], arg[1].start
            p2 = arg[1].stop, arg[2]
 
        elif isinstance(arg[1],slice):
            rayon = arg[1].stop
            x0,y0 = arg[0], arg[1].start
            p1 = x0-rayon, y0-rayon
            p2 = x0+rayon, y0+rayon
 
        else:
            p1,p2 = arg
            
        x1,y1 = p1
        x2,y2 = p2
        
        xb,xh = sorted((x1,x2))
        yb,yh = sorted((y1,y2))
 
        Xb,Yb, Xh,Yh = [ int(coor)/self.pas for coor in (xb,yb,xh,yh) ]
 
        if Xb == xb*self.pas:
            Xb -= 1
        if Yb == yb*self.pas:
            Yb -= 1

        return Xb,Yb, Xh,Yh
    
    def Paves( self, arg, Ajout=False ):
        Xb,Yb, Xh,Yh = self.Coords( arg )
        if Ajout:
            return [ self.setdefault((x,y), set()) for x in xrange(Xb, Xh+1) for y in xrange(Yb, Yh+1) ]
        else:
            return [ self[(x,y)] for x in xrange(Xb,Xh+1) for y in xrange(Yb,Yh+1) if (x,y) in self ]

    def Rects( self, arg ):
        Xb,Yb, Xh,Yh = self.Coords( arg )
        pas = self.pas
        return [ (x*pas,y*pas, pas,pas) for x in xrange(Xb,Xh+1) for y in xrange(Yb,Yh+1) if (x,y) in self ]
 
    def Intersecte(self, rect, Obj=None):
        '''Assumes rect is a pygame.rect
            and criblable items have a rect member
        '''
        res = set()
        for Ens in self.Paves(rect):
            res.update( Elem for Elem in Ens if Elem is not Obj and rect.colliderect(Elem.rect) )
                
        return res

    
    def Insere( self, arg, obj, locInfo=None ):
            
        if locInfo is None:
            Paves = self.Paves(arg,Ajout=True)
        else:
            Paves = locInfo

        self.ElemAPaves[obj] = list(Paves)
        
        for Pave in Paves:
            Pave.add(obj)
        
  
    def Retire(self, obj, strict=True):
        
        if strict:
            Paves = self.ElemAPaves.pop(obj)
        else:
            Paves = self.ElemAPaves.pop(obj,[])
            
        for Ens in Paves:
            Ens.discard(obj)

    def Deplace(self, dest, obj, strict=True):
        
        self.Retire(obj, strict=strict)
        self.Insere( dest, obj )
        
    def Afficher(self,Surface):
        import pygame
        couleur = (100,100,150)
        pas = self.pas
        for x0,y0 in self:
            pygame.draw.rect(Surface,couleur,Rect(x0*pas,y0*pas,pas,pas),1)

    def Tous(self):
        ''' Tous les elements du crible '''
        res = set()
        [ res.update(Ens) for Ens in self.itervalues() ]
        return res 
    
    def Vidange( self ):
        for Ens in self.itervalues():
            Ens.clear()
            
        self.ElemAPaves.clear()
        
    def Integrite(self):
        for Ens in self.itervalues():
            for obj in Ens:
                assert Ens in self.ElemAPaves[obj]
                
    def Integrite2(self):
        for x,y in self:
            for a,b in self:
                if (x-a)**2+(y-b)**2 > 2:
                    Intersection = self[x,y].intersection(self[a,b])
                    if Intersection:
                        print(Intersection)
                        raise ValueError('Crible incoherent, %d duplication(s) %d,%d et %d,%d'%(len(Intersection),x,y,a,b))
