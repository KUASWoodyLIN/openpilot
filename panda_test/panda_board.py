import sys
import os
path, panda_path = os.path.split(os.path.dirname(__file__))
sys.path.append(path)

import zmq
from panda import Panda

from collections import defaultdict
from common.realtime import Ratekeeper
from selfdrive.services import service_list
import selfdrive.messaging as messaging
from selfdrive.boardd.boardd import can_list_to_can_capnp, can_capnp_to_can_list

#serial = u'1f0032000651363038363036'  # recv
serial = u'360058000651363038363036'  # phone used
#serial = u'520039000651363038363036'    # send


def main(rate=100):
  panda_list = Panda.list()
  rk = Ratekeeper(rate)
  context = zmq.Context()

  # *** publishes can and health
  logcan = messaging.pub_sock(context, service_list['can'].port)
  health_sock = messaging.pub_sock(context, service_list['health'].port)

  # *** subscribes to can send
  sendcan = messaging.sub_sock(context, service_list['sendcan'].port)

  if serial in panda_list:
    panda = Panda(serial)
    panda.set_safety_mode(panda.SAFETY_ALLOUTPUT)
    panda.can_clear(0)
    print 'Connect Panda [Recv]'

    while True:

      # ******** get messages sent to the car *********
      can_msgs = panda.can_recv()
      can_msgs_bytes = []
      for address, _, dat, src in can_msgs:
        can_msgs_bytes.append((address, 0, bytes(dat), src))

      # ************* health packet @ 1hz *************
      if (rk.frame % rate) == 0:
        health = panda.health()
        msg = messaging.new_message()
        msg.init('health')

        # store the health to be logged
        msg.health.voltage = health['voltage']
        msg.health.current = health['current']
        msg.health.started = bool(health['started'])
        msg.health.controlsAllowed = bool(health['controls_allowed'])
        msg.health.gasInterceptorDetected = bool(health['gas_interceptor_detected'])
        msg.health.startedSignalDetected = bool(health['started_signal_detected'])

        health_sock.send(msg.to_bytes())

      # ************** publish to logger **************
      # TODO: refactor for speed
      if len(can_msgs) > 0:
        dat = can_list_to_can_capnp(can_msgs)
        logcan.send(dat.to_bytes())

      # ******** send can if we have a packet *********
      tsc = messaging.recv_sock(sendcan)
      if tsc is not None:
        panda.can_send_many(can_capnp_to_can_list(tsc.sendcan))

      # **************** print message ****************
      if (rk.frame % rate) == 1:
        if can_msgs:
          print can_msgs
        print 'voltage: ', health['voltage'], 'current: ', health['current'], 'started: ', health['started']

      rk.keep_time()
    else:
      print 'Panda connent fald'


if __name__ == '__main__':
  main()
