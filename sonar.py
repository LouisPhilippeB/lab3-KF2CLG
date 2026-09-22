#!/bin/python3

"""Mesure des deux sonars et signalisation par DEL."""

import math
import threading
import time

from signaleur import Signaleur
from lisseur import Lisseur
from ev_app_client_api import fermer_client, gen_ev_externe
from param import (
    APP_LIGNE,
    DEL_JAUNE_GPIO,
    DEL_VERTE_GPIO,
    DISTANCE_SONAR_MAX_CM,
    DISTANCE_SONAR_MIN_CM,
    FENETRE_LISSAGE_SONAR,
    INTERVALLE_MESURE_SONAR,
    MSG_SONAR,
    PERIODE_DEL_LENTE_S,
    PERIODE_DEL_MIN_S,
    PERIODE_DEL_MOYENNE_S,
    PERIODE_DEL_RAPIDE_S,
    SEUIL_SONAR_MESSAGE_CM,
    SEUIL_SONAR_RAPIDE_CM,
    SONAR_DROIT_ECHO_GPIO,
    SONAR_DROIT_TRIGGER_GPIO,
    SONAR_GAUCHE_ECHO_GPIO,
    SONAR_GAUCHE_TRIGGER_GPIO,
    VITESSE_SON_CM_S,
)


def _charger_gpiozero():
    try:
        from gpiozero import DigitalInputDevice, DigitalOutputDevice
    except ImportError as erreur:
        raise SystemExit("gpiozero est necessaire sur le Pi") from erreur
    return DigitalInputDevice, DigitalOutputDevice


class Sonar:

    def __init__(
        self,
        gpio_trigger,
        gpio_echo,
        gpio_del,
        envoyer=gen_ev_externe,
        horloge=time.perf_counter,
        dormir=time.sleep,
        sortie_factory=None,
        entree_factory=None,
        signaleur=None,
        grandeur_fenetre=FENETRE_LISSAGE_SONAR,
    ):
        if sortie_factory is None or entree_factory is None:
            entree_gpiozero, sortie_gpiozero = _charger_gpiozero()
            sortie_factory = sortie_factory or sortie_gpiozero
            entree_factory = entree_factory or entree_gpiozero

        self._trigger = sortie_factory(gpio_trigger)
        self._echo = entree_factory(gpio_echo, pull_up=False)
        self._signaleur = signaleur or Signaleur(
            gpio_del,
            sortie_factory=sortie_factory,
        )
        self._lisseur = Lisseur(grandeur_fenetre)
        self._envoyer = envoyer
        self._horloge = horloge
        self._dormir = dormir
        self._debut_echo = None
        self._periode_signaleur = None
        self._arrete = False
        self.derniere_distance = None

        self._trigger.off()
        self._echo.when_activated = self._front_montant
        self._echo.when_deactivated = self._front_descendant

    def _front_montant(self, _entree=None):
        if not self._arrete:
            self._debut_echo = self._horloge()

    def _front_descendant(self, _entree=None):
        fin_echo = self._horloge()
        if self._arrete or self._debut_echo is None:
            return
        duree = fin_echo - self._debut_echo
        self._debut_echo = None

        distance = VITESSE_SON_CM_S * duree / 2.0
        if not DISTANCE_SONAR_MIN_CM <= distance <= DISTANCE_SONAR_MAX_CM:
            return

        distance = self._lisseur.lisser_min_max(distance)
        self.derniere_distance = distance
        self._actualiser_signaleur(distance)
        self._transmettre_obstacle(distance)

    def _actualiser_signaleur(self, distance):
        if distance < SEUIL_SONAR_RAPIDE_CM:
            periode = PERIODE_DEL_RAPIDE_S
        elif distance < SEUIL_SONAR_MESSAGE_CM:
            periode = PERIODE_DEL_MOYENNE_S
        else:
            periode = PERIODE_DEL_LENTE_S

        if periode != self._periode_signaleur:
            print(f"clignoter: {periode}")
            self._signaleur.clignoter(periode)
            self._periode_signaleur = periode

    def _transmettre_obstacle(self, distance):
        if distance >= SEUIL_SONAR_MESSAGE_CM:
            return
        try:
            self._envoyer(
                "127.0.0.1",
                APP_LIGNE,
                MSG_SONAR,
                round(distance, 2),
            )
        except OSError as erreur:
            print(f"MSG_SONAR non transmis a ligne.py: {erreur}")

    def mesurer(self):
        if self._arrete:
            return
        self._debut_echo = None

        self._trigger.on()
        try:
            self._dormir(0.000010)
        finally:
            self._trigger.off()

    def arreter(self):
        if self._arrete:
            return
        self._arrete = True
        self._debut_echo = None

        try:
            self._signaleur.arreter()
        finally:
            self._trigger.off()
            self._trigger.close()
            self._echo.close()


def main():
    sonar_gauche = Sonar(
        SONAR_GAUCHE_TRIGGER_GPIO,
        SONAR_GAUCHE_ECHO_GPIO,
        DEL_JAUNE_GPIO,
    )
    sonar_droit = Sonar(
        SONAR_DROIT_TRIGGER_GPIO,
        SONAR_DROIT_ECHO_GPIO,
        DEL_VERTE_GPIO,
    )

    print("Sonars actifs a 10 mesures par seconde chacun.")
    try:
        while True:
            debut_cycle = time.perf_counter()
            sonar_gauche.mesurer()
            time.sleep(INTERVALLE_MESURE_SONAR / 2.0)
            sonar_droit.mesurer()
            reste = INTERVALLE_MESURE_SONAR - (
                time.perf_counter() - debut_cycle
            )
            if reste > 0:
                time.sleep(reste)
    except KeyboardInterrupt:
        pass
    finally:
        sonar_gauche.arreter()
        sonar_droit.arreter()
        fermer_client()
        print("Programme sonar arrete; GPIO et DEL desactives.")


if __name__ == "__main__":
    main()
