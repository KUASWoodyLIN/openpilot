import time
import zmq
import selfdrive.messaging as messaging

from cereal import car, log
from common.realtime import set_realtime_priority

print 8
from selfdrive.services import service_list
from selfdrive.car import get_car
from selfdrive.controls.lib.planner import Planner
from selfdrive.controls.lib.adaptivecruise import compute_speed_with_leads
from selfdrive.controls.lib.drive_helpers import learn_angle_offset
from selfdrive.controls.lib.longcontrol import LongControl
from selfdrive.controls.lib.latcontrol import LatControl
from selfdrive.controls.lib.vehicle_model import VehicleModel
print 7

def main(gctx=None):
    # start the loop
    set_realtime_priority(2)

    context = zmq.Context()
    # pub
    sendcan = messaging.pub_sock(context, service_list['sendcan'].port)
    # sub
    logcan = messaging.sub_sock(context, service_list['can'].port)

    CC = car.CarControl.new_message()
    l20 = log.Live20Data.new_message()
    CI, CP = get_car(logcan, sendcan)
    PL = Planner(CP)
    LoC = LongControl(CI.compute_gb)
    VM = VehicleModel(CP)
    LaC = LatControl(VM)
    v_cruise_kph = 30   # set cruise v
    vTarget = 30        # set Target v (front car)


    while 1:
        # 1
        CS = CI.update(CC)

        # 2
        plan_packet = PL.update(CS, LoC)
        plan = plan_packet.plan

        # 3
        # not yet

        # 4
        # make fake l20 message
        l1 = l20.leadOne
        l2 = l20.leadTwo
        l1.status = True
        actuators = car.CarControl.Actuators.new_message()
        active = True
        learn_angle_offset()
        actuators.gas, actuators.brake = LoC.update(active, CS.vEgo, CS.brakePressed, v_cruise_kph,
                                                    plan.vTarget, [plan.aTargetMin, plan.aTargetMax], plan.jerkFactor, CP)
        LaC.update()

        time.sleep(1)

if __name__ == "__main__":
    main()