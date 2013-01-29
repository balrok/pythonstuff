#!/usr/bin/python
from window import Window
from window import SubWindow
from window import findColorArea
import time
from gameobjects import HealthBar
from gameobjects import HealthPot
from gameobjects import ManaPot
from autopy import key
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
        if x1 == -1:
            return None
        startX=x1+5

    return SubWindow(win, x1, y1, abs(y1-y2), abs(x1-x2))


constants = {
    'healthbar': (290, 618, 305, 793),
    'healthbarColor': 0xe03434,
    'manabar': (314, 618, 322, 793),
    'manabarColor': 0x6084e0,
    'barBGColor': 0x545454, # background of health,mana,exp bar
    'moneyColor': 0xdcf100,
    'healthpotMoney': (515, 689),
    'manapotMoney': (515, 777)
}

def checkConstants(gameWin):
    x1,y1,x2,y2 = findColorArea(gameWin, constants['healthbarColor'], 1)
    if constants['healthbar'] != (x1,y1,x2,y2):
        print "healthbar wrong"
    x1,y1,x2,y2 = findColorArea(gameWin, constants['manabarColor'], 1)
    if constants['manabar'] != (x1,y1,x2,y2):
        print "manabar wrong"


def main():
    w = Window()
    while True:
        print "search game area"
        w.getScreenShot()
        gameWin = findGameArea(w)
        if gameWin is not None:
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
    nextSpell = 0
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
                    healthbar.saveScreenshot("bartakepot%d"% i)
                    print "send f"
                    key.tap('f')
                    healthHistory.append(i)

                else:
                    checknextHealth = i+200
                    # no healthpot left - going home
                    print "send g"
                    key.tap('g')
            elif full < 80:
                if nextSpell < i:
                    key.tap(' ')
                    print "space"
                    nextSpell=i+200



if __name__ == '__main__':
    main()
