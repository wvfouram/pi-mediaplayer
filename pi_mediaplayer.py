#!/usr/bin/python3
# Media Player for Raspberry Pi, styled after the Windows 11 Media Player (dark).
import os
import sys
import re
import json
import math
import time
import shutil
import signal
import threading
import subprocess

import gi
gi.require_version("Gtk", "3.0")
gi.require_version("Gdk", "3.0")
gi.require_version("GdkPixbuf", "2.0")
from gi.repository import Gtk, Gdk, GLib, GdkPixbuf, Pango, Gio, GObject  # noqa: E402,F401
import cairo  # noqa: E402

HOME = os.path.expanduser("~")
C_ACCENT = "#4CC2FF"
def hexc(h, a=1.0):
    h = h.lstrip("#")
    return (int(h[0:2], 16) / 255, int(h[2:4], 16) / 255, int(h[4:6], 16) / 255, a)


def _rr(cr, x, y, w, h, r):
    r = min(r, w / 2, h / 2)
    cr.new_sub_path()
    cr.arc(x + w - r, y + r, r, -math.pi / 2, 0)
    cr.arc(x + w - r, y + h - r, r, 0, math.pi / 2)
    cr.arc(x + r, y + h - r, r, math.pi / 2, math.pi)
    cr.arc(x + r, y + r, r, math.pi, 1.5 * math.pi)
    cr.close_path()


def _line(cr, *pts):
    cr.move_to(*pts[0])
    for p in pts[1:]:
        cr.line_to(*p)
    cr.stroke()


def draw_glyph(cr, name, s, col):
    """Monochrome line icons for buttons."""
    cr.save()
    cr.scale(s / 16.0, s / 16.0)
    cr.set_source_rgba(*col)
    cr.set_line_width(1.15)
    cr.set_line_cap(cairo.LINE_CAP_ROUND)
    cr.set_line_join(cairo.LINE_JOIN_ROUND)
    pi = math.pi
    L = lambda *p: _line(cr, *p)  # noqa: E731
    if name == "back":
        L((13.5, 8), (2.5, 8))
        L((7, 3.5), (2.5, 8), (7, 12.5))
    elif name == "forward":
        L((2.5, 8), (13.5, 8))
        L((9, 3.5), (13.5, 8), (9, 12.5))
    elif name == "up":
        L((8, 13.5), (8, 2.5))
        L((3.5, 7), (8, 2.5), (12.5, 7))
    elif name == "refresh":
        cr.arc(8, 8, 5.5, -pi * 0.35, pi * 1.55)
        cr.stroke()
        L((12.9, 1.8), (12.6, 4.9), (9.6, 4.6))
    elif name == "plus":
        L((8, 2.5), (8, 13.5))
        L((2.5, 8), (13.5, 8))
    elif name == "new":
        cr.set_source_rgba(*hexc(C_ACCENT))
        cr.arc(8, 8, 6.5, 0, 2 * pi)
        cr.stroke()
        L((8, 4.8), (8, 11.2))
        L((4.8, 8), (11.2, 8))
    elif name == "cut":
        cr.arc(4.5, 12, 2, 0, 2 * pi)
        cr.stroke()
        cr.arc(11.5, 12, 2, 0, 2 * pi)
        cr.stroke()
        L((5.8, 10.5), (11, 1.8))
        L((10.2, 10.5), (5, 1.8))
    elif name == "copy":
        _rr(cr, 5, 1.5, 9, 10.5, 1.5)
        cr.stroke()
        cr.move_to(3, 4.5)
        cr.line_to(3, 13)
        cr.arc_negative(4.5, 13, 1.5, pi, pi / 2)
        cr.line_to(11, 14.5)
        cr.stroke()
    elif name == "paste":
        _rr(cr, 2.5, 3, 11, 11.5, 1.5)
        cr.stroke()
        _rr(cr, 5.5, 1.5, 5, 3, 1)
        cr.stroke()
        L((5.5, 8), (10.5, 8))
        L((5.5, 11), (9, 11))
    elif name == "rename":
        _rr(cr, 1.5, 4.5, 13, 7, 1.3)
        cr.stroke()
        L((4, 8), (8, 8))
        L((10.5, 2.5), (10.5, 13.5))
        L((9, 2.5), (12, 2.5))
        L((9, 13.5), (12, 13.5))
    elif name == "delete" or name == "trash":
        L((2.5, 4), (13.5, 4))
        L((6, 4), (6.5, 2), (9.5, 2), (10, 4))
        cr.move_to(4, 4)
        cr.line_to(4.8, 14)
        cr.line_to(11.2, 14)
        cr.line_to(12, 4)
        cr.stroke()
        L((6.8, 6.8), (7, 11.5))
        L((9.2, 6.8), (9, 11.5))
    elif name == "sort":
        L((4.5, 2.5), (4.5, 13.5))
        L((2, 5), (4.5, 2.5), (7, 5))
        L((11.5, 2.5), (11.5, 13.5))
        L((9, 11), (11.5, 13.5), (14, 11))
    elif name == "view":
        for y in (3, 8, 13):
            L((2, y), (14, y))
    elif name == "more":
        for x in (3, 8, 13):
            cr.arc(x, 8, 1.1, 0, 2 * pi)
            cr.fill()
    elif name == "chevdown":
        L((4, 6), (8, 10), (12, 6))
    elif name == "chevright":
        L((6, 4), (10, 8), (6, 12))
    elif name == "close":
        L((3.5, 3.5), (12.5, 12.5))
        L((12.5, 3.5), (3.5, 12.5))
    elif name == "min":
        L((3, 8), (13, 8))
    elif name == "max":
        _rr(cr, 3, 3, 10, 10, 1.2)
        cr.stroke()
    elif name == "restore":
        _rr(cr, 3, 5, 8, 8, 1.2)
        cr.stroke()
        L((5, 3), (12, 3), (13, 4), (13, 11))
    elif name == "search":
        cr.arc(6.6, 6.6, 4.6, 0, 2 * pi)
        cr.stroke()
        L((10, 10), (14, 14))
    elif name == "pane":
        _rr(cr, 1.5, 2.5, 13, 11, 1.5)
        cr.stroke()
        L((10, 2.5), (10, 13.5))
    elif name == "terminal":
        _rr(cr, 1.5, 2.5, 13, 11, 1.5)
        cr.stroke()
        L((4, 6), (6.5, 8), (4, 10))
        L((8, 10.5), (11.5, 10.5))
    elif name == "properties":
        _rr(cr, 2.5, 1.5, 11, 13, 1.5)
        cr.stroke()
        for y in (5, 8, 11):
            cr.arc(5.2, y, 0.8, 0, 2 * pi)
            cr.fill()
            L((7.2, y), (11, y))
    elif name == "pin":
        cr.move_to(6, 2)
        cr.line_to(10, 2)
        cr.line_to(9.5, 6.5)
        cr.line_to(12, 9)
        cr.line_to(4, 9)
        cr.line_to(6.5, 6.5)
        cr.close_path()
        cr.stroke()
        L((8, 9), (8, 14))
    elif name == "pin-fill":
        cr.set_line_width(1.0)
        cr.translate(8, 8)
        cr.rotate(pi / 4)
        cr.translate(-8, -8)
        cr.move_to(6, 2)
        cr.line_to(10, 2)
        cr.line_to(9.5, 6.5)
        cr.line_to(12, 9)
        cr.line_to(4, 9)
        cr.line_to(6.5, 6.5)
        cr.close_path()
        cr.stroke()
        L((8, 9), (8, 14))
    elif name == "folder":
        cr.move_to(1.5, 4)
        cr.line_to(6, 4)
        cr.line_to(7.5, 5.5)
        cr.line_to(14.5, 5.5)
        cr.line_to(14.5, 13)
        cr.line_to(1.5, 13)
        cr.close_path()
        cr.stroke()
    elif name == "file":
        cr.move_to(3.5, 1.5)
        cr.line_to(9.5, 1.5)
        cr.line_to(12.5, 4.5)
        cr.line_to(12.5, 14.5)
        cr.line_to(3.5, 14.5)
        cr.close_path()
        cr.stroke()
        L((9.5, 1.5), (9.5, 4.5), (12.5, 4.5))
    elif name == "zip":
        _rr(cr, 2.5, 1.5, 11, 13, 1.5)
        cr.stroke()
        for y in (3, 5, 7):
            L((7, y), (9, y))
        _rr(cr, 6.5, 9, 3, 3.5, 0.6)
        cr.stroke()
    elif name == "extract":
        _rr(cr, 2.5, 6.5, 11, 8, 1.5)
        cr.stroke()
        L((8, 1.5), (8, 10))
        L((5.5, 7.5), (8, 10), (10.5, 7.5))
    elif name == "restoreitem":
        cr.arc(8.5, 8.5, 5, -pi * 0.9, pi * 0.6)
        cr.stroke()
        L((2, 3.5), (3.6, 6.6), (6.6, 5.4))
    elif name == "open":
        _rr(cr, 1.5, 1.5, 13, 13, 2)
        cr.stroke()
        L((7, 9), (12.5, 3.5))
        L((8.5, 3.5), (12.5, 3.5), (12.5, 7.5))
    elif name == "newtab":
        _rr(cr, 1.5, 3.5, 13, 10, 1.5)
        cr.stroke()
        L((1.5, 6), (8, 6))
        L((8, 3.5), (8, 6))
    elif name == "check":
        L((3, 8.5), (6.5, 12), (13, 4.5))
    elif name == "eject":
        cr.move_to(8, 3)
        cr.line_to(13, 9)
        cr.line_to(3, 9)
        cr.close_path()
        cr.stroke()
        L((3, 12.5), (13, 12.5))
    elif name == "details-view":
        for y in (3.5, 8, 12.5):
            _rr(cr, 1.5, y - 1.2, 2.4, 2.4, 0.5)
            cr.stroke()
            L((6, y), (14.5, y))
    elif name == "icons-view":
        for x in (2, 9):
            for y in (2, 9):
                _rr(cr, x, y, 5, 5, 1.2)
                cr.stroke()
    elif name == "selectall":
        _rr(cr, 2, 2, 12, 12, 1.5)
        cr.stroke()
        L((5, 8), (7.2, 10.2), (11, 6))
    elif name == "info":
        cr.arc(8, 8, 6, 0, 2 * pi)
        cr.stroke()
        L((8, 7), (8, 11.5))
        cr.arc(8, 4.8, 0.9, 0, 2 * pi)
        cr.fill()
    elif name == "share":
        cr.arc(4, 8, 1.8, 0, 2 * pi)
        cr.stroke()
        cr.arc(12, 3.8, 1.8, 0, 2 * pi)
        cr.stroke()
        cr.arc(12, 12.2, 1.8, 0, 2 * pi)
        cr.stroke()
        L((5.6, 7.1), (10.4, 4.7))
        L((5.6, 8.9), (10.4, 11.3))
    elif name == "network":
        _rr(cr, 5, 1.5, 6, 4.5, 1)
        cr.stroke()
        L((8, 6), (8, 9))
        L((3, 9), (13, 9))
        L((3, 9), (3, 11))
        L((13, 9), (13, 11))
        _rr(cr, 1, 11, 4, 3.5, 0.8)
        cr.stroke()
        _rr(cr, 11, 11, 4, 3.5, 0.8)
        cr.stroke()
    elif name == "link":
        cr.arc(5.5, 10.5, 3, pi * 0.25, pi * 1.75)
        cr.stroke()
        cr.arc(10.5, 5.5, 3, pi * 1.25, pi * 0.75)
        cr.stroke()
        L((6.5, 9.5), (9.5, 6.5))
    else:
        draw_glyph_extra(cr, name, L, pi)
    cr.restore()




