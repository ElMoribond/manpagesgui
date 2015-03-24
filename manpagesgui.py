#!/bin/env python3
# -*- coding: utf-8 -*-

# manpagesgui - GUI manual pager
# Copyright © 2015 ElMoribond (Michael Herpin)
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

from argparse import ArgumentParser, ArgumentTypeError
from functools import partial
from gettext import bindtextdomain, gettext, textdomain
from glob import glob
from os import path
from random import randrange
from re import compile, DOTALL, findall, IGNORECASE, match, MULTILINE, sub
from shutil import which
from subprocess import DEVNULL, PIPE, Popen
from textwrap import dedent
from PyQt5.QtCore import QBuffer, QByteArray, QSettings, Qt, QUrl
from PyQt5.QtGui import QCursor, QDesktopServices, QIcon, QPixmap
from PyQt5.QtWidgets import QAction, QApplication, QComboBox, QDialog, QGridLayout, QHBoxLayout, QLabel, QLayout, QLineEdit, QMessageBox, QPushButton, QStyle, QTextBrowser, QVBoxLayout, QWidget
from PyQt5.QtWebKitWidgets import QWebPage, QWebView

PROJECT_NAME= "manPagesGui"
PROJECT_VERSION= "1.0"
PROJECT_RELEASE_DATE= "2015-03-22"
PROJECT_TEAM= "ElMoribond"
PROJECT_EMAIL= "elmoribond@gmail.com"
PROJECT_URL="https://github.com/ElMoribond/manpagesgui"

bindtextdomain(PROJECT_NAME.lower(), "i18n")
textdomain(PROJECT_NAME.lower())

