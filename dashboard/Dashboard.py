import zmq
from matplotlib import pyplot as plt
from matplotlib import animation
import numpy as np
from Keyboard_input import kb

from selfdrive import messaging
from selfdrive.services import service_list

gas_press = np.zeros(20)
break_press = np.zeros(20)
steering_angle = np.zeros(20)


def animate(i):
    global gas_press, break_press, steering_angle
    char = kb.catch_input()
    if char == 119:
        kb.car_gas()
        gas_press = np.linspace(gas_press[19], kb.gas_press, 20)
        break_press = np.zeros(20)
    elif char == 97:
        kb.car_steering(False)
        steering_angle = np.linspace(steering_angle[19], kb.steering_angle, 20)
    elif char == 115:
        kb.car_break()
        break_press = np.linspace(break_press[19], kb.break_press, 20)
        gas_press = np.zeros(20)
    elif char == 100:
        kb.car_steering(True)
        steering_angle = np.linspace(steering_angle[19], kb.steering_angle, 20)
    if i == 19:
        gas_press[0:19] = kb.gas_press
        break_press[0:19] = kb.break_press
        steering_angle[0:19] = kb.steering_angle

    data = np.column_stack((gas_press, break_press, steering_angle))

    for rect, yi in zip(rects, data[i]):
        rect.set_height(yi)
    return rects


def main():
    global rects
    fig = plt.figure()

    objects = ('Gas', 'Break', 'Steering')
    y_pos = np.arange(len(objects))

    rects = plt.bar(y_pos, [0, 0, 0], color='c')
    plt.xticks(y_pos, objects)
    plt.ylim(0, 20)
    plt.yticks(np.linspace(0, 20, 21, endpoint=True))
    plt.ylabel('press')
    plt.title('Car Dashboard')

    context = zmq.Context()
    sendcan = messaging.sub_sock(context, service_list['sendcan'].port)

    # ******** get messages sent to the car ********
    can_msgs = []
    for a in messaging.drain_sock(Plant.sendcan):
        can_msgs.extend(can_capnp_to_can_list(a.sendcan, [0, 2]))
    self.cp.update_can(can_msgs)

    try:
        anim = animation.FuncAnimation(fig, animate, frames=20, interval=20, blit=True)
        plt.show()
    except KeyboardInterrupt:
        print "KeyboardInterrupt Bye"
        kb.finish()
        exit()
    except Exception as e:
        print "exception", e


if __name__ == "__main__":
    main()