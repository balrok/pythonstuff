#!/usr/bin/python
from window import Window
from window import SubWindow
from window import getArrayColor
from window import findColorArea
import time
from gameobjects import HealthBar
from gameobjects import HealthPot
from gameobjects import ManaPot
from KeyboardUnix import Keyboard
#import sys


# finds the area of a kongregate game
def findGameArea(win):
    print "searching area"
    return findColorArea(win, getArrayColor("333333"), 1)


constants = {
    'healthbar': (290, 618, 305, 793),
    'healthbarColor': 'e03434',
    'manabar': (314, 618, 322, 793),
    'manabarColor': '6084e0',
    'barBGColor': '545454', # background of health,mana,exp bar
    'moneyColor': 'dcf100',
    'healthpotMoney': (515, 689),
    'manapotMoney': (515, 777)
}

def checkConstants(gameWin):
    x1,y1,x2,y2 = findColorArea(gameWin, getArrayColor(constants['healthbarColor']), 1)
    if constants['healthbar'] != (x1,y1,x2,y2):
        print "healthbar wrong"
    x1,y1,x2,y2 = findColorArea(gameWin, getArrayColor(constants['manabarColor']), 1)
    if constants['manabar'] != (x1,y1,x2,y2):
        print "manabar wrong"


def main():
    w = Window()
    kbd = Keyboard()
    while True:
        print "search game area"
        w.getScreenShot()
        x1, y1, x2, y2 = findGameArea(w)
        print x1, y1, x2, y2
        if x1 > -1:
            gameWin = SubWindow(w, x1, y1, abs(y1-y2), abs(x1-x2))
            print "found area"
            break
    gameWin.getScreenShot()
    gameWin.current_screen.save("game1.png", "png")
    healthbar = HealthBar(gameWin, constants)
    healthbar.saveScreenshot('health')

    healthpot = HealthPot(gameWin, constants)
    healthpot.saveScreenshot('healthpotmoney')
    manapot = ManaPot(gameWin, constants)
    manapot.saveScreenshot('manapotmoney')

    if not healthpot.hasPot():
        print "no health pots"
    if not manapot.hasPot():
        print "no mana pots"

    i=0
    checknextHealth = 0
    healthHistory = []
    while True:
        time.sleep(0.05)
        i+=1
        print i
        if i > checknextHealth:
            full = healthbar.getPercentFull()
            if full < 50:
                #healthbar.saveScreenshot("bartakepot%d"% i)
                print "50% health lost"
                # can take pot, when has at least one
                canTakePot = healthpot.hasPot()
                # can take pot, when not in last 40*0.05=2seconds two pots were taken
                if len(healthHistory) > 1 and healthHistory[-2] > i-40:
                    canTakePot = False
                # can take pot, when more than 25%
                if full>25 and canTakePot:
                    checknextHealth = i+10
                    #healthpot.saveScreenshot("takepot%d"% i)
                    #healthbar.saveScreenshot("bartakepot%d"% i)
                    print "send f"
                    kbd.writeLetter('f')
                    healthHistory.append(i)
                else:
                    checknextHealth = i+50
                    # no healthpot left - going home
                    print "send g"
                    kbd.writeLetter('g')



if __name__ == '__main__':
    main()