class ManPagesDialog(QDialog):

    class AboutDialog(QDialog):

        class LicenseLabel(QLabel):

            def __init__(self):
                super().__init__("")
                self.setPixmap(QPixmap(path.join("png", "gplv3-127x51.png")))

            def mousePressEvent(self, event):
                if event.button() == Qt.LeftButton:
                    QDesktopServices.openUrl(QUrl("http://www.gnu.org/licenses/quick-guide-gplv3.html"))

            def enterEvent(self, event):
                QApplication.setOverrideCursor(QCursor(Qt.PointingHandCursor))
                super().enterEvent(event)

            def leaveEvent(self, event):
                QApplication.restoreOverrideCursor()
                super().enterEvent(event)

        def __init__(self):
            super().__init__(ManPagesDialog.self)
            self.setWindowTitle("%s %s" % (gettext("About"), PROJECT_NAME))
            css= "" if namespace.theme_color else "style='color: %s'" % namespace.link_color
            logo= QLabel()
            logo.setPixmap(ManPagesDialog.logo)
            email= QLabel("%s <a href='mailto:%s?subject=[%s]' %s>%s</a>" % (gettext("Lost in French countryside but reachable"), PROJECT_EMAIL, PROJECT_NAME, css, PROJECT_EMAIL))
            email.setOpenExternalLinks(True)
            url= QLabel("<br /><a href='%s' %s>%s</a><br />" % (PROJECT_URL, css, PROJECT_URL))
            url.setOpenExternalLinks(True)
            butttonClose= QPushButton(self.style().standardIcon(QStyle.SP_DialogCloseButton), "")
            butttonClose.clicked.connect(self.close)
            layoutFirstPart= QGridLayout()
            layoutFirstPart.addWidget(logo, 0, 0, 4, 1)
            layoutFirstPart.addWidget(QLabel("%s v%s %s %s" % (PROJECT_NAME, PROJECT_VERSION, gettext("released on"), PROJECT_RELEASE_DATE)), 0, 1, 1, 2)
            layoutFirstPart.addWidget(QLabel("%s %s" % (gettext("Created by"), PROJECT_TEAM)), 1, 1, 1, 2)
            layoutFirstPart.addWidget(email, 2, 1, 1, 2)
            layoutFirstPart.addWidget(QLabel(gettext("Released under GNU GPLv3 license")), 3, 1)
            layoutFirstPart.addWidget(self.LicenseLabel(), 3, 2, 2, 1, Qt.AlignTop|Qt.AlignRight)
            layoutFirstPart.addWidget(QLabel("\nCopyright © 2015 %s (Michael Herpin). %s.\n%s.\n%s." % (PROJECT_TEAM, gettext("All rights reserved"), gettext("This program comes with ABSOLUTELY NO WARRANTY"), gettext("This is free software, and you are welcome to redistribute it under certain conditions"))), 4, 0, 1, 3)
            layoutFirstPart.addWidget(url, 5, 0, 1, 3)
            layoutFirstPart.addWidget(butttonClose, 6, 0, 1, 3)
            self.setLayout(layoutFirstPart)

    class EditZone(QLineEdit):

        class Label(QLabel):

            def __init__(self, parent):
                super().__init__(parent)
                icon= self.style().standardIcon(QStyle.SP_MessageBoxWarning) if QIcon.fromTheme("dialog-warning").isNull() else QIcon.fromTheme("dialog-warning")
                self.setPixmap(icon.pixmap(parent.minimumSizeHint().height(), parent.minimumSizeHint().height(), QIcon.Normal, QIcon.On))
                self.setVisible(False)

            def enterEvent(self, event):
                QApplication.setOverrideCursor(QCursor(Qt.WhatsThisCursor))
                super().enterEvent(event)

            def leaveEvent(self, event):
                QApplication.restoreOverrideCursor()
                super().enterEvent(event)

        def __init__(self):
            super().__init__()
            self.setContextMenuPolicy(Qt.CustomContextMenu)
            self.customContextMenuRequested.connect(self.openContextMenu)
            self.info= self.Label(self)

        def openContextMenu(self, point):
            contextMenu= self.createStandardContextMenu()
            itemRandom= QAction(ManPagesDialog.randomPage, self, triggered= partial(ManPagesDialog.self.manpages.openPage, None, 1))
            contextMenu.addSeparator()
            contextMenu.addAction(itemRandom)
            contextMenu.exec_(self.mapToGlobal(point))

        def focusOutEvent(self, event):
            self.setFocus(True)

        def keyPressEvent(self, event):
            if not ManPagesDialog.manpagesHover or not ManPagesDialog.self.manpages.pressedKey(event):
                super().keyPressEvent(event)

        def resizeEvent(self, event):
            self.ensurePolished()
            self.info.setGeometry(self.rect().right() - self.minimumSizeHint().height(), (self.rect().height() - self.minimumSizeHint().height()) / 2, self.minimumSizeHint().height(), self.minimumSizeHint().height())

    class ManPagesZone(QWebView):

        def __init__(self):
            super().__init__()
            self.raw= False
            self.setContextMenuPolicy(Qt.CustomContextMenu)
            self.customContextMenuRequested.connect(self.openContextMenu)
            self.page().setLinkDelegationPolicy(QWebPage.DelegateAllLinks)
            self.linkClicked.connect(self.openPage)
            ManPagesDialog.self.command.returnPressed.connect(partial(self.openPage, ManPagesDialog.self.command))
            ManPagesDialog.self.pagesList.currentIndexChanged[int].connect(partial(self.openPage, -2))
            if not namespace.disable_proposal:
                ManPagesDialog.self.pagesOther.currentIndexChanged[int].connect(partial(self.openPage, -3))
            ManPagesDialog.self.buttonPrevious.clicked.connect(partial(self.openPage, False))
            ManPagesDialog.self.buttonNext.clicked.connect(partial(self.openPage, True))
            self.css= "" if namespace.theme_color else """
                body { color: """ + namespace.color + """; background-color: """ + namespace.background + """ }
                a:link { color: """ + namespace.link_color + """; background-color: """ + namespace.link_background + """ }
                h2 { color: """ + namespace.section_color + """; background-color: """ + namespace.section_background + """}
                envar { color: """ + namespace.envar_color + """; background-color: """ + namespace.envar_background + """}
                b { color: """ + namespace.bold_color + """; background-color: """ + namespace.bold_background + """}
                i { color: """ + namespace.italic_color + """; background-color: """ + namespace.italic_background + """}
                table.add { border-collapse: collapse; margin: 1em auto; }
                td.add, th.add { border: 1px solid """ + namespace.color + """; padding: 3px; }"""
            img= self.style().standardIcon(QStyle.SP_MessageBoxWarning)
            ba= QByteArray()
            img.pixmap(48, 48, QIcon.Normal, QIcon.On).save(QBuffer(ba), "PNG")
            self.css+= """
                .rawlink { height: 48px; width: 48px; background-image: url(data:image/png;base64,""" + str(ba.toBase64(), encoding='utf8') + """); }
                p, pre, table { margin-top: 0; margin-bottom: 0; vertical-align: top }"""

        def enterEvent(self, event):
            ManPagesDialog.manpagesHover= True
            super().enterEvent(event)

        def leaveEvent(self, event):
            ManPagesDialog.manpagesHover= False
            super().enterEvent(event)
    
        def mousePressEvent(self, event):
            if event.button() == Qt.BackButton and ManPagesDialog.self.buttonPrevious.isEnabled():
                ManPagesDialog.self.buttonPrevious.click()
            elif event.button() == Qt.ForwardButton and ManPagesDialog.self.buttonNext.isEnabled():
                ManPagesDialog.self.buttonNext.click()
            else:
                super().mousePressEvent(event)

        def pressedKey(self, event):
            if event.key() in [ Qt.Key_Home, Qt.Key_End, Qt.Key_Up, Qt.Key_Down, Qt.Key_PageUp, Qt.Key_PageDown ] and not event.modifiers() == Qt.ShiftModifier:
                self.keyPressEvent(event)
                return True
            return False

        def openContextMenu(self, point):
            contextMenu= QTextBrowser(self).createStandardContextMenu()
            if namespace.no_email_link and namespace.no_url_link:
                contextMenu.actions()[1].setVisible(False)
            elif len(self.selectedText()):
                contextMenu.actions()[0].setEnabled(True)
                contextMenu.actions()[0].triggered.connect(partial(app.clipboard().setText, self.selectedText()))
            elif self.anchorAt(point):
                contextMenu.actions()[1].setEnabled(True)
                contextMenu.actions()[1].triggered.connect(partial(app.clipboard().setText, self.anchorAt(point)))
            contextMenu.addSeparator()
            contextMenu.addAction(QAction(ManPagesDialog.randomPage, self, triggered= partial(self.openPage, None, 1)))
            contextMenu.exec_(self.mapToGlobal(point))

        def anchorAt(self, pos):
            print(self.page().currentFrame().hitTestContent(pos).linkUrl().toString())
            if self.page().currentFrame().hitTestContent(pos).linkUrl().scheme() in [ "http", "https", "mailto" ]:
                return self.page().currentFrame().hitTestContent(pos).linkUrl().toString().replace("−", "-")
            return False

        def openPage(self, page, option= True):
            QApplication.setOverrideCursor(QCursor(Qt.BusyCursor))
            if page == None:
                page= 0
                if not len(ManPagesDialog.pages):
                    for fn in glob(path.join(namespace.man_directory, path.join("man?", "*.gz"))):
                        ManPagesDialog.pages.append(sub(r"(.+)\.([^.]+)(\.gz)", r"\2 \1", path.basename(fn)))
                while page < option:
                    x= randrange(0, len(ManPagesDialog.pages) - 1)
                    if ManPagesDialog.self.pagesList.findText(ManPagesDialog.pages[x], Qt.MatchFixedString) == -1:
                        self.openPage(ManPagesDialog.pages[x], False)
                        page+= 1
            elif type(page) == type(bool()):
                if self.raw:
                    self.raw= False
                    self.openPage(ManPagesDialog.self.pagesList.currentIndex())
                else:
                    self.openPage(ManPagesDialog.self.pagesList.currentIndex() + 1 if page else ManPagesDialog.self.pagesList.currentIndex() - 1, option)
            elif type(page) == type(int()):
                if page == -3:
                    self.openPage(ManPagesDialog.self.pagesOther.currentText())
                elif page == -2:
                    self.openPage(ManPagesDialog.self.pagesList.currentIndex())
                elif page > -1:
                    ManPagesDialog.self.setWindowTitle("%s: %s" % (PROJECT_NAME, ManPagesDialog.self.pagesList.itemText(page)))
                    ManPagesDialog.self.pagesList.currentIndexChanged[int].disconnect()
                    ManPagesDialog.self.pagesList.setCurrentIndex(page)
                    ManPagesDialog.self.pagesList.currentIndexChanged[int].connect(partial(self.openPage, -2))
                    self.setHtml(self.applyStyle(ManPagesDialog.self.pagesList.itemData(page)[0][0]))
                    ManPagesDialog.self.buttonPrevious.setEnabled(True if ManPagesDialog.self.pagesList.currentIndex() > 0 else False)
                    ManPagesDialog.self.buttonNext.setEnabled(True if ManPagesDialog.self.pagesList.currentIndex() < ManPagesDialog.self.pagesList.count() - 1 else False)
                    if not namespace.disable_proposal:
                        ManPagesDialog.self.pagesOther.currentIndexChanged[int].disconnect()
                        ManPagesDialog.self.pagesOther.clear()
                        if len(ManPagesDialog.self.pagesList.itemData(page)[1]) > 1:
                            ManPagesDialog.self.pagesOther.setEnabled(True)
                        else:
                            ManPagesDialog.self.pagesOther.setEnabled(False)
                        for x, item in enumerate(ManPagesDialog.self.pagesList.itemData(page)[1]):
                            ManPagesDialog.self.pagesOther.addItem(item)
                            if item == ManPagesDialog.self.pagesList.currentText():
                                ManPagesDialog.self.pagesOther.setCurrentIndex(x)
                        ManPagesDialog.self.pagesOther.currentIndexChanged[int].connect(partial(self.openPage, -3))
            elif type(page) == type(list()):
                for x in page:
                    self.openPage(x, option)
            elif page == ManPagesDialog.self.command:
                pages= page.text()
                page.setText("")
                self.openPage(parsePages(pages), True)
            elif type(page) == type(QUrl()):
                if page.scheme() == ManPagesDialog.manScheme:
                    self.openPage(sub(r"%s:([\S]+)\.(.+)" % ManPagesDialog.manScheme, r"\2 \1", page.toString()))
                elif page.scheme() == ManPagesDialog.rawScheme:
                    self.raw= True
                    ManPagesDialog.self.buttonPrevious.setEnabled(True)
                    self.setHtml(self.applyStyle("<html><head><style type=\"text/css\"></style></head><body><pre>%s</pre></body></html>" % ManPagesDialog.self.pagesList.itemData(ManPagesDialog.self.pagesList.currentIndex())[0][1][1]))
                else:
                    QDesktopServices.openUrl(QUrl(page.toString().replace("−", "-")))
            elif len(page):
                errorOccurred= "%s: %s" % (page, gettext("An error occurred"))
                default= self.man(parsePages(page)[0], ManPagesDialog.DEFAULTSECTION)
                if not type(default) == type(list()):
                    if default == -2:
                        self.addError(errorOccurred, option)
                    else:
                        self.addError("%s: %s" % (parsePages(page)[0], gettext("Not Found")), option)
                else:
                    if ManPagesDialog.self.pagesList.findText(default[1], Qt.MatchFixedString) > -1:
                        if option:
                            self.openPage(ManPagesDialog.self.pagesList.findText(default[1], Qt.MatchFixedString), option)
                    else:
                        sections= self.man(parsePages(page)[0], ManPagesDialog.ALLSECTIONS)
                        source= self.man(parsePages(page)[0], ManPagesDialog.CONTENTSECTION)
                        if type(source) == type(list()) and type(sections) == type(list()):
                            ManPagesDialog.self.pagesList.currentIndexChanged[int].disconnect()
                            ManPagesDialog.self.pagesList.addItem(default[1], [ source, sections ])
                            ManPagesDialog.self.pagesList.currentIndexChanged[int].connect(partial(self.openPage, -2))
                            self.openPage(ManPagesDialog.self.pagesList.count() - 1, option)
                        else:
                            self.addError(errorOccurred, option)
            QApplication.restoreOverrideCursor()

        def man(self, page, option):
            if option == ManPagesDialog.DEFAULTSECTION:
                source= self.man("%s -D -w -M %s %s" % (namespace.man_command, namespace.man_directory, page), ManPagesDialog.POPEN)
                if source[0] == 0:
                    return sub(r"^([\S]+)(/)(\S+)(\.)(\S+)(\.gz)$", r"\1\2\3\4\5\6\n\3(\5)", source[1]).splitlines()
                elif source[0] == 16:
                    return -1
            elif option == ManPagesDialog.ALLSECTIONS:
                source= self.man("%s -D -f -m %s %s" % (namespace.man_command, namespace.man_directory, page), ManPagesDialog.POPEN)
                if source[0] == 0:
                    return sub(compile(r"^([\S]+) (\S+).*$", MULTILINE), r"\1\2", source[1]).splitlines()
            elif option == ManPagesDialog.CONTENTSECTION:
                source= self.man("%s -D -Hcat --nh -M %s %s" % (namespace.man_command, namespace.man_directory, page), ManPagesDialog.POPEN)
                if source[0] == 0:
                    tab1= findall(r"[\S ]+<img src[\S ]+>", source[1])
                    if len(tab1):
                        s= self.man("%s -D -Pcat --nh -M %s %s" % (namespace.man_command, namespace.man_directory, page), ManPagesDialog.POPEN)
                        if s[0] == 0:
                            tab2= findall(r" {7}┌[\S \n]+┘", s[1])
                            if len(tab1) == len(tab2):
                                for x, torep in enumerate(tab1):
                                    source[1]= source[1].replace(torep, self.createTable(tab2[x]))
                            else:
                                source[1]= sub(compile(r"<img src[\S ][^>]+>", DOTALL), r"<a href='raw://currentpage'><img class='rawlink' src='' /></a>", source[1])
                    else:
                        s= None
                    source[1]= sub(r"(\${1}[A-Z_.]+)", r"<envar>\1</envar>", sub(compile(r"<b>([_A-Z.0-9-]+)</b>\((\d+[A-Z]*)\)", DOTALL|IGNORECASE), r"<a href='%s:\1.\2'>\1(\2)</a>" % ManPagesDialog.manScheme, sub(r"(<style type=\"text/css\">)[\S \n]*(</style>)", r"\1\2", sub(compile(r"(\n<a name.+?(?=\n)\n)", DOTALL), r"", sub(r"^[\S \n]+(<style)", r"<html><head><meta charset='utf-8'>\1", sub(r"(?<=<body>)[\S \n]+?(?=<h2>)", r"\n", source[1]))))))
                    if not namespace.no_url_link:
                        source[1]= sub(compile(r"(https?://[\dA-Z\.-]+\.[A-Z\.-]{2,6}[\/\w&\-\.−\-;]*)/?(?<!\.)", MULTILINE|DOTALL|IGNORECASE), r"<a href='\1'>\1</a>", source[1])
                    if not namespace.no_email_link:
                        source[1]= sub(compile(r"([_A-Z0-9.+-]+@[_A-Z0-9-]+\.[A-Z0-9-.]+)", DOTALL|IGNORECASE), r"<a href='mailto://\1'>\1</a>", source[1])
                    return [ source[1].replace("<hr>", "").replace("\n\n\n", "\n").replace("\n\n", "\n"), s ]
            else:
                try:
                    proc= Popen(page, stdout= PIPE, stderr= DEVNULL, universal_newlines= True, bufsize= 1, shell= True)
                except:
                    pass
                else:
                    try:
                        source= proc.communicate(timeout= 10)[0]
                    except:
                        pass
                    else:
                        return [ proc.returncode, source ]
            return -2

        def addError(self, error, option):
            if option:
                QApplication.restoreOverrideCursor()
                QApplication.setOverrideCursor(QCursor(Qt.ArrowCursor))
                ManPagesDialog.self.setWindowTitle(PROJECT_NAME)
                QMessageBox.warning(ManPagesDialog.self, "\0", error, QMessageBox.Ok)
            if not error in ManPagesDialog.pagesError:
                ManPagesDialog.pagesError.append(error)
            ManPagesDialog.self.command.info.setToolTip("\n".join(map(str, ManPagesDialog.pagesError)))
            ManPagesDialog.self.command.info.setVisible(True)
            ManPagesDialog.self.command.setTextMargins(0, 0, ManPagesDialog.self.command.info.minimumSizeHint().height(), 0)

        def createTable(self, raw, t= ""):
            for i, line in enumerate(raw.splitlines()):
                if line.strip().startswith("┌"):
                    t= "<table class='add'>"
                elif line.strip().startswith("│"):
                    t= "%s<tr>" % t
                    for cell in line.split("│"):
                        if len(cell.strip()):
                            t= "%s%s%s%s" % (t, "<th class='add'>" if i == 1 else "<td class='add'>", cell.strip(), "</th>" if i == 1 else "</td>")
                    t= "%s</tr>" % t
                elif line.strip().startswith("└"):
                    t= "%s</table>" % t
            return t

        def applyStyle(self, html):
            return sub(r"(<style type=\"text/css\">)(</style>)", r"\1%s\2" % dedent(self.css), html)

    def __init__(self):
        super().__init__()
        ManPagesDialog.self= self
        ManPagesDialog.pagesError= list()
        ManPagesDialog.pages= list()
        ManPagesDialog.manScheme= "manpage"
        ManPagesDialog.rawScheme= "raw"
        ManPagesDialog.manpagesHover= False
        ManPagesDialog.logo= QPixmap(path.join("png", "manpagesgui.png"))
        ManPagesDialog.randomPage= gettext("Random Page")
        ManPagesDialog.DEFAULTSECTION= 0
        ManPagesDialog.ALLSECTIONS= 1
        ManPagesDialog.CONTENTSECTION= 2
        ManPagesDialog.POPEN= 3
        self.rejected.connect(self.close)
        self.setWindowFlags(Qt.WindowType_Mask|Qt.WindowMaximizeButtonHint)
        self.setWindowIcon(QIcon(ManPagesDialog.logo))
        self.setWindowTitle(PROJECT_NAME)
        if QIcon.fromTheme("go-previous").isNull() or QIcon.fromTheme("go-next").isNull() or QIcon.fromTheme("application-exit").isNull():
            self.buttonPrevious= QPushButton(self.style().standardIcon(QStyle.SP_ArrowLeft), "")
            self.buttonNext= QPushButton(self.style().standardIcon(QStyle.SP_ArrowRight), "")
            buttonQuit= QPushButton(self.style().standardIcon(QStyle.SP_DialogCloseButton), "")
        else:
            self.buttonPrevious= QPushButton(QIcon.fromTheme("go-previous"), "")
            self.buttonNext= QPushButton(QIcon.fromTheme("go-next"), "")
            buttonQuit= QPushButton(QIcon.fromTheme("application-exit"), "")
        self.buttonPrevious.setEnabled(False)
        self.buttonPrevious.setAutoDefault(False)
        self.buttonNext.setEnabled(False)
        self.buttonNext.setAutoDefault(False)
        self.command= self.EditZone()
        self.pagesList= QComboBox()
        buttonAbout= QPushButton(QIcon(ManPagesDialog.logo), "")
        buttonAbout.setIconSize(self.buttonNext.iconSize())
        buttonAbout.setAutoDefault(False)
        buttonAbout.clicked.connect(self.AboutDialog().exec_)
        layoutBox1= QHBoxLayout()
        layoutBox1.addWidget(self.buttonPrevious)
        layoutBox1.addWidget(self.buttonNext)
        layoutBox1.addWidget(self.command)
        layoutBox1.addWidget(self.pagesList)
        layoutBox1.addWidget(buttonAbout)
        layoutBox1.setContentsMargins(0, 0, 0, 0)
        layoutBox1.setStretchFactor(self.command, 1)
        layoutBox1.setStretchFactor(self.pagesList, 1)
        box1= QWidget()
        box1.setLayout(layoutBox1)
        buttonQuit.clicked.connect(self.close)
        buttonQuit.setAutoDefault(False)
        layoutBox2= QHBoxLayout()
        if not namespace.disable_proposal:
            self.pagesOther= QComboBox()
            layoutBox2.addWidget(self.pagesOther)
        layoutBox2.addWidget(buttonQuit)
        layoutBox2.setContentsMargins(0, 0, 0, 0)
        box2= QWidget()
        box2.setLayout(layoutBox2)
        self.manpages= self.ManPagesZone()
        charactereSize= self.fontMetrics().boundingRect("X")
        self.manpages.setFixedSize(charactereSize.width() * int(namespace.cols), charactereSize.height() * int(namespace.rows))
        self.settings= QSettings(PROJECT_TEAM, PROJECT_NAME)
        if self.settings.value("geometry", False):
            self.restoreGeometry(self.settings.value("geometry"))
        layout= QVBoxLayout()
        layout.addWidget(box1)
        layout.addWidget(self.manpages)
        layout.addWidget(box2)
        layout.setSizeConstraint(QLayout.SetFixedSize)
        self.setLayout(layout)

    def closeEvent(self, event):
        self.settings.setValue("geometry", self.saveGeometry())
        app.quit()

