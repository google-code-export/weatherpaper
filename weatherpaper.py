#!/usr/bin/env python

#Copyright (c) 2009 Steven Nichols <Steven@Steven-Nichols.com>

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

"""
Displays desktop wallpaper corresponding to the weather outside.
"""

__version__ = "0.1.6"

import os
import sys
import platform
import random
import math
import time
import string
from datetime import datetime, timedelta
import urllib2
import shutil
from xml.etree.ElementTree import parse
import ConfigParser
import zipfile

import pywapi
import Image
import ImageDraw
import ImageFont
#import TextOverlay

from SingleInstance import *

if(sys.platform == 'win32'):
    import ctypes


# Define constants
_PROG_SETTINGS_FILE = 'settings.cfg'
_IMAGE_META_FILE = "wallpapers.xml"
_OVERLAY_FILE = "overlay.xml"
_DEFAULT_FONT = "arialbd.ttf"
_DEFAULT_FONT_SIZE = 14
_DEFAULT_FONT_COLOR = "black"
_WEATHER_ERROR_CODE = "-1"

if(sys.platform == 'win32'):
    _PROG_WORKING_DIR = os.path.join(os.environ['APPDATA'], "WeatherPaper")
    _TEMP_DIR = os.path.join(os.environ['TMP'], "weatherpaper")
else:
    _PROG_WORKING_DIR = os.path.join(os.environ['HOME'], ".weatherpaper")
    _TEMP_DIR = os.path.join("/tmp", "weatherpaper")
if platform.release() == "XP":
    _OUTPUT_FILE = "wallpaper.bmp"
else:
    _OUTPUT_FILE = "wallpaper.jpg"
    
# Global settings dictionary
AppSettings = {}

def detectOS():
    # this was adapted from:
    # http://gitweb.compiz-fusion.org/?p=fusion/misc/compiz-manager;a=blob;f=compiz-manager
    # TODO: is there a better way to implement this ?
    if os.name == 'nt': return 'windows'
    elif os.name == 'mac': return 'mac'
    elif os.getenv('KDE_FULL_SESSION') == 'true': return 'kde'
    elif os.getenv('GNOME_DESKTOP_SESSION_ID') != '': return 'gnome'
    else: return ''

def loadSettings():
    """Load program settings from a configuration file into the global
    settings file.

    """    
    config = ConfigParser.RawConfigParser()
    config.read(os.path.join(_PROG_WORKING_DIR, _PROG_SETTINGS_FILE))
    
    s = {}
    
    # General program settings
    s['location_id'] = config.get('General', 'location_id')
    s['metric_units'] = config.getboolean('General', 'metric_units')
    s['screen_width'] = config.getint('General', 'screen_width')
    s['screen_height'] = config.getint('General', 'screen_height')
    s['refresh_delay'] = config.getint('General', 'refresh_delay')
    s['hot_threshold'] = config.getint('General', 'hot_threshold')
    s['cold_threshold'] = config.getint('General', 'cold_threshold')
    s['use_feels_like'] = config.getboolean('General', 'use_feels_like')
    s['wallpaper_pack'] = os.path.join(_PROG_WORKING_DIR, config.get('General', 'wallpaper_pack'))
    #s['symlink_enabled'] = config.getboolean('General', 'symlink_enabled')
    s['overlay_enabled'] = config.getboolean('General', 'overlay_enabled')
    
    return s
    
def saveSettings(s):
    """ Writes any changes back to the config file """
    config = ConfigParser.RawConfigParser()
    
    config.set('General', 'overlay_enabled', s['overlay_enabled'])
    config.set('General', 'wallpaper_pack', s['wallpaper_pack'])
    config.set('General', 'use_feels_like', s['use_feels_like'])
    config.set('General', 'cold_threshold', s['cold_threshold'])
    config.set('General', 'hot_threshold', s['hot_threshold'])
    config.set('General', 'refresh_delay', s['refresh_delay'])
    config.set('General', 'screen_height', s['screen_height'])
    config.set('General', 'screen_width', s['screen_width'])
    config.set('General', 'metric_units', s['metric_units'])
    config.set('General', 'location_id', s['location'])
    
    config.write(open(os.path.join(_PROG_WORKING_DIR, _PROG_SETTINGS_FILE), "wb"))

    
