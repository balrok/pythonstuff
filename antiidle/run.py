#!/usr/bin/python
from window import Window
from window import SubWindow
from window import findColorArea
from button import Button
import time
#import sys


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
    gameWin.current_screen.save("game1.png", "png")
    but = Button(gameWin)
    but.getBgArea()
    but.findShopAndRepair()
    i=0
    broken = 0
    while True:
        i+=1
        if i==200:
            break
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
        x,y = but.findCenter()
        butWin = SubWindow(gameWin, x-5, y-5, 15, 15)
        butWin.getScreenShot()
        butWin.current_screen.save("butwin.png", "png")
        print x, y
        print but.width
        print but.height
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
    print time.time()-start



if __name__ == '__main__':
    main()
