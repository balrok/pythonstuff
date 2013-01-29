import gtk.gdk
from pymouse import PyMouse
import autopy
import numpy

class Window:
    current_screen = None
    width = 0,
    height = 0
    mouse = None
    offsetTop = 0
    offsetLeft = 0


    def __init__(self):
        self.mouse = PyMouse()

    def mouseMove(self, top, left):
        self.mouse.move(top, left)

    def mouseClick(self, top, left, key=1):
        self.mouse.press(left, top, key)
        self.mouse.release(left, top, key)

    def getScreenShot(self):
        w = gtk.gdk.get_default_root_window()
        sz = w.get_size()

        pb = gtk.gdk.Pixbuf(gtk.gdk.COLORSPACE_RGB,False,8, sz[0], sz[1])
        pb = pb.get_from_drawable(w,w.get_colormap(), 0, 0, 0, 0, sz[0], sz[1])
        self.width,self.height = pb.get_width(),pb.get_height()
        self.current_screen = pb
        return self.current_screen

    def getPixel(self, top, left):
        return self.current_screen.pixel_array[top, left]

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
        self.mouse = parentWin.mouse

    # override to just shoot the smaller screen
    def getScreenShot(self):
        w = gtk.gdk.get_default_root_window()
        pb = gtk.gdk.Pixbuf(gtk.gdk.COLORSPACE_RGB,False,8, self.width, self.height)
        pb = pb.get_from_drawable(w, w.get_colormap(), self.offsetLeft, self.offsetTop, 0, 0, self.width, self.height)
        self.width, self.height = pb.get_width(), pb.get_height()
        self.current_screen = pb
        return self.current_screen




# compares two colors for equality
def eqColor(c1, c2):
    if not isinstance(c1, (list, tuple, numpy.ndarray)):
        c1 = autopy.color.hex_to_rgb(c1)
    if not isinstance(c2, (list, tuple, numpy.ndarray)):
        c2 = autopy.color.hex_to_rgb(c2)
    return numpy.array_equal(c1, c2)

# finds the top,left position of a color optionally starting at startX and startY
def findColor(win, color, step=5, startX=0, startY=0):
    if not isinstance(color, (list, tuple)):
        color = autopy.color.hex_to_rgb(color)
    # first iterate to find the area around games
    smallestX = -1
    smallestY = -1
    # first search smallestX, smallestY
    for x in range(startX, win.height, step):
        for y in range(startY, win.width, step):
            if eqColor(win.getPixel(x,y), color):
                smallestX = x
                smallestY = y
                break
        if smallestX > -1:
            break
    return smallestX, smallestY

# finds the top,left position and from there the most right and lowest position
def findColorArea(win, color, step=5, startX=0, startY=0):
    if not isinstance(color, (list, tuple)):
        color = autopy.color.hex_to_rgb(color)
    # first iterate to find the area around games
    highestX = -1
    highestY = -1
    x = 0
    smallestX, smallestY = findColor(win, color, step, startX, startY)
    if smallestX > -1:
        for y in range(smallestY, win.width, step):
            x = smallestX
            if not eqColor(win.getPixel(smallestX,y), color):
                highestY = y-step
                break
        for x in range(smallestX, win.height, step):
            y = smallestY
            if not eqColor(win.getPixel(x,smallestY), color):
                highestX = x-step
                break
    print (smallestX, smallestY, highestX, highestY)
    return smallestX, smallestY, highestX, highestY