# ----------------------------------------------------------------------------
# Shared Windows 11 dark style
# ----------------------------------------------------------------------------
BASE_CSS = """
* { font-family: "Segoe UI Variable Text", "Segoe UI", "Selawik", "Open Sans", "Noto Sans", sans-serif; }
window.fx, window.fx-dialog { background-color: #202020; color: #ffffff; font-size: 12px; }
.fx label { color: #ffffff; }
headerbar.fx-title { background: #202020; border: none; box-shadow: none; min-height: 40px; padding: 0; margin: 0; }
headerbar.fx-title:backdrop { background: #202020; }
.app-title { font-size: 12px; color: #ffffff; margin-left: 4px; }
.app-title:backdrop { color: rgba(255,255,255,0.55); }
button.wc { background: transparent; border: none; border-radius: 0; min-width: 46px; min-height: 32px; padding: 0; box-shadow: none; }
button.wc:hover { background-color: rgba(255,255,255,0.06); }
button.wc.close:hover { background-color: #C42B1C; }
.tabstrip { margin-top: 6px; margin-left: 6px; }
button.tab { outline-color: transparent; background: transparent; border: none; border-radius: 8px 8px 0 0; min-height: 34px;
   padding: 0 6px 0 12px; box-shadow: none; margin-right: 1px; }
button.tab:hover { background-color: rgba(255,255,255,0.04); }
button.tab.active { background-color: #2C2C2C; }
button.tab label { font-size: 12px; }
button.tab-x { background: transparent; border: none; border-radius: 4px; min-width: 24px; min-height: 24px; padding: 0; box-shadow: none; }
button.tab-x:hover { background-color: rgba(255,255,255,0.08); }
button.tab-new { background: transparent; border: none; border-radius: 4px; min-width: 32px; min-height: 28px; padding: 0;
   box-shadow: none; margin-top: 4px; margin-left: 2px; }
button.tab-new:hover { background-color: rgba(255,255,255,0.06); }
.bar { background-color: #2C2C2C; padding: 4px 8px; }
.bar-bottom { border-bottom: 1px solid rgba(255,255,255,0.06); }
button.tb, button.nb { background: transparent; border: none; border-radius: 4px; min-height: 32px; padding: 0 9px; box-shadow: none; color: #ffffff; }
button.nb { min-width: 34px; padding: 0; }
button.tb:hover, button.nb:hover { background-color: rgba(255,255,255,0.06); }
button.tb:active, button.nb:active { background-color: rgba(255,255,255,0.04); }
button.tb:disabled label { color: rgba(255,255,255,0.36); }
button.tb label { font-size: 12px; }
button.tb.on, button.nb.on { background-color: rgba(255,255,255,0.09); }
.vsep { background-color: rgba(255,255,255,0.08); min-width: 1px; margin: 6px 6px; }
.status { background-color: #202020; padding: 4px 12px; border-top: 1px solid rgba(255,255,255,0.06); }
.status label { font-size: 12px; color: rgba(255,255,255,0.786); }
.sec { color: rgba(255,255,255,0.786); }
.ter { color: rgba(255,255,255,0.545); }
.big-title { font-size: 20px; font-weight: 600; }
.sect-title { font-size: 14px; font-weight: 600; }
entry.field, entry.fx-search { background-color: rgba(255,255,255,0.06); color: #ffffff; border: 1px solid rgba(255,255,255,0.07);
   border-bottom: 1px solid rgba(255,255,255,0.54); border-radius: 4px; min-height: 30px; padding: 0 10px; box-shadow: none;
   font-size: 12px; caret-color: #ffffff; }
entry.field:focus, entry.fx-search:focus { background-color: #1c1c1c; border-bottom: 2px solid #4CC2FF; }
entry selection, textview text selection, entry selection:focus, textview text selection:focus { background-color: #0078D4; color: #ffffff; }
scrollbar { background: transparent; border: none; }
scrollbar slider { background-color: rgba(255,255,255,0.45); border-radius: 6px; min-width: 3px; min-height: 3px; border: none; }
scrollbar:hover slider { min-width: 6px; min-height: 6px; background-color: rgba(255,255,255,0.55); }
scrollbar trough { background: transparent; border: none; }
scale trough { background-color: rgba(255,255,255,0.3); border: none; border-radius: 2px; min-height: 4px; min-width: 4px; }
scale highlight { background-color: #4CC2FF; border: none; border-radius: 2px; min-height: 4px; min-width: 4px; }
scale slider { background-color: #4CC2FF; border: 5px solid #454545; border-radius: 50%; min-width: 12px; min-height: 12px; box-shadow: none; }
scale slider:hover { border-width: 4px; }
menu, .menu, .context-menu { background-color: #2C2C2C; color: #ffffff; border: 1px solid rgba(0,0,0,0.45); border-radius: 8px; padding: 4px; }
menu menuitem { padding: 6px 12px; border-radius: 4px; color: #ffffff; min-height: 18px; }
menu menuitem:hover { background-color: rgba(255,255,255,0.06); }
menu menuitem:disabled label { color: rgba(255,255,255,0.36); }
menu menuitem label { color: #ffffff; font-size: 12px; }
menu menuitem arrow { color: rgba(255,255,255,0.786); }
menu separator { background-color: rgba(255,255,255,0.08); margin: 4px 0; min-height: 1px; }
window.fx button, window.fx-dialog button { background-image: none; text-shadow: none; -gtk-icon-shadow: none; }
button.primary { background-color: #4CC2FF; color: #000000; border: none; border-radius: 4px; min-height: 30px; padding: 0 16px; box-shadow: none; }
button.primary label { color: #000000; }
button.primary:hover { background-color: #48B1E8; }
button.secondary { background-color: rgba(255,255,255,0.06); color: #ffffff; border: 1px solid rgba(255,255,255,0.09); border-radius: 4px; min-height: 30px; padding: 0 16px; box-shadow: none; }
button.secondary:hover { background-color: rgba(255,255,255,0.09); }
.dlg-body { background-color: #2B2B2B; padding: 24px; }
.dlg-foot { background-color: #202020; padding: 22px 24px; border-top: 1px solid rgba(0,0,0,0.3); }
.dlg-title { font-size: 20px; font-weight: 600; }
.fx-dialog label { color: #ffffff; }
.fx-dialog label.sec { color: rgba(255,255,255,0.786); }
.fx-dialog label.ter { color: rgba(255,255,255,0.545); }
checkbutton check { background-color: rgba(0,0,0,0.1); border: 1px solid rgba(255,255,255,0.6); border-radius: 4px; min-width: 18px; min-height: 18px; -gtk-icon-source: none; color: #000000; }
checkbutton check:checked { background-color: #4CC2FF; border-color: #4CC2FF; -gtk-icon-source: -gtk-icontheme("object-select-symbolic"); }
checkbutton label { color: #ffffff; font-size: 12px; margin-left: 6px; }
radiobutton radio { background-color: rgba(0,0,0,0.1); border: 1px solid rgba(255,255,255,0.6); border-radius: 50%; min-width: 18px; min-height: 18px; -gtk-icon-source: none; }
radiobutton radio:checked { background-color: #000000; border: 5px solid #4CC2FF; }
radiobutton label { color: #ffffff; font-size: 12px; margin-left: 6px; }
switch { background-color: transparent; border: 1px solid rgba(255,255,255,0.6); border-radius: 12px; min-width: 40px; min-height: 18px; }
switch:checked { background-color: #4CC2FF; border-color: #4CC2FF; }
switch slider { background-color: rgba(255,255,255,0.8); border-radius: 50%; min-width: 12px; min-height: 12px; margin: 3px; border: none; box-shadow: none; }
switch:checked slider { background-color: #000000; }
switch image { color: transparent; }
combobox button, combobox box { background-color: rgba(255,255,255,0.06); color: #ffffff; border: 1px solid rgba(255,255,255,0.07); border-radius: 4px; box-shadow: none; min-height: 30px; }
combobox button cellview, combobox button label, combobox arrow { color: #ffffff; }
spinbutton { background-color: rgba(255,255,255,0.06); color: #ffffff; border: 1px solid rgba(255,255,255,0.07); border-radius: 4px; box-shadow: none; }
spinbutton entry { background: transparent; border: none; box-shadow: none; color: #ffffff; }
spinbutton button { background: transparent; border: none; box-shadow: none; color: #ffffff; }
tooltip, tooltip.background { background-color: #2C2C2C; border: 1px solid rgba(0,0,0,0.4); border-radius: 4px; }
tooltip label { color: #ffffff; font-size: 12px; }
.set-group { background-color: rgba(255,255,255,0.05); border-radius: 4px; border: 1px solid rgba(0,0,0,0.2); padding: 12px 16px; }
.set-head { font-size: 13px; }
.set-desc { font-size: 12px; color: rgba(255,255,255,0.6); }
"""


def apply_css(extra=""):
    prov = Gtk.CssProvider()
    prov.load_from_data((BASE_CSS + extra).encode())
    Gtk.StyleContext.add_provider_for_screen(Gdk.Screen.get_default(), prov,
                                             Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION + 10)
    Gtk.Settings.get_default().set_property("gtk-application-prefer-dark-theme", True)


