from window import SubWindow
from window import eqColor
from window import findColorArea
from window import getArrayColor
from window import findColor

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
        x1,y1,x2,y2 = findColorArea(window, getArrayColor(color), 1)
        return (x1,y1,x2,y2)

    def getPercentFull(self):
        # scan for bgcolor
        self.window.getScreenShot()
        x,y = findColor(self.window, getArrayColor(self.bgcolor))
        if x>-1 and y>-1:
            x2,y2 = findColor(self.window, getArrayColor(self.barcolor))
            # when hovering over items in a trade it will cover the bar
            if x2==-1 and y==-1:
                return 100
            # we found bg - so not 100 full
            return float(y)/self.width*100
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
        if not self.type+"potMoney" in constants:
            raise Exception(self.type+"potMoney should be defined")
        self.moneyColor = constants['moneyColor']
        x1, y1 = constants[self.type+'potMoney']
        self.window = SubWindow(window, x1, y1, 1, 1)
        WindowObject.__init__(self, self.window, window)

    def hasPot(self):
        self.window.getScreenShot()
        return not eqColor(self.window.getPixel(0,0), getArrayColor(self.moneyColor))

class HealthPot(Pot):
    type='health'
    def __init__(self, window, constants):
        Pot.__init__(self, window, constants)

class ManaPot(Pot):
    type='mana'
    def __init__(self, window, constants):
        Pot.__init__(self, window, constants)

