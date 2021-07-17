# Copyright (c) 2014 Adafruit Industries
# Author: Tony DiCola
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
# THE SOFTWARE.

"""
import time

import Adafruit_GPIO.SPI as SPI
import Adafruit_SSD1306

from PIL import Image
from PIL import ImageDraw
from PIL import ImageFont

RST = None
# Raspberry Pi pin configuration:
#RST = 24
# Note the following are only used with SPI:
DC = 23
SPI_PORT = 0
SPI_DEVICE = 0

# Beaglebone Black pin configuration:
# RST = 'P9_12'
# Note the following are only used with SPI:
# DC = 'P9_15'
# SPI_PORT = 1
# SPI_DEVICE = 0

# 128x32 display with hardware I2C:
#disp = Adafruit_SSD1306.SSD1306_128_32(rst=RST)

# 128x64 display with hardware I2C:
# disp = Adafruit_SSD1306.SSD1306_128_64(rst=RST)

# Note you can change the I2C address by passing an i2c_address parameter like:
# disp = Adafruit_SSD1306.SSD1306_128_64(rst=RST, i2c_address=0x3C)

# Alternatively you can specify an explicit I2C bus number, for example
# with the 128x32 display you would use:
disp = Adafruit_SSD1306.SSD1306_128_32(rst=RST, i2c_bus=2)

# 128x32 display with hardware SPI:
# disp = Adafruit_SSD1306.SSD1306_128_32(rst=RST, dc=DC, spi=SPI.SpiDev(SPI_PORT, SPI_DEVICE, max_speed_hz=8000000))

# 128x64 display with hardware SPI:
# disp = Adafruit_SSD1306.SSD1306_128_64(rst=RST, dc=DC, spi=SPI.SpiDev(SPI_PORT, SPI_DEVICE, max_speed_hz=8000000))

# Alternatively you can specify a software SPI implementation by providing
# digital GPIO pin numbers for all the required display pins.  For example
# on a Raspberry Pi with the 128x32 display you might use:
# disp = Adafruit_SSD1306.SSD1306_128_32(rst=RST, dc=DC, sclk=18, din=25, cs=22)

# Initialize library.
disp.begin()

# Clear display.
disp.clear()
disp.display()

# Create blank image for drawing.
# Make sure to create image with mode '1' for 1-bit color.
width = disp.width
height = disp.height
image = Image.new('1', (width, height))

# Get drawing object to draw on image.
draw = ImageDraw.Draw(image)

# Draw a black filled box to clear the image.
draw.rectangle((0,0,width,height), outline=0, fill=0)

# Draw some shapes.
# First define some constants to allow easy resizing of shapes.
padding = 2
shape_width = 20
top = padding
bottom = height-padding
# Move left to right keeping track of the current x position for drawing shapes.
x = 0

# Load default font.
#font = ImageFont.load_default()
thinFont = ImageFont.truetype('GeosansLight.ttf', 10)
draw.text((0, 0),    'CH',  font=thinFont, fill=255)
thinFont2 = ImageFont.truetype('GeosansLight.ttf', 14)
#draw.text((40, 0),    'SENDER',  font=thinFont2, fill=255)
#draw.text((40, 10),    'RECEIVER',  font=thinFont2, fill=255)
draw.text((40, 16),    'REPEATER',  font=thinFont2, fill=255)

draw.text((40,-3), '1758', font=thinFont2, fill=255)

# Alternatively load a TTF font.  Make sure the .ttf font file is in the same directory as the python script!
# Some other nice fonts to try: http://www.dafont.com/bitmap.php


boldFont = ImageFont.truetype('theboldfont.ttf', 44)
x = 14
draw.text((x, 0),    '3',  font=boldFont, fill=255)
#draw.text((x, top+20), 'World!', font=font, fill=255)

x=104
top = 0
draw.rectangle((x, top, x+20, top+10), outline=255, fill=0)
draw.rectangle((x+20, top+3, x+23, top+7), outline=255, fill=0)
percent = 90
width=int((percent-5) / 5)
draw.rectangle((x+1, top+1, x+width, top+9), outline=255, fill=255)

x=80
draw.arc([(x, top), (x+16, top+16)], 210, 330, fill=255)
draw.arc([(x+3, top+3), (x+13, top+13)], 210, 335, fill=255)
draw.ellipse((x+7,top+7, x+9, top+9), outline=255, fill=255)
draw.line((x+14,top+8,x+14,top+9), fill=255)
draw.line((x+16,top+6,x+16,top+9), fill=255)
draw.line((x+18,top+4,x+18,top+9), fill=255)
draw.line((x+20,top+2,x+20,top+9), fill=255)

# Draw an ellipse.
#draw.ellipse((x, top , x+shape_width, bottom), outline=255, fill=0)
#x += shape_width+padding
# Draw a rectangle.
#draw.rectangle((x, top, x+shape_width, bottom), outline=255, fill=0)
#x += shape_width+padding
# Draw a triangle.
#draw.polygon([(x, bottom), (x+shape_width/2, top), (x+shape_width, bottom)], outline=255, fill=0)
#x += shape_width+padding
# Draw an X.
#draw.line((x, bottom, x+shape_width, top), fill=255)
#draw.line((x, top, x+shape_width, bottom), fill=255)
#x += shape_width+padding


# Display image.
disp.image(image)
disp.display()








# Draw some shapes.
# First define some constants to allow easy resizing of shapes.
padding = 2
shape_width = 20
top = padding
bottom = height-padding
# Move left to right keeping track of the current x position for drawing shapes.
x = 0

draw.text((0, 0),    'CH',  font=thinFont, fill=255)
thinFont2 = ImageFont.truetype('GeosansLight.ttf', 14)
#draw.text((40, 0),    'SENDER',  font=thinFont2, fill=255)
#draw.text((40, 10),    'RECEIVER',  font=thinFont2, fill=255)
draw.text((40, 16),    'REPEATER',  font=thinFont2, fill=255)

draw.text((40,-3), '1758', font=thinFont2, fill=255)

# Alternatively load a TTF font.  Make sure the .ttf font file is in the same directory as the python script!
# Some other nice fonts to try: http://www.dafont.com/bitmap.php


boldFont = ImageFont.truetype('theboldfont.ttf', 44)
x = 14
draw.text((x, 0),    '3',  font=boldFont, fill=255)
#draw.text((x, top+20), 'World!', font=font, fill=255)

x=104
top = 0
draw.rectangle((x, top, x+20, top+10), outline=255, fill=0)
draw.rectangle((x+20, top+3, x+23, top+7), outline=255, fill=0)
percent = 90
width=int((percent-5) / 5)
draw.rectangle((x+1, top+1, x+width, top+9), outline=255, fill=255)

x=80
draw.arc([(x, top), (x+16, top+16)], 210, 330, fill=255)
draw.arc([(x+3, top+3), (x+13, top+13)], 210, 335, fill=255)
draw.ellipse((x+7,top+7, x+9, top+9), outline=255, fill=255)
draw.line((x+14,top+8,x+14,top+9), fill=255)
draw.line((x+16,top+6,x+16,top+9), fill=255)
draw.line((x+18,top+4,x+18,top+9), fill=255)
draw.line((x+20,top+2,x+20,top+9), fill=255)


# Display image.
disp.image(image)
disp.display()


"""
