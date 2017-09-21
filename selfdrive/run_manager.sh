#!/bin/bash

export PYTHONPATH="${PYTHONPATH}://home/woodylin/github/openpilot"
export PREPAREONLY=1
export OPTEST=1
export OLD_CAN=1
export NOBOARD
export NOPROG
export NOLOG
export NOUPLOAD
export NOVISION
export LEAN
export NOCONTROL

./manager.py
