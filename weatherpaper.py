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

__version__ = "0.1.5"

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

import pywapi
import Image
import ImageDraw
import ImageFont
import TextOverlay

from SingleInstance import *

if(sys.platform == 'win32'):
    import ctypes

# Global settings dictionary
AppSettings = {}

def loadSettings(settings_file='settings.cfg'):
    """Load program settings from a configuration file into the global
    settings file.

    """    
    config = ConfigParser.RawConfigParser()
    config.read(settings_file)
    
    s = {}
    
    # General program settings
    s['location_id'] = config.get('General', 'location_id')
    s['metric_units'] = config.getboolean('General', 'metric_units')
    s['screen_width'] = config.getint('General', 'screen_width')
    s['screen_height'] = config.getint('General', 'screen_height')
    s['refresh_delay'] = config.getint('General', 'refresh_delay')
    s['hot_threshold'] = config.getint('General', 'hot_threshold')
    s['use_heat_index'] = config.getboolean('General', 'use_heat_index')
    s['weather_error_code'] = config.get('General', 'weather_error_code')
    
    # File and folder path settings
    if(config.getboolean('Paths', 'relative_paths')):
        # Make all paths relative
        s['images_dir'] = os.path.join(os.getcwd(), config.get('Paths', 'images_dir'))
        s['wallpaper_file'] = os.path.join(s['images_dir'], config.get('Paths', 'wallpaper_file'))
        s['symlink'] = os.path.join(s['images_dir'], config.get('Paths', 'symlink'))
        s['symlink_enabled'] = config.getboolean('Paths', 'symlink_enabled')
        s['image_meta_file'] = os.path.join(s['images_dir'], config.get('Paths', 'image_meta_file'))
        s['overly_file'] = os.path.join(s['images_dir'], 'overlay.xml')
        s['conditions_file'] = os.path.join(os.getcwd(), config.get('Paths', 'conditions_file'))
        s['conditions_file_enabled'] = config.getboolean('Paths', 'conditions_file_enabled')
    else:
        # Use absolute paths
        s['images_dir'] = config.get('Paths', 'images_dir')
        s['wallpaper_file'] = config.get('Paths', 'wallpaper_file')
        s['symlink'] = config.get('Paths', 'symlink')
        s['symlink_enabled'] = config.getboolean('Paths', 'symlink_enabled')
        s['image_meta_file'] = config.get('Paths', 'image_meta_file')
        s['conditions_file'] = config.get('Paths', 'conditions_file')
        s['conditions_file_enabled'] = config.getboolean('Paths', 'conditions_file_enabled')
    
    # If this is Windows XP, wallpaper must be a BMP.
    if platform.release() == "XP":
        s['wallpaper_file'] += '.bmp'
    else:
        s['wallpaper_file'] += '.jpg'
    
    # Text overlay settings
    s['overlay_enabled'] = config.getboolean('Overlay', 'overlay_enabled')
    s['overlay_position'] = config.getint('Overlay', 'overlay_position')
    s['overlay_margin_x'] = config.getint('Overlay', 'overlay_margin_x')
    s['overlay_margin_y'] = config.getint('Overlay', 'overlay_margin_y')
    s['overlay_font'] = config.get('Overlay', 'overlay_font')
    s['overlay_font_size'] = config.getint('Overlay', 'overlay_font_size')
    s['overlay_fill_color'] = config.get('Overlay', 'overlay_fill_color')
    s['overlay_shadow_color'] = config.get('Overlay', 'overlay_shadow_color')
    return s
    
def saveSettings(settings_file='settings.cfg'):
    print "saveSettings not implemented" 
    
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
        heat_index = -42.379 + (2.04901523 * tempF) + (10.14333127 * humidity) + (-0.22475541 * tempF * humidity)  + (-0.00683783 * tempF**2) + (-0.05481717 * humidity**2) + (0.00122874 * tempF**2 * humidity) + (0.00085282 * tempF * humidity**2) + (-0.00000199 * tempF**2 * humidity**2)
    
    # Convert back to Celcius if needed
    if AppSettings['metric_units']:
        heat_index = round(getCelcius(heat_index),0)
    
    return int(heat_index)


def getWallpaper(code):
    """Returns a random wallpaper from the set of wallpapers 
    matching the given weather code.

    """
    global AppSettings
    
    # Retrieve meta information from XML document
    meta_data = open(AppSettings['image_meta_file'], 'r')
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
        wallpaper.append( getWallpaper(AppSettings['weather_error_code']) )
    
    return wallpaper[0]


