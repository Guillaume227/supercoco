class MortJoueur(Exception):
    pass


class InterruptionDePartie(Exception):
    pass


class TransferMonde(Exception):

    def __init__(self, monde_suivant, entree=0, decompte=False):
        """ Entree 0 est la position normale de depart """
        self.entree = entree
        self.monde = monde_suivant
        self.decompte = decompte
