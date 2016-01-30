#!/usr/bin/python
# Takes a list of files as its arguments. These are the JSON data files
# from a Twitter archive. So, for example:
# python TwitterBookImages.py ~/TwitterArchive/data/js/tweets/*.js

# A very early version of this was based on:
# http://www.leancrew.com/all-this/2013/01/completing-my-twitter-archive/
# but any errors are mine (@amac)

from datetime import datetime, timedelta
import sys
import json
import urllib
import re
import os.path
import Image, ImageDraw, ImageFont, ImageEnhance
import textwrap

# Constants
# A ton, I don't generally use this many but was lazy

# Where to put the output files (a directory name without trailing slash)
OUTPUT_DIRECTORY = 'output'

# Number of hours to correct the date
# I used 8 because mostly my tweets were in SF
# I couldn't see a time zone and didn't geotag my tweets
DATE_CORRECTION = -8

# This is a font from Google that I liked
FONT = 'OpenSans-Regular.ttf'

# Some colours
# White for the background and text background
BACKGROUND_COLOUR = (255,255,255,255)
TEXT_BACKGROUND_COLOUR = BACKGROUND_COLOUR

# Black for the text
TEXT_COLOUR = (0,0,0,255)
DATE_TEXT_COLOUR = TEXT_COLOUR

# These are numbers and ratios I used for a 7x7 blurb.com book
# If doing a text only page (no image) I used 4096x4096 which makes a ~500K image
TEXT_ONLY_PIXEL_SIZE = 4096
# Below a certain size is too small to print well
# These are used in the program logic to test for the size being too small
# and if too small, to creat at the new size
MINIMUM_PIXEL_SIZE = 1364
WITH_MEDIA_PIXEL_SIZE = 1400
# Constants to figure out font size and padding
FONT_SIZE_CONSTANT = 0.046875
NO_MEDIA_TEXT_SIZE_MULTIPLE = 1.6
DATE_SIZE_MULTIPLE = .5
PADDING_CONSTANT = 63
# Corresponding character counts to use with linewrap
MEDIA_TWEET_CHAR_LENGTH = 36
NO_MEDIA_TWEET_CHAR_LENGTH = 20

# this cleans up the Tweet text
# this is probably a subset of what should be done, 
# but can be expanded if necessary
def process_tweet_text(text=''):
 #remove links
 text=re.sub(r"http\S+", "", text) 
 #change ampersand
 text=re.sub(r"\&amp\;", "&", text) 
 #removing leading spaces
 text=re.sub(r"^ ", "", text) 
 return (text)