def invalidArgument(value, text= None):
    raise ArgumentTypeError("'%s' %s" % (value, text if text else gettext("is not valid argument")))

def directory(value):
    if path.isdir(value):
        return value
    invalidArgument(value, gettext("directory not found"))

def command(value):
    if which(value):
        return value
    invalidArgument(value, gettext("command not found"))

def checkInteger(value, min, max):
    if value.isdigit() and int(value) >= min and int(value) <= max:
        return value
    invalidArgument(value)

def rowsNumber(value):
    return checkInteger(value, 20, 120)

def colsNumber(value):
    return checkInteger(value, 90, 200)

def pagesNumber(value):
    return checkInteger(value, 0, 20)

def colorString(value):
    if match(r"^[A-F0-9]{6}$", value, IGNORECASE) or value.lower() in [ "aliceblue", "antiquewhite", "aqua", "aquamarine", "azure", "beige", "bisque", "black", "blanchedalmond", "blue", "blueviolet", "brown", "burlywood", "cadetblue", "chartreuse", "chocolate", "coral", "cornflowerblue", "cornsilk", "crimson", "cyan", "darkblue", "darkcyan", "darkgoldenrod", "darkgray", "darkgreen", "darkkhaki", "darkmagenta", "darkolivegreen", "darkorange", "darkorchid", "darkred", "darksalmon", "darkseagreen", "darkslateblue", "darkslategray", "darkturquoise", "darkviolet", "deeppink", "deepskyblue", "dimgray", "dodgerblue", "firebrick", "floralwhite", "forestgreen", "fuchsia", "gainsboro", "ghostwhite", "gold", "goldenrod", "gray", "green", "greenyellow", "honeydew", "hotpink", "indianred", "indigo", "ivory", "khaki", "lavender", "lavenderblush", "lawngreen", "lemonchiffon", "lightblue", "lightcoral", "lightcyan", "lightgoldenrodyellow", "lightgray", "lightgreen", "lightpink", "lightsalmon", "lightseagreen", "lightskyblue", "lightslategray", "lightsteelblue", "lightyellow", "lime", "limegreen", "linen", "magenta", "maroon", "mediumaquamarine", "mediumblue", "mediumorchid", "mediumpurple", "mediumseagreen", "mediumslateblue", "mediumspringgreen", "mediumturquoise", "mediumvioletred", "midnightblue", "mintcream", "mistyrose", "moccasin", "navajowhite", "navy", "oldlace", "olive", "olivedrab", "orange", "orangered", "orchid", "palegoldenrod", "palegreen", "paleturquoise", "palevioletred", "papayawhip", "peachpuff", "peru", "pink", "plum", "powderblue", "purple", "rebeccapurple", "red", "rosybrown", "royalblue", "saddlebrown", "salmon", "sandybrown", "seagreen", "seashell", "sienna", "silver", "skyblue", "slateblue", "slategray", "snow", "springgreen", "steelblue", "tan", "teal", "thistle", "tomato", "turquoise", "violet", "wheat", "white", "whitesmoke", "yellow", "yellowgreen" ]:
        return value
    invalidArgument(value)

