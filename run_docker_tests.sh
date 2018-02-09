#!/bin/bash
set -e

docker build -t tmppilot -f Dockerfile.openpilot .

docker run --rm \
  -v "$(pwd)"/selfdrive/test/tests/plant/out:/tmp/openpilot/selfdrive/test/tests/plant/out \
  tmppilot /bin/sh -c 'cd /tmp/openpilot/selfdrive/test/tests/plant && OPTEST=1 ./test_longitudinal.py'


sudo docker run -it --name openpilot \
  --privileged \
  -v /dev/bus/usb:/dev/bus/usb \
  -v /dev/video0:/dev/video0 \
  -v "$(pwd)":/home/share/openpilot \
  -v /tmp/.X11-unix:/tmp/.X11-unix \
  -e DISPLAY=unix$DISPLAY \
  -e USER=root \
  tmppilot
