# Copyright 2023 antillia.com Toshiyuki Arai
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
# ImageMaskDatasetGenerator.py
# 2023/07/17
# 2023/07/21 Added create_rotated_image_and_mask method
# 2023/07/25 Modified to read parameters from a configuration file.
# 2023/07/25 Modified to generate both Benign and Malignant dataset.

import os
import sys
import cv2
import numpy as np

import shutil
from PIL import Image, ImageDraw, ImageOps, ImageFilter
import glob
import csv
import json
import traceback
from ConfigParser import ConfigParser

class ImageMaskDatasetGenerator:

  def __init__(self, segmentation_csv,  annotation_csv,  category = "Malignant", resize=512):
    self.segmentation_csv= segmentation_csv
    self.category        = category
    self.output_size     = resize

    with open(annotation_csv) as f:
     reader = csv.reader(f)
     header = next(reader)
     N = 0
     for i, item in enumerate(header):
       if item == "Pathology Classification/ Follow up":
         N = i
         break
         
     self.categories = {}
     for row in reader:
       image_id = row[0] 
       category     = row[N]     
       #print("BorM {}".format(category))
       self.categories[image_id] = category

  def draw_shape(self, draw, shape):
    name = shape["name"]
    print("---- name {}".format(name))
    if name == "circle":
      #"cx":522,"cy":1310,"r":20}
      x = shape["cx"]
      y = shape["cy"]
      r = shape["r"]
      cx = x - r
      cy = y - r
      rx = x + r
      ry = y + r
      print("Draw circle")
      draw.ellipse((cx, cy,rx, ry), fill="white") 

    if name == "ellipse":  
      #"cx":522,"cy":1310,"rx":16,"ry":20}
      cx = shape["cx"]
      cy = shape["cy"]
      rx = shape["rx"]
      ry = shape["rx"]

      print("Draw ellipse")
      box = [(cx, cy),(cx+rx), (cy+ry)]
      print(box)
      
      draw.ellipse(box, fill="white") 
             
    if name == "polygon":
      all_points_x = shape["all_points_x"]
      all_points_y = shape["all_points_y"]
      all_points = []
      lx = len(all_points_x)
      ly = len(all_points_y)
      if lx != ly:
        raise Exception("Fatal Error: not matched all_point_x and all_point_y")
    
      for i in range(lx):
        x = all_points_x[i]
        y = all_points_y[i]
        all_points.append((x, y))
      print("Draw polygon ")
      
      draw.polygon(all_points, fill ="white") 
             
  # 2023/07/21 Added
  def create_rotated_image_and_mask(self, resized_image, resized_mask, filename,
                                    output_images_dir, output_masks_dir):
      ANGLES = [90, 180, 270]

      for angle in ANGLES:
        rotated_image = resized_image.rotate(angle)
        rotated_mask  = resized_mask.rotate(angle)
        output_filename = "rotated_" + str(angle) + "_" + filename

        rotated_image_file = os.path.join(output_images_dir, output_filename)
        rotated_image.save(rotated_image_file)
        rotated_mask_file = os.path.join(output_masks_dir, output_filename)
        rotated_mask.save(rotated_mask_file)


  def create_image_and_mask(self,image_id, image_filepath, 
                      shapes, filename,
                      output_images_dir, output_masks_dir, ):
    print("create_image_and_mask shapes {}".format(shapes))
    
    try:
      BorM = self.categories[image_id]
      if BorM != self.category:
        print("----filename  Benign {}".format(filename, BorM))
        
        return
      if BorM == self.category:
        print("class {}".format(BorM))
        image = Image.open(image_filepath)
        image = image.convert("RGB")

        # Create resize image
        resized = self.resize(image, output_size=self.output_size)
        image_filepath = os.path.join(output_images_dir, filename)
        # Save resized image
        resized.save(image_filepath)

        w, h  = image.size
        mask = Image.new("RGB", (w, h)) 

        draw = ImageDraw.Draw(mask)
        
        for shape in shapes:
          self.draw_shape(draw, shape)
          
        #mask.show()
        #input("---------")
        
        print("filename {}".format(filename))

        # Create resized mask
        output_filepath = os.path.join(output_masks_dir, filename)
        resized_mask = self.resize(mask, output_size=self.output_size)

        resized_mask.save(output_filepath)
        print("Saved resized mask {}".format(output_filepath))

        # 2023/07/21
        self.create_rotated_image_and_mask(resized, resized_mask, filename,
                                    output_images_dir, output_masks_dir)

        # Create mirrored image
        mirrored = ImageOps.mirror(resized)
        image_filepath = os.path.join(output_images_dir, "mirrored_" + filename)
        mirrored.save(image_filepath)
        
        # Create mirrored mask
        mirrored_mask = ImageOps.mirror(resized_mask)
        mask_filepath = os.path.join(output_masks_dir, "mirrored_" + filename)
        mirrored_mask.save(mask_filepath)

        # Create flipped image
        flipped = ImageOps.flip(resized)
        image_filepath = os.path.join(output_images_dir, "flipped_" + filename)
        flipped.save(image_filepath)
        
        # Create flipped mask
        flipped_mask = ImageOps.flip(resized_mask)
        mask_filepath = os.path.join(output_masks_dir, "flipped_" + filename)
        flipped_mask.save(mask_filepath)
        
    except:
      traceback.print_exc()

  def find_image_filepath(self, filename, images_dirs):
    image_filepath = ""
    for images_dir in images_dirs:        
      image_filepath = os.path.join(images_dir, filename)
      if os.path.exists(image_filepath):
        break

    if os.path.exists(image_filepath):
      return image_filepath
    else:
      raise Exception("Not found image_filepath")

  def generate(self, images_dirs, output_images_dir, output_masks_dir):

    if not os.path.exists(output_images_dir):
      os.makedirs(output_images_dir)
    if not os.path.exists(output_masks_dir):
      os.makedirs(output_masks_dir)

    segmentations = {}
    filenames     = []
    with open(self.segmentation_csv) as f:
      reader = csv.reader(f)
      header = next(reader)
      for rows in reader:        
        #print(rows)
        filename = rows[0]
        #print(rows[5])
        # region_shape_attributes
        shape    = json.loads(rows[5])
        if segmentations.get(filename):
          ls = segmentations[filename]
          ls.append(shape)
        else:
          filenames.append(filename)
          segmentations[filename] = [shape]
      
      for filename in filenames:
        image_id = filename.split(".")[0]
        image_filepath = self.find_image_filepath(filename, images_dirs) 

        shapes  = segmentations[filename]
        print("filename {} --- shapes len {} shape {}".format(filename, len(shapes), shape))
        self.create_image_and_mask(image_id, image_filepath, 
                                       shapes, filename,
                                       output_images_dir, output_masks_dir, )
        
  def resize(self, image, output_size=512):
     w, h = image.size
     bigger = w
     if h >bigger:
       bigger = h
     background = Image.new("L", (bigger, bigger))
     x = (bigger - w)//2
     y = (bigger - h)//2

     background.paste(image, (x, y))
     background = background.resize((output_size, output_size))
     return background


