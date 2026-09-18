from param import DISTANCE_PAR_TRANSITION_CM
from moteur import Moteur

class EtatMoteur:
    AVANT = 1
    ARRET = 0
    ARRIERE = -1

class TraqueurDistance:
    def __init__(self, enc_rot, etat_moteur=0):
        self.__enc_rot = enc_rot
        self.__transitions = 0
        self.__delta = 0
        enc_rot.when_activated = self.__transition
        enc_rot.when_deactivated = self.__transition

    def __transition(self, enc):
        self.__transitions += self.__delta

    def etat_moteur(self, etat_moteur):
        self.__delta = etat_moteur

    def distance(self):
        tmp = self.__transitions * DISTANCE_PAR_TRANSITION_CM
        self.__transitions = 0
        return tmp

    def reinit(self):
        self.__transitions = 0

    def fermer(self):
        self.reinit()
        self.__enc_rot.close()

class MoteurTraque(Moteur):
    def __init__(self, pwm, pin_avant, pin_arriere, traqueur):
        self.traqueur = traqueur
        super().__init__(pwm, pin_avant, pin_arriere)

    def avancer(self, puissance):
        super().avancer(puissance)
        self.traqueur.etat_moteur(EtatMoteur.AVANT)

    def reculer(self, puissance):
        super().reculer(puissance)
        self.traqueur.etat_moteur(EtatMoteur.ARRIERE)

    def arreter(self):
        super().arreter()
        self.traqueur.etat_moteur(EtatMoteur.ARRET)

    def fermer(self):
        super().fermer()
        self.traqueur.fermer()
