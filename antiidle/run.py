#!/usr/bin/python
from window import Window
from window import SubWindow
from window import getArrayColor
from window import findColorArea
from button import Button
import time
import sys


# finds the area of a kongregate game
def findGameArea(win):
    print "searching area"
    return findColorArea(win, getArrayColor("333333"), 1)


def main():
    w = Window()
    start = time.time()
    while True:
        print "search game area"
        w.getScreenShot()
        x1, y1, x2, y2 = findGameArea(w)
        if x1 > -1:
            gameWin = SubWindow(w, x1, y1, abs(x1-x2), abs(y1-y2))
            print "found area"
            break
    gameWin.getScreenShot()
    but = Button(gameWin)
    but.getBgArea()
    but.findShopAndRepair()
    i=0
    broken = 0
    while True:
        i+=1
        if but.isBroken():
            broken += 1
            if broken == 5:
                broken = 0
                print "BROKEN"
                x = but.repairButton[0]
                y = but.repairButton[1]
                gameWin.mouseMove(x, y)
                gameWin.mouseClick(x, y)
                #break
        else:
            broken = 0
        print "search button"
        gameWin.getScreenShot()
        #butWin = SubWindow(gameWin, x1, y1, abs(x1-x2), abs(y1-y2))
        #butWin.getScreenShot()
        #gameWin.current_screen.save("game%d.png"%i, "png")
        x,y = but.findCenter()
        if but.width < 10 or but.height < 10: # not found
            continue
        print (x,y)
        gameWin.mouseMove(x, y)
        gameWin.mouseClick(x, y)

        #x1,y1,x2,y2 = but.area
        #butWin = SubWindow(gameWin, x1, y1, abs(x1-x2), abs(y1-y2))
        #butWin.getScreenShot()
        #butWin.current_screen.save("button%d.png"%i, "png")
        #time.sleep(0.2)
        #if time.time()-start > 60:
        #    sys.exit()

        print but

        #print but
        #if but[0] > -1:
        #    mouse.move(left+but[0], top+but[1])



if __name__ == '__main__':
    main()
