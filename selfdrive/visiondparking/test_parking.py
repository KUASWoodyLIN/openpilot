import zmq

import selfdrive.messaging as messaging
from selfdrive.services import service_list
from common.realtime import set_realtime_priority, Ratekeeper

def main():
    rate = 20

    context = zmq.Context()
    parking = messaging.sub_sock(context, service_list['parking'].port)

    working = False
    find = False
    longitudinal = .0
    lateral = .0

    rk = Ratekeeper(rate,print_delay_threshold=2./1000)
    while 1:
        pkg = messaging.recv_sock(parking)
        if pkg is not None:
            working = pkg.parking.working
            find = pkg.parking.findtarget
            longitudinal = pkg.parking.targetLoc
            lateral = pkg.parking.targetLac
        
        print("Working:",working," Find:",find," Loc:",longitudinal," Lac:",lateral)
        rk.keep_time()

if __name__ == "__main__":
    main()