def parsing():
    parser= ArgumentParser(description= gettext("GUI manual pager"))
    parser.add_argument("--man-command", "-M", type= command, action= "store", default= "man", help= "%s (default: %%(default)s)" % (gettext("man command")))
    parser.add_argument("--man-directory", "-D", type= directory, action= "store", default= "/usr/share/man", help= "%s (default: %%(default)s)" % (gettext("manual pages directory")))
    parser.add_argument("--random-page", "-p", type= pagesNumber, action= "store", default= "0", help= "%s (default: %%(default)s)" % gettext("Number of random pages displayed"))
    parser.add_argument("--disable-proposal", "-P", action= "store_true", help= gettext("Disables other proposals pages"))
    parser.add_argument("--cols", "-C", type= colsNumber, action= "store", default= "92", help= "%s (default: %%(default)s)" % gettext("Number of columns displayed"))
    parser.add_argument("--rows", "-R", type= rowsNumber, action= "store", default= "41", help= "%s (default: %%(default)s)" % gettext("Number of rows displayed"))
    parser.add_argument("--no-email-link", "-ne", action= "store_true", help= gettext("Disables email links"))
    parser.add_argument("--no-url-link", "-nu", action= "store_true", help= gettext("Disables URL links"))
    parser.add_argument("--theme-color", "-t", action= "store_true", help= gettext("Use theme's colors"))
    parser.add_argument("--color", "-c", type= colorString, action= "store", default= "LightSlateGray", help= "%s (default: %%(default)s)" % gettext("Text color"))
    parser.add_argument("--background", "-b", type= colorString, action= "store", default= "CornSilk", help= "%s (default: %%(default)s)" % gettext("Background color"))
    parser.add_argument("--section-color", "-sc", type= colorString, action= "store", default= "CornSilk", help= "%s (default: %%(default)s)" % gettext("Section text color"))
    parser.add_argument("--section-background", "-sb", type= colorString, action= "store", default= "CadetBlue", help= "%s (default: %%(default)s)" % gettext("Section background color"))
    parser.add_argument("--link-color", "-lc", type= colorString, action= "store", default= "Navy", help= "%s (default: %%(default)s)" % gettext("Link text color"))
    parser.add_argument("--link-background", "-lb", type= colorString, action= "store", default= "CornSilk", help= "%s (default: %%(default)s)" % gettext("Link background color"))
    parser.add_argument("--bold-color", "-bc", type= colorString, action= "store", default= "Orange", help= "%s (default: %%(default)s)" % gettext("Bold text color"))
    parser.add_argument("--bold-background", "-bb", type= colorString, action= "store", default= "CornSilk", help= "%s (default: %%(default)s)" % gettext("Bold background color"))
    parser.add_argument("--italic-color", "-ic", type= colorString, action= "store", default= "DarkCyan", help= "%s (default: %%(default)s)" % gettext("Italic text color"))
    parser.add_argument("--italic-background", "-ib", type= colorString, action= "store", default= "CornSilk", help= "%s (default: %%(default)s)" % gettext("Italic background color"))
    parser.add_argument("--envar-color", "-vc", type= colorString, action= "store", default= "DarkMagenta", help= "%s (default: %%(default)s)" % gettext("Environment variable text color"))
    parser.add_argument("--envar-background", "-vb", type= colorString, action= "store", default= "CornSilk", help= "%s (default: %%(default)s)" % gettext("Environment variable background color"))
    parser.add_argument("--version", "-V", action= "version", version= "%s v%s" % (PROJECT_NAME, PROJECT_VERSION))
    return parser.parse_known_args()

def parsePages(extra):
    if type(extra) == type(list()):
        extra= ' '.join(map(str, extra))
    extra= compile(r"(\d(?:\S+)? \S+|\S+)", DOTALL).findall(extra.replace("\"", "").replace("'", "").replace("`", ""))
    for i, page in enumerate(extra):
        if "(" in page:
            extra[i]= sub(r"(.+)\((.+)\)", r"\2 \1", page)
    return [ x for x in extra if x != "" and not x.startswith("-") ]

if __name__ == "__main__":
    namespace, extra= parsing()
    app= QApplication(extra)
    ui= ManPagesDialog()
    if int(namespace.random_page):
        ui.manpages.openPage(None, int(namespace.random_page))
    ui.manpages.openPage(parsePages(extra), False)
    ui.show()
    if not namespace.disable_proposal:
        ui.pagesOther.setFixedWidth(ui.pagesList.width())
    exit(app.exec_())
