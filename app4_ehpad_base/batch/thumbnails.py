import glob
import os
from PIL import Image, ImageOps

path = '/App/media_root/residents/'
folders = glob.glob(path + '*')
for folder in folders:
    liste_photos_in_folder = []
    liste_photos_in_thumbnails = []
    files = glob.glob(folder + '/*.*')
    thumbnails = glob.glob(folder + '/thumbnails' +'/*.*')
    for pict in files:
        liste_photos_in_folder.append(pict.split('/')[-1])
    for thumb in thumbnails:
        liste_photos_in_thumbnails.append(thumb.split('/')[-1])
    liste_photo_to_thumbnail = list(set(liste_photos_in_folder)-set(liste_photos_in_thumbnails))
    if len(liste_photo_to_thumbnail) != 0:
        for new_pic in liste_photo_to_thumbnail:
            picture = Image.open(folder + '/' + new_pic)
            rotate_picture = ImageOps.exif_transpose(picture)
            rotate_picture.thumbnail((10000, 500))
            path_dest=path+folder.split('/')[-1] + '/thumbnails/'
            if os.path.exists (path_dest):
                if not os.path.isfile(path_dest + new_pic.split('/')[-1]):
                    rotate_picture.save(path_dest + new_pic.split('/')[-1])
            else:
                os.makedirs(path_dest)
                rotate_picture.save(path_dest + new_pic.split('/')[-1])