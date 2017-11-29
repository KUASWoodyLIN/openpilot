import sys
import os
path, panda_path = os.path.split(os.path.dirname(__file__))
sys.path.append(path)

import zmq
import selfdrive.messaging as messaging
from selfdrive.services import service_list
from common.realtime import sec_since_boot, set_realtime_priority, Ratekeeper

def main():
    # start the loop
    set_realtime_priority(2)


    context = zmq.Context()

    vision = messaging.sub_sock(context, service_list['vision'].port)

    rk = Ratekeeper(2, print_delay_threshold=1. /1000)

    while 1:
        # lead_msgs = []
        # last_lead = None
        # for a in messaging.drain_sock(vision):
        #     lead_msgs.append(a)
        # if lead_msgs:
        #     last_lead = lead_msgs[-1]
        # print last_lead

        lead = messaging.recv_sock(vision)
        if lead is not None:
            dRel = lead.vision.dRel
            yRel = lead.vision.yRel
            vRel = lead.vision.vRel
            aRel = lead.vision.aRel
            vLead = lead.vision.vLead
            aLead = lead.vision.aLead
            dPath = lead.vision.dPath
            vLat = lead.vision.vLat
            vLeadk = lead.vision.vLeadK
            aLeadk = lead.vision.aLeadK
        print lead

        rk.keep_time()


if __name__ == '__main__':
    main()
