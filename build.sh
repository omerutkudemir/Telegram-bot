#!/bin/bash
set -e
apt-get update
apt-get install -y google-chrome-stable
pip install -r requirements.txt
