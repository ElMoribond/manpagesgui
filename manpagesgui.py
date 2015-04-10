#!/bin/env python3
# -*- coding: utf-8 -*-

# manpagesgui v1.21 - GUI manual pager
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
from os import access, F_OK, path, sep, W_OK
from random import randrange
from re import compile, DOTALL, findall, IGNORECASE, match, MULTILINE, sub
from shutil import which
from subprocess import DEVNULL, PIPE, Popen
from textwrap import dedent
from PyQt5.QtCore import QBuffer, QByteArray, QSettings, Qt, QUrl
from PyQt5.QtGui import QCursor, QDesktopServices, QIcon, QPixmap
from PyQt5.QtWidgets import QAbstractItemView, QAction, QApplication, QButtonGroup, QCheckBox, QComboBox, QDialog, QGroupBox, QGridLayout, QHBoxLayout, QLabel, QLayout, QLineEdit, QMenu, QMessageBox, QPushButton, QRadioButton, QSizePolicy, QStyle, QTableWidget, QTableWidgetItem, QTextBrowser, QVBoxLayout, QWidget
from PyQt5.QtWebKitWidgets import QWebPage, QWebView
try:
    from lxml import etree as ET
except:
    LXML= False
else:
    LXML= True

PROJECT_NAME= "manPagesGui"
PROJECT_VERSION= "1.2.1"
PROJECT_RELEASE_DATE= "2015-04-10"
PROJECT_TEAM= "ElMoribond"
PROJECT_EMAIL= "elmoribond@gmail.com"
PROJECT_URL= "https://github.com/ElMoribond/manpagesgui"

bindtextdomain(PROJECT_NAME.lower(), path.join(path.dirname(path.realpath(__file__)), "i18n"))
textdomain(PROJECT_NAME.lower())

class MDialog(QDialog):

    def __init__(self, title):
        super().__init__(ManPagesGUI.self)
        self.setWindowTitle(title)
        self.rejected.connect(self.close)

    def exec_(self):
        ManPagesGUI.self.buttonExtra.setFocus()
        super().open()

    def closeEvent(self, event):
        ManPagesGUI.self.command.setFocus()
        super().closeEvent(event)

class Dialog(MDialog):

    def __init__(self, title):
        super().__init__(title)
        buttons= QWidget()
        self.layoutButton, self.buttonCancel, self.buttonValidate, self.layout= QHBoxLayout(buttons), QPushButton(gettext("Cancel")), QPushButton(gettext("OK")), QVBoxLayout(self)
        self.layoutButton.addStretch(1)
        self.buttonCancel.clicked.connect(self.close)
        self.layoutButton.addWidget(self.buttonCancel)
        self.layoutButton.addWidget(self.buttonValidate)
        self.layout.addWidget(buttons)
        self.layout.setSizeConstraint(QLayout.SetFixedSize)

class MLabel(QLabel):

    def enterEvent(self, event):
        QApplication.setOverrideCursor(QCursor(Qt.PointingHandCursor))
        super().enterEvent(event)

    def leaveEvent(self, event):
        QApplication.restoreOverrideCursor()
        super().leaveEvent(event)

