from window import SubWindow
from window import findColorArea
from window import findColor
import autopy
import os

# all gameobjects which have a window assigned
class WindowObject(object):
    parentWindow=None
    window=None
    def __init__(self, window, parentWindow):
        self.window = window
        self.parentWindow = parentWindow
    def saveScreenshot(self, name):
        self.window.getScreenShot()
        self.window.current_screen.save(name+'.png', 'png')

class Bar(WindowObject):
    type='default'
    bgcolor=''
    barcolor=''
    width=0

    def __init__(self, window, constants):
        if not self.type+"bar" in constants:
            constants[self.type+'bar'] = self.findWindow(window, constants[self.type+"barColor"])
        x1, y1, x2, y2 = constants[self.type+'bar']
        self.window = SubWindow(window, x1, y1, abs(y1-y2), abs(x1-x2))
        WindowObject.__init__(self, self.window, window)
        self.bgcolor = constants['barBGColor']
        self.barcolor = constants[self.type+"barColor"]
        self.width=abs(y1-y2)

    def findWindow(self, window, color):
        x1,y1,x2,y2 = findColorArea(window, color, 1)
        return (x1,y1,x2,y2)

    def getPercentFull(self):
        # scan for bgcolor
        self.window.getScreenShot()
        x,y = findColor(self.window, self.bgcolor)
        if y>-1:
            x2,y2 = findColor(self.window, self.barcolor)
            # when hovering over items in a trade it will cover the bar
            # which causes to first display background and then healthbar
            if y2==0:
                return float(y)/self.width*100
            # we found bg - so not 100 full
        return 100

class HealthBar(Bar):
    type='health'
    def __init__(self, window, constants):
        Bar.__init__(self, window, constants)

class ManaBar(Bar):
    type='mana'
    def __init__(self, window, constants):
        Bar.__init__(self, window, constants)




class Pot(WindowObject):
    type='default'
    window=None
    moneyColor=''
    def __init__(self, window, constants):
        self.moneyColor = constants['moneyColor']
        x1, y1 = constants[self.type+'potMoney']
        self.window = SubWindow(window, x1, y1, 1, 1)
        WindowObject.__init__(self, self.window, window)

    def hasPot(self):
        self.window.getScreenShot()
        return self.window.getPixel(0,0) != self.moneyColor

class HealthPot(Pot):
    type='health'
    def __init__(self, window, constants):
        Pot.__init__(self, window, constants)

class ManaPot(Pot):
    type='mana'
    def __init__(self, window, constants):
        Pot.__init__(self, window, constants)


class ItemWindow(WindowObject):
    type='default'
    window=None
    def __init__(self, window, constants):
        rec = constants[self.type+'Window']
        self.window = SubWindow(window, rec[0][0], rec[0][1], rec[1][0], rec[1][1])
        WindowObject.__init__(self, self.window, window)

class InventoryWindow(ItemWindow):
    type="inventory"
    def __init__(self, window, constants):
        ItemWindow.__init__(self, window, constants)
        self.item_space = autopy.bitmap.Bitmap.open(os.path.join('img', 'item_space.png'))
    def hasSpace(self):
        self.window.getScreenShot()
        coord = self.window.current_screen.find_bitmap(self.item_space, 0.2)
        return coord is not None

class LootWindow(ItemWindow):
    type="loot"
    def __init__(self, window, constants):
        ItemWindow.__init__(self, window, constants)
        self.bottom_right = autopy.bitmap.Bitmap.open(os.path.join('img', 'loot_bottom_right.png'))
    def hasLoot(self):
        self.window.getScreenShot()
        coord = self.window.current_screen.find_bitmap(self.bottom_right, 0.1, None, 0)
        return coord is not None
