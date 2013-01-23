#!/usr/bin/env python
# downloaded from ftp://ftp.heanet.ie/disk1/download.sourceforge.net/pub/sourceforge/i/i-/i-am-human/Source/KeyboardUnix.py
#
# pykey -- a Python version of crikey,
# http://shallowsky.com/software/crikey
# Simulate keypresses under X11.
#
# This software is copyright 2008 by Akkana Peck.
# Please share and re-use this under the terms of the GPLv2
# or, at your option, any later GPL version.

"""
BUG :
    in writeLetter
    if (self.UseXTest==2) == True
        write in the terminal
        use correct keyboard (azerty)
    else
        write in the selected window
        use qwerty keyboard
"""

import Xlib.display
import Xlib.X
import Xlib.XK
import Xlib.protocol.event

import time

class Keyboard(object):

    def __init__(self):
        self.UseXTest = True

        try :
            import Xlib.ext.xtest
        except ImportError:
            self.UseXTest = False
            print "no XTest extension; using XSendEvent"


        self.display = Xlib.display.Display()
        self.window = self.display.get_input_focus()._data["focus"];

        if self.UseXTest and not self.display.query_extension("XTEST") :
            self.UseXTest = False

        self.special_X_keysyms = {
            ' ' : "space",
            '\t' : "Tab",
            '\n' : "Return",  # for some reason this needs to be cr, not lf
            '\r' : "Return",
            '\e' : "Escape",
            '!' : "exclam",
            '#' : "numbersign",
            '%' : "percent",
            '$' : "dollar",
            '&' : "ampersand",
            '"' : "quotedbl",
            '\'' : "apostrophe",
            '(' : "parenleft",
            ')' : "parenright",
            '*' : "asterisk",
            '=' : "equal",
            '+' : "plus",
            ',' : "comma",
            '-' : "minus",
            '.' : "period",
            '/' : "slash",
            ':' : "colon",
            ';' : "semicolon",
            '<' : "less",
            '>' : "greater",
            '?' : "question",
            '@' : "at",
            '[' : "bracketleft",
            ']' : "bracketright",
            '\\' : "backslash",
            '^' : "asciicircum",
            '_' : "underscore",
            '`' : "grave",
            '{' : "braceleft",
            '|' : "bar",
            '}' : "braceright",
            '~' : "asciitilde"
            }


    def get_keysym(self, ch) :
        keysym = Xlib.XK.string_to_keysym(ch)
        if keysym == 0 :
            # Unfortunately, although this works to get the correct keysym
            # i.e. keysym for '#' is returned as "numbersign"
            # the subsequent display.keysym_to_keycode("numbersign") is 0.
            keysym = Xlib.XK.string_to_keysym(self.special_X_keysyms[ch])
        return keysym

    def is_shifted(self, ch) :
        if ch.isupper() :
            return True
        if "~!@#$%^&*()_+{}|:\"<>?".find(ch) >= 0 :
            return True
        return False

    def char_to_keycode(self, ch) :
        keysym = self.get_keysym(ch)
        keycode = self.display.keysym_to_keycode(keysym)
        if keycode == 0 :
            print "Sorry, can't map", ch

        if (self.is_shifted(ch)) :
            shift_mask = Xlib.X.ShiftMask
        else :
            shift_mask = 0

        return keycode, shift_mask

    def writeKeyCode(self, k):
        keycode = self.display.keysym_to_keycode(k)
        self.writeCode(keycode, 0)

    def writeLetter(self, ch):
        keycode, shift_mask = self.char_to_keycode(ch)
        self.writeCode(keycode, shift_mask)

    def writeCode(self, keycode, shift_mask):
        if (self.UseXTest==True) :
            if shift_mask != 0 :
                Xlib.ext.xtest.fake_input(self.display, Xlib.X.KeyPress, 50)
            Xlib.ext.xtest.fake_input(self.display, Xlib.X.KeyPress, keycode)
            Xlib.ext.xtest.fake_input(self.display, Xlib.X.KeyRelease, keycode)
            if shift_mask != 0 :
                Xlib.ext.xtest.fake_input(self.display, Xlib.X.KeyRelease, 50)
        else :
            event = Xlib.protocol.event.KeyPress(
                time = int(time.time()),
                root = self.display.screen().root,
                window = self.window,
                same_screen = 0, child = Xlib.X.NONE,
                root_x = 0, root_y = 0, event_x = 0, event_y = 0,
                state = shift_mask,
                detail = keycode
                )
            self.window.send_event(event, propagate = True)
            event = Xlib.protocol.event.KeyRelease(
                time = int(time.time()),
                root = self.display.screen().root,
                window = self.window,
                same_screen = 0, child = Xlib.X.NONE,
                root_x = 0, root_y = 0, event_x = 0, event_y = 0,
                state = shift_mask,
                detail = keycode
                )
            self.window.send_event(event, propagate = True)
        self.display.sync()


    def write(self, string):
        for ch in string:
            self.writeLetter(ch)