def draw_glyph_extra(cr, name, L, pi):
    if name == "save":
        _rr(cr, 2, 2, 12, 12, 1.5)
        cr.stroke()
        _rr(cr, 4.5, 2, 6, 4, 0.5)
        cr.stroke()
        _rr(cr, 4.5, 9, 7, 5, 0.5)
        cr.stroke()
    elif name == "undo":
        cr.move_to(3, 7)
        cr.curve_to(6, 3.5, 13, 4.5, 13, 10)
        cr.stroke()
        L((3, 3), (3, 7), (7, 7))
    elif name == "redo":
        cr.move_to(13, 7)
        cr.curve_to(10, 3.5, 3, 4.5, 3, 10)
        cr.stroke()
        L((13, 3), (13, 7), (9, 7))
    elif name == "replace":
        L((2, 5), (10, 5))
        L((7.5, 2.5), (10, 5), (7.5, 7.5))
        L((14, 11), (6, 11))
        L((8.5, 8.5), (6, 11), (8.5, 13.5))
    elif name == "zoomin":
        cr.arc(6.6, 6.6, 4.6, 0, 2 * pi)
        cr.stroke()
        L((10, 10), (14, 14))
        L((4.6, 6.6), (8.6, 6.6))
        L((6.6, 4.6), (6.6, 8.6))
    elif name == "zoomout":
        cr.arc(6.6, 6.6, 4.6, 0, 2 * pi)
        cr.stroke()
        L((10, 10), (14, 14))
        L((4.6, 6.6), (8.6, 6.6))
    elif name == "fit":
        L((2, 5.5), (2, 2), (5.5, 2))
        L((10.5, 2), (14, 2), (14, 5.5))
        L((14, 10.5), (14, 14), (10.5, 14))
        L((5.5, 14), (2, 14), (2, 10.5))
    elif name == "wrap":
        L((2, 3), (14, 3))
        cr.move_to(2, 8)
        cr.line_to(11.5, 8)
        cr.curve_to(15, 8, 15, 13, 11.5, 13)
        cr.line_to(8, 13)
        cr.stroke()
        L((9.5, 11.3), (8, 13), (9.5, 14.7))
        L((2, 13), (5, 13))
    elif name == "play":
        cr.move_to(4.5, 2.5)
        cr.line_to(13, 8)
        cr.line_to(4.5, 13.5)
        cr.close_path()
        cr.fill()
    elif name == "pause":
        _rr(cr, 3.5, 2.5, 3, 11, 0.8)
        cr.fill()
        _rr(cr, 9.5, 2.5, 3, 11, 0.8)
        cr.fill()
    elif name in ("next", "prev"):
        if name == "prev":
            cr.translate(16, 0)
            cr.scale(-1, 1)
        cr.move_to(3, 3)
        cr.line_to(10.5, 8)
        cr.line_to(3, 13)
        cr.close_path()
        cr.fill()
        _rr(cr, 11, 3, 2, 10, 0.6)
        cr.fill()
    elif name == "shuffle":
        L((2, 4), (5, 4), (11, 12), (14, 12))
        L((2, 12), (5, 12), (11, 4), (14, 4))
        L((12, 2), (14, 4), (12, 6))
        L((12, 10), (14, 12), (12, 14))
    elif name in ("repeat", "repeat1"):
        cr.move_to(3, 9)
        cr.line_to(3, 6)
        cr.arc(5, 6, 2, pi, 1.5 * pi)
        cr.line_to(13, 4)
        cr.stroke()
        L((11, 2), (13, 4), (11, 6))
        cr.move_to(13, 7)
        cr.line_to(13, 10)
        cr.arc(11, 10, 2, 0, 0.5 * pi)
        cr.line_to(3, 12)
        cr.stroke()
        L((5, 10), (3, 12), (5, 14))
        if name == "repeat1":
            cr.set_font_size(5)
            cr.move_to(6.8, 9.8)
            cr.show_text("1")
    elif name in ("volume", "mute"):
        cr.move_to(1.5, 6)
        cr.line_to(4.5, 6)
        cr.line_to(8, 2.5)
        cr.line_to(8, 13.5)
        cr.line_to(4.5, 10)
        cr.line_to(1.5, 10)
        cr.close_path()
        cr.stroke()
        if name == "mute":
            L((10.5, 6), (14.5, 10))
            L((14.5, 6), (10.5, 10))
        else:
            cr.arc(8, 8, 3.5, -pi / 3.5, pi / 3.5)
            cr.stroke()
            cr.arc(8, 8, 6.2, -pi / 3.5, pi / 3.5)
            cr.stroke()
    elif name == "fullscreen":
        L((2, 6), (2, 2), (6, 2))
        L((10, 2), (14, 2), (14, 6))
        L((14, 10), (14, 14), (10, 14))
        L((6, 14), (2, 14), (2, 10))
        L((2, 2), (6, 6))
        L((14, 14), (10, 10))
    elif name == "unfullscreen":
        L((6, 2), (6, 6), (2, 6))
        L((10, 2), (10, 6), (14, 6))
        L((10, 14), (10, 10), (14, 10))
        L((6, 14), (6, 10), (2, 10))
    elif name == "rotate":
        cr.arc(8, 9, 5, pi * 1.15, pi * 2.85)
        cr.stroke()
        L((2.5, 2.5), (3.4, 6.4), (7.2, 5.4))
    elif name == "heart":
        cr.move_to(8, 13.5)
        cr.curve_to(1, 8, 1.5, 2.5, 5, 2.5)
        cr.curve_to(6.5, 2.5, 7.5, 3.5, 8, 4.5)
        cr.curve_to(8.5, 3.5, 9.5, 2.5, 11, 2.5)
        cr.curve_to(14.5, 2.5, 15, 8, 8, 13.5)
        cr.stroke()
    elif name == "pen":
        L((2.5, 13.5), (3.2, 10.5), (11, 2.7), (13.3, 5), (5.5, 12.8), (2.5, 13.5))
        L((9.5, 4.2), (11.8, 6.5))
    elif name == "highlighter":
        L((3, 13.5), (13, 13.5))
        cr.move_to(5, 11)
        cr.line_to(11, 3)
        cr.line_to(13.5, 5)
        cr.line_to(7.5, 12.5)
        cr.line_to(5, 12.5)
        cr.close_path()
        cr.stroke()
    elif name == "eraser":
        cr.move_to(2.5, 10)
        cr.line_to(9, 3.5)
        cr.line_to(13.5, 8)
        cr.line_to(8, 13.5)
        cr.line_to(5.5, 13.5)
        cr.close_path()
        cr.stroke()
        L((6, 6.5), (10.5, 11))
        L((8, 13.5), (14, 13.5))
    elif name == "crop":
        L((4.5, 1.5), (4.5, 11.5), (14.5, 11.5))
        L((1.5, 4.5), (11.5, 4.5), (11.5, 14.5))
    elif name == "camera":
        _rr(cr, 1.5, 4, 13, 9.5, 1.6)
        cr.stroke()
        L((5, 4), (6, 2.5), (10, 2.5), (11, 4))
        cr.arc(8, 8.8, 2.6, 0, 2 * pi)
        cr.stroke()
    elif name == "timer":
        cr.arc(8, 9, 5.5, 0, 2 * pi)
        cr.stroke()
        L((8, 9), (8, 5.8))
        L((6.3, 1.8), (9.7, 1.8))
    elif name == "settings":
        n = 8
        cr.new_path()
        for i in range(n * 2):
            a = i * pi / n
            r = 6.6 if i % 2 == 0 else 5.0
            a1, a2 = a - pi / (n * 2.4), a + pi / (n * 2.4)
            cr.line_to(8 + r * math.cos(a1), 8 + r * math.sin(a1))
            cr.line_to(8 + r * math.cos(a2), 8 + r * math.sin(a2))
        cr.close_path()
        cr.stroke()
        cr.arc(8, 8, 2.2, 0, 2 * pi)
        cr.stroke()
    elif name == "history":
        cr.arc(8, 8, 6, pi * 1.05, pi * 2.85)
        cr.stroke()
        L((1.2, 6.2), (2.3, 8.6), (4.6, 7.3))
        L((8, 4.6), (8, 8.2), (10.5, 9.7))
    elif name == "image":
        _rr(cr, 1.5, 2.5, 13, 11, 1.5)
        cr.stroke()
        L((1.5, 11), (5.5, 7), (9, 10.5), (11, 8.5), (14.5, 12))
        cr.arc(10.5, 5.5, 1.2, 0, 2 * pi)
        cr.stroke()
    elif name == "music":
        cr.arc(4.5, 12, 2, 0, 2 * pi)
        cr.stroke()
        cr.arc(12, 10.5, 2, 0, 2 * pi)
        cr.stroke()
        L((6.5, 12), (6.5, 3.5), (14, 2), (14, 10.5))
    elif name == "video":
        _rr(cr, 1.5, 3.5, 9.5, 9, 1.5)
        cr.stroke()
        L((11, 6.5), (14.5, 4.5), (14.5, 11.5), (11, 9.5))
    elif name == "queue":
        for y in (3, 7):
            L((2, y), (14, y))
        L((2, 11), (8, 11))
        cr.move_to(10.5, 9)
        cr.line_to(14, 11.5)
        cr.line_to(10.5, 14)
        cr.close_path()
        cr.fill()
    elif name == "edit":
        L((2.5, 13.5), (3.2, 10.5), (11, 2.7), (13.3, 5), (5.5, 12.8), (2.5, 13.5))
    elif name == "slideshow":
        _rr(cr, 1.5, 2.5, 13, 9, 1.5)
        cr.stroke()
        cr.move_to(6.5, 5)
        cr.line_to(10, 7)
        cr.line_to(6.5, 9)
        cr.close_path()
        cr.fill()
        L((5, 14), (11, 14))
    elif name == "print":
        _rr(cr, 1.5, 6, 13, 6, 1.2)
        cr.stroke()
        L((4.5, 6), (4.5, 1.5), (11.5, 1.5), (11.5, 6))
        _rr(cr, 4.5, 9.5, 7, 5, 0.5)
        cr.stroke()
    elif name == "wallpaper":
        _rr(cr, 1.5, 2.5, 13, 9, 1.2)
        cr.stroke()
        L((1.5, 9.5), (5, 6), (8, 9), (10, 7), (14.5, 10.5))
        L((5.5, 14), (10.5, 14))
        L((8, 11.5), (8, 14))
    elif name == "list":
        for y in (3.5, 8, 12.5):
            cr.arc(2.5, y, 0.9, 0, 2 * pi)
            cr.fill()
            L((5.5, y), (14, y))
    elif name == "add":
        L((8, 2.5), (8, 13.5))
        L((2.5, 8), (13.5, 8))
    elif name == "split":
        _rr(cr, 1.5, 2.5, 13, 11, 1.5)
        cr.stroke()
        L((8, 2.5), (8, 13.5))
    elif name == "keyboard":
        _rr(cr, 1, 3.5, 14, 9, 1.5)
        cr.stroke()
        for x in (4, 6.7, 9.3, 12):
            cr.rectangle(x - 0.5, 6, 1, 1)
        cr.fill()
        L((4.5, 10), (11.5, 10))


class Icon(Gtk.DrawingArea):
    """Monochrome glyph icon."""

    def __init__(self, name, size=16, color=None):
        super().__init__()
        self.name = name
        self.size = size
        self.color = color
        self.set_size_request(size, size)
        self.set_valign(Gtk.Align.CENTER)
        self.connect("draw", self._draw)

    def set_icon(self, name):
        self.name = name
        self.queue_draw()

    def _draw(self, w, cr):
        col = self.color or (1, 1, 1, 1)
        p = self.get_parent()
        if not self.is_sensitive() or (p and not p.is_sensitive()):
            col = (1, 1, 1, 0.36)
        draw_glyph(cr, self.name, self.size, col)


