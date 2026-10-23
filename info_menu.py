"""Offline information dialogs and native cascading history menu. Workflow: README.md."""
from __future__ import annotations

import html
import json
from pathlib import Path
import re

from PySide6 import QtCore, QtGui, QtWidgets
from localization import LocalizedTextBrowser
from app_identity import APP_NAME, APP_TAGLINE

ROOT = Path(__file__).resolve().parent
RELEASE_CACHE = ROOT / 'data' / 'info' / 'attack-release-notes.json'
REPOSITORY_URL = 'https://github.com/NicoaTheSix/MITREATTACK_SIMULATOR'
AUTHOR_MESSAGE = 'Hi this is Nicoa. Thank you for using this tool. If you like it,you can give me a star in github'
AUTHOR_IMAGE = ROOT / 'assets' / 'nicoa-hackmd-cover-under-1mb.png'
MITRE_URL = 'https://www.mitre.org/who-we-are'
ATTACK_URL = 'https://attack.mitre.org/'
HISTORY_URL = 'https://attack.mitre.org/resources/versions/'


def paragraph(text):
    return '<p>' + html.escape(text) + '</p>'


def link(url, label=None):
    return '<p><a href="' + html.escape(url, quote=True) + '">' + html.escape(label or url) + '</a></p>'


class InformationImage(QtWidgets.QWidget):
    """Fit the complete pixel illustration without stretching or cropping."""

    def __init__(self, pixmap, parent=None):
        super().__init__(parent)
        self.pixmap = pixmap
        self.setObjectName('infoIllustration')
        self.setAccessibleName('Nicoa author illustration')
        self.setMinimumSize(160, 90)
        self.setSizePolicy(QtWidgets.QSizePolicy.Policy.Expanding,
                           QtWidgets.QSizePolicy.Policy.Expanding)

    def sizeHint(self):
        return QtCore.QSize(760, 428)

    def paintEvent(self, event):
        painter = QtGui.QPainter(self)
        painter.fillRect(self.rect(), QtCore.Qt.GlobalColor.black)
        size = self.pixmap.size().scaled(self.size(), QtCore.Qt.AspectRatioMode.KeepAspectRatio)
        target = QtCore.QRect(QtCore.QPoint(), size)
        target.moveCenter(self.rect().center())
        painter.drawPixmap(target, self.pixmap)


def show_information(window, title, body, image_path=None):
    window.operation_report(f'Input file: {Path(__file__).resolve()}', 0, 0)
    if image_path is not None:
        image_path = Path(image_path).resolve()
        window.operation_report(f'Input image: {image_path}', 0, 0)
    window.operation_report('Output files: None (read-only information dialog)', 0, 0)
    window.operation_report('[Info 1/2] Preparing ' + title, 0, 2)
    dialog = QtWidgets.QDialog(window)
    dialog.setAttribute(QtCore.Qt.WidgetAttribute.WA_DeleteOnClose)
    dialog.setWindowTitle(title)
    dialog.resize(720, 490)
    layout = QtWidgets.QVBoxLayout(dialog)
    if image_path is not None:
        pixmap = QtGui.QPixmap(str(image_path))
        if pixmap.isNull():
            window.operation_report('[Info image] Image unavailable: ' + str(image_path), 1, 2)
        else:
            dialog.resize(900, 700)
            layout.addWidget(InformationImage(pixmap, dialog), 3)
    browser = LocalizedTextBrowser()
    browser.setObjectName('infoContent')
    browser.setOpenLinks(False)
    browser.setOpenExternalLinks(False)
    browser.setHtml('<h1>' + html.escape(title) + '</h1>' + body)
    if image_path is not None:
        browser.setMinimumHeight(140)

    def open_link(url):
        window.operation_report('Input URL: ' + url.toString(), 0, 0)
        window.operation_report('Output files: None (open default browser)', 0, 0)
        window.operation_report('[Info link 1/2] Opening selected website', 1, 2)
        if url.scheme() not in ('https', 'http') or not url.host() or url.userInfo():
            window.operation_report('[Info link 2/2] Unsupported website address', 2, 2)
            return
        opened = QtGui.QDesktopServices.openUrl(url)
        window.operation_report('[Info link 2/2] ' + ('Complete' if opened else 'Could not open browser'), 2, 2)
        if not opened:
            QtWidgets.QMessageBox.warning(dialog, 'Website', 'Could not open the browser. Copy the displayed URL to open it manually.')

    browser.anchorClicked.connect(open_link)
    layout.addWidget(browser, 1)
    buttons = QtWidgets.QDialogButtonBox(QtWidgets.QDialogButtonBox.StandardButton.Close)
    buttons.rejected.connect(dialog.close)
    layout.addWidget(buttons)
    window.info_dialog = dialog
    dialog.show()
    window.operation_report('[Info 2/2] Complete: ' + title, 2, 2)
    return dialog


