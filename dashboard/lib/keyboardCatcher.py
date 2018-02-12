# coding:utf-8

import numpy as np
import curses


class KeyboardCatcher(object):
  def __init__(self):
    self.gas_press = 0
    self.brake_press = 0
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
    if self.brake_press != 0:
      self.brake_press = 0
    else:
      self.gas_press += 0.04
      self.brake_press = 0
    self.display_info('W')

  def car_steering(self, angle):
    if angle:
      self.steering_angle += 0.05
      self.display_info('D')
    else:
      self.steering_angle -= 0.05
      self.display_info('A')

  def car_brake(self):
    if self.gas_press != 0:
      self.gas_press = 0
    else:
      self.brake_press += 0.04
      self.gas_press = 0
    self.display_info('S')

  def catch_input(self):
    char = self.screen.getch()
    if char == 119 or char == 87:
      self.car_gas()
    elif char == 97 or char == 65:
      self.car_steering(False)
    elif char == 115 or char == 83:
      self.car_brake()
    elif char == 100 or char == 68:
      self.car_steering(True)
    return char

  def get_data(self):

    if self.get_count == 5:
      self.get_count = 0

    if self.get_count == 0:
      gas_press = np.linspace(self.gas_press_last, self.gas_press, 5)
      brake_press = np.linspace(self.brake_press_last, self.brake_press, 5)
      steering_angle = np.linspace(self.steering_angle_last, self.steering_angle, 5)
    elif self.get_count == 4:
      self.gas_press_last = self.gas_press
      self.brake_press_last = self.brake_press
      self.steering_angle_last = self.steering_angle
    else:
      self.get_count += 1

    return gas_press[self.get_count], brake_press[self.get_count], steering_angle[self.get_count]

  def finish(self):
    # 恢复控制台默认设置（若不恢复，会导致即使程序结束退出了，控制台仍然是没有回显的）
    curses.nocbreak()
    self.screen.keypad(0)
    curses.echo()
    # 结束窗口
    curses.endwin()