class WinTitlebar(Gtk.HeaderBar):
    """Title bar with Windows 11 caption buttons. Pack your own widgets with pack_start()."""

    def __init__(self, window):
        super().__init__()
        self.win = window
        self.get_style_context().add_class("fx-title")
        self.set_show_close_button(False)
        self.set_custom_title(Gtk.Box())
        wc = Gtk.Box(spacing=0)
        wc.set_valign(Gtk.Align.START)
        for name, cb, extra in (("min", lambda *_: window.iconify(), ""),
                                ("max", lambda *_: self.toggle_max(), ""),
                                ("close", lambda *_: window.close(), "close")):
            b = Gtk.Button()
            b.get_style_context().add_class("wc")
            if extra:
                b.get_style_context().add_class(extra)
            ic = Icon(name, 10)
            b.add(ic)
            b.connect("clicked", cb)
            if name == "max":
                self.max_icon = ic
            wc.pack_start(b, False, False, 0)
        self.pack_end(wc)
        window.connect("window-state-event", self._wstate)
        window.set_titlebar(self)

    def toggle_max(self):
        if self.win.is_maximized():
            self.win.unmaximize()
        else:
            self.win.maximize()

    def _wstate(self, w, ev):
        maxed = bool(ev.new_window_state & Gdk.WindowState.MAXIMIZED)
        self.max_icon.set_icon("restore" if maxed else "max")
        return False


def app_title(text, logo_draw):
    """Little logo + app name for the left of the title bar."""
    box = Gtk.Box(spacing=8)
    box.set_margin_start(14)
    da = Gtk.DrawingArea()
    da.set_size_request(16, 16)
    da.set_valign(Gtk.Align.CENTER)
    da.connect("draw", lambda w, cr: logo_draw(cr, 16))
    box.pack_start(da, False, False, 0)
    lb = Gtk.Label(label=text)
    lb.get_style_context().add_class("app-title")
    box.pack_start(lb, False, False, 0)
    return box, lb


class JsonSettings(dict):
    def __init__(self, app_dir, defaults):
        super().__init__(defaults)
        self.dir = os.path.join(HOME, ".config", app_dir)
        self.file = os.path.join(self.dir, "settings.json")
        try:
            with open(self.file) as f:
                self.update(json.load(f))
        except (OSError, ValueError):
            pass

    def save(self):
        try:
            os.makedirs(self.dir, exist_ok=True)
            tmp = self.file + ".tmp"
            with open(tmp, "w") as f:
                json.dump(self, f, indent=1)
            os.replace(tmp, self.file)
        except OSError:
            pass


def vsep():
    s = Gtk.Box()
    s.get_style_context().add_class("vsep")
    return s


def logo_pixbuf(draw, size):
    surf = cairo.ImageSurface(cairo.FORMAT_ARGB32, size, size)
    draw(cairo.Context(surf), size)
    return Gdk.pixbuf_get_from_surface(surf, 0, 0, size, size)
def label(text="", cls=None, xalign=0.0, ellipsize=False, wrap=False, markup=False):
    lb = Gtk.Label()
    if markup:
        lb.set_markup(text)
    else:
        lb.set_text(text)
    lb.set_xalign(xalign)
    if cls:
        for c in cls.split():
            lb.get_style_context().add_class(c)
    if ellipsize:
        lb.set_ellipsize(Pango.EllipsizeMode.END)
    if wrap:
        lb.set_line_wrap(True)
        lb.set_line_wrap_mode(Pango.WrapMode.WORD_CHAR)
    return lb


def add_cls(w, *cls):
    ctx = w.get_style_context()
    for c in cls:
        ctx.add_class(c)
    return w


def tb_button(icon, text, cb=None, chev=False, tip=None):
    b = Gtk.Button()
    add_cls(b, "tb")
    box = Gtk.Box(spacing=7)
    if icon:
        box.pack_start(Icon(icon), False, False, 0)
    if text:
        box.pack_start(Gtk.Label(label=text), False, False, 0)
    if chev:
        box.pack_start(Icon("chevdown", 10), False, False, 0)
    b.add(box)
    b.set_relief(Gtk.ReliefStyle.NONE)
    b.set_tooltip_text(tip or text or None)
    if cb:
        b.connect("clicked", lambda w: cb(w))
    return b


def icon_button(icon, cb, cls="nb", tip=None, size=16):
    b = Gtk.Button()
    add_cls(b, cls)
    b.add(Icon(icon, size))
    b.set_relief(Gtk.ReliefStyle.NONE)
    if tip:
        b.set_tooltip_text(tip)
    b.connect("clicked", lambda w: cb(w))
    return b


def build_menu(spec):
    """spec: list of None (separator) or dicts: label, cb, icon, place, accel, sensitive, checked, sub."""
    menu = Gtk.Menu()
    add_cls(menu, "context-menu")
    for it in spec:
        if it is None:
            menu.append(Gtk.SeparatorMenuItem())
            continue
        mi = Gtk.MenuItem()
        box = Gtk.Box(spacing=12)
        ic = None
        if it.get("checked"):
            ic = Icon("check", 16)
        elif it.get("pixbuf") is not None:
            ic = Gtk.Image.new_from_pixbuf(it["pixbuf"])
        elif it.get("icon"):
            ic = Icon(it["icon"], 16)
        if ic is None:
            ic = Gtk.Box()
            ic.set_size_request(16, 16)
        box.pack_start(ic, False, False, 0)
        lb = Gtk.Label(label=it["label"])
        lb.set_xalign(0)
        box.pack_start(lb, True, True, 0)
        if it.get("accel"):
            al = Gtk.Label(label=it["accel"])
            al.get_style_context().add_class("dim-label")
            al.set_opacity(0.55)
            al.set_margin_start(24)
            box.pack_end(al, False, False, 0)
        mi.add(box)
        mi.set_sensitive(it.get("sensitive", True))
        if it.get("sub") is not None:
            mi.set_submenu(build_menu(it["sub"]))
        elif it.get("cb"):
            cb = it["cb"]
            mi.connect("activate", lambda w, cb=cb: GLib.idle_add(cb))
        menu.append(mi)
    menu.show_all()
    return menu


def popup_menu(menu, widget, event=None):
    menu.attach_to_widget(widget, None)
    if event is not None:
        menu.popup_at_pointer(event)
    else:
        menu.popup_at_widget(widget, Gdk.Gravity.SOUTH_WEST, Gdk.Gravity.NORTH_WEST, None)


# ----------------------------------------------------------------------------
# Windows 11 style dialogs
# ----------------------------------------------------------------------------
class WinDialog(Gtk.Window):
    def __init__(self, parent, title, body=None, primary="OK", secondary="Cancel", width=440, extra=None,
                 markup=False):
        super().__init__(transient_for=parent, modal=True)
        add_cls(self, "fx-dialog")
        self.set_decorated(False)
        self.set_resizable(False)
        self.set_default_size(width, -1)
        self.set_position(Gtk.WindowPosition.CENTER_ON_PARENT)
        self.set_type_hint(Gdk.WindowTypeHint.DIALOG)
        self.set_title(title)
        self.cb = None
        outer = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        self.body = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        add_cls(self.body, "dlg-body")
        self.body.pack_start(label(title, "dlg-title"), False, False, 0)
        if body:
            lb = label(body, wrap=True, markup=markup)
            lb.set_max_width_chars(60)
            self.body.pack_start(lb, False, False, 0)
        if extra:
            self.body.pack_start(extra, False, False, 0)
        outer.pack_start(self.body, True, True, 0)
        self.foot = Gtk.Box(spacing=8, homogeneous=True)
        add_cls(self.foot, "dlg-foot")
        self.primary_btn = None
        if primary:
            pb = Gtk.Button(label=primary)
            add_cls(pb, "primary")
            pb.connect("clicked", lambda *_: self.done(True))
            self.foot.pack_start(pb, True, True, 0)
            pb.set_can_default(True)
            self.set_default(pb)
            self.primary_btn = pb
        if secondary:
            sb = Gtk.Button(label=secondary)
            add_cls(sb, "secondary")
            sb.connect("clicked", lambda *_: self.done(False))
            self.foot.pack_start(sb, True, True, 0)
        if primary or secondary:
            outer.pack_start(self.foot, False, False, 0)
        self.add(outer)
        self.connect("key-press-event", self._key)

    def _key(self, w, ev):
        if ev.keyval == Gdk.KEY_Escape:
            self.done(False)
            return True
        return False

    def done(self, ok):
        cb = self.cb
        self.cb = None
        self.hide()
        if cb:
            cb(ok)
        self.destroy()

    def ask(self, cb=None):
        self.cb = cb
        self.show_all()
        if self.primary_btn:
            self.primary_btn.grab_focus()


def info_dialog(parent, title, body):
    WinDialog(parent, title, body, primary="OK", secondary=None).ask()


def confirm(parent, title, body, yes, cb, no="Cancel"):
    WinDialog(parent, title, body, primary=yes, secondary=no).ask(cb)


def error_list_dialog(parent, title, errors):
    lines = []
    for p, msg in errors[:12]:
        lines.append(f"{os.path.basename(p) or p}: {msg}" if p else msg)
    if len(errors) > 12:
        lines.append(f"...and {len(errors) - 12} more")
    info_dialog(parent, title, "\n".join(lines))




# ----------------------------------------------------------------------------
# Media Player
# ----------------------------------------------------------------------------
import random  # noqa: E402
import hashlib  # noqa: E402
import urllib.parse  # noqa: E402

gi.require_version("Gst", "1.0")
gi.require_version("GstPbutils", "1.0")
from gi.repository import Gst, GstPbutils  # noqa: E402

APP_ID = "io.github.pimediaplayer"
CACHE_DIR = os.path.join(GLib.get_user_cache_dir(), "pi-mediaplayer")
DEFAULTS = {"width": 1100, "height": 700, "maximized": False, "volume": 0.8, "shuffle": False, "repeat": "off",
            "music_dirs": [os.path.join(HOME, "Music")], "video_dirs": [os.path.join(HOME, "Videos")]}
AUDIO_EXT = {".mp3", ".flac", ".ogg", ".oga", ".opus", ".wav", ".m4a", ".aac", ".wma", ".mka"}
VIDEO_EXT = {".mp4", ".mkv", ".webm", ".mov", ".avi", ".m4v", ".ogv", ".mpg", ".mpeg", ".wmv", ".ts", ".3gp"}

