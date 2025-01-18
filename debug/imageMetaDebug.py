import os
from PIL import Image
from PIL.ExifTags import TAGS

# this is used for finding metadata in images. just plug in the folder where you want to scan and it'll
# loop through and find anything that has GPS locations


def has_gps_info(exif):
    for tag, value in exif.items():
        decoded = TAGS.get(tag, tag)
        if decoded == "GPSInfo":
            return True
    return False


directory = '../images/downOnTheFarm'

for filename in os.listdir(directory):
    if filename.lower().endswith(('.png', '.jpg', '.jpeg', '.tiff', '.bmp', '.gif')):
        image = Image.open(os.path.join(directory, filename))
        exif_data = image._getexif()
        if exif_data and has_gps_info(exif_data):
            print(f"{filename} contains GPS info")


