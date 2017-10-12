import zmq
from common.realtime import Ratekeeper
from selfdrive import messaging
from selfdrive.boardd.boardd import can_capnp_to_can_list
from selfdrive.services import service_list
from selfdrive.test.plant.plant import get_car_can_parser, car_plant

import matplotlib.pyplot as plt
import numpy as np

class plt_carstate():
    def __init__(self):
        gas_array = []
        brake_array = []
        steer_array = []
        speed_array = []
        frame = 0
        time = np.linspace(0, 10, 1001)




def main():

    rate = 100
    context = zmq.Context()
    sendcan = messaging.sub_sock(context, service_list['sendcan'].port)

    gas_array = []
    brake_array = []
    steer_array = []
    speed_array = []
    frame = 0
    time = np.linspace(0, 10, 1001)

    # init
    distance, distance_prev = 0., 0.
    speed, speed_prev = 0., 0.
    angle_steer = 0.
    grade = 0.0
    ts = 1./rate

    cp = get_car_can_parser()

    rk = Ratekeeper(rate, print_delay_threshold=100)

    while True:
        # ******** get messages sent to the car ********
        can_msgs = []
        for a in messaging.drain_sock(sendcan):
            can_msgs.extend(can_capnp_to_can_list(a.sendcan, [0, 2]))
        cp.update_can(can_msgs)
        if cp.vl[0x1fa]['COMPUTER_BRAKE_REQUEST']:
          brake = cp.vl[0x1fa]['COMPUTER_BRAKE']
        else:
          brake = 0.0

        if cp.vl[0x200]['GAS_COMMAND'] > 0:
          gas = cp.vl[0x200]['GAS_COMMAND'] / 256.0
        else:
          gas = 0.0

        if cp.vl[0xe4]['STEER_TORQUE_REQUEST']:
          steer_torque = cp.vl[0xe4]['STEER_TORQUE']*1.0/0xf00
        else:
          steer_torque = 0.0

        # ******** run the car ********
        speed, acceleration = car_plant(distance_prev, speed_prev, grade, gas, brake)
        distance = distance_prev + speed * ts
        speed = speed_prev + acceleration * ts
        if speed <= 0:
            speed = 0
            acceleration = 0

        # ******** lateral ********
        angle_steer -= (steer_torque / 10.0) * ts

        # ******** update prev ********
        speed_prev = speed
        distance_prev = distance

        # ******** print message ********
        if (rk.frame % (rate / 5)) == 0:
          print "gas: %.2f  brake: %.2f  steer: %5.2f  %6.2f m  %6.2f m/s  %6.2f m/s2  %.2f ang" \
                % (gas, brake, steer_torque, distance, speed, acceleration, angle_steer)


        # plot
        # ctrl + /
        gas_array.append(gas)
        brake_array.append(brake)
        steer_array.append(steer_torque)
        speed_array.append(speed)
        if frame % 1001 == 1000:
            plt.subplot(2, 1, 1)
            plt.plot(time, np.array(gas_array), 'g')
            plt.plot(time, np.array(brake_array), 'r')
            plt.scatter(time, np.array(gas_array), c='g')
            plt.scatter(time, np.array(brake_array), c='r')
            plt.xlabel('Time [s]')
            plt.ylabel('Pedal')
            plt.legend(['Gas pedal', 'Brake pedal'], loc=0)
            plt.grid()

            plt.subplot(2, 1, 2)
            plt.scatter(time, np.array(speed_array), c='b')
            plt.plot(time, np.array(speed_array), 'b')
            plt.xlabel('Time [s]')
            plt.ylabel('m/s')
            plt.grid()

            plt.show()
            exit()
        frame = frame + 1


        rk.keep_time()

if __name__ == "__main__":
    main()