CSS = """
window.fx.player { background-color: #202020; }
.navpane { background-color: #202020; padding: 6px; }
button.navitem { background: transparent; border: none; border-radius: 4px; min-height: 38px; padding: 0 12px; box-shadow: none; }
button.navitem:hover { background-color: rgba(255,255,255,0.06); }
button.navitem.selected { background-color: rgba(255,255,255,0.08); box-shadow: inset 3px 0 #4CC2FF; }
button.navitem label { font-size: 13px; }
.content { background-color: #272727; border-top-left-radius: 8px; border-top: 1px solid rgba(0,0,0,0.3); border-left: 1px solid rgba(0,0,0,0.3); }
.page-title { font-size: 28px; font-weight: 600; }
treeview.view.songs { background-color: #272727; color: #ffffff; font-size: 13px; }
treeview.view.songs:selected { background-color: rgba(255,255,255,0.09); color: #ffffff; }
treeview.view.songs:hover { background-color: rgba(255,255,255,0.05); }
treeview.view.songs header button { background: #272727; border: none; box-shadow: none; padding: 4px 10px; color: rgba(255,255,255,0.7); }
.playerbar { background-color: #1C1C1C; border-top: 1px solid rgba(255,255,255,0.06); padding: 8px 14px; }
.np-title { font-size: 14px; font-weight: 600; }
.np-artist { font-size: 12px; color: rgba(255,255,255,0.65); }
.time { font-size: 11px; color: rgba(255,255,255,0.65); }
button.ctl { background: transparent; border: none; border-radius: 50%; min-width: 36px; min-height: 36px; padding: 0; box-shadow: none; }
button.ctl:hover { background-color: rgba(255,255,255,0.08); }
button.ctl.on { color: #4CC2FF; }
button.big { background-color: #4CC2FF; border-radius: 50%; min-width: 42px; min-height: 42px; }
button.big:hover { background-color: #48B1E8; }
button.vtile { background: transparent; border: none; border-radius: 6px; padding: 6px; box-shadow: none; }
button.vtile:hover { background-color: rgba(255,255,255,0.06); }
.vt-name { font-size: 12px; }
.vt-sub { font-size: 11px; color: rgba(255,255,255,0.6); }
.nowplaying { background-color: #111111; }
.np-big-title { font-size: 26px; font-weight: 600; }
.np-big-sub { font-size: 15px; color: rgba(255,255,255,0.7); }
.empty { font-size: 13px; color: rgba(255,255,255,0.65); }
"""


def draw_logo(cr, s):
    cr.save()
    cr.scale(s / 16.0, s / 16.0)
    g = cairo.LinearGradient(0, 0, 16, 16)
    g.add_color_stop_rgb(0, 0.95, 0.45, 0.25)
    g.add_color_stop_rgb(1, 0.85, 0.2, 0.5)
    _rr(cr, 1, 1, 14, 14, 3.5)
    cr.set_source(g)
    cr.fill()
    cr.set_source_rgba(1, 1, 1, 0.95)
    cr.move_to(6, 4.5)
    cr.line_to(11.5, 8)
    cr.line_to(6, 11.5)
    cr.close_path()
    cr.fill()
    cr.restore()


def fmt_time(ns):
    if ns is None or ns < 0:
        return "0:00"
    s = int(ns / Gst.SECOND)
    h, m, s = s // 3600, s // 60 % 60, s % 60
    return f"{h}:{m:02d}:{s:02d}" if h else f"{m}:{s:02d}"


def media_kind(p):
    e = os.path.splitext(p)[1].lower()
    return "audio" if e in AUDIO_EXT else ("video" if e in VIDEO_EXT else None)


def to_uri(p):
    return Gio.File.new_for_path(p).get_uri()


# ---------------------------------------------------------------- library scanning
class Library:
    def __init__(self, st):
        self.st = st
        self.lock = threading.Lock()
        self.cache = {}
        self.cache_file = os.path.join(CACHE_DIR, "library.json")
        try:
            with open(self.cache_file) as f:
                self.cache = json.load(f)
        except (OSError, ValueError):
            self.cache = {}
        self.disc = None

    def save(self):
        try:
            os.makedirs(CACHE_DIR, exist_ok=True)
            with open(self.cache_file, "w") as f:
                json.dump(self.cache, f)
        except OSError:
            pass

    def files(self, dirs, kind):
        out = []
        for d in dirs:
            for root, ds, fs in os.walk(d):
                ds[:] = [x for x in ds if not x.startswith(".")]
                for f in fs:
                    p = os.path.join(root, f)
                    if not f.startswith(".") and media_kind(p) == kind:
                        out.append(p)
        return out

    def info(self, p):
        """Title, artist, album, track, duration (ns). Cached by path + mtime."""
        try:
            mt = os.path.getmtime(p)
        except OSError:
            return None
        c = self.cache.get(p)
        if c and c.get("mtime") == mt:
            return c
        base = os.path.splitext(os.path.basename(p))[0]
        d = {"mtime": mt, "title": re.sub(r"^\d+[\s.\-_]+", "", base) or base, "artist": "", "album": "",
             "track": 0, "duration": 0, "art": None}
        try:
            if self.disc is None:
                self.disc = GstPbutils.Discoverer.new(5 * Gst.SECOND)
            inf = self.disc.discover_uri(to_uri(p))
            d["duration"] = inf.get_duration()
            for s in inf.get_stream_list():
                tags = s.get_tags()
                if not tags:
                    continue
                for key_, gst_key in (("title", "title"), ("artist", "artist"), ("album", "album")):
                    ok, v = tags.get_string(gst_key)
                    if ok and v:
                        d[key_] = v
                ok, n = tags.get_uint("track-number")
                if ok:
                    d["track"] = n
                ok, sample = tags.get_sample("image")
                if ok and sample and not d["art"]:
                    d["art"] = self._save_art(p, sample)
        except Exception:
            pass
        if not d["art"]:
            for n in ("cover.jpg", "cover.png", "folder.jpg", "folder.png", "front.jpg", "album.jpg"):
                fp = os.path.join(os.path.dirname(p), n)
                if os.path.exists(fp):
                    d["art"] = fp
                    break
        with self.lock:
            self.cache[p] = d
        return d

    def _save_art(self, p, sample):
        try:
            buf = sample.get_buffer()
            ok, mi = buf.map(Gst.MapFlags.READ)
            if not ok:
                return None
            data = bytes(mi.data)
            buf.unmap(mi)
            os.makedirs(os.path.join(CACHE_DIR, "art"), exist_ok=True)
            out = os.path.join(CACHE_DIR, "art", hashlib.md5(p.encode()).hexdigest() + ".img")
            with open(out, "wb") as f:
                f.write(data)
            return out
        except Exception:
            return None


def video_thumb(p, w=220, h=124):
    """Thumbnail for a video: freedesktop cache, then ffmpegthumbnailer, else None."""
    uri = to_uri(p)
    md5 = hashlib.md5(uri.encode()).hexdigest() + ".png"
    for d in ("x-large", "large", "normal"):
        tp = os.path.join(GLib.get_user_cache_dir(), "thumbnails", d, md5)
        if os.path.exists(tp):
            try:
                return GdkPixbuf.Pixbuf.new_from_file_at_scale(tp, w, h, True)
            except GLib.Error:
                pass
    if shutil.which("ffmpegthumbnailer"):
        tp = os.path.join(GLib.get_user_cache_dir(), "thumbnails", "large", md5)
        os.makedirs(os.path.dirname(tp), exist_ok=True)
        try:
            subprocess.run(["ffmpegthumbnailer", "-i", p, "-o", tp, "-s", "256", "-t", "15%"],
                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=20)
            if os.path.exists(tp):
                return GdkPixbuf.Pixbuf.new_from_file_at_scale(tp, w, h, True)
        except (OSError, subprocess.SubprocessError, GLib.Error):
            pass
    return grab_frame(p, w, h)


def grab_frame(p, w, h):
    """Use GStreamer to grab a frame 10% into the video."""
    try:
        pipe = Gst.ElementFactory.make("playbin", None)
        pipe.set_property("uri", to_uri(p))
        pipe.set_property("audio-sink", Gst.ElementFactory.make("fakesink", None))
        vbin = Gst.parse_bin_from_description(
            "videoconvert ! videoscale ! video/x-raw,format=RGB,pixel-aspect-ratio=1/1 ! appsink name=s sync=false",
            True)
        pipe.set_property("video-sink", vbin)
        sink = vbin.get_by_name("s")
        pipe.set_state(Gst.State.PAUSED)
        pipe.get_state(5 * Gst.SECOND)
        ok, dur = pipe.query_duration(Gst.Format.TIME)
        if ok and dur > 0:
            pipe.seek_simple(Gst.Format.TIME, Gst.SeekFlags.FLUSH | Gst.SeekFlags.KEY_UNIT, int(dur * 0.1))
            pipe.get_state(5 * Gst.SECOND)
        sample = sink.emit("pull-preroll")
        if not sample:
            pipe.set_state(Gst.State.NULL)
            return None
        caps = sample.get_caps().get_structure(0)
        vw, vh = caps.get_value("width"), caps.get_value("height")
        buf = sample.get_buffer()
        ok, mi = buf.map(Gst.MapFlags.READ)
        data = bytes(mi.data)
        buf.unmap(mi)
        pipe.set_state(Gst.State.NULL)
        stride = (vw * 3 + 3) // 4 * 4
        pb = GdkPixbuf.Pixbuf.new_from_bytes(GLib.Bytes.new(data), GdkPixbuf.Colorspace.RGB, False, 8, vw, vh, stride)
        s = min(w / vw, h / vh)
        return pb.scale_simple(max(1, int(vw * s)), max(1, int(vh * s)), GdkPixbuf.InterpType.BILINEAR)
    except Exception:
        return None


def art_pixbuf(art, size):
    if art:
        try:
            pb = GdkPixbuf.Pixbuf.new_from_file_at_scale(art, size, size, True)
            return pb
        except GLib.Error:
            pass
    surf = cairo.ImageSurface(cairo.FORMAT_ARGB32, size, size)
    cr = cairo.Context(surf)
    g = cairo.LinearGradient(0, 0, size, size)
    g.add_color_stop_rgb(0, 0.25, 0.25, 0.3)
    g.add_color_stop_rgb(1, 0.15, 0.15, 0.18)
    _rr(cr, 0, 0, size, size, size * 0.08)
    cr.set_source(g)
    cr.fill()
    cr.translate(size * 0.25, size * 0.25)
    draw_glyph(cr, "music", size * 0.5, (1, 1, 1, 0.6))
    return Gdk.pixbuf_get_from_surface(surf, 0, 0, size, size)


# ---------------------------------------------------------------- player engine
class Player(GObject.Object):
    __gsignals__ = {"changed": (GObject.SignalFlags.RUN_FIRST, None, ()),
                    "eos": (GObject.SignalFlags.RUN_FIRST, None, ()),
                    "error": (GObject.SignalFlags.RUN_FIRST, None, (str,))}

    def __init__(self):
        super().__init__()
        self.pipe = Gst.ElementFactory.make("playbin", "player")
        self.video_widget = None
        sink = Gst.ElementFactory.make("gtksink", "vsink")
        if sink is not None:
            self.pipe.set_property("video-sink", sink)
            self.video_widget = sink.get_property("widget")
        if os.environ.get("PI_MEDIAPLAYER_FAKEAUDIO"):
            self.pipe.set_property("audio-sink", Gst.ElementFactory.make("fakesink", None))
        bus = self.pipe.get_bus()
        bus.add_signal_watch()
        bus.connect("message::eos", lambda *a: self.emit("eos"))
        bus.connect("message::error", self._error)
        bus.connect("message::state-changed", self._state)
        self.playing = False

    def _error(self, bus, msg):
        err, dbg = msg.parse_error()
        self.stop()
        self.emit("error", err.message)

    def _state(self, bus, msg):
        if msg.src is self.pipe:
            old, new, pend = msg.parse_state_changed()
            self.playing = new == Gst.State.PLAYING
            self.emit("changed")

    def load(self, path):
        self.pipe.set_state(Gst.State.NULL)
        self.pipe.set_property("uri", to_uri(path))
        self.pipe.set_state(Gst.State.PLAYING)

    def play(self):
        self.pipe.set_state(Gst.State.PLAYING)

    def pause(self):
        self.pipe.set_state(Gst.State.PAUSED)

    def stop(self):
        self.pipe.set_state(Gst.State.NULL)
        self.playing = False

    def position(self):
        ok, p = self.pipe.query_position(Gst.Format.TIME)
        return p if ok else 0

    def duration(self):
        ok, d = self.pipe.query_duration(Gst.Format.TIME)
        return d if ok else 0

    def seek(self, ns):
        self.pipe.seek_simple(Gst.Format.TIME, Gst.SeekFlags.FLUSH | Gst.SeekFlags.KEY_UNIT, max(0, int(ns)))

    def set_volume(self, v):
        self.pipe.set_property("volume", max(0.0, min(1.0, v)))

    def set_mute(self, m):
        self.pipe.set_property("mute", m)


