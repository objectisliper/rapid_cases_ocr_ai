"""
Conqueror v.1
System that extracts error messages from screen recordings
of different software error occurrences

Image preprocessing and cleanup

Michael Drozdovsky, 2020
michael@drozdovsky.com
"""
import cv2
import numpy as np


class ImagePreprocessing(object):
    """
    Class to preprocess images for better classification
    and object detection
    """
    @staticmethod
    def adjust_gamma(image, gamma=1.0):
        inv_gamma = 1.0 / gamma
        table = np.array([
            ((i / 255.0) ** inv_gamma) * 255 for i in np.arange(0, 256)
        ]).astype("uint8")
        return cv2.LUT(image, table)

    @staticmethod
    def exaggerate(image):
        # exaggerates regions of interest
        image = image[..., 2] #- image[..., 1] - image[..., 2]
        ret, image = cv2.threshold(image, 127, 255, cv2.THRESH_BINARY)
        return image

    @staticmethod
    def highlight(image):
        #hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)
        lower_red = np.array([150, 150, 150])
        upper_red = np.array([255, 255, 255])

        mask = cv2.inRange(image, lower_red, upper_red)
        res = cv2.bitwise_and(image, image, mask=mask)

        return res