def getFahrenheit(tempC):
    """Convert degrees Celcius to degrees Fahrenheit"""
    return tempC * (9.0/5.0) + 32

def getCelcius(tempF):
    """Convert degrees Fahrenheit to degrees Celcius"""
    return (tempF - 32) * (5.0/9.0)
    
def getHeatIndex(temp, humidity):
    """Calculate what a given temperature feels like"""
    global AppSettings
    # Convert temperature to Fahrenheit if needed
    if AppSettings['metric_units']:
        tempF = getFahrenheit(int(temp))
    else:
        tempF = int(temp)
        
    # Convert from string to int
    humidity = int(humidity)
    
    # Heat index cannot be calculated for temperatures < 80 degrees F
    if tempF < 80:
        heat_index = tempF
    else:
        # Forumla from NOAA - http://www.crh.noaa.gov/jkl/?n=heat_index_calculator
        heat_index = (-42.379 + (2.04901523 * tempF) + (10.14333127 * humidity) +
         (-0.22475541 * tempF * humidity) + (-0.00683783 * tempF**2) + 
         (-0.05481717 * humidity**2) + (0.00122874 * tempF**2 * humidity) + 
         (0.00085282 * tempF * humidity**2) + (-0.00000199 * tempF**2 * humidity**2))
    
    # Convert back to Celcius if needed
    if AppSettings['metric_units']:
        heat_index = round(getCelcius(heat_index),0)
    
    return int(heat_index)


def ExtractFile(filename):
    """Extracts a file from a zip archive and returns the path to the extracted file"""
    try:
        zf = zipfile.ZipFile(AppSettings['wallpaper_pack'], "r")
        
        # If this zip contains a directory as the first item
        if zf.namelist()[0][-1:] == '/':
            zf.extract(zf.namelist()[0] + filename, _TEMP_DIR)
            return os.path.join(_TEMP_DIR, zf.namelist()[0] + filename)
        else:
            zf.extract(filename, _TEMP_DIR)
            return os.path.join(_TEMP_DIR, filename)
    except:
        raise
        
    return None

def ReadFileInZip(filename, mode):
    """Return a file object to a file within a zip"""
    try:
        zf = zipfile.ZipFile(AppSettings['wallpaper_pack'], "r")
        
        # If files are contained in a directory
        folder = os.path.dirname(zf.namelist()[0])
        
        if len(folder) != 0:
            if mode == "r":
                print os.path.normpath(folder + "/" + filename)
                fp = zf.open(folder + "/" + filename)
            else:
                zf.extract(folder + "/" + filename, _TEMP_DIR)
                fp = open(os.path.join(_TEMP_DIR, os.path.join(folder, filename)), mode)
                print "Extracting %s from %s" % (filename, AppSettings['wallpaper_pack'])
        else:
            if mode == "r":
                    fp = zf.open(filename)
            else:
                zf.extract(filename, _TEMP_DIR)
                fp = open(os.path.join(_TEMP_DIR, filename), mode)
                print "Extracting %s from %s" % (filename, AppSettings['wallpaper_pack'])
    except:
        raise
        
    return fp

