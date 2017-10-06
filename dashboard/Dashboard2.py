import time
import zmq
from matplotlib import pyplot as plt
from matplotlib import animation
import numpy as np

from common.realtime import Ratekeeper
from selfdrive import messaging
from selfdrive.boardd.boardd import can_capnp_to_can_list
from selfdrive.services import service_list
from selfdrive.test.plant.plant import get_car_can_parser

frame = 0
gas_press_last = 0
break_press_last = 0
steering_angle_last = 0

# histograms set
fig = plt.figure()
objects = ('Gas', 'Break', 'Steering')
y_pos = np.arange(len(objects))
rects = plt.bar(y_pos, [0, 0, 0], color='c')
plt.xticks(y_pos, objects)
plt.ylim(0, 20)
plt.yticks(np.linspace(0, 20, 21, endpoint=True))
plt.ylabel('press')
plt.title('Car Dashboard')

# zmq set
context = zmq.Context()
sendcan = messaging.sub_sock(context, service_list['sendcan'].port)

# car parameter
cp = get_car_can_parser()

def data_gen():
    global frame, gas_press_last, break_press_last, steering_angle_last

    # get data
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
        steer_torque = cp.vl[0xe4]['STEER_TORQUE'] * 1.0 / 0xf00
    else:
        steer_torque = 0.0
    if (frame % 100) == 0:
        print "gas: %.2f  brake: %.2f  steer: %5.2f" % (gas, brake, steer_torque)


    # create show data
    if frame != 0:
        gas_press = np.linspace(gas_press_last, gas, 20)
        break_press = np.linspace(break_press_last, brake, 20)
        steering_angle = np.linspace(steering_angle_last, steer_torque, 20)
    else:
        gas_press = np.linspace(0, gas, 20)
        break_press = np.linspace(0, brake, 20)
        steering_angle = np.linspace(0, steer_torque, 20)
        gas_press_last = gas
        break_press_last = brake
        steering_angle_last = steer_torque

    frame = frame + 1
    data = np.column_stack((gas_press, break_press, steering_angle))
    yield data

def run(data):
    # update the data
    gas_press, break_press, steering_angle = data
    plt.bar([0, 1, 2], [gas_press, break_press, steering_angle])

    for rect, yi in zip(rects, data[i]):
        rect.set_height(yi)
    return rects


try:
    ani = animation.FuncAnimation(fig, run, data_gen, blit=False, interval=20,repeat=False)
    plt.show()
except KeyboardInterrupt:
    exit()
except Exception as e:
    print "exception", e


"""
def main():




if __name__ == "__main__":
    main()
"""