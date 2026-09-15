"""Modele du moteur du robot mobile."""

from param import PWM_MAX, PWM_MIN
from traqueurDistance import EtatMoteur

class Moteur:
    def __init__(self, pwm, pin_avant, pin_arriere, traqueur=None):
        self._pwm = pwm
        self._pin_avant = pin_avant
        self._pin_arriere = pin_arriere
        self.traqueur = traqueur
        self.arreter()

    @staticmethod
    def limiter_puissance(puissance):
        puissance = float(puissance)
        return max(PWM_MIN, min(PWM_MAX, puissance))

    def notifier_traqueur(self, etat):
        if (self.traqueur is not None):
            self.traqueur.etat_moteur(etat)

    def avancer(self, puissance):
        self._pin_avant.on()
        self._pin_arriere.off()
        self._pwm.value = self.limiter_puissance(puissance)
        self.notifier_traqueur(EtatMoteur.AVANT)

    def reculer(self, puissance):
        self._pin_avant.off()
        self._pin_arriere.on()
        self._pwm.value = self.limiter_puissance(puissance)
        self.notifier_traqueur(EtatMoteur.ARRIERE)

    def arreter(self):
        self._pwm.value = PWM_MIN
        self._pin_avant.off()
        self._pin_arriere.off()
        self.notifier_traqueur(EtatMoteur.ARRET)

    def fermer(self):
        self.arreter()
        self._pwm.close()
        self._pin_avant.close()
        self._pin_arriere.close()
        if (self.traqueur is not None):
            self.traqueur.fermer()