def getWallpaper(code):
    """Returns a random wallpaper from the set of wallpapers 
    matching the given weather code.

    """
    global AppSettings
    
    # Retrieve meta information from XML document
    meta_data = ReadFileInZip(_IMAGE_META_FILE, "r")
    images = parse(meta_data).getroot().findall('image')

    # An array of wallpapers matching the current conditions
    wallpaper = []

    # For each image listed
    for image in images:
        # Get the weather codes for the image
        try:
            # Remove spaces and split using the "," as a deliminator
            codes = image.attrib['codes'].replace(' ','').split(',')
        except KeyError:
            print "Malformed XML document: missing 'codes' attribute in \"%s\"" % image.find('file').text
            continue

        # If the current weather matches the image weather
        if code in codes:
            wallpaper.append(image)
                
            
    #print "# of matching wallpapers =", len(wallpaper)

    # Add some randomness
    random.shuffle(wallpaper)
    
    # If no matches were found
    # try again using the error code
    if len(wallpaper) == 0:
        if code != _WEATHER_ERROR_CODE:
            errorfile = getWallpaper(_WEATHER_ERROR_CODE)
        else:
            print "No error wallpaper defined"
            exit(0)
    
    meta_data.close()
    
    return wallpaper[0]


def drawOverlayFromFile(WStatus):
    """ Draw an overlay on a specified file using the formatting pulled from an 
    XML document. 
    
    """
    
    # Open the image
    try:
        fp = ReadFileInZip(WStatus['filename'], "rb")
    except IOError:
        print "Could not open wallpaper file:\n%s" % WStatus['filename']
        exit(2)
        
    image = Image.open(fp)
    image.load() #Make sure PIL has read the data
    draw = ImageDraw.Draw(image)
      
    # Open the XML document
    xml_file = ReadFileInZip(_OVERLAY_FILE, 'r')
    root = parse(xml_file).getroot()
    
    prev_font = None
    
    for font in root:
        # Font settingsAppSettings['xml_file']
        try:
            size = int(font.attrib['size'])
        except KeyError:
            size = _DEFAULT_FONT_SIZE
        
        try:    
            fill_color = font.attrib['fill']
        except KeyError:
            fill_color = _DEFAULT_FONT_COLOR

        try:
            font_file = font.attrib['file']
        except KeyError:
            if prev_font == None:
                font_obj = ImageFont.truetype(_DEFAULT_FONT, size)
            else:
                font_obj = ImageFont.truetype(prev_font, size)
        else:
            # Extract the font file
            try:
                filename = ExtractFile(font_file)
            except KeyError:
                print "There is no item named %s in the pack." % font_file
                font_obj = ImageFont.truetype(_DEFAULT_FONT, size)
                prev_font = _DEFAULT_FONT
            else:
                font_obj = ImageFont.truetype(filename, size)
                prev_font = filename
        
        # Optional alignment
        try:
            alignment = font.attrib['align']
        except KeyError:
            alignment = None
            
        # Optional border
        try: 
            border = int(font.attrib['border'])
            bordercolor = font.attrib['bordercolor']
        except KeyError:
            border = None
            bordercolor = None
        
        # Draw the line one-by-one
        for line in font:
            # Get the text between the open and close tags
            text = '' if line.text == None else line.text
            
            # If this is not an error message
            if WStatus['code'] != _WEATHER_ERROR_CODE and line.tag != 'errorline':
                # Text replacements
                text = text.replace('%title%', WStatus['title'])
                text = text.replace('%author%', WStatus['author'])
                text = text.replace('%temp%', WStatus['temp'])
                text = text.replace('%degree%', u'\u00B0')
                text = text.replace('%unit%', 'C' if AppSettings['metric_units'] else 'F' )
                text = text.replace('%condition%', WStatus['condition'])
                text = text.replace('%humidity%', WStatus['humidity'])
                text = text.replace('%date%', WStatus['date'])
                text = text.replace('%forecast%', WStatus['forecast'])
                text = text.replace('%feelslike%', str(WStatus['feels_like']))
            # If this is an error message
            elif WStatus['code'] == _WEATHER_ERROR_CODE and line.tag == 'errorline':
                text = text.replace('%errormsg%', WStatus['errormsg'])
            # Otherwise, ignore the line
            else:
                continue

            # The first X-coordinate is manditory, but afterwards, it can be
            # left off. If it is not specified, the previous value of x will
            # be used.
            try:
                x = int(line.attrib['x'])
            except KeyError:
                try:
                    x = x_prev # use the previously defined x value
                except NameError:
                    print "overlay.xml: The first line tag must have x and y coordinates."
                    exit(2)
            else:
                # A negative indicates distance from right edge
                if x < 0: 
                    x = x + image.size[0]   # Add the width of the image
                x_prev = x

            # Align the text right if necessary
            if alignment == "right":
                line_width = draw.textsize(text, font=font_obj)[0]
                x = x - line_width
                
            # The first Y-coordinate is manditory, but afterwards, it can be
            # left off. If it is not specified, the previous value of y will
            # be incremented by the font's line height and used."""
            try:
                y =  int(line.attrib['y'])
            except:
                # increment y by the line-hight
                y = y + draw.textsize(text, font=font_obj)[1]
            else:
                if y < 0: # negative indicates distance from bottom
                    y = y + image.size[1]
                    
            print "x =", x, ", y =", y, ", text =", text
                
            # Draw border if one exists
            if border is not None:
                for i in range(0, border):
                    # Thin border
                    if i == 0:
                        draw.text((x-1, y), text, font=font_obj, fill=bordercolor)
                        draw.text((x+1, y), text, font=font_obj, fill=bordercolor)
                        draw.text((x, y-1), text, font=font_obj, fill=bordercolor)
                        draw.text((x, y+1), text, font=font_obj, fill=bordercolor)
                    else:
                        # Thick border
                        draw.text((x-i, y-i), text, font=font_obj, fill=bordercolor)
                        draw.text((x+i, y-i), text, font=font_obj, fill=bordercolor)
                        draw.text((x-i, y+i), text, font=font_obj, fill=bordercolor)
                        draw.text((x+i, y+i), text, font=font_obj, fill=bordercolor)
            
            # Draw the overlay
            draw.text((x, y), text, font=font_obj, fill=fill_color)
    
    # Load the settings
    output_file = os.path.join(_PROG_WORKING_DIR, _OUTPUT_FILE)
    
    # Save the new file
    if os.path.exists(output_file):
        os.remove(output_file)
    # XP does not support image types other than BMP
    if platform.release() == "XP":
        image.save(output_file, "BMP", quality=100)
    else:
        image.save(output_file, "JPEG", quality=100)
    
    
    # Close and delete temporary file
    filename = fp.name
    fp.close()
    os.remove(filename)


