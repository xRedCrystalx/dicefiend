#!/bin/bash

cd /opt/dicefiend
source .venv/bin/activate

clear
while true; do
    python3 main.py
    echo "Python script crashed or exited. Restarting in 5 seconds..."
    sleep 5
done