GENERATOR = "generator"

if __name__ == "__main__":
  try:
    config_file  = "./image_mask_generator.config"
    if len(sys.argv) == 2:
      config_file = sys.argv[1]
    config       = ConfigParser(config_file)
    if not os.path.exists(config_file):
      Notfound = "Not found config file " + config_file
      raise Exception(Notfound)
    
    images_dirs      = config.get(GENERATOR, "images_dirs")
                                  #dvalue=["./Low energy images of CDD-CESM", "./Subtracted images of CDD-CESM"])
    segmentation_csv = config.get(GENERATOR, "segmentation_file") 
                                  #dvalue="./Radiology_hand_drawn_segmentations_v2.csv")
    annotation_csv   = config.get(GENERATOR, "annotation_file")   
                                  #dvalue="./Radiology-manual-annotations.csv")

    output_dir       = config.get(GENERATOR, "output_dir") #"./CDD-CESM-master/"
    resize           = config.get(GENERATOR, "resize")
    print("--- output_dir {}".format(output_dir))
    if os.path.exists(output_dir):
      shutil.rmtree(output_dir)
    if not os.path.exists(output_dir):
      os.makedirs(output_dir)

    categories = ["Benign", "Malignant"]

    for category in categories:
      categorized_output_images_dir = os.path.join(output_dir , category + "/images/")
      categorized_output_masks_dir  = os.path.join(output_dir , category + "/masks/")

      generator = ImageMaskDatasetGenerator(segmentation_csv,  annotation_csv, category=category)

      generator.generate(images_dirs,  
                       categorized_output_images_dir,
                       categorized_output_masks_dir)


  except:
    traceback.print_exc()