# Create a new image that has the current weather conditions overlayed on the background
'''
def drawOverlay(input_file, text):
    global AppSettings

    try:
        fp = open(input_file, "rb")
    except IOError:
        print "Could not open wallpaper file:\n%s" % input_file
        exit(2)
        
    image = Image.open(fp)
    image.load() #Make sure PIL has read the data
    
    # Load the settings
    output_file = os.path.join(_PROG_WORKING_DIR, _OUTPUT_FILE)
    location = AppSettings['overlay_position']
    fill=AppSettings['overlay_fill_color']
    shadow = AppSettings['overlay_shadow_color']
    font = ImageFont.truetype(AppSettings['overlay_font'], AppSettings['overlay_font_size'])
    
    # Resize the image to match the current resolution
    if( image.size != (AppSettings['screen_width'], AppSettings['screen_height']) ):
        print "Resize from %s to %s" % (image.size, (AppSettings['screen_width'], AppSettings['screen_height']))
        image = image.resize((AppSettings['screen_width'], AppSettings['screen_height']), Image.ANTIALIAS)
    
    # Draw the overlay onto the image   
    TextOverlay.drawTextBorder(image, text, font, fill, shadow, location, AppSettings['overlay_margin_x'], AppSettings['overlay_margin_y'])
    
    # Save the new file
    if os.path.exists(output_file):
        os.remove(output_file)
    # XP does not support image types other than BMP
    if platform.release() == "XP":
        image.save(output_file, "BMP", quality=100)
    else:
        image.save(output_file, "JPEG", quality=100)
    fp.close()
'''


