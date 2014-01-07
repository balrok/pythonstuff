#!/usr/bin/python
from window import Window
from window import SubWindow
from window import findColorArea
import time
import autopy
import os
import colorsys
#import sys


class Whack(object):
    height = 241
    width = 481
    top = 129
    left = 20
    def __init__(self, win):
        self.img_G = autopy.bitmap.Bitmap.open(os.path.join('whack_G.png'))
        self.img_A = autopy.bitmap.Bitmap.open(os.path.join('whack_A.png'))
        self.img_M = autopy.bitmap.Bitmap.open(os.path.join('whack_M.png'))
        self.img_W = autopy.bitmap.Bitmap.open(os.path.join('whack_W.png'))
        self.img_RG = autopy.bitmap.Bitmap.open(os.path.join('whack_RG.png'))
        self.img_E = autopy.bitmap.Bitmap.open(os.path.join('whack_E.png'))
        self.win = win
        if win == 1:
            return
        area = self.getArea()
        self.squares = [[0,0,0,0,0,0], [0,0,0,0,0,0], [0,0,0,0,0,0], [0,0,0,0,0,0], [0,0,0,0,0,0], [0,0,0,0,0,0], [0,0,0,0,0,0], [0,0,0,0,0,0], [0,0,0,0,0,0], [0,0,0,0,0,0], [0,0,0,0,0,0], [0,0,0,0,0,0]]
        for row in range(0,6):
            for col in range(0,12):
                self.squares[col][row] = SubWindow(area, 40*row, 40*col, 40, 40)

    def isEmptySquare(self, square):
        # an empty square has mostly the same colors everywhere
        for x in range(0,30,2):
            for y in range(0,30,2):
                if not self.similarColor(square.get_color(x,y), square.get_color(y,x)):
                    return False
        return True

    def testOffline(self):
        square = autopy.bitmap.Bitmap.open("found150.png")
        print self.isImg(square, self.img_RG, True)

    def hasArea(self):
        print "check area"
        # TODO doesn't work yet
        return True
        for row in range(0,6):
            for col in range(0,12):
                self.squares[col][row].getScreenShot()
                self.squares[col][row].current_screen.save("square"+str(col)+str(row)+".png")
                if self.isImg(self.squares[col][row].current_screen, self.img_E):
                    print "found area"
                    return True
        return False
    def getArea(self):
        return SubWindow(self.win, self.top+37, self.left+6, self.width, self.height)
    def findClicks(self,i):
        clicks = []
        for row in range(0,6):
            for col in range(0,12):
                self.squares[col][row].getScreenShot()
                #self.squares[col][row].current_screen.save("square"+str(col)+str(row)+".png")
                square = self.squares[col][row].current_screen
                if not self.isImg(square, self.img_RG) and not self.isEmptySquare(square):
                    print "found "+str(i)+str(len(clicks))
                    #self.isImg(square, self.img_RG, True)
                    #self.squares[col][row].current_screen.save("found"+str(i)+str(len(clicks))+".png")

                    clicks.append(((col*40)+5, (row*40)+5))
        return clicks

    def toRGB(self, color):
        B = color%256
        color-=B
        G = color %(256*256)/256
        color-=G*256
        R=color/(256*256)
        return (R,G,B)

    def similarColor(self, color1, color2, debug=False):
        c1 = self.toRGB(color1)
        c2 = self.toRGB(color2)
        h1 = colorsys.rgb_to_hls(c1[0], c1[1], c1[2])
        h2 = colorsys.rgb_to_hls(c2[0], c2[1], c2[2])
        if debug:
            print h1,h2

        return (h1[1]<=h2[1]+20 and h1[1] >= h2[1]-20) and (h1[0]<=h2[0]+0.1 and h1[0] >= h2[0]-0.1)

    def isImg(self, square, img, debug=False):
        for i in range(0,30,2):
            if not self.similarColor(square.get_color(i,i), img.get_color(i,i), debug):
                return False
        return True


# finds the area of a kongregate game
def findGameArea(win):
    print "searching area"
    # favicons often have the same color, but are smaller in size
    # so ignore this line
    startX=0
    x1=0
    x2=0
    while abs(x1-x2) < 200:
        x1, y1, x2, y2 = findColorArea(win, 0x333333, 1, startX)
        print x1,y1,x2,y2
        if x1 == -1:
            return None
        startX=x1+5

    return SubWindow(win, x1, y1, abs(y1-y2), abs(x1-x2))


def main():
    w = Window()
    start = time.time()
    while True:
        print "search game area"
        w.getScreenShot()
        w.current_screen.save("test.png")
        gameWin = findGameArea(w)
        if gameWin is not None:
            print "found area"
            break
    gameWin.getScreenShot()
    gameWin.current_screen.save("whack1.png", "png")
    whack = Whack(gameWin)
    area = whack.getArea()
    area.getScreenShot()
    area.current_screen.save("whack2.png", "png")
    i=0
    while True:
        if whack.hasArea():
            break
        time.sleep(0.3)
    ignoreUntilNextClick = (9999,9999)
    resetIgnore = 0
    while True:
        if resetIgnore < time.time():
            print "reset",resetIgnore, time.time()
            resetIgnore = time.time() + 100
            ignoreUntilNextClick = (9999,9999)
        i+=1
        print i
        print "search button"
        coords = whack.findClicks(i)
        if len(coords) < 1:
            continue
        if len(coords) > 7:
            return
        c=0
        last = (9999, 9999)
        for coord in coords:
            c+=1
            y,x = coord
            print "coord",coord
            if y > ignoreUntilNextClick[0] - 90 and y < ignoreUntilNextClick[0] + 90 and x == ignoreUntilNextClick[1]:
                print "ignore", ignoreUntilNextClick
                continue
            #tmp = SubWindow(area, x-10, y-10, 30, 30)
            #tmp.getScreenShot()
            #tmp.current_screen.save("click"+str(i)+str(c)+".png")
            area.mouseMove(x, y)
            area.mouseClick()
            gameWin.mouseMove(10, 10)
            last = coord
        if last[0] != 9999:
            print "last",last
            ignoreUntilNextClick = last
            resetIgnore = time.time() + 0.6
    print time.time()-start



if __name__ == '__main__':
    main()
