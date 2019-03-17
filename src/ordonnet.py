"""
Created on 2 Jun 2012

@author: Zarastro
"""
from __future__ import print_function


class Ordonnet(object):
    """Structure de donnees, dictionaire ordonne"""

    def __init__(self, elems=[]):

        self.__elems = list(elems)
        self.__nomb_elems = len(self.__elems)
        self.__ordonne()

    def __ordonne(self):
        self.__ordre = dict((elem, i) for i, elem in enumerate(self.__elems))

    def __iter__(self):
        return iter(self.__elems)

    def index(self, elem):
        return self.__ordre[elem]

    def __contains__(self, elem):
        return elem in self.__ordre

    def __getitem__(self, index):
        return self.__elems[index]

    def __getslice__(self, i, j):
        return self.__elems[i:j]

    def __len__(self):
        return self.__nomb_elems

    def insere(self, elem, index=None):

        if index is None:
            self.__elems.append(elem)
            self.__ordre[elem] = self.__nomb_elems

        else:
            self.__elems.insert(index, elem)
            self.__ordonne()

        self.__nomb_elems += 1

    def ote(self, elem):
        index = self.__ordre.pop(elem)
        del self.__elems[index]
        self.__nomb_elems -= 1
        if index < self.__nomb_elems:
            # si ce n'est pas le dernier elements, tri necessaire.
            self.__ordonne()

    def deplace(self, elem, nouvelIndex=None):

        vieilIndex = self.__ordre[elem]
        if nouvelIndex is not None and nouvelIndex < 0:
            nouvelIndex += self.__nomb_elems

        self.ote(elem)

        if nouvelIndex is None or vieilIndex > nouvelIndex:
            pass
        else:
            nouvelIndex += 1

        self.insere(elem, nouvelIndex)

    def remplace(self, elem, novElem):
        index = self.__ordre.pop(elem)
        self.__ordre[novElem] = index
        self.__elems[index] = novElem

    def integrite(self):
        for i, elem in enumerate(self.__elems):
            try:
                assert i == self.__ordre[elem]  # syncro de l'ordre du dictionaire et de la liste
            except:
                print('integrite', i, elem, self.__ordre[elem])

            assert self.__elems.count(elem) == 1  # unicite des elements de la liste

        assert len(self.__elems) == self.__nomb_elems

    def __getstate__(self):
        """soyons sur de ne pas le serialiser par megarde """
        raise ValueError("ne devrait pas etre seralise")
