#!/usr/bin/python
#coding:utf-8
import zmq
import selfdrive.messaging as messaging



import curses
import matplotlib.pyplot as plt

from cereal import car, log
from common.numpy_fast import clip
from common.realtime import sec_since_boot, set_realtime_priority, Ratekeeper
from common.profiler import Profiler
from common.params import Params

from selfdrive.config import Conversions as CV
from selfdrive.services import service_list
from selfdrive.car import get_car
from selfdrive.controls.lib.alertmanager import AlertManager

V_CRUISE_MAX = 144
V_CRUISE_MIN = 8
V_CRUISE_DELTA = 8
V_CRUISE_ENABLE_MIN = 40

AWARENESS_TIME = 360.      # 6 minutes limit without user touching steering wheels
AWARENESS_PRE_TIME = 20.   # a first alert is issued 20s before start decelerating the car
AWARENESS_DECEL = -0.2     # car smoothly decel at .2m/s^2 when user is distracted

class keyboardCatcher():
    def __init__(self):
        self.gas_press = 0
        self.break_press =0
        self.steering_angle = 0
        #初始化 curses
        self.screen = curses.initscr()
        #設置不回應
        curses.noecho()
        #設置不需要按回車立即響應
        curses.cbreak()
        #開啟鍵盤模式
        self.screen.keypad(1)
        #阻塞模式讀取0 非阻塞1
        self.screen.nodelay(1)


    def car_gas(self):
        self.gas_press += 1
        self.break_press = 0
        print 'W'

    def car_steering(self,angle):
        if angle:
            self.steering_angle += 1
            print 'D'
        else:
            self.steering_angle -= 1
            print 'A'

    def car_break(self):
        self.break_press += 1
        self.gas_press = 0
        print 'S'

    def finish(self):
        #恢复控制台默认设置（若不恢复，会导致即使程序结束退出了，控制台仍然是没有回显的）
        curses.nocbreak()
        self.screen.keypad(0)
        curses.echo()
        #结束窗口
        curses.endwin()

