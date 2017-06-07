
class MortJoueur(Exception):
    pass

class InterruptionDePartie(Exception):
    pass

class TransferMonde(Exception):

    def __init__( self, MondeSuivant, Entree=0, Decompte=False ):
        """ Entree 0 est la position normale de depart """
        self.entree   = Entree
        self.monde    = MondeSuivant
        self.decompte = Decompte
