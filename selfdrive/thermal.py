"""Methods for reading system thermal information."""
import selfdrive.messaging as messaging

def read_tz(x):
  with open("/sys/devices/virtual/thermal/thermal_zone%d/temp" % x) as f:
    ret = max(0, int(f.read()))
  return ret

def read_tz_linux_cpu(x):
  with open("/sys/devices/platform/coretemp.0/hwmon/hwmon1/temp%d_input" % x) as f:
    ret = int(f.read())/100
  return ret

def read_thermal():
  dat = messaging.new_message()
  dat.init('thermal')
  dat.thermal.cpu0 = read_tz_linux_cpu(2) #read_tz(5)
  dat.thermal.cpu1 = read_tz_linux_cpu(3) #read_tz(7)
  dat.thermal.cpu2 = read_tz_linux_cpu(4) #read_tz(10)
  dat.thermal.cpu3 = read_tz_linux_cpu(5) #read_tz(12)
  dat.thermal.mem = 600#read_tz(2)
  dat.thermal.gpu = 600#read_tz(16)
  dat.thermal.bat = 600#read_tz(29)
  return dat
