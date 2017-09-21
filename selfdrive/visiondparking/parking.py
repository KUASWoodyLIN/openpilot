import os
import time
import random
import zmq

import selfdrive.messaging as messaging
from selfdrive.services import service_list
from common.profiler import Profiler
from common.realtime import set_realtime_priority, Ratekeeper


class Parking(object):
    def __init__(self, gctx, rate=20):
        """ init all parameter """
        self.rate = rate

        # *** log ***
        context = zmq.Context()

        # pub
        self.parking = messaging.pub_sock(context, service_list['parking'].port)

        # sub
        self.live100 = messaging.sub_sock(context, service_list['live100'].port)

        # parameter
        self.working = False
        self.find = False
        self.longitudinal = .0
        self.lateral = .0

        # Monitoring system help you to record the running time by calling checkpoint function
        self.prof = Profiler()

        # loop running time keeper
        self.rk = Ratekeeper(self.rate, print_delay_threshold=2./1000)

    def data_get(self):
        """ get the message from live100 port """
        l100 = messaging.recv_sock(self.live100)
        if l100 is not None:
            self.enable = l100.live100.enable            #cruise mode
            self.v_ego = l100.live100.vEgo               #car speed
            self.steer_angle = l100.live100.angleSteers  #car steer angle

        self.prof.checkpoint("data get")

    def main_loop(self):
        """ put your code here """

        self.working = True
        self.find = True
        self.longitudinal = random.randint(0,99)    # Front
        self.lateral = random.randint(0,50)         # left, right

        self.prof.checkpoint("main loop")

    def data_send(self):
        """ send the message to parking port """
        dat = messaging.new_message()
        dat.init('parking')

        dat.parking.working = self.working
        dat.parking.findtarget = self.find
        dat.parking.targetLoC = self.longitudinal
        dat.parking.targetLaC = self.lateral

        self.parking.send(dat.to_bytes())
        self.prof.checkpoint("data send")

    def monitor(self):
        """this only monitor the cumulative lag, but does not enforce a rate"""
        self.rk.monitor_time()

    def wait(self):
        """wait until the 1/rate sec is over"""
        if self.rk.keep_time():
            self.prof.display()

def parking_thread(gctx, rate=20):
    set_realtime_priority(1)
    pkg = Parking(gctx, rate)
    while 1:
        pkg.data_get()
        pkg.main_loop()
        pkg.data_send()

        # Two choose one
        #pkg.monitor()
        pkg.wait()


def main(gctx=None):
    parking_thread(gctx, 20)

if __name__ == "__main__":
    main()
