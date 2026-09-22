from threading import Thread, Event
from time import sleep

class Signaleur:
    def __init__(self, led):
        self.led = led
        self.__quit = Event()
        self.__timeout = 5

    @staticmethod
    def __thr_signaleur(quit, led, timeout):
        timeout = timeout / 2.0
        try:
            while not quit.is_set():
                led.toggle()
            quit.wait(timeout)
        finally:
            led.off()

    def demarrer(self):
        self.arreter()

        self.thread = Thread(
            target=lambda: self.__thr_signaleur(self.__quit, self.led, self.__timeout),
            daemon=True
        )
        self.thread.start()

    def arreter(self):
        self.__quit.set()
        self.thread.join()

    def clignoter(self, timeout):
        if (timeout < 0.05):
            raise ValueError("La durée de clignotement minimale est de 0.05s.")

        self.__timeout = timeout
        self.demarrer()