class ManPagesGUI(QDialog):
    POPEN, DEFAULTSECTION, ALLSECTIONS, CONTENTSECTION, FINDSHORT, FINDFULL, FINDREGEX= range(0, 7)
    OpenBox, resultDialog, manpagesHover, pagesError, pages, manScheme, rawScheme= 0, None, False, list(), list(), "manpage", "raw"
    randomPage, errorOccurred, notFound= gettext("Random Page"), gettext("An error occurred"), gettext("Not Found")

    class AboutDialog(MDialog):

        class Label(MLabel):

            def __init__(self):
                super().__init__()
                self.setPixmap(QPixmap(path.join(path.dirname(path.realpath(__file__)), "png", "gplv3-127x51.png")))

            def mousePressEvent(self, event):
                if event.button() == Qt.LeftButton:
                    QDesktopServices.openUrl(QUrl("http://www.gnu.org/licenses/quick-guide-gplv3.html"))

        # Init de AboutDialog
        def __init__(self):
            super().__init__("%s %s" % (ManPagesGUI.self.about, PROJECT_NAME))
            logo, butttonClose, layout, sty= QLabel(), QPushButton(self.style().standardIcon(QStyle.SP_DialogCloseButton), ""), QGridLayout(self), "" if namespace.theme_color else "style='color: %s'" % namespace.link_color
            logo.setPixmap(ManPagesGUI.logo)
            email= QLabel("%s <a href='mailto:%s?subject=[%s]' %s>%s</a>" % (gettext("Lost in French countryside but reachable"), PROJECT_EMAIL, PROJECT_NAME, sty, PROJECT_EMAIL))
            email.setOpenExternalLinks(True)
            url= QLabel("<br /><a href='%s' %s>%s</a><br />" % (PROJECT_URL, sty, PROJECT_URL))
            url.setOpenExternalLinks(True)
            butttonClose.clicked.connect(self.close)
            layout.addWidget(logo, 0, 0, 4, 1)
            layout.addWidget(QLabel("%s v%s %s %s" % (PROJECT_NAME, PROJECT_VERSION, gettext("released on"), PROJECT_RELEASE_DATE)), 0, 1, 1, 2)
            layout.addWidget(QLabel("%s %s" % (gettext("Created by"), PROJECT_TEAM)), 1, 1, 1, 2)
            layout.addWidget(email, 2, 1, 1, 2)
            layout.addWidget(QLabel(gettext("Released under GNU GPLv3 license")), 3, 1)
            layout.addWidget(self.Label(), 3, 2, 2, 1, Qt.AlignTop|Qt.AlignRight)
            layout.addWidget(QLabel("\nCopyright © 2015 %s (Michael Herpin). %s.\n%s.\n%s." % (PROJECT_TEAM, gettext("All rights reserved"), gettext("This program comes with ABSOLUTELY NO WARRANTY"), gettext("This is free software, and you are welcome to redistribute it under certain conditions"))), 4, 0, 1, 3)
            layout.addWidget(url, 5, 0, 1, 3)
            layout.addWidget(butttonClose, 6, 0, 1, 3)
            layout.setSizeConstraint(QLayout.SetFixedSize)

    class EditZone(QLineEdit):

        class Label(MLabel):

            def __init__(self, parent):
                super().__init__(parent)
                icon= self.style().standardIcon(QStyle.SP_MessageBoxWarning) if QIcon.fromTheme("dialog-warning").isNull() else QIcon.fromTheme("dialog-warning")
                self.setPixmap(icon.pixmap(parent.minimumSizeHint().height(), parent.minimumSizeHint().height(), QIcon.Normal, QIcon.On))
                self.setVisible(False)
        
        # Init de EditZone
        def __init__(self):
            super().__init__()
            self.setContextMenuPolicy(Qt.CustomContextMenu)
            self.customContextMenuRequested.connect(self.openContextMenu)
            self.info= self.Label(self)

        def focusOutEvent(self, event):
            if ManPagesGUI.self.buttonExtra.hasFocus():
                super().focusOutEvent(event)
            else:
                self.setFocus()

        def resizeEvent(self, event):
            self.ensurePolished()
            self.info.setGeometry(self.rect().right() - self.minimumSizeHint().height(), (self.rect().height() - self.minimumSizeHint().height()) / 2, self.minimumSizeHint().height(), self.minimumSizeHint().height())
            if not namespace.no_proposal:
                ui.pagesOther.setFixedWidth(self.width())
            super().resizeEvent(event)

        def keyPressEvent(self, event):
            if not ManPagesGUI.manpagesHover or not ManPagesGUI.self.manpages.pressedKey(event):
                super().keyPressEvent(event)

        def openContextMenu(self, point):
            contextMenu= self.createStandardContextMenu()
            contextMenu.addSeparator()
            contextMenu.addAction(QAction(ManPagesGUI.randomPage, self, triggered= partial(ManPagesGUI.self.manpages.openPage, None, 1)))
            contextMenu.exec_(self.mapToGlobal(point))

    class ManPageZone(QWebView):

        def __init__(self):
            super().__init__()
            self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
            self.setContextMenuPolicy(Qt.CustomContextMenu)
            self.customContextMenuRequested.connect(self.openContextMenu)
            self.page().setLinkDelegationPolicy(QWebPage.DelegateAllLinks)
            self.linkClicked.connect(self.openPage)
            ManPagesGUI.self.command.returnPressed.connect(partial(self.openPage, ManPagesGUI.self.command))
            ManPagesGUI.self.pagesList.currentIndexChanged[int].connect(partial(self.openPage, -2))
            if not namespace.no_proposal:
                ManPagesGUI.self.pagesOther.currentIndexChanged[int].connect(partial(self.openPage, -3))
            ManPagesGUI.self.buttonPrevious.clicked.connect(partial(self.openPage, False))
            ManPagesGUI.self.buttonNext.clicked.connect(partial(self.openPage, True))
            self.raw, ba, img= False, QByteArray(), self.style().standardIcon(QStyle.SP_MessageBoxWarning)
            img.pixmap(48, 48, QIcon.Normal, QIcon.On).save(QBuffer(ba), "PNG")
            self.css= "%s%s" % ("" if namespace.theme_color else """
                body { color: """ + namespace.color + """; background-color: """ + namespace.background + """ }
                a:link { color: """ + namespace.link_color + """; background-color: """ + namespace.link_background + """ }
                h2 { color: """ + namespace.section_color + """; background-color: """ + namespace.section_background + """}
                envar { color: """ + namespace.envar_color + """; background-color: """ + namespace.envar_background + """}
                b { color: """ + namespace.bold_color + """; background-color: """ + namespace.bold_background + """}
                i { color: """ + namespace.italic_color + """; background-color: """ + namespace.italic_background + """}
                table.add { border-collapse: collapse; margin: 1em auto; }
                td.add, th.add { border: 1px solid """ + namespace.color + """; padding: 3px; }\n""", """
                .rawlink { height: 48px; width: 48px; background-image: url(data:image/png;base64,""" + str(ba.toBase64(), encoding= "utf8") + """); }
                p, pre, table { margin-top: 0; margin-bottom: 0; vertical-align: top }""")

        def enterEvent(self, event):
            ManPagesGUI.manpagesHover= True
            super().enterEvent(event)

        def leaveEvent(self, event):
            ManPagesGUI.manpagesHover= False
            super().leaveEvent(event)

        def mousePressEvent(self, event):
            if event.button() == Qt.BackButton and ManPagesGUI.self.buttonPrevious.isEnabled():
                ManPagesGUI.self.buttonPrevious.click()
            elif event.button() == Qt.ForwardButton and ManPagesGUI.self.buttonNext.isEnabled():
                ManPagesGUI.self.buttonNext.click()
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
                contextMenu.actions()[0].triggered.connect(partial(app.clipboard().setText, self.selectedText().replace("−", "-")))
            elif self.anchorAt(point):
                contextMenu.actions()[1].setEnabled(True)
                contextMenu.actions()[1].triggered.connect(partial(app.clipboard().setText, self.anchorAt(point)))
            contextMenu.addSeparator()
            contextMenu.addAction(QAction(ManPagesGUI.randomPage, self, triggered= partial(self.openPage, None, 1)))
            contextMenu.exec_(self.mapToGlobal(point))

        def anchorAt(self, pos):
            if self.page().currentFrame().hitTestContent(pos).linkUrl().scheme() in [ "ftp", "http", "https", "mailto" ]:
                return self.page().currentFrame().hitTestContent(pos).linkUrl().toString().replace("−", "-")
            return False

        def openPage(self, page, option= True):
            QApplication.setOverrideCursor(QCursor(Qt.BusyCursor))
            if page is None:
                page= 0
                if not len(ManPagesGUI.pages):
                    if namespace.man_directory:
                        dir= namespace.man_directory
                    else:
                        dir= self.man("manpath", ManPagesGUI.POPEN)
                        dir= dir[1].rstrip() if dir[0] == 0 else path.join(sep, "usr", "share", "man")
                    for fn in glob(path.join(dir, "man?", "*.gz")):
                        ManPagesGUI.pages.append(sub(r"(.+)\.([^.]+)\.gz", r"\2 \1", path.basename(fn)))
                while page < option:
                    x= randrange(0, len(ManPagesGUI.pages) - 1)
                    if ManPagesGUI.self.pagesList.findText(ManPagesGUI.pages[x], Qt.MatchFixedString) == -1:
                        self.openPage(ManPagesGUI.pages[x], False)
                        page+= 1
            elif type(page) == type(bool()):
                if self.raw and not page:
                    self.openPage(ManPagesGUI.self.pagesList.currentIndex())
                else:
                    self.openPage(ManPagesGUI.self.pagesList.currentIndex() + 1 if page else ManPagesGUI.self.pagesList.currentIndex() - 1, option)
                self.raw= False
            elif type(page) == type(int()):
                if page == -3:
                    self.openPage(ManPagesGUI.self.pagesOther.currentText())
                elif page == -2:
                    self.openPage(ManPagesGUI.self.pagesList.currentIndex())
                elif page > -1:
                    ManPagesGUI.self.setWindowTitle("%s: %s" % (PROJECT_NAME, ManPagesGUI.self.pagesList.itemText(page)))
                    ManPagesGUI.self.pagesList.currentIndexChanged[int].disconnect()
                    ManPagesGUI.self.pagesList.setCurrentIndex(page)
                    ManPagesGUI.self.pagesList.currentIndexChanged[int].connect(partial(self.openPage, -2))
                    self.setHtml(self.applyStyle(ManPagesGUI.self.pagesList.itemData(page)[0][0]))
                    ManPagesGUI.self.buttonPrevious.setEnabled(True if ManPagesGUI.self.pagesList.currentIndex() > 0 else False)
                    ManPagesGUI.self.buttonNext.setEnabled(True if ManPagesGUI.self.pagesList.currentIndex() < ManPagesGUI.self.pagesList.count() - 1 else False)
                    if not namespace.no_proposal:
                        ManPagesGUI.self.pagesOther.currentIndexChanged[int].disconnect()
                        ManPagesGUI.self.pagesOther.clear()
                        if len(ManPagesGUI.self.pagesList.itemData(page)[1]) > 1:
                            ManPagesGUI.self.pagesOther.setEnabled(True)
                        else:
                            ManPagesGUI.self.pagesOther.setEnabled(False)
                        for x, item in enumerate(ManPagesGUI.self.pagesList.itemData(page)[1]):
                            ManPagesGUI.self.pagesOther.addItem(item)
                            if item == ManPagesGUI.self.pagesList.currentText():
                                ManPagesGUI.self.pagesOther.setCurrentIndex(x)
                        ManPagesGUI.self.pagesOther.currentIndexChanged[int].connect(partial(self.openPage, -3))
            elif type(page) == type(list()):
                for x in page:
                    self.openPage(x, option)
            elif page == ManPagesGUI.self.command:
                pages= page.text()
                page.setText("")
                self.openPage(parsePages(pages), True)
            elif type(page) == type(QUrl()):
                if page.scheme() == ManPagesGUI.manScheme:
                    self.openPage(sub(r"%s:([\S]+)\.(.+)" % ManPagesGUI.manScheme, r"\2 \1", page.toString()))
                elif page.scheme() == ManPagesGUI.rawScheme:
                    self.raw= True
                    ManPagesGUI.self.buttonPrevious.setEnabled(True)
                    self.setHtml(self.applyStyle("<html><head><style type=\"text/css\"></style></head><body><pre>%s</pre></body></html>" % ManPagesGUI.self.pagesList.itemData(ManPagesGUI.self.pagesList.currentIndex())[0][1][1]))
                else:
                    QDesktopServices.openUrl(QUrl(page.toString().replace("−", "-")))
            else:
                default= self.man(parsePages(page)[0], ManPagesGUI.DEFAULTSECTION)
                if type(default[0]) != type(str()):
                    if default[0] == -1:
                        self.addError("%s: %s" % (parsePages(page)[0], ManPagesGUI.notFound), option)
                    else:
                        self.addError("%s: %s" % (page, ManPagesGUI.errorOccurred), option)
                else:
                    if ManPagesGUI.self.pagesList.findText(default[0], Qt.MatchFixedString) > -1:
                        if option:
                            self.openPage(ManPagesGUI.self.pagesList.findText(default[0], Qt.MatchFixedString), option)
                    else:
                        sections, source= self.man(parsePages(page)[0], ManPagesGUI.ALLSECTIONS), self.man(parsePages(page)[0], ManPagesGUI.CONTENTSECTION)
                        if type(source[0]) == type(sections[0]) == type(str()):
                            ManPagesGUI.self.pagesList.currentIndexChanged[int].disconnect()
                            ManPagesGUI.self.pagesList.addItem(default[0], [ source, sections ])
                            ManPagesGUI.self.pagesList.currentIndexChanged[int].connect(partial(self.openPage, -2))
                            self.openPage(ManPagesGUI.self.pagesList.count() - 1, option)
                        else:
                            self.addError("%s: %s" % (page, ManPagesGUI.errorOccurred), option)
            QApplication.restoreOverrideCursor()

        def man(self, page, option, Tout= 20):
            cmd= "%s -D%s%s" % (namespace.man_command, " -M%s" % namespace.man_directory if namespace.man_directory else "", " -Len" if namespace.no_locale else "")
            if option in [ ManPagesGUI.DEFAULTSECTION, ManPagesGUI.FINDFULL, ManPagesGUI.FINDREGEX|ManPagesGUI.FINDFULL ]:
                fnToP, fnToPr= r"^[\S]+/(\S+)\.(\S+)\.gz$", r"\1(\2)"
            if option == ManPagesGUI.POPEN:
                try:
                    proc= Popen(page, stdout= PIPE, stderr= DEVNULL, universal_newlines= True, bufsize= 1, shell= True)
                except:
                    pass
                else:
                    try:
                        source= proc.communicate(timeout= Tout)[0]
                    except:
                        pass
                    else:
                        return [ proc.returncode, source ]
            elif option == ManPagesGUI.DEFAULTSECTION:
                source= self.man("%s -w %s" % (cmd, page), ManPagesGUI.POPEN)
                if source[0] == 0:
                    return sub(fnToP, fnToPr, source[1]).splitlines()
                elif source[0] == 16:
                    return [ -1 ]
            elif option == ManPagesGUI.ALLSECTIONS:
                source= self.man("%s -f %s" % (cmd, page), ManPagesGUI.POPEN)
                if source[0] == 0:
                    return sub(compile(r"^([\S]+) (\S+).*$", MULTILINE), r"\1\2", source[1]).splitlines()
            elif option == ManPagesGUI.CONTENTSECTION:
                source= self.man("%s -Hcat --nh %s" % (cmd, page), ManPagesGUI.POPEN)
                if source[0] == 0:
                    tab1= findall(r"[\S ]+<img src[\S ]+>", source[1])
                    if len(tab1):
                        s= self.man("%s -Pcat --nh %s" % (cmd, page), ManPagesGUI.POPEN)
                        if s[0] == 0:
                            tab2= findall(r" {7}┌[\S \n]+┘", s[1])
                            if len(tab1) == len(tab2):
                                for x, torep in enumerate(tab1):
                                    source[1]= source[1].replace(torep, self.createTable(tab2[x]))
                            else:
                                source[1]= sub(compile(r"<img src[\S ][^>]+>", DOTALL), r"<a href='%s://currentpage'><img class='rawlink' src='' /></a>" % ManPagesGUI.rawScheme, source[1])
                    else:
                        s= None
                    source[1]= sub(r"(\${1}[A-Z_.]+)", r"<envar>\1</envar>", sub(compile(r"<b>([_A-Z.0-9-]+)</b>\((\d+[A-Z]*)\)", DOTALL|IGNORECASE), r"<a href='%s:\1.\2'>\1(\2)</a>" % ManPagesGUI.manScheme, sub(r"(<style type=\"text/css\">)[\S \n]*(</style>)", r"\1\2", sub(compile(r"(\n<a name.+?(?=\n)\n)", DOTALL), r"", sub(r"^[\S \n]+(<style)", r"<html><head><meta charset='utf-8'>\1", sub(r"(?<=<body>)[\S \n]+?(?=<h2>)", r"\n", source[1]))))))
                    if not namespace.no_url_link:
                        source[1]= sub(compile(r"(https?://[\dA-Z\.-]+\.[A-Z\.-]{2,6}[\/\w&\-\.−\-;]*)/?(?<!\.)", MULTILINE|DOTALL|IGNORECASE), r"<a href='\1'>\1</a>", source[1])
                    if not namespace.no_email_link:
                        source[1]= sub(compile(r"([_A-Z0-9.+-]+@[_A-Z0-9-]+\.[A-Z0-9-.]+)", DOTALL|IGNORECASE), r"<a href='mailto://\1'>\1</a>", source[1])
                    return [ source[1].replace("<hr>", "").replace("\n\n\n", "\n").replace("\n\n", "\n"), s ]
            elif option in [ ManPagesGUI.FINDSHORT, ManPagesGUI.FINDFULL, ManPagesGUI.FINDREGEX|ManPagesGUI.FINDSHORT, ManPagesGUI.FINDREGEX|ManPagesGUI.FINDFULL ]:
                addOption, Tout= [ "k", 25 ] if option in [ ManPagesGUI.FINDSHORT, ManPagesGUI.FINDREGEX|ManPagesGUI.FINDSHORT ] else [ "K -w", 60 * 2 ]
                if option in [ ManPagesGUI.FINDREGEX|ManPagesGUI.FINDSHORT, ManPagesGUI.FINDREGEX|ManPagesGUI.FINDFULL ]:
                    addOption, Tout= "%s --regex" % addOption, Tout * 2
                source= self.man("%s -%s \"%s\"" % (cmd, addOption, page), ManPagesGUI.POPEN, Tout)
                if source[0] == 0:
                    if option in [ ManPagesGUI.FINDSHORT, ManPagesGUI.FINDREGEX|ManPagesGUI.FINDSHORT ]:
                        return source[1].splitlines()
                    else:
                        return sub(compile(fnToP, MULTILINE|DOTALL), fnToPr, source[1]).splitlines()
                    return [ source[1] ]
                elif source[0] == 16:
                    return [ -1 ]
            return [ -2 ]

        def addError(self, error, option):
            if option:
                QApplication.restoreOverrideCursor()
                QApplication.setOverrideCursor(QCursor(Qt.ArrowCursor))
                ManPagesGUI.self.setWindowTitle(PROJECT_NAME)
                QMessageBox.warning(ManPagesGUI.self, "\0", error, QMessageBox.Ok)
            if not error in ManPagesGUI.pagesError:
                ManPagesGUI.pagesError.append(error)
            ManPagesGUI.self.command.info.setToolTip("\n".join(map(str, ManPagesGUI.pagesError)))
            ManPagesGUI.self.command.info.setVisible(True)
            ManPagesGUI.self.command.setTextMargins(0, 0, ManPagesGUI.self.command.info.minimumSizeHint().height(), 0)

        def createTable(self, raw, tab= ""):
            for i, line in enumerate(raw.splitlines()):
                if line.strip().startswith("┌"):
                    tab= "<table class='add'>"
                elif line.strip().startswith("│"):
                    tab= "%s<tr>" % tab
                    for cell in line.split("│"):
                        if len(cell.strip()):
                            tab= "%s%s%s%s" % (tab, "<th class='add'>" if i == 1 else "<td class='add'>", cell.strip(), "</th>" if i == 1 else "</td>")
                    tab= "%s</tr>" % tab
                elif line.strip().startswith("└"):
                    tab= "%s</table>" % tab
            return tab

        def applyStyle(self, html):
            return sub(r"(<style type=\"text/css\">)(</style>)", r"\1%s\2" % dedent(self.css), html)

    class TextSearchDialog(Dialog):

        class ResultDialog(Dialog):

            class TableWidget(QTableWidget):

                def __init__(self, source, header, w= 0):
                    super().__init__()
                    self.setSortingEnabled(True)
                    self.sortByColumn(0, Qt.AscendingOrder)
                    self.verticalHeader().setVisible(False)
                    self.setSelectionMode(QAbstractItemView.MultiSelection)
                    self.setSelectionBehavior(QAbstractItemView.SelectRows)
                    self.setColumnCount(len(header))
                    self.setHorizontalHeaderLabels(header)
                    self.setRowCount(len(source))
                    self.selectionModel().selectionChanged.connect(self.actualizeButton)
                    if len(header) > 1:
                        for i, item in enumerate(source):
                            self.setItem(i, 0, QTableWidgetItem(item[0].replace(" (", "(")))
                            self.setItem(i, 1, QTableWidgetItem(item[1]))
                    else:
                        for i, item in enumerate(source):
                            self.setItem(i, 0, QTableWidgetItem(item))
                    self.resizeColumnsToContents()
                    self.resizeRowsToContents()
                    for i in range(len(header)):
                        w+= self.columnWidth(i)
                    self.setMinimumWidth(w)

                def mouseDoubleClickEvent(self, event):
                    pass

            # Init de ResultDialog
            def __init__(self, title, source, header):
                super().__init__(title)
                self.setContextMenuPolicy(Qt.CustomContextMenu)
                self.customContextMenuRequested.connect(self.openContextMenu)
                self.buttonValidate.clicked.connect(self.openpages)
                self.table= self.TableWidget(source, header)
                self.actualizeButton()
                self.layout.insertWidget(0, self.table)

            def actualizeButton(self):
                self.buttonValidate.setEnabled(True if len(self.table.selectionModel().selectedRows()) else False)

            def openContextMenu(self, point):
                contextMenu= QMenu()
                contextMenu.addAction(QAction(gettext("Select All"), self, triggered= self.table.selectAll))
                contextMenu.addAction(QAction(gettext("Unselect All"), self, triggered= self.table.clearSelection))
                contextMenu.exec_(self.mapToGlobal(point))

            def openpages(self):
                for item in self.table.selectionModel().selectedRows():
                    ManPagesGUI.self.manpages.openPage(self.table.item(item.row(), 0).text(), False)

        # Init de TextSearchDialog
        def __init__(self):
            super().__init__(ManPagesGUI.self.textSearch)
            self.edit, self.name, self.description, self.content, self.searchIn, self.regexString= QLineEdit(self), gettext("Name's page"), gettext("Description"), gettext("Content page"), gettext("Search in"), gettext("Regex string")
            self.edit.setMaxLength(64)
            radioButtons, zButtons, self.r0, self.r1, self.r2= QButtonGroup(self), QGroupBox(self.searchIn), QRadioButton(self.name), QRadioButton(self.description), QRadioButton(self.content)
            self.r0.setChecked(True)
            zButtons.setStyleSheet("QGroupBox { border: 1px solid gray; margin-top: 0.5em; } QGroupBox::title { subcontrol-origin: margin; left: 10px; padding: 0 3px 0 3px; }")
            layoutButtons, self.regex= QHBoxLayout(zButtons), QCheckBox(self.regexString)
            for item in [ self.r0, self.r1, self.r2 ]:
                radioButtons.addButton(item)
                layoutButtons.addWidget(item)
            self.edit.returnPressed.connect(self.buttonValidate.click)
            self.buttonValidate.clicked.connect(self.launchSearch)
            self.layout.insertWidget(0, self.edit)
            self.layout.insertWidget(1, self.regex)
            self.layout.insertWidget(2, zButtons)
            self.edit.setFocus()

        def launchSearch(self):
            QApplication.setOverrideCursor(QCursor(Qt.BusyCursor))
            source= ManPagesGUI.self.manpages.man(self.edit.text(), ManPagesGUI.FINDREGEX if self.regex.isChecked() else 0 | ManPagesGUI.FINDSHORT if self.r0.isChecked() or self.r1.isChecked() else ManPagesGUI.FINDFULL)
            QApplication.restoreOverrideCursor()
            if type(source[0]) == type(str()):
                if self.r2.isChecked():
                    title, source, header= self.content, list(set(source)), [ self.name ]
                else:
                    fl= list()
                    for line in source:
                        line= sub(r"([\S ]+)\) +- ([\S ]+)", r"\1)#\2", line).split("#")
                        if self.regex.isChecked() and findall(r"%s" % self.edit.text(), line[0 if self.r0.isChecked() else 1], IGNORECASE) or not self.regex.isChecked() and self.edit.text() in line[0 if self.r0.isChecked() else 1]:
                            fl.append(line)
                    title, source, header= self.name if self.r0.isChecked() else self.description, fl, [ self.name, self.description ]
                if len(source):
                    self.close()
                    ManPagesGUI.resultDialog= self.ResultDialog("%s: %s(%d)" % (self.searchIn, title, len(source)), source, header)
                    ManPagesGUI.resultDialog.show()
                else:
                    QMessageBox.critical(ManPagesGUI.self, "\0", ManPagesGUI.notFound, QMessageBox.Ok)
            else:
                QMessageBox.critical(ManPagesGUI.self, "\0", ManPagesGUI.notFound if source[0] == -1 else ManPagesGUI.errorOccurred, QMessageBox.Ok)

    class KeyBindingDialog(Dialog):

        class LineEdit(QLineEdit):

            def __init__(self, dialog):
                super().__init__()
                self.dialog, self.key, self.keyF, self.controlMod, self.altMod, self.shiftMod= dialog, range(Qt.Key_A, Qt.Key_Z), range(Qt.Key_F1, Qt.Key_F35), gettext("Control"), gettext("Alt"), gettext("Shift")

            def keyPressEvent(self, event, text= ""):
                if event.modifiers() == Qt.ControlModifier:
                    text= "%s + " % self.controlMod
                elif event.modifiers() == Qt.AltModifier:
                    text= "%s + " % self.altMod
                elif event.modifiers() == Qt.ShiftModifier:
                    text= "%s + " % self.shiftMod
                elif event.modifiers() == Qt.ControlModifier|Qt.AltModifier:
                    text= "%s + %s + " % (self.controlMod, self.altMod)
                elif event.modifiers() == Qt.ControlModifier|Qt.ShiftModifier:
                    text= "%s + %s + " % (self.controlMod, self.shiftMod)
                elif event.modifiers() == Qt.AltModifier|Qt.ShiftModifier:
                    text= "%s + %s + " % (self.altMod, self.shiftMod)
                elif event.modifiers() == Qt.ControlModifier|Qt.AltModifier|Qt.ShiftModifier:
                    text= "%s + %s + %s + " % (self.controlMod, self.altMod, self.shiftMod)
                if event.key() in self.keyF:
                    text= "%sF%d" % (text, self.keyF.index(event.key() + 1))
                elif event.key() == Qt.Key_Escape:
                    self.dialog.close()
                if len(text) and event.key() in self.key:
                    text= "%s%s" % (text, chr(event.key()))
                self.setText(text)

            def setText(self, text):
                self.dialog.buttonValidate.setEnabled(True if text is not None and not text.endswith("+ ") and not self.dialog.isKey(text) or text is None and self.dialog.getsetCommand() is not None else False)
                super().setText(text)

        # Init de KeyBindingDialog
        def __init__(self, i, fn):
            super().__init__(ManPagesGUI.self.keyBinding)
            self.wm, self.file, self.edit, self.command= i, fn, self.LineEdit(self), QLineEdit()
            self.command.setMaxLength(48)
            self.buttonValidate.clicked.connect(partial(self.getsetCommand, self.edit, None))
            self.layout.insertWidget(0, QLabel("%s?\n%s.\n" % (gettext("What key combination you want to use"), gettext("Valid without keybinding for remove"))))
            self.layout.insertWidget(1, self.edit)
            self.layout.insertWidget(2, QLabel("%s:\n" % gettext("Command line options")))
            self.layout.insertWidget(3, self.command)
            self.edit.setFocus()

        def exec_(self):
            if self.wm == ManPagesGUI.OpenBox:
                try:
                    self.tree= ET.parse(self.file)
                    self.string= sub(r"(\{\S+\})\S+", r"\1", self.tree.getroot().tag)
                    self.keyboard= self.tree.getroot().find("%skeyboard" % self.string)
                except:
                    QMessageBox.critical(ManPagesGUI.self, "\0", "%s\n(%s)" % (gettext("Processing error"), self.file), QMessageBox.Ok)
                else:
                    if len(self.keyboard):
                        self.edit.setText(self.getsetCommand())
                    super().exec_()

        def getsetCommand(self, key= None, current= None):
            if self.wm == ManPagesGUI.OpenBox:
                if key:
                    key= key.text().replace("%s + " % self.edit.controlMod, "C-").replace("%s + " % self.edit.altMod, "A-").replace("%s + " % self.edit.shiftMod, "S-")
                for c in self.keyboard:
                    action= c.find("%saction" % self.string)
                    if action is not None and len(action):
                        for i in list(action):
                            if i.text and match(r"^%scommand$" % self.string, i.tag) and path.basename(i.text.split()[0]) == PROJECT_NAME.lower():
                                if key:
                                    if len(key):
                                        c.set("key", key)
                                        i.text= "%s %s" % (PROJECT_NAME.lower(), self.command.text().strip())
                                    current= c
                                    break
                                else:
                                    self.command.setText(i.text.replace("%s " % PROJECT_NAME.lower(), ""))
                                    return c.get("key").replace("C-", "%s + " % self.edit.controlMod).replace("A-", "%s + " % self.edit.altMod).replace("S-", "%s + " % self.edit.shiftMod)
                if key:
                    if current is not None:
                        if not len(key):
                            self.keyboard.remove(current)
                    elif len(key):
                        keybind= ET.Element('keybind')
                        keybind.set("key", key)
                        action= ET.SubElement(keybind, "action")
                        action.set("name", "Execute")
                        command= ET.SubElement(action, "command")
                        command.text= "%s %s" % (PROJECT_NAME.lower(), self.command.text().strip())
                        self.keyboard.append(keybind)
                    else:
                        return
                    self.tree.write(self.file)
                    ManPagesGUI.self.manpages.man("openbox --reconfigure", ManPagesGUI.POPEN)
                    self.close()

        def isKey(self, key):
            if self.wm == ManPagesGUI.OpenBox:
                key= key.replace("%s + " % self.edit.controlMod, "C-|").replace("%s + " % self.edit.altMod, "A-|").replace("%s + " % self.edit.shiftMod, "S-|").split("|")
                for c in self.keyboard:
                    if c.get("key") and set(c.get("key").replace("C-", "C-|").replace("A-", "A-|").replace("S-", "S-|").split("|")) == set(key):
                        return True
            return False

    class Menu(QMenu):

        def __init__(self, parent):
            super().__init__()
            AkeyBinding, Aabout, AtextSearch= None, QAction(parent.about, self, triggered= parent.AboutDialog().exec_), QAction(parent.textSearch, self, triggered= parent.TextSearchDialog().exec_)
            for i, fn in enumerate([ path.join(path.expanduser("~"), ".config", "openbox", "lxde-rc.xml") ]):
                if access(fn, F_OK|W_OK):
                    if i == ManPagesGUI.OpenBox and LXML:
                        AkeyBinding= QAction(parent.keyBinding, self, triggered= parent.KeyBindingDialog(i, fn).exec_)
                    break
            if AkeyBinding is None:
                AkeyBinding= QAction(parent.keyBinding, self)
                AkeyBinding.setEnabled(False)
            self.addAction(Aabout)
            self.addAction(AtextSearch)
            self.addAction(AkeyBinding)

        def closeEvent(self, event):
            ManPagesGUI.self.command.setFocus()
            super().closeEvent(event)

    # Init de ManPagesGUI
    def __init__(self):
        super().__init__()
        ManPagesGUI.self, ManPagesGUI.logo= self, QPixmap(path.join(path.dirname(path.realpath(__file__)), "png", "%s.png" % PROJECT_NAME.lower()))
        self.setWindowIcon(QIcon(ManPagesGUI.logo))
        self.setWindowTitle(PROJECT_NAME)
        self.rejected.connect(self.close)
        if QIcon.fromTheme("go-previous").isNull() or QIcon.fromTheme("go-next").isNull() or QIcon.fromTheme("application-exit").isNull():
            buttonQuit, self.buttonPrevious, self.buttonNext= QPushButton(self.style().standardIcon(QStyle.SP_DialogCloseButton), ""), QPushButton(self.style().standardIcon(QStyle.SP_ArrowLeft), ""), QPushButton(self.style().standardIcon(QStyle.SP_ArrowRight), "")
        else:
            buttonQuit, self.buttonPrevious, self.buttonNext= QPushButton(QIcon.fromTheme("application-exit"), ""), QPushButton(QIcon.fromTheme("go-previous"), ""), QPushButton(QIcon.fromTheme("go-next"), "")
        self.buttonPrevious.setEnabled(False)
        self.buttonNext.setEnabled(False)
        self.command, self.pagesList, self.buttonExtra= self.EditZone(), QComboBox(), QPushButton(QIcon(ManPagesGUI.logo), "")
        self.buttonExtra.setIconSize(self.buttonNext.iconSize())
        for b in [ self.buttonPrevious, self.buttonNext, self.buttonExtra, buttonQuit ]:
            b.setAutoDefault(False)
        box1, box2, self.about, self.keyBinding, self.textSearch= QWidget(), QWidget(), gettext("About"), gettext("Keybinding"), gettext("Text search")
        layoutBox1, layoutBox2= QHBoxLayout(box1), QHBoxLayout(box2)
        layoutBox1.addWidget(self.buttonPrevious)
        layoutBox1.addWidget(self.buttonNext)
        layoutBox1.addWidget(self.command)
        layoutBox1.addWidget(self.pagesList)
        layoutBox1.addWidget(self.buttonExtra)
        layoutBox1.setContentsMargins(0, 0, 0, 0)
        layoutBox1.setStretchFactor(self.pagesList, 1)
        layoutBox1.setStretchFactor(self.command, 1)
        buttonQuit.clicked.connect(self.close)
        if not namespace.no_proposal:
            self.pagesOther= QComboBox()
            layoutBox2.addWidget(self.pagesOther)
        layoutBox2.addWidget(buttonQuit)
        layoutBox2.setContentsMargins(0, 0, 0, 0)
        layout, self.settings, self.manpages, self.menu= QVBoxLayout(self), QSettings(PROJECT_TEAM, PROJECT_NAME), self.ManPageZone(), self.Menu(self)
        self.buttonExtra.setMenu(self.menu)
        if namespace.no_resize:
            layoutBox1.setStretchFactor(self.command, 1)
            self.manpages.setFixedSize(self.fontMetrics().boundingRect("X").width() * int(namespace.cols), self.fontMetrics().boundingRect("X").height() * int(namespace.rows))
            layout.setSizeConstraint(QLayout.SetFixedSize)
            if self.settings.contains("position"):
                self.move(self.settings.value("position"))
        elif self.settings.value("geometry", False):
            self.restoreGeometry(self.settings.value("geometry"))
        layout.addWidget(box1)
        layout.addWidget(self.manpages)
        layout.addWidget(box2)

    def closeEvent(self, event):
        if ManPagesGUI.resultDialog:
            ManPagesGUI.resultDialog.close()
        self.settings.setValue("position", self.pos())
        self.settings.setValue("geometry", self.saveGeometry())
        self.settings.sync()
        app.quit()

