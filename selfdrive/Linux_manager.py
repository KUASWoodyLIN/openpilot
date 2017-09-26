import os
import sys
import time
import importlib
import subprocess
import signal
import traceback
import usb1
from multiprocessing import Process
sys.path.append('/home/woodylin/github/openpilot')
from selfdrive.services import service_list

#import hashlib
import zmq

from setproctitle import setproctitle

from selfdrive.swaglog import cloudlog
import selfdrive.messaging as messaging
from selfdrive.thermal import read_thermal
from selfdrive.registration import register #"imei" "serial"just work on phone, so on linux can't get "dongle_id" and "access_token"
from selfdrive.version import version

import common.crash as crash
from common.params import Params

from selfdrive.loggerd.config import ROOT

BASEDIR = os.path.join(os.path.dirname(os.path.realpath(__file__)), "../")
baseui_running = False

managed_processes = {
  #"uploader": "selfdrive.loggerd.uploader",
  "controlsd": "selfdrive.controls.controlsd",
  "radard": "selfdrive.controls.radard",
  #"loggerd": ("loggerd", ["./loggerd"]),
  #"logmessaged": "selfdrive.logmessaged",
  #"tombstoned": "selfdrive.tombstoned",
  #"logcatd": ("logcatd", ["./logcatd"]),
  #"proclogd": ("proclogd", ["./proclogd"]),
  #"boardd": ("boardd", ["./boardd"]),   # switch to c++ boardd
  #"ui": ("ui", ["./ui"]),
  #"visiond": ("visiond", ["./visiond"]),
  #"sensord": ("sensord", ["./sensord"]), 
  }

running = {}
def get_running():
  return running

# processes to end with SIGINT instead of SIGTERM
interrupt_processes = []

car_started_processes = [
  'controlsd',
  'loggerd',
  'sensord',
  'radard',
  'visiond',
  'proclogd',
]

def launcher(proc,gctx):
    try:
        #import the process
        mod = importlib.import_module(proc)
        
        #rename the process
        setproctitle(proc)

        #exec the process
        mod.main(gctx)
    except KeyboardInterrupt:
        cloudlog.info("child %s got ctrl-c" % proc)
    except Exception:
        crash.capture_exception()
        raise

def nativelauncher(pargs, cwd):
    #exec the process
    print "now in ",cwd
    os.chdir(cwd)

    #because when extracted from pex zips permissions get lost
    os.chmod(pargs[0], 0o700)
    
    os.execvp(pargs[0],pargs)


def start_managed_process(name):
    if name in running or name not in managed_processes:
        return
    proc = managed_processes[name]
    if isinstance(proc,basestring):
        cloudlog.info("starting python %s" % proc)
        running[name] = Process(name=name, target=launcher, args=(proc,gctx))
    else:
        pdir, pargs = proc
        cwd = os.path.join(BASEDIR,"selfdrive")
        if pdir is not None:
            cwd = os.path.join(cwd,pdir)
        cloudlog.info("starting process %s" % name)
        running[name] = Process(name=name, target=nativelauncher, args=(pargs,cwd))
    running[name].start()

def kill_managed_process(name):
    if name not in running or name not in managed_processes:
        return
    cloudlog.info("killing %s" % name)

    if running[name].exitcode is None:
        if name in interrupt_processes:
            os.kill(running[name].pid, signal.SIGINT)
        else:
            running[name].terminate()

        # give it 5 seconds to die
        running[name].join(5.0)
        if running[name].exitcode is None:
            cloudlog.critical("unkillable process %s failed to exit! rebooting in 15 if it doesn't die" % name)
        else:
            cloudlog.info("killing %s with SIGKILL" % name)
            os.kill(running[name].pid, signal.SIGKILL)
            running[name].join()

    cloudlog.info("%s is dead with %d" %(name, running[name].exitcode))
    del running[name]

def cleanup_all_processes(signal, frame):
    cloudlog.info("caught ctrl-c %s %s" % (signal, frame))
    for name in running.keys():
        kill_managed_process(name)
    sys.exit(0)

def system(cmd):
    try:
        cloudlog.info("running %s" % cmd)
        subprocess.check_output(cmd, stderr=subprocess.STDOUT, shell=True)
    except subprocess.CalledProcessError, e:
        cloudlog.event("running failed",
            cmd = e.cmd,
            output = e.output,
            returncode = e.returncode)