def read_releases():
    print(f'Input file: {RELEASE_CACHE}', flush=True)
    print('Output files: None (Info menu in memory)', flush=True)
    print('[Info history 1/2] Reading offline release introductions', flush=True)
    try:
        if RELEASE_CACHE.stat().st_size > 512 * 1024:
            raise ValueError('Release cache exceeds size limit')
        payload = json.loads(RELEASE_CACHE.read_text(encoding='utf-8'))
        rows = payload['releases']
        if payload.get('schema_version') != 1 or not isinstance(rows, list) or len(rows) > 100:
            raise ValueError('Unsupported release cache')
        seen = set()
        for row in rows:
            version, url, summary = row['version'], row['url'], row['summary']
            if (not isinstance(version, str) or not re.fullmatch(r'\d+\.\d+', version)
                    or version in seen or not isinstance(summary, str) or not summary.strip()
                    or not isinstance(url, str) or not url.startswith('https://attack.mitre.org/resources/updates/')
                    or len(summary) > 10000):
                raise ValueError('Invalid release entry')
            seen.add(version)
        rows.sort(key=lambda row: tuple(map(int, row['version'].split('.'))), reverse=True)
    except (OSError, ValueError, KeyError, TypeError) as error:
        print(f'[Info history 2/2] Offline cache unavailable: {error}; official history link remains available', flush=True)
        return []
    print(f'[Info history 2/2] Complete: {len(rows)} official release entries', flush=True)
    return rows


def build_info_menu(window):
    menu = window.menuBar().addMenu('Info')
    window.info_menu = menu
    manual = menu.addAction('Manual')
    manual.setShortcut('F1')
    manual.triggered.connect(window.open_manual)
    about_title = 'About ' + APP_NAME
    about = menu.addAction(about_title)
    about.triggered.connect(lambda: show_information(window, about_title,
        '<h2>' + html.escape(APP_NAME) + '</h2>' + paragraph(APP_TAGLINE)
        + link(REPOSITORY_URL)))
    menu.addSeparator()
    author = menu.addAction('Author information')
    author.triggered.connect(lambda: show_information(window, 'Author information',
        paragraph(AUTHOR_MESSAGE) + link(REPOSITORY_URL), image_path=AUTHOR_IMAGE))
    mitre = menu.addAction('MITRE information')
    mitre.triggered.connect(lambda: show_information(window, 'MITRE information',
        paragraph('MITRE is a nonprofit organization established to advance national security and serve the public interest as an independent adviser. It applies systems thinking and technical research to complex public-interest challenges.')
        + paragraph('Summary of MITRE’s official introduction:') + link(MITRE_URL)))
    attack = menu.addAction('MITRE ATT&&CK information')
    attack.triggered.connect(lambda: show_information(window, 'MITRE ATT&CK information',
        paragraph('MITRE ATT&CK is an openly available knowledge base describing adversary tactics and techniques drawn from observed activity. Organizations use it to build threat models and guide cybersecurity analysis and methods.')
        + paragraph('Summary of the official ATT&CK introduction:') + link(ATTACK_URL)))
    menu.addSeparator()
    history = menu.addMenu('Version update history')
    window.info_history_menu = history
    history.addSection(APP_NAME)
    tool = history.addAction('2026-10-19 — v20 data and Info menu')
    tool.triggered.connect(lambda: show_information(window, 'Tool update — 2026-10-19',
        paragraph('Updated the default Enterprise, Mobile and ICS data to ATT&CK v20.0. Added the Info menu with author information, official introductions, clickable websites and cascading release history. Added the Manual workspace tab with a heading outline, guide navigation and links to application features.')
        + paragraph('This is a dated tool update; ATT&CK data release numbers are listed separately below.')
        + link(REPOSITORY_URL)))
    history.addSection('MITRE ATT&&CK — official releases')
    for row in read_releases():
        action = history.addAction('ATT&&CK v' + row['version'])
        action.setData(row['version'])
        action.triggered.connect(lambda checked=False, entry=row: show_information(window,
            'ATT&CK v' + entry['version'] + ' — release notes',
            paragraph('Short excerpt from the official release notes. Open the link below for the complete changelog:')
            + paragraph(entry['summary']) + link(entry['url'], 'Read the complete official release notes')
            + link(entry['url'])))
    history.addSeparator()
    full = history.addAction('All official versions…')
    full.triggered.connect(lambda: show_information(window, 'Official ATT&CK version history', link(HISTORY_URL)))
    return menu
