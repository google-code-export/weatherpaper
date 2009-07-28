#!/bin/bash

#Copyright (c) 2009 Steven Nichols <Steven@Steven-Nichols.com>
#
#Permission is hereby granted, free of charge, to any person obtaining a copy
#of this software and associated documentation files (the "Software"), to deal
#in the Software without restriction, including without limitation the rights
#to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
#copies of the Software, and to permit persons to whom the Software is
#furnished to do so, subject to the following conditions:
#
#The above copyright notice and this permission notice shall be included in
#all copies or substantial portions of the Software.
#
#THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
#IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
#FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
#AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
#LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
#OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
#THE SOFTWARE.

DATA_FOLDER="$HOME/.weatherpaper"
PROGRAM_FOLDER="/opt/WeatherPaper"

# Make sure only root can run our script
if [ "$(id -u)" != "0" ]; then
   echo "This script must be run as root" 1>&2
   exit 1
fi

# If the data folder does not exist...
# Wouldn't want to overwrite someones settings.
if [ ! -d "$DATA_FOLDER" ]; then
    # Make the data folder
    mkdir "$DATA_FOLDER"
    # Copy necessary files
    cp settings.cfg "$DATA_FOLDER"
    cp tango.zip "$DATA_FOLDER"
fi

# Make the program folder
mkdir "$PROGRAM_FOLDER"
# Copy files
cp weatherpaper.py "$PROGRAM_FOLDER"
cp pywapi.py "$PROGRAM_FOLDER"
cp zipfile.py "$PROGRAM_FOLDER"
cp arialbd.ttf "$PROGRAM_FOLDER"
cp LICENSE.txt "$PROGRAM_FOLDER"