def manager_thread():
    global baseui_running

    #new loop
    context = zmq.Context()
    thermal_sock = messaging.pub_sock(context,service_list['thermal'].port)
    health_sock = messaging.sub_sock(context,service_list['health'].port)

    cloudlog.info("manager start")
    cloudlog.info(dict(os.environ))

    panda = False
    """if os.getenv("NOBOARD") is None:
        # *** wait for board ***
        panda = wait_for_device() == 0x2300

    #flash the device
    if os.getenv("NOPROG") is None:
        #flash the board
        boarddir = os.path.join(BASEDIR,"panda/board/")
        mkfile = "Makefile" if panda else "Makefile.legacy"
        print "using",mkfile
        system("cd %s && make -f %s" % (boarddir,mkfile))"""

    start_managed_process("boardd")
    
    started = False
    logger_dead = False
    count = 0
    #set 5 second timeout on health socket
    #5x slower than expected
    health_sock.RCVTIMEO = 5000

    while 1:
        # get health of board, log this in "thermal"
        td = messaging.recv_sock(health_sock,wait=True) 
        td = messaging.new_message()
        td.init('health')
        td.health.started = True
        print td

        # replace thermald
        msg = read_thermal()

        # thermal message now also includes free space
        avail = 1.0
        msg.thermal.freeSpace = avail
        msg.thermal.batteryPercent = 100
        msg.thermal.batteryStatus = "Charging"
        
        thermal_sock.send(msg.to_bytes())
        print msg

        # TODO: add car battery voltage check
        max_temp = max(msg.thermal.cpu0, msg.thermal.cpu1,
                       msg.thermal.cpu2, msg.thermal.cpu3) / 10.0

        # start constellation of processes when the car starts
        # with 2% left, we killall, otherwise the phone is bricked
        if td is not None and td.health.started and avail >0.02:
            if not started:
                Params().car_start()
                started = True
            for p in car_started_processes:
                start_managed_process(p)
        else:
            started = False
            for p in car_started_processes:
                kill_managed_process(p)

            if msg.thermal.batteryPercent < 5 and msg.thermal.batteryStatus == "Discharging":
                os.system('LD_LIBRARY_PATH="" svc power shutdown')

        # check the status of all processes, did any of them die?
        for p in running:
            cloudlog.debug("    running %s %s" % (p, running[p]))

        if (count%60) == 0:
            cloudlog.event("STATUS_PACKET",
                running=running.keys(),
                count=count,
                health=(td.to_dict() if td else None),
                thermal=msg.to_dict())

        count += 1

# optional, build the c++ binaries and preimport the python for speed
def manager_prepare():
  # update submodules
  system("cd %s && git submodule init panda opendbc pyextra" % BASEDIR)
  system("cd %s && git submodule update panda opendbc pyextra" % BASEDIR)

  # build cereal first
  subprocess.check_call(["make", "-j4"], cwd=os.path.join(BASEDIR, "cereal"))

  # build all processes
  os.chdir(os.path.dirname(os.path.abspath(__file__)))
  for p in managed_processes:
    proc = managed_processes[p]
    if isinstance(proc, basestring):
      # import this python
      cloudlog.info("preimporting %s" % proc)
      importlib.import_module(proc)
    else:
      # build this process
      cloudlog.info("building %s" % (proc,))
      try:
        subprocess.check_call(["make", "-j4"], cwd=proc[0])
      except subprocess.CalledProcessError:
        # make clean if the build failed
        cloudlog.info("building %s failed, make clean" % (proc, ))
        subprocess.check_call(["make", "clean"], cwd=proc[0])
        subprocess.check_call(["make", "-j4"], cwd=proc[0])


def wait_for_device():
    while 1:
        try:
            context = usb1.USBContext()
            for device in context.getDeviceList(skip_on_error=True):
                if (device.getVendorID() == 0xbbaa and device.getProductID() == 0xddcc) or \
                   (device.getVendorID() == 0x0483 and device.getProductID() == 0xdf11):
                   bcd = device.getbcdDevice()
                   handle = device.open()
                   handle.claimInterface(0)
                   cloudlog.info("found board")
                   handle.close()
                   return bcd
                print device
        except Exception as e:
            print "exception", r,
        print "waiting ..."
        time.sleep(1)

def main():
    params = Params()
    params.manager_start()

    if params.get("IsMetric") is None:
        params.put("IsMetric",0)
    if params.get("IsRearViewMirror") is None:
        params.put("IsRearViewMirror",1)

    #manage_init
    #os.umask(0)
    global gctx
    gctx = {}
    """try:
        manager_prepare()
    except Exception:
        traceback.print_exc()"""

    try:
        manager_thread()
    except Exception:
        traceback.print_exc()
    finally:
        cleanup_all_processes(None,None)

if __name__ == "__main__":
    main()
        