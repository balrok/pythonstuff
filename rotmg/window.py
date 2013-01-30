import autopy

class Window:
    current_screen = None
    width = 0,
    height = 0
    offsetTop = 0
    offsetLeft = 0

    def mouseMove(self, top, left):
        print "move",(self.offsetLeft+left, self.offsetTop+top)
        autopy.mouse.move(self.offsetLeft+left, self.offsetTop+top)
        print autopy.mouse.get_pos()

    def mouseClick(self, key=autopy.mouse.LEFT_BUTTON):
        autopy.mouse.click(key)

    def getScreenShot(self):
        self.current_screen = autopy.bitmap.capture_screen()
        self.width=self.current_screen.width
        self.height=self.current_screen.width
        return self.current_screen

    def getPixel(self, top, left):
        return self.current_screen.get_color(left, top)

# to increase performance it might be intelligent to not capture the whole screen, but a subscreen
# so a subwindow is a smaller part of the screen
class SubWindow(Window):
    # where does this screen start inside the window?
    def __init__(self, parentWin, offsetTop, offsetLeft, width, height):
        self.offsetTop = offsetTop
        self.offsetLeft = offsetLeft
        self.offsetTop += parentWin.offsetTop
        self.offsetLeft += parentWin.offsetLeft
        self.width = width
        self.height = height
        self.parentWin = parentWin

    # override to just shoot the smaller screen
    def getScreenShot(self):
        self.current_screen = autopy.bitmap.capture_screen(((self.offsetLeft,self.offsetTop),(self.width,self.height)))
        return self.current_screen

# finds the top,left position of a color optionally starting at startX and startY
def findColor(win, color, step=5, startX=0, startY=0):
    # first iterate to find the area around games
    smallestX = -1
    smallestY = -1
    # first search smallestX, smallestY
    for x in range(startX, win.height, step):
        for y in range(startY, win.width, step):
            if win.getPixel(x,y) == color:
                smallestX = x
                smallestY = y
                break
        if smallestX > -1:
            break
    return smallestX, smallestY

# finds the top,left position and from there the most right and lowest position
def findColorArea(win, color, step=5, startX=0, startY=0):
    # first iterate to find the area around games
    highestX = -1
    highestY = -1
    x = 0
    smallestX, smallestY = findColor(win, color, step, startX, startY)
    if smallestX > -1:
        for y in range(smallestY, win.width, step):
            x = smallestX
            if win.getPixel(smallestX,y) != color:
                highestY = y-step
                break
        for x in range(smallestX, win.height, step):
            y = smallestY
            if win.getPixel(x,smallestY) != color:
                highestX = x-step
                break
    print (smallestX, smallestY, highestX, highestY)
    return smallestX, smallestY, highestX, highestY
