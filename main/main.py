import numpy as np
import cv2
from numba import njit,prange, set_num_threads
import time
import multiprocessing as mp
import threading


class Hologram():
    def __init__(self):
        self.hologram=None
    def createHologramModel(self,img):
        img_rows, img_cols, rgb = img.shape
        hol_shape = (img_rows * 2) + img_cols + 1
        self.rows=img_rows
        self.col=img_cols
        self.channel=rgb
        self.hologram = np.zeros((hol_shape, hol_shape, rgb), dtype=int)
        self.hologram = self.hologram.astype(np.uint8)
        self.hologram = cv2.cvtColor(self.hologram, cv2.COLOR_RGB2BGR)
    def getHologram(self):
        return self.hologram
    def getImgProp(self):
        return self.rows, self.col, self.channel
    def reset(self):
        for i in self.hologram:
            for j in i:
                j[0]=j[1]=j[2]=0


@njit(fastmath=True,nogil=True,cache=True,parallel=True)
def frameToHol(img,hologram,img_rows,img_cols,rgb):


    "UP"

    _row=0
    _col=img_rows

    cur_row=_row
    cur_col=_col
    for r in prange(img.shape[0]):
            for c in prange(img.shape[1]):
                hologram[cur_row+r][cur_col+c][:] = img[r][c][:]


    "Left"
    _row=img_rows+img_cols
    _col=0

    cur_col=_col
    cur_row=_row

    for r in prange(img.shape[0]):
            for c in prange(img.shape[1]):
                hologram[cur_row-c][cur_col+r][:] = img[r][c][:]


    "Down"
    _row = img_cols+img_rows+img_rows
    _col = img_rows+img_cols

    cur_row = _row
    cur_col = _col
    for r in prange(img.shape[0]):
        for c in prange(img.shape[1]):
            hologram[cur_row-r][cur_col-c][:] = img[r][c][:]


    _row = img_rows
    _col = (img_rows*2)+img_cols

    cur_col = _col
    cur_row = _row

    for r in prange(img.shape[0]):
        for c in prange(img.shape[1]):
                hologram[cur_row+c][cur_col-r][:] = img[r][c][:]


    return hologram



def videoToNumpy(path,text):
    cap = cv2.VideoCapture(path)
    frameCount = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    frameWidth = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    frameHeight = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

    buf = np.empty((frameCount, frameHeight, frameWidth, 3), np.dtype('uint8'))

    fc = 0
    ret = True
    pt=0
    while (fc < frameCount and ret):
        ret, buf[fc] = cap.read()

        fc += 1
        j=int( fc / frameCount *100)
        if pt < j:
            pt = j
            text.text = "Loading video: " + str(j) + "%"
    cap.release()



    return buf

def image_resize(image, width = None, height = None, inter = cv2.INTER_AREA):
    # initialize the dimensions of the image to be resized and
    # grab the image size
    dim = None
    (h, w) = image.shape[:2]

    # if both the width and height are None, then return the
    # original image
    if width is None and height is None:
        return image

    # check to see if the width is None
    if width is None:
        # calculate the ratio of the height and construct the
        # dimensions
        r = height / float(h)
        dim = (int(w * r), height)

    # otherwise, the height is None
    else:
        # calculate the ratio of the width and construct the
        # dimensions
        r = width / float(w)
        dim = (width, int(h * r))

    # resize the image
    resized = cv2.resize(image, dim, interpolation = inter)

    # return the resized image
    return resized

def createMP4(holograms,text):
    frameSize = (holograms[0].shape[0], holograms[0].shape[1])

    out = cv2.VideoWriter('holograms/rar.avi', cv2.VideoWriter_fourcc(*'DIVX'), 30, frameSize)
    pt=0
    for i in range(0, holograms.shape[0]):
        j= int(i / holograms.shape[0] *100)
        if pt < j:
            pt = j
            text.text = "Saving video: " + str(j) + "%"
        img = holograms[i]
        out.write(img)
    text.text = "Video saved!!"
    out.release()

def makeVideo(videoPath,text, basewidth=300, maxQuality=False, threading=False):

        if threading:
            set_num_threads(mp.cpu_count())
        else:
            set_num_threads(1)

        video = videoToNumpy(videoPath,text)

        # img = Image.open(r"C:\Users\TheDimitri\PycharmProjects\hologram\phototest\test.jpg")
        collectionFrame = []
        img = image_resize(video[0], width=basewidth)
        H = Hologram()
        H.createHologramModel(img)
        hologram = H.getHologram()
        img_rows, img_cols, rgb = H.getImgProp()
        pt=0
        for i in range(int(video.shape[0])):
            img = image_resize(video[i], width=basewidth)

            j = int( i / (video.shape[0]) *100)
            frame = np.array(frameToHol(img, hologram, img_rows, img_cols, rgb))
            collectionFrame.append(frame)
           # yield j * 100
            if pt<j:
                pt=j
                text.text="Making hologram: "+str(j)+"%"
        createMP4(np.asarray(collectionFrame),text)


class th(threading.Thread):
    def __init__(self,videoPath,text,basewidth=300,maxQuality=False,threading=False):
        super(th, self).__init__()
        self.videoPath=videoPath
        self.basewidth=basewidth
        self.maxQuality = maxQuality
        self.threading = threading
        self.text=text

    def run(self):
            makeVideo(self.videoPath,self.text,self.basewidth,self.maxQuality,self.threading)







#makeVideo(r"C:\Users\TheDimitri\PycharmProjects\hologram\phototest\rar.mp4")