def drawOverlayFromFile(WStatus):
    """ Draw an overlay on a specified file using the formatting pulled from an 
    XML document. 
    
    """
    # Open the image
    try:
        fp = open(os.path.join(AppSettings['images_dir'], WStatus['filename']), "rb")
    except IOError:
        print "Could not open wallpaper file:\n%s" % WStatus['filename']
        exit(2)
        
    image = Image.open(fp)
    image.load() #Make sure PIL has read the data
    draw = ImageDraw.Draw(image)
      
    # Open the XML document
    xml_file = open(AppSettings['overly_file'], 'r')
    root = parse(xml_file).getroot()
    
    for font in root:
        # Font settingsAppSettings['xml_file']
        size = int(font.attrib['size'])
        fill_color = font.attrib['fill']

        try:
            font_file = font.attrib['file']
        except KeyError:
            font_obj = ImageFont.truetype(AppSettings['overlay_font'], size)
        else:
            font_obj = ImageFont.truetype(os.path.join(AppSettings['images_dir'], font_file), size)
        
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
            if WStatus['code'] != AppSettings['weather_error_code'] and line.tag != 'errorline':
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
            # If this is an error message
            elif WStatus['code'] == AppSettings['weather_error_code'] and line.tag == 'errorline':
                text = text.replace('%errormsg%', WStatus['errormsg'])
            # Otherwise, ignore the line
            else:
                continue
            
            # The first X-coordinate is manditory, but afterwards, it can be
            # left off. If it is not specified, the previous value of x will
            # be used.
            try:
                x = int(line.attrib['x'])
            except:
                x = x_prev # use the previously defined x value
            else:
                # A negative indicates distance from right edge
                if x < 0: 
                    x = x + image.size[0]   # Add the width of the image

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
    output_file = AppSettings['wallpaper_file']
    
    # Save the new file
    if os.path.exists(output_file):
        os.remove(output_file)
    # XP does not support image types other than BMP
    if platform.release() == "XP":
        image.save(output_file, "BMP", quality=100)
    else:
        image.save(output_file, "JPEG", quality=100)
    fp.close()


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
    output_file = AppSettings['wallpaper_file']
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
    if sys.platform == 'win32':
        # http://mail.python.org/pipermail/python-list/2005-July/330379.html
        #shutil.copyfile(os.path.join(images_dir, wallpaper[0].find('file').text), wallpaperfile)
        # Refresh the desktop
        SPI_SETDESKWALLPAPER = 20 # According to http://support.microsoft.com/default.aspx?scid=97142
        ctypes.windll.user32.SystemParametersInfoA(SPI_SETDESKWALLPAPER, 0, AppSettings['wallpaper_file'], 0)
        #cs = ctypes.c_buffer(output_file)
        #ctypes.windll.user32.SystemParametersInfoA(win32con.SPI_SETDESKWALLPAPER,0,output_file,0)
        #win32gui.SystemParametersInfo (win32con.SPI_SETDESKWALLPAPER, bmp_path, win32con.SPIF_SENDCHANGE)
        #os.system('RUNDLL32.EXE USER32.DLL,UpdatePerUserSystemParameters ,1 ,True')
    # Mac OS X
    elif sys.platform == 'darwin':
        # http://stackoverflow.com/questions/431205/how-can-i-programatically-change-the-background-in-mac-os-x#431273
        import subprocess

        SCRIPT = """/usr/bin/osascript<<END
        tell application "Finder"
        set desktop picture to POSIX file "%s"
        end tell
        END"""

        subprocess.Popen(SCRIPT % AppSettings['wallpaper_file'], shell=True)
    # Linux
    else:
        # Gnome
        # http://www.tuxradar.com/content/code-project-use-weather-wallpapers
        cmd = string.join(["gconftool-2 -s /desktop/gnome/background/picture_filename -t string \"",AppSettings['wallpaper_file'],"\""],'')
        os.system(cmd)

        # This seems to work well for Gnome, but not KDE
        # Change the symbolic link from the old to the new wallpaper
        """
        try:
            os.remove(AppSettings['symlink'])
        except OSError:
            pass
        os.symlink(AppSettings['wallpaper_file'], AppSettings['symlink'])
        """
        

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
        shutil.copyfile(os.path.join(AppSettings['images_dir'], WStatus['filename']), AppSettings['wallpaper_file'])

    # Force the desktop to update the wallpaper
    updateDesktop()    

def ReadCredits(xmlFile):
    """Read the Title, Author and URL from the Metadata file"""
    try:
        fp = open(xmlFile)
    except IOError:
        print "Could not open file %s" % xmlFile
        
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
        'heat_index': '',
        'condition': '',
        'date': '',
        'humidity': '',
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
                # Reset weather date so that the error image is replace when the connection
                # is re-established
                previous_weather_date = ''
                # Write connection error to log
                if AppSettings['conditions_file_enabled']:
                    out = open(AppSettings['conditions_file'], 'w')
                    out.write('Could not connect')
                    out.close()
                # Draw status on image
                if AppSettings['overlay_enabled']:
                    # Create error object
                    WError = {
                        'code': AppSettings['weather_error_code'],
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
                    time.sleep(5) # try again in 30 seconds
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
                WStatus['forecast'] = weather['forecasts'][0]['text']
                WStatus['temp_unit'] = weather['units']['temperature']
                
                # Calculate the heat index
                WStatus['heat_index'] = getHeatIndex(WStatus['temp'], WStatus['humidity'])

                print WStatus['date']
                print 'Weather Code:',  WStatus['code'], "(%s)" %  WStatus['condition']
                print 'Current temperature: %s (feels like %s)' % (WStatus['temp'],  WStatus['heat_index'])
            
                # Force a change the weather code
                if AppSettings['use_heat_index'] and WStatus['heat_index'] >= AppSettings['hot_threshold']:
                        WStatus['code'] = '36' # HOT!
                elif int(WStatus['temp']) >= AppSettings['hot_threshold']:
                        WStatus['code'] = '36' # HOT!
                
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
    pathname = os.path.dirname(sys.argv[0])
    fullpath = os.path.abspath(pathname) 
    os.chdir(fullpath)

    # Prevent multiple copies of this process from running simultaneously
    appInstance = ApplicationInstance('weatherpaper.pid')
    
    # Load the dictionary of program settings
    AppSettings = loadSettings()
    
    ReadCredits(AppSettings['image_meta_file'])
    
    # Run main
    main()
