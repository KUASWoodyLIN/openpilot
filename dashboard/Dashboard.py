import zmq
from common.realtime import Ratekeeper
from selfdrive import messaging
from selfdrive.boardd.boardd import can_capnp_to_can_list
from selfdrive.services import service_list
from selfdrive.test.plant.plant import get_car_can_parser

import matplotlib.pyplot as plt
import numpy as np


def main():

    rate = 100
    context = zmq.Context()
    sendcan = messaging.sub_sock(context, service_list['sendcan'].port)

    gas_array = []
    brake_array = []
    steer_array = []
    frame = 0


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
        if (rk.frame % (rate / 5)) == 0:
          print "gas: %.2f  brake: %.2f  steer: %5.2f" % (gas, brake, steer_torque)


        # plot
        # ctrl + /
        # gas_array.append(gas)
        # brake_array.append(brake)
        # steer_array.append(steer_torque)
        # time = np.linspace(0, 30, 3000)
        # if frame % 3001 == 3000:
        #     plt.plot(
        #         time, np.array(gas_array), 'g',
        #         time, np.array(brake_array), 'r',
        #     )
        #     plt.xlabel('Time [s]')
        #     plt.ylabel('Pedal []')
        #     plt.legend(['Gas pedal', 'Brake pedal'], loc=0)
        #     plt.show()
        # frame = frame + 1


        rk.keep_time()

if __name__ == "__main__":
    main()