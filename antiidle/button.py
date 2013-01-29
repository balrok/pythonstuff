#!/usr/bin/python

from window import eqColor
from window import findColor

class Button(object):
    # height and width of the button
    height = 0
    width = 0
    # last position
    lastTop = -1
    lastLeft = -1

    area = (0,0,0,0)

    # the color of the button - somethimes blue, sometimes red.. find it out..
    color = [0xc86400, 0x0064c8]

    # the bg color left and right from the button
    brokeBgColor = 0x990000
    okBgColor = 0x666666

    # the color surrounding the button area
    buttoneAreaColor = 0x333333
    # the color of a highlighted repairbutton
    repairColor = 0x9b68e9

    def __init__(self, win):
        self.win = win

    # finds the center of the button
    def findCenter(self):
        if self.lastLeft == -1:
            # very coarse grained search for some point of the button
            for color in self.color:
                top,left = findColor(self.win, color, 20)
                if top > -1:
                    self.color = color # also set the correct color
                    break
        else:
            # the button doesnt move so fast, that lastTop and lastLeft is a good guess
            top, left = self.lastTop, self.lastLeft

        # from the center go most left and most right and take the center again
        for l in range(left, 0, -1):
            if not eqColor(self.win.getPixel(top,l), self.color):
                canContinue = False
                for jump in range(0,40,2):
                    if eqColor(self.win.getPixel(top-jump,l), self.color): # try to jump over the text if exist
                        l-=jump-1
                        canContinue = True
                        break
                mLeft = l+1
                if canContinue:
                    continue
                break
        for l in range(left, left+200, 1):
            if not eqColor(self.win.getPixel(top,l), self.color):
                canContinue = False
                for jump in range(0,40,2):
                    if eqColor(self.win.getPixel(top+jump,l), self.color): # try to jump over the text if exist
                        l+=jump+1
                        canContinue = True
                        break
                mRight = l-1
                if canContinue:
                    continue
                break

        hCenter = mLeft+((mRight-mLeft)/2)
        # from top,hCenter go most up, and most down - take the center
        for t in range(top, 0, -1):
            if not eqColor(self.win.getPixel(t,hCenter), self.color):
                canContinue = False
                for jump in range(0,40,2):
                    if eqColor(self.win.getPixel(t-jump,hCenter), self.color): # try to jump over the text if exist
                        t-=jump-1
                        canContinue = True
                        break
                mTop = t+1
                if canContinue:
                    continue
                break
        for t in range(top, top+200, 1):
            if not eqColor(self.win.getPixel(t,hCenter), self.color):
                canContinue = False
                for jump in range(0,40,2):
                    if eqColor(self.win.getPixel(t+jump,hCenter), self.color): # try to jump over the text if exist
                        t+=jump+1
                        canContinue = True
                        break
                mBot = t-1
                if canContinue:
                    continue
                break
        vCenter = mTop+((mBot-mTop)/2)

        self.height = mBot-mTop
        self.width = mRight-mLeft
        self.lastTop = vCenter
        self.lastLeft = hCenter

        self.area = (mTop,mLeft,mBot,mRight) # could be used for debugging
        return vCenter,hCenter

    def isBroken(self):
        # look at the bg-area on both points for the brokencolor
        return eqColor(self.win.getPixel(self.bgArea[0], self.bgArea[1]), self.brokeBgColor) or eqColor(self.win.getPixel(self.bgArea[1], self.bgArea[2]), self.brokeBgColor)

    def getBgArea(self):
        # first we need the button center
        top, left = self.findCenter()
        mLeftTop, mLeft = self.getBgAreaHorizontal(top, left, -1)
        mRightTop, mRight = self.getBgAreaHorizontal(top, left, 1)
        self.bgArea = (mLeftTop, mLeft, mRightTop, mRight)
        # with mLeft and mRight we should be able to calculate all centers for the button
        return mLeftTop, mLeft, mRightTop, mRight

    # helper for getBgArea gets the most left or most right part depending on the step
    # the comments are designed for going to the left.. but depending on the step it could also go to the right
    def getBgAreaHorizontal(self, top, left, step):
        print "getBgAreaHorizontal",top,left,step
        countTo = 0
        if step > 0:
            countTo = left+1000
        # find the border of the button
        for l in range(left, countTo, step):
            if not eqColor(self.win.getPixel(top,l), self.color):
                mLeft = l+(5*step) # go a little more left when we found the border of the button
                break
        # then we go to the most left part from here
        for l in range(mLeft, countTo, step):
            if not eqColor(self.win.getPixel(top,l), self.okBgColor):
                mLeft = l+((-1)*step)
                mTop = top
                break
        print mLeft
        # now look if we can get more left if we go up or down a bit
        #up
        better = False
        for t in range(top, 0, -1):
            for l in range(mLeft, countTo, step):
                if not eqColor(self.win.getPixel(t,l), self.okBgColor):
                    newMLeft = l+((-1)*step)
                    break
            if (step < 0 and newMLeft < mLeft) or (step > 0 and newMLeft > mLeft):
                mLeft = newMLeft
                mTop = t
                better = True
                print "better1",mLeft
            else:
                break
        #down
        if not better:
            for t in range(top, top+200, 1):
                for l in range(mLeft, countTo, step):
                    if not eqColor(self.win.getPixel(t,l), self.okBgColor):
                        newMLeft = l+((-1)*step)
                        break
                if (step < 0 and newMLeft < mLeft) or (step > 0 and newMLeft > mLeft):
                    mLeft = newMLeft
                    mTop = t
                    print "better2",mLeft
                else:
                    break
        # now we should realy have the mLeft
        return mTop, mLeft

    def findShopAndRepair(self):
        # finding repair starts from the left bgArea - searches down.. the first violet button
        # is the shop - after this comes the repairbutton
        # so go down and search for 333333 (gamearea bg)
        # first time it isn't 333333 it is the shop-button
        # and again for repair
        top = self.bgArea[0]
        left = self.bgArea[1]+10 # add a bit so it isn't too close to the border
        for t in range(top, top+200, 1):
            if eqColor(self.win.getPixel(t,left), self.buttoneAreaColor):
                top = t
                break
        for t in range(top, top+200, 1):
            if not eqColor(self.win.getPixel(t,left), self.buttoneAreaColor):
                self.shopButton = (t+10, left) # found the shopButton
                top = t+20
                break
        for t in range(top, top+200, 1):
            if eqColor(self.win.getPixel(t,left), self.buttoneAreaColor):
                top = t
                break
        for t in range(top, top+200, 1):
            if not eqColor(self.win.getPixel(t,left), self.buttoneAreaColor):
                self.repairButton = (t+10, left) # found the repairButton
                top = t+20
                break

    def __str__(self):
        return 'Button: wh(%d, %d) tl(%d, %d)' % (self.width, self.height, self.lastTop, self.lastLeft)
