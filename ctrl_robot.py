#!/bin/python3

"""Controle des moteurs et odometrie du robot."""

import math
import time

from ev_app import EvApp
from ev_app_client_api import gen_ev_externe
from param import (
    APP_CTRL_ROBOT,
    APP_LIGNE,
    ENCODEUR_DROIT_GPIO,
    ENCODEUR_GAUCHE_GPIO,
    INTERVALLE_AFFICHAGE_ENCODEURS,
    INTERVALLE_ODOMETRIE,
    LARGEUR_ROBOT_CM,
    MOTEUR_DROIT_IN1,
    MOTEUR_DROIT_IN2,
    MOTEUR_DROIT_PWM,
    MOTEUR_GAUCHE_IN1,
    MOTEUR_GAUCHE_IN2,
    MOTEUR_GAUCHE_PWM,
    MSG_ARRETER,
    MSG_AVANCER,
    MSG_BLOQUER,
    MSG_DEBLOQUER,
    MSG_INIT,
    MSG_PIVOTER_D,
    MSG_PIVOTER_G,
    MSG_POSITION,
    MSG_RECULER,
    MSG_VITESSE,
)
from robot import Robot
from traqueur_distance import MoteurTraque, TraqueurDistance


class CtrlRobot(EvApp):
    def __init__(
        self,
        port_no,
        robot,
        envoyer=gen_ev_externe,
        horloge=time.perf_counter,
        **app_options,
    ):
        app_options.setdefault("tmo", INTERVALLE_ODOMETRIE)
        super().__init__(port_no, **app_options)
        self.robot = robot
        self._envoyer = envoyer
        self._horloge = horloge

        self.x = 0.0
        self.y = 0.0
        self.angle = 0.0
        self._dernier_calcul = self._horloge()
        self._dernier_affichage = self._dernier_calcul

        self._actions = {
            MSG_INIT: self.initialiser_odometrie,
            MSG_ARRETER: self.robot.arreter,
            MSG_BLOQUER: self.robot.bloquer,
            MSG_DEBLOQUER: self.robot.debloquer,
            MSG_AVANCER: self.robot.avancer,
            MSG_RECULER: self.robot.reculer,
            MSG_PIVOTER_G: self.robot.pivoter_gauche,
            MSG_PIVOTER_D: self.robot.pivoter_droite,
        }

    @staticmethod
    def lire_vitesse(evenement):
        donnees = evenement.split()
        if not donnees or donnees[0] == "":
            raise ValueError("Vitesse manquante")
        return Robot.limiter_vitesse(donnees[0])

    def initialiser_odometrie(self):
        """Arrete le robot et remet les compteurs et la pose a zero."""
        self.robot.debloquer()
        self.robot.arreter()
        self.robot.distance()  # Remet les compteurs des encodeurs a zero.

        self.x = 0.0
        self.y = 0.0
        self.angle = 0.0
        self._dernier_calcul = self._horloge()

        self._transmettre_position()

    def _transmettre_position(self):
        x = round(self.x, 4)
        y = round(self.y, 4)
        angle_degres = round(math.degrees(self.angle), 4) % 360

        try:
            self._envoyer(
                "127.0.0.1",
                APP_LIGNE,
                MSG_POSITION,
                x,
                y,
                angle_degres,
            )
        except OSError as erreur:
            print(f"MSG_POSITION non transmis a ligne.py: {erreur}")

    def _afficher_encodeurs(self, maintenant):
        if maintenant - self._dernier_affichage < INTERVALLE_AFFICHAGE_ENCODEURS:
            return

        self._dernier_affichage = maintenant
        print(
            "POSITION | "
            f"x={self.x:.2f} cm y={self.y:.2f} cm "
            f"angle={math.degrees(self.angle) % 360:.2f} deg"
        )

    def actualiser_odometrie(self):
        maintenant = self._horloge()
        duree = maintenant - self._dernier_calcul
        if duree < INTERVALLE_ODOMETRIE:
            return False

        distance_gauche, distance_droite = self.robot.distance()
        distance = (distance_droite + distance_gauche) / 2.0
        variation_angle = (
            distance_droite - distance_gauche
        ) / LARGEUR_ROBOT_CM
        angle_milieu = self.angle + variation_angle / 2.0
        self.x += math.cos(angle_milieu) * distance
        self.y += math.sin(angle_milieu) * distance
        self.angle += variation_angle
        self._dernier_calcul = maintenant
        self._transmettre_position()
        self._afficher_encodeurs(maintenant)
        return True

    def _traiter_commande(self, evenement):
        if evenement.type == MSG_VITESSE:
            try:
                vitesse = self.lire_vitesse(evenement)
                self.robot.vitesse = vitesse
                print(f"MSG_VITESSE recu: {vitesse:.2f}.")
            except (TypeError, ValueError) as erreur:
                print(f"MSG_VITESSE invalide ignore: {erreur}")
            return

        action = self._actions.get(evenement.type)
        if action is None:
            print(f"Message inconnu ignore: {evenement.type}")
            return

        try:
            resultat = action()
            if resultat is False:
                print(
                    "MSG_AVANCER refuse: obstacle detecte; "
                    "recul et pivotements seulement."
                )
                return
            print(
                f"Commande recue: type={evenement.type}, "
                f"vitesse={self.robot.vitesse:.2f}, "
                f"bloque={self.robot.est_bloque}."
            )
        except (TypeError, ValueError) as erreur:
            self.robot.arreter()
            print(f"Commande invalide, robot arrete: {erreur}")

    def dispatch_event(self, evenement):
        if evenement is not None:
            self._traiter_commande(evenement)
        self.actualiser_odometrie()

    def quitter(self):
        self.robot.fermer()
        print("Controleur arrete; moteurs et encodeurs desactives.")


def creer_controleur(port_no=APP_CTRL_ROBOT):
    try:
        from gpiozero import (
            DigitalInputDevice,
            DigitalOutputDevice,
            PWMOutputDevice,
        )
    except ImportError as erreur:
        raise SystemExit(
            "gpiozero est necessaire: "
        ) from erreur

    traqueur_gauche = TraqueurDistance(
            DigitalInputDevice(ENCODEUR_GAUCHE_GPIO)
    )
    traqueur_droit = TraqueurDistance(
            DigitalInputDevice(ENCODEUR_DROIT_GPIO)
    )
    moteur_gauche = MoteurTraque(
        PWMOutputDevice(MOTEUR_GAUCHE_PWM),
        DigitalOutputDevice(MOTEUR_GAUCHE_IN1),
        DigitalOutputDevice(MOTEUR_GAUCHE_IN2),
        traqueur_gauche,
    )
    moteur_droit = MoteurTraque(
        PWMOutputDevice(MOTEUR_DROIT_PWM),
        DigitalOutputDevice(MOTEUR_DROIT_IN1),
        DigitalOutputDevice(MOTEUR_DROIT_IN2),
        traqueur_droit,
    )
    robot = Robot(moteur_gauche, moteur_droit)
    return CtrlRobot(port_no, robot)


def main():
    controleur = creer_controleur()
    print(f"Controleur du robot en ecoute sur le port {APP_CTRL_ROBOT}.")
    print(f"Positions transmises localement a ligne.py:{APP_LIGNE}.")
    controleur.run()


if __name__ == "__main__":
    main()