# ---------------------------------------------------------------- window
class PlayerWindow(Gtk.ApplicationWindow):
    def __init__(self, app, files=None):
        super().__init__(application=app)
        self.app = app
        self.st = app.settings
        self.lib = app.library
        self.queue = []
        self.qpos = -1
        self.order = []
        self.cur = None
        self.seeking = False
        self._menu = None
        self.gen = 0
        self.set_title("Media Player")
        self.set_icon_name("pi-mediaplayer")
        ctx = self.get_style_context()
        ctx.add_class("fx")
        ctx.add_class("player")
        self.set_default_size(self.st["width"], self.st["height"])
        if self.st.get("maximized"):
            self.maximize()
        self.connect("key-press-event", self._key)
        self.connect("configure-event", self._configure)
        self.connect("delete-event", self._on_close)
        self.connect("window-state-event", self._wstate)
        tb = WinTitlebar(self)
        t, _ = app_title("Media Player", draw_logo)
        tb.pack_start(t)
        tb.show_all()
        self.tb = tb

        self.player = Player()
        self.player.set_volume(self.st["volume"])
        self.player.connect("eos", lambda p: self.next_track(auto=True))
        self.player.connect("changed", lambda p: self._sync_buttons())
        self.player.connect("error", lambda p, m: self._play_error(m))

        root = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        body = Gtk.Box()
        nav = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
        nav.get_style_context().add_class("navpane")
        nav.set_size_request(220, -1)
        self.nav_items = {}
        for key_, icon, text in (("home", "home", "Home"), ("music", "music", "Music library"),
                                 ("video", "video", "Video library"), ("queue", "queue", "Play queue")):
            b = Gtk.Button()
            b.get_style_context().add_class("navitem")
            row = Gtk.Box(spacing=14)
            row.pack_start(Icon(icon, 16), False, False, 0)
            row.pack_start(label(text), False, False, 0)
            b.add(row)
            b.connect("clicked", lambda w, k=key_: self.show_page(k))
            nav.pack_start(b, False, False, 0)
            self.nav_items[key_] = b
        ob = Gtk.Button()
        ob.get_style_context().add_class("navitem")
        row = Gtk.Box(spacing=14)
        row.pack_start(Icon("open", 16), False, False, 0)
        row.pack_start(label("Open file(s)"), False, False, 0)
        ob.add(row)
        ob.connect("clicked", lambda w: self.open_dialog())
        nav.pack_end(ob, False, False, 0)
        self.nav = nav
        body.pack_start(nav, False, False, 0)
        self.stack = Gtk.Stack()
        self.stack.set_transition_type(Gtk.StackTransitionType.CROSSFADE)
        self.stack.get_style_context().add_class("content")
        body.pack_start(self.stack, True, True, 0)
        root.pack_start(body, True, True, 0)
        root.pack_start(self._build_bar(), False, False, 0)
        self.add(root)

        # pages
        self.pages = {}
        for k in ("home", "music", "video", "queue"):
            sw = Gtk.ScrolledWindow()
            sw.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
            self.stack.add_named(sw, k)
            self.pages[k] = sw
        self.np = self._build_nowplaying()
        self.stack.add_named(self.np, "now")
        root.show_all()
        self.drag_dest_set(Gtk.DestDefaults.ALL, [Gtk.TargetEntry.new("text/uri-list", 0, 0)], Gdk.DragAction.COPY)
        self.connect("drag-data-received", self._drop)
        GLib.timeout_add(500, self._tick)
        self.show_page("home")
        if files:
            self.play_files(files)

    # ---------------- player bar
    def _build_bar(self):
        bar = Gtk.Box(spacing=12)
        bar.get_style_context().add_class("playerbar")
        left = Gtk.Box(spacing=10)
        left.set_size_request(280, -1)
        self.bar_art = Gtk.Image.new_from_pixbuf(art_pixbuf(None, 48))
        artb = Gtk.Button()
        artb.get_style_context().add_class("vtile")
        artb.add(self.bar_art)
        artb.set_tooltip_text("Now playing")
        artb.connect("clicked", lambda w: self.cur and self.show_page("now"))
        left.pack_start(artb, False, False, 0)
        col = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
        col.set_valign(Gtk.Align.CENTER)
        self.bar_title = label("Nothing playing", "np-title", ellipsize=True)
        self.bar_artist = label("", "np-artist", ellipsize=True)
        col.pack_start(self.bar_title, False, False, 0)
        col.pack_start(self.bar_artist, False, False, 0)
        left.pack_start(col, True, True, 0)
        bar.pack_start(left, False, False, 0)

        mid = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
        ctl = Gtk.Box(spacing=8)
        ctl.set_halign(Gtk.Align.CENTER)

        def cb(icon, fn, tip, cls="ctl"):
            b = Gtk.Button()
            for c in cls.split():
                b.get_style_context().add_class(c)
            b.add(Icon(icon, 16, color=(0, 0, 0, 1) if "big" in cls else None))
            b.set_tooltip_text(tip)
            b.connect("clicked", lambda w: fn())
            ctl.pack_start(b, False, False, 0)
            return b
        self.b_shuffle = cb("shuffle", self.toggle_shuffle, "Shuffle")
        self.b_prev = cb("prev", self.prev_track, "Previous (Ctrl+B)")
        self.b_play = cb("play", self.play_pause, "Play (Space)", "ctl big")
        self.b_next = cb("next", lambda: self.next_track(), "Next (Ctrl+F)")
        self.b_repeat = cb("repeat", self.cycle_repeat, "Repeat")
        mid.pack_start(ctl, False, False, 0)
        srow = Gtk.Box(spacing=8)
        self.t_pos = label("0:00", "time")
        self.t_dur = label("0:00", "time")
        self.seek = Gtk.Scale.new_with_range(Gtk.Orientation.HORIZONTAL, 0, 1, 0.001)
        self.seek.set_draw_value(False)
        self.seek.connect("button-press-event", lambda *a: setattr(self, "seeking", True) or False)
        self.seek.connect("button-release-event", self._seek_release)
        srow.pack_start(self.t_pos, False, False, 0)
        srow.pack_start(self.seek, True, True, 0)
        srow.pack_start(self.t_dur, False, False, 0)
        mid.pack_start(srow, False, False, 0)
        bar.pack_start(mid, True, True, 0)

        right = Gtk.Box(spacing=4)
        right.set_size_request(240, -1)
        right.set_halign(Gtk.Align.END)
        self.b_vol = Gtk.Button()
        self.b_vol.get_style_context().add_class("ctl")
        self.vol_icon = Icon("volume", 16)
        self.b_vol.add(self.vol_icon)
        self.b_vol.set_tooltip_text("Mute (M)")
        self.b_vol.connect("clicked", lambda w: self.toggle_mute())
        right.pack_start(self.b_vol, False, False, 0)
        self.vol = Gtk.Scale.new_with_range(Gtk.Orientation.HORIZONTAL, 0, 1, 0.01)
        self.vol.set_draw_value(False)
        self.vol.set_size_request(110, -1)
        self.vol.set_value(self.st["volume"])
        self.vol.connect("value-changed", self._vol_changed)
        right.pack_start(self.vol, False, False, 0)
        self.b_full = Gtk.Button()
        self.b_full.get_style_context().add_class("ctl")
        self.b_full.add(Icon("fullscreen", 16))
        self.b_full.set_tooltip_text("Full screen (F11)")
        self.b_full.connect("clicked", lambda w: self.toggle_fullscreen())
        right.pack_start(self.b_full, False, False, 0)
        more = Gtk.Button()
        more.get_style_context().add_class("ctl")
        more.add(Icon("more", 16))
        more.connect("clicked", self._more_menu)
        right.pack_start(more, False, False, 0)
        bar.pack_end(right, False, False, 0)
        self.bar = bar
        self._sync_buttons()
        return bar

    def _sync_buttons(self):
        self.b_play.get_child().set_icon("pause" if self.player.playing else "play")
        self.b_play.set_tooltip_text("Pause (Space)" if self.player.playing else "Play (Space)")
        for b, on in ((self.b_shuffle, self.st["shuffle"]), (self.b_repeat, self.st["repeat"] != "off")):
            ctx = b.get_style_context()
            (ctx.add_class if on else ctx.remove_class)("on")
            b.get_child().color = hexc(C_ACCENT) if on else None
            b.get_child().queue_draw()
        self.b_repeat.get_child().set_icon("repeat1" if self.st["repeat"] == "one" else "repeat")
        self.b_repeat.set_tooltip_text({"off": "Repeat: off", "all": "Repeat: all", "one": "Repeat: one"}[self.st["repeat"]])

    def _tick(self):
        if self.cur and not self.seeking:
            pos, dur = self.player.position(), self.player.duration()
            self.t_pos.set_text(fmt_time(pos))
            self.t_dur.set_text(fmt_time(dur))
            self.seek.set_value(pos / dur if dur else 0)
        return True

    def _seek_release(self, w, ev):
        self.seeking = False
        dur = self.player.duration()
        if dur:
            GLib.idle_add(lambda: self.player.seek(self.seek.get_value() * dur) or False)
        return False

    def _vol_changed(self, s):
        v = s.get_value()
        self.st["volume"] = v
        self.player.set_volume(v)
        self.player.set_mute(False)
        self.vol_icon.set_icon("mute" if v == 0 else "volume")

    def toggle_mute(self):
        m = not self.player.pipe.get_property("mute")
        self.player.set_mute(m)
        self.vol_icon.set_icon("mute" if m else "volume")

    # ---------------- pages
    def show_page(self, k):
        for kk, b in self.nav_items.items():
            ctx = b.get_style_context()
            (ctx.add_class if kk == k else ctx.remove_class)("selected")
        if k == "now":
            self.stack.set_visible_child_name("now")
            return
        builder = {"home": self._build_home, "music": self._build_music, "video": self._build_video,
                   "queue": self._build_queue}[k]
        sw = self.pages[k]
        child = sw.get_child()
        if child:
            child.destroy()
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        box.set_margin_start(28)
        box.set_margin_end(28)
        box.set_margin_top(20)
        box.set_margin_bottom(20)
        builder(box)
        sw.add(box)
        sw.show_all()
        self.stack.set_visible_child_name(k)

    def _head(self, box, title, buttons=()):
        row = Gtk.Box(spacing=8)
        row.pack_start(label(title, "page-title"), False, False, 0)
        for text, icon, fn in buttons:
            b = tb_button(icon, text, lambda w, fn=fn: fn())
            row.pack_end(b, False, False, 0)
        box.pack_start(row, False, False, 6)

    def _song_list(self, songs, on_activate):
        store = Gtk.ListStore(str, str, str, str, str, str)
        for p, d in songs:
            store.append([d.get("title") or os.path.basename(p), d.get("artist") or "Unknown artist",
                          d.get("album") or "Unknown album", fmt_time(d.get("duration") or 0), p,
                          "▶" if p == self.cur else ""])
        tv = Gtk.TreeView(model=store)
        tv.get_style_context().add_class("songs")
        tv.set_enable_search(False)
        for i, (title, cid, w, exp) in enumerate((("", 5, 26, False), ("Title", 0, 300, True), ("Artist", 1, 180, False),
                                                  ("Album", 2, 200, False), ("Length", 3, 70, False))):
            r = Gtk.CellRendererText()
            r.set_property("ellipsize", Pango.EllipsizeMode.END)
            r.set_padding(8, 9)
            if cid == 5:
                r.set_property("foreground", C_ACCENT)
            elif cid != 0:
                r.set_property("foreground-rgba", Gdk.RGBA(1, 1, 1, 0.7))
            c = Gtk.TreeViewColumn(title, r, text=cid)
            c.set_expand(exp)
            c.set_min_width(w)
            c.set_resizable(cid != 5)
            tv.append_column(c)
        tv.connect("row-activated", lambda t, tp, c: on_activate(tp.get_indices()[0]))

        def press(w, ev):
            if ev.button == 3:
                res = tv.get_path_at_pos(int(ev.x), int(ev.y))
                if res:
                    i = res[0].get_indices()[0]
                    p = store[res[0]][4]
                    m = build_menu([
                        {"label": "Play", "icon": "play", "cb": lambda: on_activate(i)},
                        {"label": "Play next", "icon": "next", "cb": lambda: self.add_to_queue([p], nxt=True)},
                        {"label": "Add to play queue", "icon": "queue", "cb": lambda: self.add_to_queue([p])},
                        None,
                        {"label": "Show in folder", "icon": "open", "cb": lambda: self.show_in_folder(p)},
                    ])
                    self._menu = m
                    popup_menu(m, tv, ev)
                return True
            return False
        tv.connect("button-press-event", press)
        return tv

    def _build_home(self, box):
        self._head(box, "Home")
        box.pack_start(label("Recent media", "sect-title"), False, False, 4)
        recent = self.st.get("recent", [])
        recent = [p for p in recent if os.path.exists(p)][:12]
        if not recent:
            box.pack_start(label("Songs and videos you play will show up here. Open the Music or Video library to "
                                 "get started.", "empty", wrap=True), False, False, 0)
        fb = Gtk.FlowBox()
        fb.set_selection_mode(Gtk.SelectionMode.NONE)
        fb.set_max_children_per_line(8)
        fb.set_homogeneous(True)
        fb.set_valign(Gtk.Align.START)
        items = []
        for p in recent:
            b, img = self._tile(p)
            b.connect("clicked", lambda w, p=p: self.play_files([p]))
            fb.add(b)
            items.append((img, p))
        box.pack_start(fb, False, False, 0)
        self._fill_tiles(items)

    def _tile(self, p):
        d = self.lib.cache.get(p, {})
        b = Gtk.Button()
        b.get_style_context().add_class("vtile")
        col = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        img = Gtk.Image()
        img.set_size_request(200, 112)
        col.pack_start(img, False, False, 0)
        col.pack_start(label(d.get("title") or os.path.splitext(os.path.basename(p))[0], "vt-name", ellipsize=True),
                       False, False, 0)
        sub = d.get("artist") or ("Video" if media_kind(p) == "video" else "")
        col.pack_start(label(sub, "vt-sub", ellipsize=True), False, False, 0)
        b.add(col)
        b.set_size_request(212, -1)
        return b, img

    def _fill_tiles(self, items):
        self.gen += 1
        gen = self.gen

        def work():
            for img, p in items:
                if gen != self.gen:
                    return
                if media_kind(p) == "video":
                    pb = video_thumb(p, 200, 112)
                else:
                    d = self.lib.info(p) or {}
                    pb = art_pixbuf(d.get("art"), 112)
                if pb is not None:
                    GLib.idle_add(lambda img=img, pb=pb: img.set_from_pixbuf(pb))
        threading.Thread(target=work, daemon=True).start()

    def _build_music(self, box):
        files = sorted(self.lib.files(self.st["music_dirs"], "audio"), key=lambda p: p.casefold())
        self._head(box, "Music", [("Shuffle and play", "shuffle", lambda: self.play_files(files, shuffle=True)),
                                  ("Add folder", "add", lambda: self.add_folder("music_dirs"))])
        box.pack_start(label(f"{len(files)} songs   |   " + ", ".join(d.replace(HOME, "~") for d in self.st["music_dirs"]),
                             "sec"), False, False, 0)
        if not files:
            box.pack_start(label("No music found. Put songs in your Music folder or use Add folder.", "empty"),
                           False, False, 8)
            return
        status = label("Reading song details...", "ter")
        box.pack_start(status, False, False, 0)
        holder = Gtk.Box()
        box.pack_start(holder, True, True, 0)

        def work():
            songs = [(p, self.lib.info(p) or {}) for p in files]
            self.lib.save()
            songs.sort(key=lambda s: ((s[1].get("artist") or "~").casefold(), (s[1].get("album") or "").casefold(),
                                      s[1].get("track") or 0, (s[1].get("title") or "").casefold()))
            GLib.idle_add(done, songs)

        def done(songs):
            status.hide()
            order = [p for p, _ in songs]
            tv = self._song_list(songs, lambda i: self.play_files(order, start=i))
            holder.pack_start(tv, True, True, 0)
            holder.show_all()
        threading.Thread(target=work, daemon=True).start()

    def _build_video(self, box):
        files = sorted(self.lib.files(self.st["video_dirs"], "video"), key=lambda p: os.path.getmtime(p), reverse=True)
        self._head(box, "Videos", [("Add folder", "add", lambda: self.add_folder("video_dirs"))])
        box.pack_start(label(f"{len(files)} videos   |   " + ", ".join(d.replace(HOME, "~") for d in self.st["video_dirs"]),
                             "sec"), False, False, 0)
        if not files:
            box.pack_start(label("No videos found. Put videos in your Videos folder or use Add folder.", "empty"),
                           False, False, 8)
            return
        fb = Gtk.FlowBox()
        fb.set_selection_mode(Gtk.SelectionMode.NONE)
        fb.set_max_children_per_line(8)
        fb.set_homogeneous(True)
        fb.set_valign(Gtk.Align.START)
        items = []
        for p in files:
            b, img = self._tile(p)
            b.connect("clicked", lambda w, p=p: self.play_files([p]))
            fb.add(b)
            items.append((img, p))
        box.pack_start(fb, False, False, 0)
        self._fill_tiles(items)

    def _build_queue(self, box):
        self._head(box, "Play queue", [("Clear", "trash", self.clear_queue)])
        if not self.queue:
            box.pack_start(label("The play queue is empty.", "empty"), False, False, 8)
            return
        songs = [(p, self.lib.cache.get(p) or {"title": os.path.basename(p)}) for p in self.queue]
        tv = self._song_list(songs, lambda i: self.play_index(i))
        box.pack_start(tv, True, True, 0)

    def _build_nowplaying(self):
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        box.get_style_context().add_class("nowplaying")
        self.np_stack = Gtk.Stack()
        # music
        m = Gtk.Box(spacing=28)
        m.set_halign(Gtk.Align.CENTER)
        m.set_valign(Gtk.Align.CENTER)
        self.np_art = Gtk.Image()
        m.pack_start(self.np_art, False, False, 0)
        col = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        col.set_valign(Gtk.Align.CENTER)
        self.np_title = label("", "np-big-title", wrap=True)
        self.np_sub = label("", "np-big-sub", wrap=True)
        col.pack_start(self.np_title, False, False, 0)
        col.pack_start(self.np_sub, False, False, 0)
        m.pack_start(col, False, False, 0)
        self.np_stack.add_named(m, "music")
        # video
        vbox = Gtk.Box()
        if self.player.video_widget is not None:
            vw = self.player.video_widget
            vw.set_hexpand(True)
            vw.set_vexpand(True)
            ev = Gtk.EventBox()
            ev.add(vw)
            ev.connect("button-press-event", self._video_click)
            vbox.pack_start(ev, True, True, 0)
        else:
            vbox.pack_start(label("Video output isn't available (install gstreamer1.0-gtk3).", "empty", xalign=0.5),
                            True, True, 0)
        self.np_stack.add_named(vbox, "video")
        box.pack_start(self.np_stack, True, True, 0)
        return box

    def _video_click(self, w, ev):
        if ev.type == Gdk.EventType._2BUTTON_PRESS:
            self.toggle_fullscreen()
        elif ev.type == Gdk.EventType.BUTTON_PRESS and ev.button == 1:
            self.play_pause()
        return True

    # ---------------- queue / playback
    def play_files(self, files, start=0, shuffle=False):
        files = [os.path.abspath(f) for f in files if media_kind(f)]
        if not files:
            return
        self.queue = list(files)
        if shuffle:
            self.st["shuffle"] = True
            start = random.randrange(len(files))
        self._make_order(start)
        self.play_index(start)

    def add_to_queue(self, files, nxt=False):
        files = [f for f in files if media_kind(f)]
        if not self.queue:
            self.play_files(files)
            return
        if nxt:
            pos = self.qpos + 1
            self.queue[pos:pos] = files
        else:
            self.queue.extend(files)
        self._make_order(self.qpos)

    def clear_queue(self):
        self.player.stop()
        self.queue = []
        self.qpos = -1
        self.cur = None
        self._now_info()
        self.show_page("queue")

    def _make_order(self, start):
        idx = list(range(len(self.queue)))
        if self.st["shuffle"]:
            rest = [i for i in idx if i != start]
            random.shuffle(rest)
            self.order = [start] + rest
        else:
            self.order = idx

    def play_index(self, i):
        if not (0 <= i < len(self.queue)):
            return
        self.qpos = i
        p = self.queue[i]
        self.cur = p
        self.player.load(p)
        self.player.set_volume(self.st["volume"])
        rec = [x for x in self.st.get("recent", []) if x != p]
        rec.insert(0, p)
        self.st["recent"] = rec[:30]
        self._now_info()
        if media_kind(p) == "video":
            self.np_stack.set_visible_child_name("video")
            self.show_page("now")
        else:
            self.np_stack.set_visible_child_name("music")

    def _now_info(self):
        p = self.cur
        if not p:
            self.bar_title.set_text("Nothing playing")
            self.bar_artist.set_text("")
            self.bar_art.set_from_pixbuf(art_pixbuf(None, 48))
            self.set_title("Media Player")
            return
        d = self.lib.cache.get(p)

        def show(d):
            title = d.get("title") or os.path.basename(p)
            artist = d.get("artist") or ("" if media_kind(p) == "video" else "Unknown artist")
            self.bar_title.set_text(title)
            self.bar_artist.set_text(artist)
            self.set_title(f"{title} - Media Player")
            if media_kind(p) == "audio":
                self.bar_art.set_from_pixbuf(art_pixbuf(d.get("art"), 48))
                self.np_art.set_from_pixbuf(art_pixbuf(d.get("art"), 280))
                self.np_title.set_text(title)
                self.np_sub.set_text(" • ".join(x for x in (artist, d.get("album")) if x))
            else:
                self.bar_art.set_from_pixbuf(art_pixbuf(None, 48))
            return False
        if d:
            show(d)
        else:
            show({"title": os.path.splitext(os.path.basename(p))[0]})
            threading.Thread(target=lambda: GLib.idle_add(show, self.lib.info(p) or {}), daemon=True).start()

    def play_pause(self):
        if not self.cur:
            if self.queue:
                self.play_index(0)
            else:
                files = sorted(self.lib.files(self.st["music_dirs"], "audio"), key=lambda p: p.casefold())
                if files:
                    self.play_files(files)
            return
        if self.player.playing:
            self.player.pause()
        else:
            self.player.play()

    def next_track(self, auto=False):
        if not self.queue:
            return
        if auto and self.st["repeat"] == "one":
            self.play_index(self.qpos)
            return
        k = self.order.index(self.qpos) if self.qpos in self.order else -1
        if k + 1 < len(self.order):
            self.play_index(self.order[k + 1])
        elif self.st["repeat"] == "all" or not auto:
            if auto or self.st["repeat"] == "all":
                self._make_order(self.order[0] if not self.st["shuffle"] else random.randrange(len(self.queue)))
                self.play_index(self.order[0])
        else:
            self.player.stop()
            self._sync_buttons()

    def prev_track(self):
        if not self.queue:
            return
        if self.player.position() > 3 * Gst.SECOND:
            self.player.seek(0)
            return
        k = self.order.index(self.qpos) if self.qpos in self.order else 0
        self.play_index(self.order[max(0, k - 1)])

    def toggle_shuffle(self):
        self.st["shuffle"] = not self.st["shuffle"]
        if self.queue:
            self._make_order(self.qpos if self.qpos >= 0 else 0)
        self._sync_buttons()

    def cycle_repeat(self):
        self.st["repeat"] = {"off": "all", "all": "one", "one": "off"}[self.st["repeat"]]
        self._sync_buttons()

    def _play_error(self, msg):
        info_dialog(self, "Can't play this file", f"{os.path.basename(self.cur or '')}\n\n{msg}")

    # ---------------- misc actions
    def open_dialog(self):
        dlg = Gtk.FileChooserDialog(title="Open file(s)", transient_for=self, action=Gtk.FileChooserAction.OPEN)
        dlg.add_buttons("Cancel", Gtk.ResponseType.CANCEL, "Open", Gtk.ResponseType.OK)
        dlg.set_select_multiple(True)
        f = Gtk.FileFilter()
        f.set_name("Media files")
        for e in sorted(AUDIO_EXT | VIDEO_EXT):
            f.add_pattern("*" + e)
            f.add_pattern("*" + e.upper())
        dlg.add_filter(f)
        dlg.set_current_folder(os.path.join(HOME, "Music") if os.path.isdir(os.path.join(HOME, "Music")) else HOME)
        if dlg.run() == Gtk.ResponseType.OK:
            files = dlg.get_filenames()
            dlg.destroy()
            self.play_files(files)
            return
        dlg.destroy()

    def add_folder(self, key_):
        dlg = Gtk.FileChooserDialog(title="Add a folder to the library", transient_for=self,
                                    action=Gtk.FileChooserAction.SELECT_FOLDER)
        dlg.add_buttons("Cancel", Gtk.ResponseType.CANCEL, "Add", Gtk.ResponseType.OK)
        dlg.set_current_folder(HOME)
        if dlg.run() == Gtk.ResponseType.OK:
            p = dlg.get_filename()
            if p and p not in self.st[key_]:
                self.st[key_].append(p)
        dlg.destroy()
        self.show_page("music" if key_ == "music_dirs" else "video")

    def show_in_folder(self, p):
        if shutil.which("pi-explorer"):
            subprocess.Popen(["pi-explorer", "--select", p], start_new_session=True)
        else:
            try:
                Gio.AppInfo.launch_default_for_uri(Gio.File.new_for_path(os.path.dirname(p)).get_uri(), None)
            except GLib.Error:
                pass

    def _more_menu(self, w):
        spec = [
            {"label": "Open file(s)", "icon": "open", "accel": "Ctrl+O", "cb": self.open_dialog},
            {"label": "Show in folder", "icon": "folder", "sensitive": bool(self.cur),
             "cb": lambda: self.show_in_folder(self.cur)},
            None,
            {"label": "Speed", "sub": [{"label": f"{r}x", "cb": (lambda r=r: self.set_rate(r))}
                                       for r in (0.5, 0.75, 1, 1.25, 1.5, 2)]},
            {"label": "Clear play queue", "icon": "trash", "cb": self.clear_queue},
        ]
        m = build_menu(spec)
        self._menu = m
        popup_menu(m, w)

    def set_rate(self, r):
        pos = self.player.position()
        self.player.pipe.seek(r, Gst.Format.TIME, Gst.SeekFlags.FLUSH | Gst.SeekFlags.ACCURATE,
                              Gst.SeekType.SET, pos, Gst.SeekType.NONE, 0)

    def toggle_fullscreen(self):
        if self.is_fs:
            self.unfullscreen()
        else:
            if self.cur and media_kind(self.cur) == "video":
                self.show_page("now")
            self.fullscreen()

    is_fs = False

    def _wstate(self, w, ev):
        self.is_fs = bool(ev.new_window_state & Gdk.WindowState.FULLSCREEN)
        self.nav.set_visible(not self.is_fs)
        self.bar.set_visible(not self.is_fs)
        self.b_full.get_child().set_icon("unfullscreen" if self.is_fs else "fullscreen")
        return False

    def _drop(self, w, ctx, x, y, data, info, t):
        files = []
        for u in data.get_uris() or []:
            p = Gio.File.new_for_uri(u).get_path()
            if p and os.path.isdir(p):
                for root, ds, fs in os.walk(p):
                    files += sorted(os.path.join(root, f) for f in fs if media_kind(f))
            elif p:
                files.append(p)
        if files:
            self.play_files(files)

    def _configure(self, w, ev):
        if not self.is_maximized() and not self.is_fs:
            self.st["width"], self.st["height"] = self.get_size()
        return False

    def _on_close(self, *a):
        self.st["maximized"] = self.is_maximized()
        self.player.stop()
        self.st.save()
        self.lib.save()
        return False

    def _key(self, w, ev):
        k = ev.keyval
        kl = Gdk.keyval_to_lower(k)
        ctrl = bool(ev.state & Gdk.ModifierType.CONTROL_MASK)
        if isinstance(self.get_focus(), Gtk.Entry):
            return False
        if k == Gdk.KEY_space or (ctrl and kl == Gdk.KEY_p) or k == Gdk.KEY_AudioPlay:
            self.play_pause()
        elif (ctrl and kl == Gdk.KEY_f) or k == Gdk.KEY_AudioNext:
            self.next_track()
        elif (ctrl and kl == Gdk.KEY_b) or k == Gdk.KEY_AudioPrev:
            self.prev_track()
        elif ctrl and kl == Gdk.KEY_o:
            self.open_dialog()
        elif k == Gdk.KEY_Right and not ctrl:
            self.player.seek(self.player.position() + 10 * Gst.SECOND)
        elif k == Gdk.KEY_Left and not ctrl:
            self.player.seek(self.player.position() - 10 * Gst.SECOND)
        elif k == Gdk.KEY_Up and not ctrl:
            self.vol.set_value(min(1, self.vol.get_value() + 0.05))
        elif k == Gdk.KEY_Down and not ctrl:
            self.vol.set_value(max(0, self.vol.get_value() - 0.05))
        elif kl == Gdk.KEY_m and not ctrl:
            self.toggle_mute()
        elif k in (Gdk.KEY_F11,) or (kl == Gdk.KEY_f and not ctrl and self.cur and media_kind(self.cur) == "video"):
            self.toggle_fullscreen()
        elif k == Gdk.KEY_Escape and self.is_fs:
            self.unfullscreen()
        else:
            return False
        return True


