import sys
import os
import time
path, panda_path = os.path.split(os.path.dirname(__file__))
sys.path.append(path)

from panda import Panda
from common.realtime import Ratekeeper

#serial = u'1f0032000651363038363036'    # recv
serial = u'360058000651363038363036'    # send

def check_recv_alive(rk, rate, panda):
    recv_alive = False
    while not recv_alive:
        can_msgs = panda.can_recv()
        for address, _, dat, src in can_msgs:
            recv_alive = True if address == 426 and dat == 'Start' else False
        if (rk.frame % rate) == 1:
            print can_msgs
        rk.keep_time()
    panda.can_send(0x1aa, 'Start', 0)


def main(rate=100):

    rk = Ratekeeper(rate)

    panda_list = Panda.list()

    if serial in panda_list:
        panda = Panda(serial)
        panda.set_safety_mode(panda.SAFETY_ALLOUTPUT)
        panda.can_clear(0)
        print 'Connect Panda [Send]'
        check_recv_alive(rk, rate, panda)

        while True:
            for i in range(255):
                panda.can_send(0x1aa, str(i), 0)
                if (rk.frame % rate) == 1:
                    health = panda.health()
                    print 'voltage: ', health['voltage'], 'current: ', health['current'], 'started: ', health['started']

                rk.keep_time()
    else:
        print 'Not Panda connect'


if __name__ == '__main__':
    main()
