import cv2
import logging
from app1_base.log import Logger
from django.conf import settings
import os
from pathlib import Path

logger = Logger("extract_pic", level=logging.ERROR).run()

def extract_picture (video, filename):
    # logger.info(f'variables input {video, filename}')
    # cap = cv2.VideoCapture(video)
    # i = 0
    # # cap.isOpened() == True
    # while cap.isOpened():
    #     ret, frame = cap.read()
    #     logger.info(f'ret: {ret}')
    #     # frame=cv2.rotate(frame, cv2.cv2.ROTATE_90_CLOCKWISE)
    #     if not ret:
    #         break
    #     if i % 2 == 0:
    #         try:
    #             cv2.imwrite(video[:-4] + '/' + filename + '_' + str(i) + '.jpg', frame)
    #         except Exception as hair:
    #             logger.info(f'ya R {hair}')
    #     i+=1
    # cap.release()
    # cv2.destroyAllWindows()
    path = video[:-4]
    if os.path.exists(path):
        for file in os.listdir(path):
            os.remove(path + '/' + file)
        os.removedirs(path)
    os.mkdir(path)
    cap = cv2.VideoCapture(video)
    i = 0
    while cap.isOpened():
        ret, frame = cap.read()
        # frame=cv2.rotate(frame, cv2.cv2.ROTATE_90_CLOCKWISE)
        if not ret:
            break

        if i % 2 == 0:
            cv2.imwrite(
                path + '/' + filename + '_' + str(
                    i) + '.jpg', frame)
        i += 1
    cap.release()
    cv2.destroyAllWindows()