# given a picture file, date, tweet text and output file name
# add a text overlay to the picture and save a new output file
#
# if no input file is given or the file is not openable,
# create a text only image for the tweet text
def add_tweet(in_file='', #this will be '.jpg' if none otherwise will be an image
              date='', #the date expressed in text in the format for adding to the image
              text='', #the tweet text
              out_file='test.jpg', # the output filename
              padding=50, # the padding to use around the text
              opacity=0.5): # the opacity for the text box

    # load the input image or create one
    # An in_file of '.jpg' with no extra filename 
    # is a signifier of no media and so is a tiny filesize
    # the variable "media" is made true if there is a pic
    if (in_file == '.jpg') or (os.path.getsize(in_file) < 100):
     print "Text Only: "+out_file
     img = Image.new("RGB", (TEXT_ONLY_PIXEL_SIZE, 1), BACKGROUND_COLOUR)
     media=0  
    else: 
     media=1
     try:
      img = Image.open(in_file).convert('RGB')
     except:
      print "Media didn't open for "+in_file
      print "Text Only: "+out_file
      img = Image.new("RGB", (TEXT_ONLY_PIXEL_SIZE, 1), BACKGROUND_COLOUR)
      media=0

    # figure out whether it is a vertical or horizontal image
    # use "vertical" as a boolean for it
    # 1) make the image square based on the longest side
    # 2) make sure it is bigger than the MINIMUM_PIXEL_SIZE 
    # 3) if it isn't make a new one that is WITH_MEDIA_PIXEL_SIZE big
    # and place the old one in the new one with a border

    vertical=0
    # check which side is longer (width is [0])
    if (img.size[0]<img.size[1]):

     vertical=1
     # make sure the bigger side is bigger than MINIMUM_PIXEL_SIZE
     # if so, create a new square image and center the old one inside
     # if not, create new bigger image and center the old one inside 
     if (img.size[1]>MINIMUM_PIXEL_SIZE): 
      new_img = Image.new("RGB", (img.size[1], img.size[1]), BACKGROUND_COLOUR)  
      new_img.paste(img, (((img.size[1]-img.size[0])/2),0))
     else:
      new_img = Image.new("RGB", (WITH_MEDIA_PIXEL_SIZE, WITH_MEDIA_PIXEL_SIZE), BACKGROUND_COLOUR)  
      new_img.paste(img, (((WITH_MEDIA_PIXEL_SIZE-img.size[0])/2),((WITH_MEDIA_PIXEL_SIZE-img.size[1])/2)))
     img=new_img
    else:

     vertical=0
     # make sure the bigger side is bigger than MINIMUM_PIXEL_SIZE
     # if so, create a new square image and center the old one inside
     # if not, create new bigger image and center the old one inside 
     if (img.size[0]>MINIMUM_PIXEL_SIZE): 
      new_img = Image.new("RGB", (img.size[0], img.size[0]), BACKGROUND_COLOUR)  
      new_img.paste(img, (0,0))
     else:
      new_img = Image.new("RGB", (WITH_MEDIA_PIXEL_SIZE, WITH_MEDIA_PIXEL_SIZE), BACKGROUND_COLOUR)  
      new_img.paste(img, (((WITH_MEDIA_PIXEL_SIZE-img.size[0])/2),((WITH_MEDIA_PIXEL_SIZE-img.size[1])/2)))
     img=new_img

    # The text will be overlaid with a level of transparency.
    # that happens by:
    # 1) creating a new image that with a transparent background
    # 2) figuring out how much space the text will take
    # 3) creating a translucent background for that text box
    # 4) adding the text and date
    # 5) putting the image with the text box over the image created above
    # 6) write the resulting file

    # 1) create a new image that with a transparent background
    rect = Image.new('RGBA', (img.size[0],img.size[1]), (0,0,0,0))

    # 2) figure out how much space the text will take
    # calculate some variables to use for font size and padding

    font_size = int((FONT_SIZE_CONSTANT)*(img.size[0]))
    padding = int (padding*font_size/PADDING_CONSTANT)
    #change this if you want vertical padding to be different
    vert_padding = padding  

    # if this is a tweet with media, text should be small
    # otherwise bigger
    # NB there is a much more scientific way to do this
    # but this seemed easier at the time
    # the better way would be to use normal_font.getsize(text) to 
    # get the exact width and height for a particular text
    if media: 
     lines = textwrap.wrap(text,MEDIA_TWEET_CHAR_LENGTH)
    else:
     lines = textwrap.wrap(text,NO_MEDIA_TWEET_CHAR_LENGTH)
     font_size = int(font_size*NO_MEDIA_TEXT_SIZE_MULTIPLE)

    # Load the fonts for the tweet text and date (small_font)
    normal_font = ImageFont.truetype(FONT, font_size)
    small_font = ImageFont.truetype(FONT, int(font_size*DATE_SIZE_MULTIPLE))
    
    # Calculate beginning height of text box
    # if media then the box should be as low as possible, given padding
    # if not then should be centered
    if media: rect_start=rect.size[1]-((vert_padding*1.5)+((len(lines)+DATE_SIZE_MULTIPLE)*font_size))
    else: rect_start=(rect.size[1]/2)-((((len(lines)+DATE_SIZE_MULTIPLE)*font_size))/2)

    # 3) create a translucent background for the text box
    # Draw the text box rectangle
    draw = ImageDraw.Draw(rect) 
    draw.rectangle((0,rect_start,rect.size[0],rect.size[1]), fill=TEXT_BACKGROUND_COLOUR)
    # Make it translucent
    alpha = rect.split()[3]
    alpha = ImageEnhance.Brightness(alpha).enhance(opacity)
    rect.putalpha(alpha)

    # 4) addi the text & date
    # this version puts the date immediately above the tweet text

    # offset is the place to write text
    # start the text a bit below the begining of the text box
    offset = rect_start+(vert_padding*.1)
    # write the date as Day of the Week, Month Day, Year
    draw.text((padding, offset), date.strftime("%A, %B %d, %Y"), font=small_font, fill=DATE_TEXT_COLOUR)
    #move the offset down by the size of the date text
    offset += int(font_size*DATE_SIZE_MULTIPLE)

    # for each line in all the lines of the tweet
    # write the tweet text and increment the offset
    for line in lines:
      draw.text((padding, offset),
              line, font=normal_font, fill=TEXT_COLOUR)
      offset += font_size

    # 5) put the image with the text box over the image created above
    # 6) write the resulting file
    Image.composite(rect, img, rect).save(OUTPUT_DIRECTORY+'/'+out_file+'.jpg', 'JPEG')
 
# Main body of the program
# The argument is the list of JSON files

# Count is used to ensure unique filenames and count the number of tweets
count=0

# Loop through each json file provided as an argument
for json_file in sys.argv[1:]:
  print "JSON File: "+json_file
  # open the file, get rid of the first line, and load its json as data
  with open(json_file) as data_file:    
    #get rid of the first line
    data_file.readline()
    #read the rest in as json
    data = json.load(data_file) 

  # for each tweet in the resulting data structure
  for tweet in data:
    count = count +1 
    # grab the "created_at", strip out the colons for the file name 
    # and add the count to the end
    # NB that this is a little wrong now because I realized that it would
    # be better to call the date the date minus 8hrs
    # If I edit this, fix that.
    filename=re.sub(r"\:", "-", tweet['created_at'])+str(count)
    # the date below is used for the date to be put on the pic
    date = datetime.strptime(tweet['created_at'][0:16], "%Y-%m-%d %H:%M") + timedelta(hours=DATE_CORRECTION)
 
    # image_name is going to be used for the name of the image
    # associated with the tweet
    # If it is nothing, that will signify no media with the tweet
    image_name = ''

    # Loop through the media entities in the tweet data structure
    if 'entities' in tweet: 
     entities = tweet['entities']
     if 'media' in entities:
      # for each bit of media, grab its url through regex matching
      for media in entities['media']:
       matched = re.search('media\/(.+?)\.jpg', media['media_url']) 
       image_name = matched.group(1)
       print "IMAGE FOUND:"+image_name
       # retrieve the image if it isn't already local
       # I believe the ":large" is the largest size twitter returns
       # Also, Twitter uses URL obscurity for security, so you can
       # retrieve images from protected accounts
       if not os.path.isfile(image_name+'.jpg'): 
         # would be great to have error handling here, but lazy
         # also Twitter has an unsupported "feature" that allows original image
         # size retrievals with :orig
         # although, for my images I didn't see a difference 
         # between this and :large
         urllib.urlretrieve(media['media_url']+':orig', image_name+'.jpg')

     #Add the tweet text to the image
     #or create a new image with just the tweet text
     add_tweet(image_name+'.jpg', date, process_tweet_text(tweet['text']) , filename, 75, .5)
