import zmq
import selfdrive.messaging as messaging
from selfdrive.services import service_list
from common.realtime import sec_since_boot, set_realtime_priority, Ratekeeper


def main():
    # start the loop
    set_realtime_priority(2)

    context = zmq.Context()

    vision = messaging.pub_sock(context, service_list['vision'].port)

    rk = Ratekeeper(6, print_delay_threshold=2. / 1000)

    i = 0
    while 1:
        lead = messaging.new_message()
        lead.init('vision')

        lead.vision.dRel = i
        lead.vision.yRel = i
        lead.vision.vRel = i
        lead.vision.aRel = i
        lead.vision.vLead = i
        lead.vision.aLead = i
        lead.vision.dPath = i
        lead.vision.vLat = i
        i = i +1
        vision.send(lead.to_bytes())
        print lead

        rk.keep_time()


if __name__ == "__main__":
    main()
