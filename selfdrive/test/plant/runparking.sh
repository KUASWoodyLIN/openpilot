#!/bin/bash

export OPTEST=1
export OLD_CAN=1

pushd ../../visiondparking
./parking.py &
pid1=$!
./test_parking.py &
pid2=$!
trap "trap - SIGTERM && kill $pid1 && kill $pid2" SIGINT SIGTERM EXIT