class Control(object):
    def __init__(self, gctx, rate=100):
        self.rate = rate

        context =zmq.Context()
        # pub
        sendcan = messaging.pub_sock(context, service_list['sendcan'.port])         #send to car

        # sub
        self.thermal = messaging.sub_sock(context, service_list['thermal'].port)    #from manager
        self.health = messaging.sub_sock(context, service_list['health'].port)      #from boardd
        logcan = messaging.sub_sock(context, service_list['can'].port)              #from car

        self.CC = car.CarControl.new_message()
        # down need board support
        self.CI, self.CP = get_car(logcan,sendcan)  ###123
        self.AM = AlertManager()

        # write CarParams
        params = Params()

        # fake plan
        self.plan_ts = 0
        self.plan = log.Plan.new_message()
        self.plan.lateralValid = False
        self.plan.longitudinalValid = False

        # controls enabled state
        self.enabled = False
        self.last_enable_request = 0

        # rear view camer stste
        self.rear_view_toggle = False
        self.rear_view_allowed = (params.get("IsRearViewMirror") == "1")

        self.v_cruise_kph = 255

        # 0.0 - 1.0    6min to selfdriving
        self.awareness_status = 1.0


        self.soft_disable_timer = None

        self.overtemp = False   #phone temperature
        self.free_space = 1.0   #phone SDcard

        self.rk = Ratekeeper(self.rate, print_delay_threshold=2./1000)

    def data_sample(self):
        self.prof = Profiler()
        self.cur_time = sec_since_boot()
        # first read can and compute car states
        self.CS = self.CI.update()  ###

        self.prof.checkpoint("carInterface")

        # *** thermal checking logic ***
        # thermal data, checked every second
        td = messaging.recv_sock(self.thermal)
        if td is not None:
            # Check temperature
            self.overtemp = any(
                t > 950
                for t in (td.thermal.cpu0, td.thermal.cpu1, td.thermal.cpu2,
                          td.thermal.cpu3, td.thermal.mem, td.thermal.gpu))
            # under 15% of space free
            self.free_space = td.thermal.free_space

    def state_control(self):
        # did it request to enable?
        enable_request, enable_condition = False, False

        # reset awareness status on steering
        if self.CS.steeringPressed or not self.enabled:
            self.awareness_status = 1.0
        elif self.enabled:
            # gives the user 6 minutes
            self.awareness_status -= 1.0/(self.rate * AWARENESS_TIME)
            if self.awareness_status <= 0.:
                self.AM.add("driverDistracted", self.enabled)
            elif self.awareness_status <= AWARENESS_PRE_TIME / AWARENESS_TIME and \
                 self.awareness_status >= (AWARENESS_PRE_TIME - 0.1) / AWARENESS_TIME:
                self.AM.add("preDriverDistracted", self.enabled)

        # handa button presses
        for b in self.CS.buttonEvents:
            print b

            # button presses for rear view
            if b.type == "leftBlinker" or b.type == "rightBlinker":
                if b.pressed and self.rear_view_allowed:
                    self.rear_view_toggle = True
                else:
                    self.rear_view_toggle = False

            if b.type == "altButton1" and b.pressed:
                self.rear_view_toggle = not self.rear_view_toggle

            if not self.CP.enableCruise and self.enabled and not b.pressed:
                if b.type == "accelCruise":
                    self.v_cruise_kph -= (self.v_cruise_kph % V_CRUISE_DELTA) - V_CRUISE_DELTA
                elif b.type == "decelCruise":
                    self.v_cruise_kph -= (self.v_cruise_kph % V_CRUISE_DELTA) + V_CRUISE_DELTA
                self.v_cruise_kph = clip(self.v_cruise_kph, V_CRUISE_MIN, V_CRUISE_MAX)

            if not self.enabled and b.type in ["accelCruise", "decelCruise"] and not b.pressed:
                enable_request = True

            # do disable on button down
            if b.type == "cancel" and b.pressed:
                self.AM.add("disable", self.enabled)

        self.prof.checkpoint("Buttons")

        # *** health checking logic ***
        hh = messaging.recv_sock(self.health)
        if hh is not None:
            # if the board isn't allowing controls but somehow we are enabled!
            # TODO: this should be in state transition with a function follower logic
            if not hh.health.controlsAllowed and self.enabled:
                self.AM.add("controlsMismatch", self.enabled)

        # disable if the pedals are pressed while engaged, this is a user disable
        if self.enabled:
            if self.CS.gasPressed or self.CS.brakePressed or not self.CS.cruiseState.available:
                self.AM.add("disable", self.enabled)

            # it can happen that car cruise disables while comma system is enabled: need to
            # keep braking if needed or if the speed is very low
            # TODO: for the Acura, cancellation below 25mph is normal. Issue a non loud alert
            if self.CP.enableCruise and not self.CS.cruiseState.enabled and \
                    (self.CC.brake <= 0. or self.CS.vEgo < 0.3):
                self.AM.add("cruiseDisabled", self.enabled)

        if enable_request:
            # check for pressed pedals
            if self.CS.gasPressed or self.CS.brakePressed:
                self.AM.add("pedalPressed", self.enabled)
                enable_request = False
            else:
                print "enabled pressed at", self.cur_time
                self.last_enable_request = self.cur_time

            # don't engage with less than 15% free
            if self.free_space < 0.15:
                self.AM.add("outOfSpace", self.enabled)
                enable_request = False

        if self.CP.enableCruise:
            enable_condition = ((self.cur_time - self.last_enable_request) < 0.2) and self.CS.cruiseState.enabled
        else:
            enable_condition = enable_request

        if self.CP.enableCruise and self.CS.cruiseState.enabled:
            self.v_cruise_kph = self.CS.cruiseState.speed * CV.MS_TO_KPH

        self.prof.checkpoint("AdaptiveCruise")

        # *** what's the plan ***





def main():

    kb = keyboardCatcher()

    while True:
        try:
            char = kb.screen.getch()
            if char==119:
                kb.car_gas()
            elif char==97:
                kb.car_steering(False)
            elif char==115:
                kb.car_break()
            elif char==100:
                kb.car_steering(True)
        except KeyboardInterrupt:
            kb.finish()
            exit()
        except Exception as e:
            print "exception",e

if __name__ == "__main__":
    main()