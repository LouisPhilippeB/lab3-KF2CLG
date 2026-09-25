"""Modele du robot mobile."""

import math

from param import (
    FACTEUR_MOTEUR_DROIT_PIVOT_D,
    FACTEUR_MOTEUR_GAUCHE_PIVOT_G,
    VITESSE_MAX,
    VITESSE_MIN,
    VITESSE_ROTATION_MIN,
    VITESSE_INITIALE,
)


class Robot:
    def __init__(self, moteur_gauche, moteur_droit):
        self._moteur_gauche = moteur_gauche
        self._moteur_droit = moteur_droit
        self._bloque = False
        self.vitesse = VITESSE_INITIALE

    @property
    def vitesse(self):
        return self._vitesse

    @vitesse.setter
    def vitesse(self, valeur):
        self._vitesse = self.limiter_vitesse(valeur)

    @property
    def est_bloque(self):
        return self._bloque

    @staticmethod
    def limiter_vitesse(vitesse):
        vitesse = float(vitesse)
        if not math.isfinite(vitesse):
            raise ValueError("La vitesse doit etre un nombre fini")
        return max(VITESSE_MIN, min(VITESSE_MAX, vitesse))

    def avancer(self):
        if self._bloque:
            self.arreter()
            return False
        puissance = self.limiter_vitesse(self.vitesse)
        self._moteur_gauche.avancer(puissance)
        self._moteur_droit.avancer(puissance)
        return True

    def reculer(self):
        puissance = self.limiter_vitesse(self.vitesse)
        self._moteur_gauche.reculer(puissance)
        self._moteur_droit.reculer(puissance)
        return True

    def pivoter_gauche(self):
        puissance = max(
            VITESSE_ROTATION_MIN,
            self.limiter_vitesse(self.vitesse),
        )
        puissance_gauche = self.limiter_vitesse(
            puissance * FACTEUR_MOTEUR_GAUCHE_PIVOT_G
        )
        self._moteur_gauche.reculer(puissance_gauche)
        self._moteur_droit.avancer(puissance)
        return True

    def pivoter_droite(self):
        puissance = max(
            VITESSE_ROTATION_MIN,
            self.limiter_vitesse(self.vitesse),
        )
        puissance_droite = self.limiter_vitesse(
            puissance * FACTEUR_MOTEUR_DROIT_PIVOT_D
        )
        self._moteur_gauche.avancer(puissance)
        self._moteur_droit.reculer(puissance_droite)
        return True

    def bloquer(self):
        if self._bloque:
            return
        self._bloque = True
        self.arreter()

    def debloquer(self):
        self._bloque = False

    def arreter(self):
        self._moteur_gauche.arreter()
        self._moteur_droit.arreter()

    def fermer(self):
        self.arreter()
        self._moteur_gauche.fermer()
        self._moteur_droit.fermer()

    def distance(self):
        distance_gauche = self._moteur_gauche.traqueur.distance()
        distance_droite = self._moteur_droit.traqueur.distance()
        return distance_gauche, distance_droite