def invalidArgument(value, text= None):
    raise ArgumentTypeError("'%s' %s" % (value, text if text else gettext("is not valid argument")))

def directory(value):
    return value if path.isdir(value) else invalidArgument(value, gettext("directory not found"))

def command(value):
    return value if which(value) else invalidArgument(value, gettext("command not found"))

def checkInteger(value, min, max):
    return value if value.isdigit() and int(value) >= min and int(value) <= max else invalidArgument(value)

def rowsNumber(value):
    return checkInteger(value, 20, 120)

def colsNumber(value):
    return checkInteger(value, 90, 200)

def pagesNumber(value):
    return checkInteger(value, 0, 20)

def colorString(value):
    return value if match(r"^[A-F0-9]{6}$", value, IGNORECASE) or value.lower() in [ "aliceblue", "antiquewhite", "aqua", "aquamarine", "azure", "beige", "bisque", "black", "blanchedalmond", "blue", "blueviolet", "brown", "burlywood", "cadetblue", "chartreuse", "chocolate", "coral", "cornflowerblue", "cornsilk", "crimson", "cyan", "darkblue", "darkcyan", "darkgoldenrod", "darkgray", "darkgreen", "darkkhaki", "darkmagenta", "darkolivegreen", "darkorange", "darkorchid", "darkred", "darksalmon", "darkseagreen", "darkslateblue", "darkslategray", "darkturquoise", "darkviolet", "deeppink", "deepskyblue", "dimgray", "dodgerblue", "firebrick", "floralwhite", "forestgreen", "fuchsia", "gainsboro", "ghostwhite", "gold", "goldenrod", "gray", "green", "greenyellow", "honeydew", "hotpink", "indianred", "indigo", "ivory", "khaki", "lavender", "lavenderblush", "lawngreen", "lemonchiffon", "lightblue", "lightcoral", "lightcyan", "lightgoldenrodyellow", "lightgray", "lightgreen", "lightpink", "lightsalmon", "lightseagreen", "lightskyblue", "lightslategray", "lightsteelblue", "lightyellow", "lime", "limegreen", "linen", "magenta", "maroon", "mediumaquamarine", "mediumblue", "mediumorchid", "mediumpurple", "mediumseagreen", "mediumslateblue", "mediumspringgreen", "mediumturquoise", "mediumvioletred", "midnightblue", "mintcream", "mistyrose", "moccasin", "navajowhite", "navy", "oldlace", "olive", "olivedrab", "orange", "orangered", "orchid", "palegoldenrod", "palegreen", "paleturquoise", "palevioletred", "papayawhip", "peachpuff", "peru", "pink", "plum", "powderblue", "purple", "rebeccapurple", "red", "rosybrown", "royalblue", "saddlebrown", "salmon", "sandybrown", "seagreen", "seashell", "sienna", "silver", "skyblue", "slateblue", "slategray", "snow", "springgreen", "steelblue", "tan", "teal", "thistle", "tomato", "turquoise", "violet", "wheat", "white", "whitesmoke", "yellow", "yellowgreen" ] else invalidArgument(value)