def updateDesktop():
    """Force the desktop to redraw the wallpaper"""
    global AppSettings

    # Detect which OS we are running
    # MS Windows
    if detectOS() == 'windows':
        # http://mail.python.org/pipermail/python-list/2005-July/330379.html
        #shutil.copyfile(os.path.join(images_dir, wallpaper[0].find('file').text), wallpaperfile)
        # Refresh the desktop
        SPI_SETDESKWALLPAPER = 20 # According to http://support.microsoft.com/default.aspx?scid=97142
        ctypes.windll.user32.SystemParametersInfoA(SPI_SETDESKWALLPAPER, 0, os.path.join(_PROG_WORKING_DIR, _OUTPUT_FILE), 0)
        #cs = ctypes.c_buffer(output_file)
        #ctypes.windll.user32.SystemParametersInfoA(win32con.SPI_SETDESKWALLPAPER,0,output_file,0)
        #win32gui.SystemParametersInfo (win32con.SPI_SETDESKWALLPAPER, bmp_path, win32con.SPIF_SENDCHANGE)
        #os.system('RUNDLL32.EXE USER32.DLL,UpdatePerUserSystemParameters ,1 ,True')
    # Mac OS X
    elif detectOS() == 'mac':
        # http://stackoverflow.com/questions/431205/how-can-i-programatically-change-the-background-in-mac-os-x#431273
        import subprocess

        SCRIPT = """/usr/bin/osascript<<END
        tell application "Finder"
        set desktop picture to POSIX file "%s"
        end tell
        END"""

        subprocess.Popen(SCRIPT % os.path.join(_PROG_WORKING_DIR, _OUTPUT_FILE), shell=True)
    # Linux Gnome
    elif detectOS() == 'gnome':
        # http://www.tuxradar.com/content/code-project-use-weather-wallpapers
        cmd = string.join(["gconftool-2 -s /desktop/gnome/background/picture_filename -t string \"",os.path.join(_PROG_WORKING_DIR, _OUTPUT_FILE),"\""],'')
        os.system(cmd)
    elif detectOS() == 'kde': 
            if os.getenv('KDE_SESSION_VERSION') == '':
                # KDE 3.5
                cmd = "dcop kdesktop KBackgroundIface setWallpaper %s 6" % os.path.join(_PROG_WORKING_DIR, _OUTPUT_FILE)
                os.system(cmd)
            else:
                # KDE 4
                cmd = "kwriteconfig --file plasma-appletsrc --group Containments --group 1 --group Wallpaper --group image --key wallpaper %s" % os.path.join(_PROG_WORKING_DIR, _OUTPUT_FILE)
                os.system(cmd)
    else:
        # Attempt to create a symbolic link from the old to the new wallpaper
        try:
            os.remove(AppSettings['symlink'])
        except OSError:
            pass
        os.symlink(os.path.join(_PROG_WORKING_DIR, _OUTPUT_FILE), os.path.join(_PROG_WORKING_DIR, 'symlink'))
        

def updateWallpaper(WStatus):
    """Performs the updating of the wallpaper.
    Tasks: draw overlay, copy file, call updateDesktop()
    
    """
    global AppSettings
        
    # If a corner has been specified for the overlay
    if AppSettings['overlay_enabled']:
        # Create a new image that has the current weather conditions overlayed on the background
        # Draw the overlay onto the image   
        #drawOverlay(os.path.join(AppSettings['images_dir'], WStatus['filename']), text)
        drawOverlayFromFile(WStatus)
    else:
        # Don't draw overlay, just copy the file
        shutil.copyfile(os.path.join(AppSettings['images_dir'], WStatus['filename']), os.path.join(_PROG_WORKING_DIR, _OUTPUT_FILE))

    # Force the desktop to update the wallpaper
    updateDesktop()    


