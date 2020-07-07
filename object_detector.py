import cv2
import numpy as np


if __name__ == '__main__':
    PATCH_SIZE = 8

    img = cv2.imread('./tests/detection/image1.png')
    img = np.float32(img) / 255.0

    print(img.shape)
    for i in range(0, img.shape[0], PATCH_SIZE):
        for j in range(0, img.shape[1], PATCH_SIZE):
            subimg = img[i:i+PATCH_SIZE, j:j+PATCH_SIZE, :]

            # Calculate gradient
            gx = cv2.Sobel(img, cv2.CV_32F, 1, 0, ksize=1)
            gy = cv2.Sobel(img, cv2.CV_32F, 0, 1, ksize=1)
            mag, angle = cv2.cartToPolar(gx, gy, angleInDegrees=True)

    print(mag)
    print(angle)
    print('Done!')
