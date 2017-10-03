# coding:utf-8
import curses
import time

import zmq
from cereal import car, log
import selfdrive.messaging as messaging
from selfdrive.car.honda.carcontroller import CarController
from selfdrive.controls.lib.alertmanager import AlertManager
from selfdrive.services import service_list
from selfdrive.car import get_car
from selfdrive.car.honda import hondacan
from selfdrive.boardd.boardd import can_list_to_can_capnp



from common.realtime import set_realtime_priority, Ratekeeper


class keyboardCatcher():
    def __init__(self):
        self.gas_press = 0
        self.break_press = 0
        self.steering_angle = 0
        # 初始化 curses
        self.screen = curses.initscr()
        # 設置不回應
        curses.noecho()
        # 設置不需要按回車立即響應
        curses.cbreak()
        # 開啟鍵盤模式
        self.screen.keypad(1)
        # 阻塞模式讀取0 非阻塞1
        self.screen.nodelay(1)

    def display_info(self, str):
        # 使用指定的colorpair显示文字
        self.screen.addstr(str)
        self.screen.refresh()

    def car_gas(self):
        self.gas_press += 1
        self.break_press = 0
        self.display_info('W')

    def car_steering(self, angle):
        if angle:
            self.steering_angle += 1
            self.display_info('D')
        else:
            self.steering_angle -= 1
            self.display_info('A')

    def car_break(self):
        self.break_press += 1
        self.gas_press = 0
        self.display_info('S')

    def catch_input(self):
        char = self.screen.getch()
        if char == 119 or char == 87:
            self.car_gas()
        elif char == 97 or char == 65:
            self.car_steering(False)
        elif char == 115 or char == 83:
            self.car_break()
        elif char == 100 or char == 68:
            self.car_steering(True)
        return char

    def finish(self):
        # 恢复控制台默认设置（若不恢复，会导致即使程序结束退出了，控制台仍然是没有回显的）
        curses.nocbreak()
        self.screen.keypad(0)
        curses.echo()
        # 结束窗口
        curses.endwin()


def data_send(kb, frame, sendcan):
    can_send = []
    idx = frame %4
    can_send.append(hondacan.create_steering_control(kb.steering_angle, False, idx))
    if (frame % 2) ==0:
        idx = (frame / 2) % 4
        can_send.append(hondacan.create_brake_command(kb.break_press, pcm_override=True, pcm_cancel_cmd=True, idx=0))
        can_send.append(hondacan.create_gas_command(kb.gas_press, idx))

    sendcan.send(can_list_to_can_capnp(can_send, msgtype='sendcan').to_bytes())


def main():
    # keyboard
    kb = keyboardCatcher()

    # loop rate 0.01s
    rate = 100
    frame = 0

    # start the loop
    set_realtime_priority(2)

    context = zmq.Context()

    # pub
    sendcan = messaging.pub_sock(context, service_list['sendcan'].port)

    # sub
    logcan = messaging.sub_sock(context, service_list['logcan'].port)

    """
    CC = car.CarControl.new_message()
    CI, CP = get_car(logcan, sendcan)
    AM = AlertManager()
    """

    CC = CarController()

    rk = Ratekeeper(rate, print_delay_threshold=2. / 1000)

    while True:
        try:
            # catch keyboard input
            kb.catch_input()
            # publish data
            data_send(kb, frame, sendcan)
            # run loop at fixed rate
            rk.keep_time()
        except KeyboardInterrupt:
            kb.finish()
            exit()
        except Exception as e:
            print "exception", e


if __name__ == "__main__":
    main()