def ReadCredits():
    """Read the Title, Author and URL from the Metadata file"""

    try:
        fp =  ReadFileInZip(_IMAGE_META_FILE, "r")
    except IOError, KeyError:
        print "Could not open file %s" % _IMAGE_META_FILE
        exit(2)

    for line in fp:
        # Extract the title
        index = line.find("@title")
        if index != -1:
            print line[index+6:].strip()
        
        # Extract the author
        index = line.find("@author")
        if index != -1:
            print line[index+7:].strip()
        
        # Extract the url 
        index = line.find("@url")
        if index != -1:
            print line[index+4:].strip()
    
def main():
    """ Main function of Weather Wallpaper """
    global AppSettings
    
    # Weather Status dictionary
    # Contains all the weather information that gets passed between functions
    # These may be referenced from overlay.xml by placing "%" around the name,
    # as in; "%temp%" or "%author%".
    WStatus = {
        'title': '',
        'author': '',
        'filename': '',
        'code': '',
        'temp': '',
        'feels_like': '',
        'condition': '',
        'date': '',
        'humidity': '',
        'wind_chill': '',
        'forecast': '',
        'temp_unit': '',
    }    

    # Previous weather conditions haven't been set yet
    previous_weather_code = -1
    previous_weather_date = ''

    # Initialize last update to one week ago to make sure we update on start
    lastUpdate = datetime.now() - timedelta(days = 7)

    #Start main loop
    while(True):
        # Get the current time
        now = datetime.now()
        # Compare current time to last update timestaWStatusmp
        # This is better than using wait() because it forces a refresh immidiately
        # after resuming from suspend/hibernate
        if (now - lastUpdate) > timedelta(minutes = AppSettings['refresh_delay']):
            # update the timestamp
            lastUpdate = now
            
            # Retrive current weather from yahoo weather
            # The complete documentation for the Yahoo Weather RSS feed
            # can be found at http://developer.yahoo.com/weather/
            weather = None
            try:
                weather = pywapi.get_weather_from_yahoo(AppSettings['location_id'], 'metric' if AppSettings['metric_units'] else '')
            except urllib2.URLError:
                print "Could Not Connect"
                # Reset weather date so that the error image is replace when 
                # the connection is re-established
                previous_weather_date = ''
                # Draw status on image
                if AppSettings['overlay_enabled']:
                    # Create error object
                    WError = {
                        'code': _WEATHER_ERROR_CODE,
                        'errormsg': 'Could Not Connect',
                        'filename': None
                    }
                    wallpaper = getWallpaper(WError['code'])
                    WError['filename'] = wallpaper.find('file').text
                    print WStatus['filename']
                    drawOverlayFromFile(WError)
                    #drawOverlay(os.path.join(AppSettings['images_dir'], wallpaper.find('file').text), text)
                    updateDesktop()
                # Retry every 5 seconds
                while weather is None:
                    time.sleep(5)
                    try: 
                        weather = pywapi.get_weather_from_yahoo(AppSettings['location_id'], 'metric' if AppSettings['metric_units'] else '')
                    except urllib2.URLError:
                        pass
            
            # Retrieve the date/time this weather info was issued
            WStatus['date'] = weather['condition']['date']
            
            # Update the wallpaper only when newer data is available
            if previous_weather_date != WStatus['date']:
                previous_weather_date = WStatus['date']
                
                # Retrieve the new weather information
                WStatus['code'] = weather['condition']['code']
                WStatus['temp'] = weather['condition']['temp']
                WStatus['condition'] = weather['condition']['text']
                WStatus['humidity'] = weather['atmosphere']['humidity']
                WStatus['wind_chill'] = weather['wind']['chill']
                WStatus['forecast'] = weather['forecasts'][0]['text']
                WStatus['temp_unit'] = weather['units']['temperature']
                
                # Feels like temperature
                if (WStatus['temp_unit'] == 'F' and int(WStatus['temp']) > 80) \
                  or (WStatus['temp_unit'] == 'C' and int(WStatus['temp']) > 27):
                    WStatus['feels_like'] = getHeatIndex(WStatus['temp'], WStatus['humidity'])     
                elif (WStatus['temp_unit'] == 'F' and int(WStatus['temp']) < 50) \
                  or (WStatus['temp_unit'] == 'C' and int(WStatus['temp']) < 10):
                    WStatus['feels_like'] = WStatus['wind_chill']
                else:
                    WStatus['feels_like'] = WStatus['temp']

                print WStatus['date']
                print 'Weather Code:',  WStatus['code'], "(%s)" %  WStatus['condition']
                print 'Current temperature: %s (feels like %s)' % (WStatus['temp'],  WStatus['feels_like'])
            
                # Force a change the weather code
                if AppSettings['use_feels_like']:
                    if int(WStatus['feels_like']) >= AppSettings['hot_threshold']:
                        WStatus['code'] = '36' # HOT!
                    elif int(WStatus['feels_like']) <= AppSettings['cold_threshold']:
                        WStatus['code'] = '25' # COLD!
                else:
                    if int(WStatus['temp']) >= AppSettings['hot_threshold']:
                        WStatus['code'] = '36' # HOT!
                    elif int(WStatus['temp']) <= AppSettings['cold_threshold']:
                        WStatus['code'] = '25' # COLD!
                        
                
                # Only update the image if the condition has changed
                if(int(WStatus['code']) != int(previous_weather_code)):
                    print "Select a new wallpaper (Conditions changed from %s to %s)"%(
                        previous_weather_code, WStatus['code'])
                
                    # Bring the variable up to date
                    previous_weather_code = WStatus['code']
                    
                    # Get a random wallpaper matching the current condition
                    wallpaper = getWallpaper(WStatus['code'])

                    # Get the title and author of the wallpaper
                    try:
                        WStatus['title'] = wallpaper.find('title').text
                    except (KeyError, AttributeError):
                        WStatus['title'] = ''
                        
                    try:
                        WStatus['author'] = wallpaper.find('author').text
                    except (KeyError, AttributeError):
                        WStatus['author'] = ''
                    
                    WStatus['filename'] = wallpaper.find('file').text
                
                # Does the following as necessary:
                # Write conditions file, draw overlay, copy image file, call updateDesktop()
                updateWallpaper(WStatus)
            
        # Short delay, this is the minimum "refresh rate"
        time.sleep(10) # Ten seconds
        
        # Update settings
        # This allows live updating without restarts
        AppSettingsNew = loadSettings()
        # If settings have changed since the last time we checked
        if AppSettings != AppSettingsNew:
            print "Change to settings file detected"
            
            
            # Update the settings
            AppSettings = AppSettingsNew
            
            # Force a full refresh
            updateWallpaper(WStatus)
            previous_weather_date = ''
            lastUpdate = datetime.now() - timedelta(days = 7)
        
    # Before exiting remove our lock so this process can be run again
    appInstance.exitApplication()
    
    
if __name__ == "__main__":
    # Change the current working directory to where this program is located.
    # This allows us to use relative paths
    #pathname = os.path.dirname(sys.argv[0])
    #fullpath = os.path.abspath(pathname) 
    #os.chdir(fullpath)

    # Prevent multiple copies of this process from running simultaneously
    #appInstance = ApplicationInstance('weatherpaper.pid')
    
    # Load the dictionary of program settings
    AppSettings = loadSettings()
    
    #ReadCredits()
    
    # Run main
    try:
        main()
    finally:
        # Clean up temporary files
        shutil.rmtree(_TEMP_DIR, True)