def parsing():
    _num, _col, _def= gettext("number"), gettext("color"), gettext("default")
    parser= ArgumentParser(description= gettext("GUI manual pager"))
    parser.add_argument("--man-command", "-M", type= command, action= "store", default= "man", help= "%s (%s: %%(default)s)" % (gettext("man command"), _def), metavar= gettext("command"))
    parser.add_argument("--man-directory", "-D", type= directory, action= "store", default= False, help= "%s (%s: %%(default)s)" % (gettext("manual pages directory"), _def), metavar= gettext("directory"))
    parser.add_argument("--no-locale", "-nl", action= "store_true", help= gettext("Do not display pages in local language"))
    parser.add_argument("--no-proposal", "-np", action= "store_true", help= gettext("Disables other proposals pages"))
    parser.add_argument("--no-resize", "-nr", action= "store_true", help= gettext("Disable window resizing"))
    parser.add_argument("--random-page", "-p", type= pagesNumber, action= "store", default= "0", help= "%s (%s: %%(default)s)" % (gettext("Number of random pages displayed"), _def), metavar= _num)
    parser.add_argument("--cols", "-C", type= colsNumber, action= "store", default= "92", help= "%s (%s: %%(default)s)" % (gettext("Number of columns displayed"), _def), metavar= _num)
    parser.add_argument("--rows", "-R", type= rowsNumber, action= "store", default= "41", help= "%s (%s: %%(default)s)" % (gettext("Number of rows displayed"), _def), metavar= _num)
    parser.add_argument("--no-email-link", "-ne", action= "store_true", help= gettext("Disables email links"))
    parser.add_argument("--no-url-link", "-nu", action= "store_true", help= gettext("Disables URL links"))
    parser.add_argument("--theme-color", "-t", action= "store_true", help= gettext("Use theme's colors"))
    parser.add_argument("--color", "-c", type= colorString, action= "store", default= "LightSlateGray", help= "%s (%s: %%(default)s)" % (gettext("Text color"), _def), metavar= _col)
    parser.add_argument("--background", "-b", type= colorString, action= "store", default= "CornSilk", help= "%s (%s: %%(default)s)" % (gettext("Background color"), _def), metavar= _col)
    parser.add_argument("--section-color", "-sc", type= colorString, action= "store", default= "CornSilk", help= "%s (%s: %%(default)s)" % (gettext("Section text color"), _def), metavar= _col)
    parser.add_argument("--section-background", "-sb", type= colorString, action= "store", default= "CadetBlue", help= "%s (%s: %%(default)s)" % (gettext("Section background color"), _def), metavar= _col)
    parser.add_argument("--link-color", "-lc", type= colorString, action= "store", default= "Navy", help= "%s (%s: %%(default)s)" % (gettext("Link text color"), _def), metavar= _col)
    parser.add_argument("--link-background", "-lb", type= colorString, action= "store", default= "CornSilk", help= "%s (%s: %%(default)s)" % (gettext("Link background color"), _def), metavar= _col)
    parser.add_argument("--bold-color", "-bc", type= colorString, action= "store", default= "Orange", help= "%s (%s: %%(default)s)" % (gettext("Bold text color"), _def), metavar= _col)
    parser.add_argument("--bold-background", "-bb", type= colorString, action= "store", default= "CornSilk", help= "%s (%s: %%(default)s)" % (gettext("Bold background color"), _def), metavar= _col)
    parser.add_argument("--italic-color", "-ic", type= colorString, action= "store", default= "DarkCyan", help= "%s (%s: %%(default)s)" % (gettext("Italic text color"), _def), metavar= _col)
    parser.add_argument("--italic-background", "-ib", type= colorString, action= "store", default= "CornSilk", help= "%s (%s: %%(default)s)" % (gettext("Italic background color"), _def), metavar= _col)
    parser.add_argument("--envar-color", "-vc", type= colorString, action= "store", default= "DarkMagenta", help= "%s (%s: %%(default)s)" % (gettext("Environment variable text color"), _def), metavar= _col)
    parser.add_argument("--envar-background", "-vb", type= colorString, action= "store", default= "CornSilk", help= "%s (%s: %%(default)s)" % (gettext("Environment variable background color"), _def), metavar= _col)
    parser.add_argument("--version", "-V", action= "version", version= "%s v%s" % (PROJECT_NAME, PROJECT_VERSION), help= gettext("Display version number and exit"))
    return parser.parse_known_args()

def parsePages(extra):
    if type(extra) == type(list()):
        extra= " ".join(map(str, extra))
    extra= compile(r"\d(?:\S+)? \S+|\S+", DOTALL).findall(extra.replace("\"", "").replace("'", "").replace("`", ""))
    for i, page in enumerate(extra):
        if "(" in page:
            extra[i]= sub(r"(.+)\((.+)\)", r"\2 \1", page)
    return [ x for x in extra if x != "" and not x.startswith("-") ]

if __name__ == "__main__":
    namespace, extra= parsing()
    app, ui= QApplication(extra), ManPagesGUI()
    if int(namespace.random_page):
        ui.manpages.openPage(None, int(namespace.random_page))
    ui.manpages.openPage(parsePages(extra), False)
    ManPagesGUI.self.command.setFocus()
    ui.show()
    exit(app.exec_())
