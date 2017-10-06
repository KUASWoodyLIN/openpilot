# coding:utf-8
import sys
import os
sys.path.append('/home/woodylin/github/openpilot')
import curses
import time

import zmq
import numpy as np
from cereal import car, log
import selfdrive.messaging as messaging
from selfdrive.car.honda.carcontroller import CarController
from selfdrive.controls.lib.alertmanager import AlertManager
from selfdrive.services import service_list
from selfdrive.car import get_car
from selfdrive.car.honda import hondacan
from selfdrive.boardd.boardd import can_list_to_can_capnp
from common.numpy_fast import clip



from common.realtime import set_realtime_priority, Ratekeeper


class keyboardCatcher():
    def __init__(self):
        self.gas_press = 0
        self.brake_press = 0
        self.steering_angle = 0
        self.gas_press_last = 0
        self.brake_press_last = 0
        self.steering_angle_last = 0
        self.gas_press_array = np.zeros(5)
        self.brake_press_array = np.zeros(5)
        self.steering_angle_array = np.zeros(5)
        self.first_time = True
        self.state_change = False
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
        if self.brake_press != 0:
            self.brake_press = 0
        else:
            self.gas_press += 0.02
            self.brake_press = 0
        self.display_info('W')

    def car_steering(self, angle):
        if angle:
            self.steering_angle += 0.03
            self.display_info('D')
        else:
            self.steering_angle -= 0.03
            self.display_info('A')

    def car_brake(self):
        if self.gas_press != 0:
            self.gas_press = 0
        else:
            self.brake_press += 0.02
            self.gas_press = 0
        self.display_info('S')

    def catch_input(self):
        char = self.screen.getch()
        if char == 119 or char == 87:
            self.car_gas()
            self.state_change = True
        elif char == 97 or char == 65:
            self.car_steering(False)
            self.state_change = True
        elif char == 115 or char == 83:
            self.car_brake()
            self.state_change = True
        elif char == 100 or char == 68:
            self.car_steering(True)
            self.state_change = True
        else:
            self.state_change = False
        return char

    def get_data(self):
        if self.first_time:
            self.get_count = 0
            self.first_time = False
        elif self.get_count == 4:
            self.get_count = 0
        else:
            self.get_count = self.get_count + 1

        if self.get_count == 0:
            self.gas_press_array = np.linspace(self.gas_press_last, self.gas_press, 5)
            self.brake_press_array = np.linspace(self.brake_press_last, self.brake_press, 5)
            self.steering_angle_array = np.linspace(self.steering_angle_last, self.steering_angle, 5)
        elif self.get_count == 4:
            self.gas_press_last = self.gas_press
            self.brake_press_last = self.brake_press
            self.steering_angle_last = self.steering_angle

        return self.gas_press_array[self.get_count], self.brake_press_array[self.get_count], self.steering_angle_array[self.get_count]

    def finish(self):
        # 恢复控制台默认设置（若不恢复，会导致即使程序结束退出了，控制台仍然是没有回显的）
        curses.nocbreak()
        self.screen.keypad(0)
        curses.echo()
        # 结束窗口
        curses.endwin()


def data_send(kb, frame, sendcan, accord, crv, GAS_MAX, BRAKE_MAX, STEER_MAX, GAS_OFFSET):
    gas, brake, steer_torque = kb.get_data()
    # if frame % 100 == 0:
    #     print "gas: %.2f  brake: %.2f  steer: %5.2f" % (gas, brake, steer_torque)
    # steer torque is converted back to CAN reference (positive when steering right)
    apply_gas = int(clip(gas * GAS_MAX, 0, GAS_MAX - 1))
    apply_brake = int(clip(brake * BRAKE_MAX, 0, BRAKE_MAX - 1))
    apply_steer = int(clip(-steer_torque * STEER_MAX, -STEER_MAX, STEER_MAX))
    # apply_gas = int(clip(kb.gas_press * GAS_MAX, 0, GAS_MAX - 1))
    # apply_brake = int(clip(kb.brake_press * BRAKE_MAX, 0, BRAKE_MAX - 1))
    # apply_steer = int(clip(-kb.steering_angle * STEER_MAX, -STEER_MAX, STEER_MAX))

    can_sends = []
    if accord:
      idx = frame % 2
      can_sends.append(hondacan.create_accord_steering_control(apply_steer, idx))
    else:
      idx = frame % 4
      can_sends.extend(hondacan.create_steering_control(apply_steer, crv, idx))
    if (frame % 2) == 0:
        idx = (frame / 2) % 4
        can_sends.append(hondacan.create_brake_command(apply_brake, pcm_override=True, pcm_cancel_cmd=True, chime=0, idx=idx))
        gas_amount = (apply_gas + GAS_OFFSET) * (apply_gas > 0)
        can_sends.append(hondacan.create_gas_command(gas_amount, idx))

    sendcan.send(can_list_to_can_capnp(can_sends, msgtype='sendcan').to_bytes())

def main():
    # keyboard
    kb = keyboardCatcher()

    # loop rate 0.01s
    rate = 100
    frame = 0
    accord = False
    crv = False
    civic = False

    GAS_MAX = 1004
    BRAKE_MAX = 1024/4
    if civic:
      is_fw_modified = os.getenv("DONGLE_ID") in ['b0f5a01cf604185c']
      STEER_MAX = 0x1FFF if is_fw_modified else 0x1000
    elif crv:
      STEER_MAX = 0x300  # CR-V only uses 12-bits and requires a lower value
    else:
      STEER_MAX = 0xF00
    GAS_OFFSET = 328

    # start the loop
    set_realtime_priority(2)

    context = zmq.Context()

    # pub
    sendcan = messaging.pub_sock(context, service_list['sendcan'].port)

    # sub
    logcan = messaging.sub_sock(context, service_list['can'].port)


    #CC = car.CarControl.new_message()
    #CI, CP = get_car(logcan, sendcan)
    #AM = AlertManager()


    CC = CarController()

    rk = Ratekeeper(rate, print_delay_threshold=2. / 1000)

    while True:
        try:
            # catch keyboard input
            kb.catch_input()
            # publish data
            frame = frame + 1
            data_send(kb, frame, sendcan, accord, crv, GAS_MAX, BRAKE_MAX, STEER_MAX, GAS_OFFSET)
            #print frame
            # run loop at fixed rate
            rk.keep_time()
        except KeyboardInterrupt:
            kb.finish()
            exit()
        except Exception as e:
            print "exception", e


if __name__ == "__main__":
    main()