_orig_extra = draw_glyph_extra


def draw_glyph_extra(cr, name, L, pi):  # noqa: F811
    if name == "home":
        L((2, 8), (8, 2.5), (14, 8))
        L((3.5, 6.8), (3.5, 14), (12.5, 14), (12.5, 6.8))
        _rr(cr, 6.5, 9.5, 3, 4.5, 0.4)
        cr.stroke()
    elif name == "folder":
        cr.move_to(1.5, 4)
        cr.line_to(6, 4)
        cr.line_to(7.5, 5.5)
        cr.line_to(14.5, 5.5)
        cr.line_to(14.5, 13)
        cr.line_to(1.5, 13)
        cr.close_path()
        cr.stroke()
    else:
        _orig_extra(cr, name, L, pi)


class PlayerApp(Gtk.Application):
    def __init__(self):
        super().__init__(application_id=APP_ID, flags=Gio.ApplicationFlags.HANDLES_COMMAND_LINE)
        self.win = None

    def do_startup(self):
        Gtk.Application.do_startup(self)
        Gst.init(None)
        self.settings = JsonSettings("pi-mediaplayer", DEFAULTS)
        self.library = Library(self.settings)
        apply_css(CSS)
        GLib.timeout_add_seconds(20, lambda: self.settings.save() or True)

    def do_command_line(self, cmd):
        cwd = cmd.get_cwd() or HOME
        files = []
        for a in cmd.get_arguments()[1:]:
            if a.startswith("-"):
                continue
            p = Gio.File.new_for_uri(a).get_path() if "://" in a else os.path.join(cwd, os.path.expanduser(a))
            if p:
                files.append(p)
        if self.win is None:
            self.win = PlayerWindow(self, files)
            self.win.connect("destroy", lambda *a: setattr(self, "win", None))
            self.win.present()
        else:
            if files:
                self.win.play_files(files)
            self.win.present()
        return 0


def main():
    GLib.set_prgname("pi-mediaplayer")
    GLib.set_application_name("Media Player")
    app = PlayerApp()
    signal.signal(signal.SIGINT, signal.SIG_DFL)
    return app.run(sys.argv)


if __name__ == "__main__":
    sys.exit(main())
