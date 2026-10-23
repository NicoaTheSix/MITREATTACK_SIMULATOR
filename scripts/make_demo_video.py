"""Capture the real Fusion Studio Qt workflow and render a captioned MP4.

Operation flow, inputs, outputs and prerequisites: scripts/README.md.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import time
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("QT_FONT_DPI", "96")

from PySide6 import QtCore, QtGui, QtTest, QtWidgets

from app_identity import APP_NAME
from attack_catalog import external_id
from atlas_matrix import KEY as ATLAS_KEY
from localization import tr
from main import MainWindow, configure_application

WIDTH, HEIGHT, FPS = 1920, 1080, 24
APP_SIZE = (1640, 760)
VIEW = QtCore.QRectF(48, 101, 1824, 845)
SCENES = [
    ("intro", "把威脅知識，整理成可交付的研究工作區", "ATT&CK · ATLAS · CAR", 5),
    ("workspace", "01  建立獨立研究文件", "新增文件，讓不同研究與演練保有各自的選取內容。", 8),
    ("search", "02  搜尋並納入 ATT&CK 技術", "輸入技術 ID 或名稱，選取 PowerShell 與 Scheduled Task。", 13),
    ("details", "03  查閱技術與實際案例", "閱讀原始技術說明、平台、戰術與 Procedure Examples。", 9),
    ("matrix", "04  以矩陣檢視研究範圍", "開啟 ATT&CK 矩陣，搜尋技術並檢視所選內容。", 9),
    ("atlas", "05  加入 AI 威脅研究", "在獨立 ATLAS 矩陣搜尋 Prompt Injection，保留 ATT&CK 選取。", 10),
    ("car", "06  參考 CAR 偵測分析", "開啟分析條目，查看偵測邏輯並納入 Workplace。", 8),
    ("export", "07  保存專案、匯出研究清單", "Studio JSON 保存工作內容；CSV 方便後續整理與交換。", 10),
    ("outro", "讓資安研究，有一個共同的工作台", "Fusion Studio  |  Nicoa Wu", 6),
]


def log(message):
    print(message, flush=True)


def wait_for(condition, label, seconds=90):
    deadline = time.monotonic() + seconds
    while not condition():
        if time.monotonic() > deadline:
            raise TimeoutError(label)
        QtTest.QTest.qWait(20)
    QtWidgets.QApplication.processEvents()


def font(size, bold=False):
    value = QtGui.QFont("Microsoft JhengHei")
    value.setPixelSize(size)
    value.setBold(bold)
    return value


class Recorder:
    def __init__(self, window, output, encoder, preview_only):
        self.window, self.output = window, output
        self.preview_only = preview_only
        self.frames = 0
        self.scene_frames = 0
        self.total_frames = sum(s[3] for s in SCENES) * FPS
        self.scene = None
        self.mouse = QtCore.QPointF(1350, 680)
        self.click_ring = 0.0
        self.cached = None
        self.cards = []
        self.subtitle_rows = []
        self.elapsed = 0.0
        self.proc = None
        self.log_stream = None
        self.logo = QtGui.QImage(str(ROOT / "assets/fusion-studio-icon-pixel-v2.png"))
        if not preview_only:
            self.log_stream = (output / "encoder.log").open("wb")
            self.proc = subprocess.Popen([
                encoder, "-y", "-f", "rawvideo", "-pix_fmt", "rgb24",
                "-s", f"{WIDTH}x{HEIGHT}", "-r", str(FPS), "-i", "pipe:0",
                "-an", "-c:v", "libx264", "-preset", "veryfast", "-crf", "19",
                "-pix_fmt", "yuv420p", "-movflags", "+faststart",
                str(output / "fusion-studio-demo-zh-TW.mp4"),
            ], stdin=subprocess.PIPE, stdout=subprocess.DEVNULL, stderr=self.log_stream)

    def begin(self, scene):
        self.scene = scene
        self.scene_frames = 0
        self.subtitle_rows.append((self.elapsed, self.elapsed + scene[3], scene[1], scene[2]))
        self.elapsed += scene[3]
        log(f"[Demo 2/4 capture] {len(self.subtitle_rows)}/{len(SCENES)}: {scene[0]} — {scene[1]}")
        self.capture()

    def capture(self):
        QtWidgets.QApplication.processEvents()
        source = self.window.grab().toImage()
        popup = QtWidgets.QApplication.activePopupWidget()
        if popup is not None and popup.isVisible():
            painter = QtGui.QPainter(source)
            location = self.window.mapFromGlobal(popup.mapToGlobal(QtCore.QPoint(0, 0)))
            painter.drawPixmap(location, popup.grab())
            painter.end()
        self.cached = source.scaled(
            int(VIEW.width()), int(VIEW.height()),
            QtCore.Qt.AspectRatioMode.IgnoreAspectRatio,
            QtCore.Qt.TransformationMode.SmoothTransformation)

    def position(self, widget, point=None):
        point = point or widget.rect().center()
        return QtCore.QPointF(widget.mapTo(self.window, point))

    def frame(self):
        image = QtGui.QImage(WIDTH, HEIGHT, QtGui.QImage.Format.Format_RGB888)
        painter = QtGui.QPainter(image)
        painter.setRenderHint(QtGui.QPainter.RenderHint.Antialiasing)
        gradient = QtGui.QLinearGradient(0, 0, WIDTH, HEIGHT)
        gradient.setColorAt(0, QtGui.QColor("#07101e"))
        gradient.setColorAt(1, QtGui.QColor("#132137"))
        painter.fillRect(image.rect(), gradient)
        key, title, subtitle, duration = self.scene
        seconds = self.scene_frames / FPS
        if key in ("intro", "outro"):
            painter.setPen(QtGui.QPen(QtGui.QColor("#23374e"), 1))
            for x in range(0, WIDTH, 80):
                painter.drawLine(x, 0, x, HEIGHT)
            for y in range(0, HEIGHT, 80):
                painter.drawLine(0, y, WIDTH, y)
            reveal = min(1.0, seconds / .6)
            painter.setOpacity(reveal)
            offset = (1 - reveal) * 28
            painter.drawImage(QtCore.QRectF(874, 140 + offset, 172, 172), self.logo)
            painter.setPen(QtGui.QColor("#f5f8ff"))
            painter.setFont(font(84, True))
            painter.drawText(QtCore.QRectF(100, 338 + offset, 1720, 120), QtCore.Qt.AlignmentFlag.AlignCenter, APP_NAME)
            painter.setPen(QtGui.QColor("#61c4ff"))
            painter.setFont(font(32))
            painter.drawText(QtCore.QRectF(100, 480 + offset, 1720, 65), QtCore.Qt.AlignmentFlag.AlignCenter, title)
            painter.setPen(QtGui.QColor("#c3d1e1"))
            painter.setFont(font(27))
            painter.drawText(QtCore.QRectF(100, 590 + offset, 1720, 60), QtCore.Qt.AlignmentFlag.AlignCenter, subtitle)
            painter.setFont(font(23))
            final_line = "真實桌面介面示範  /  繁體中文" if key == "intro" else "nick5901879@gmail.com  ·  MIT License（原創程式碼）"
            painter.drawText(QtCore.QRectF(100, 690 + offset, 1720, 60), QtCore.Qt.AlignmentFlag.AlignCenter, final_line)
            painter.setOpacity(1)
            painter.setPen(QtGui.QColor("#8299b3"))
            painter.setFont(font(17))
            painter.drawText(QtCore.QRectF(60, 985, 1800, 42), QtCore.Qt.AlignmentFlag.AlignCenter,
                             "獨立社群專案  ·  MITRE ATT&CK® / ATLAS / CAR 保留各自授權  ·  未獲 MITRE 背書")
        else:
            painter.setPen(QtGui.QColor("#69c7ff"))
            painter.setFont(font(21, True))
            painter.drawText(48, 43, APP_NAME)
            painter.setPen(QtGui.QColor("#edf4ff"))
            painter.setFont(font(28, True))
            painter.drawText(340, 47, title)
            painter.setFont(font(17))
            painter.setPen(QtGui.QColor("#a2b8d2"))
            painter.drawText(QtCore.QRectF(1470, 20, 400, 38), QtCore.Qt.AlignmentFlag.AlignRight,
                             f"操作示範   {len(self.subtitle_rows)-1:02d} / 07")
            painter.fillRect(VIEW.adjusted(-2, -2, 2, 2), QtGui.QColor("#3a526c"))
            painter.drawImage(VIEW.topLeft(), self.cached)
            scale = VIEW.width() / APP_SIZE[0]
            point = VIEW.topLeft() + self.mouse * scale
            if self.click_ring > 0:
                painter.setPen(QtGui.QPen(QtGui.QColor(85, 204, 255, int(200 * self.click_ring)), 3))
                painter.setBrush(QtCore.Qt.BrushStyle.NoBrush)
                radius = 12 + (1 - self.click_ring) * 25
                painter.drawEllipse(point, radius, radius)
            path = QtGui.QPainterPath(point)
            path.lineTo(point + QtCore.QPointF(0, 24))
            path.lineTo(point + QtCore.QPointF(6, 18))
            path.lineTo(point + QtCore.QPointF(13, 31))
            path.lineTo(point + QtCore.QPointF(19, 28))
            path.lineTo(point + QtCore.QPointF(12, 15))
            path.lineTo(point + QtCore.QPointF(23, 14))
            path.closeSubpath()
            painter.setPen(QtGui.QPen(QtGui.QColor("#07101e"), 2))
            painter.setBrush(QtGui.QColor("#f4faff"))
            painter.drawPath(path)
            painter.setPen(QtGui.QColor("#edf4ff"))
            painter.setFont(font(28))
            painter.drawText(QtCore.QRectF(60, 965, 1800, 50), QtCore.Qt.AlignmentFlag.AlignCenter, subtitle)
            painter.setPen(QtGui.QColor("#96afcb"))
            painter.setFont(font(16))
            painter.drawText(QtCore.QRectF(60, 1022, 1800, 28), QtCore.Qt.AlignmentFlag.AlignCenter,
                             "Fusion Studio 實際 Qt 介面 · 示範文件與匯出檔案均為真實操作產生 · 無旁白")
        painter.fillRect(0, HEIGHT - 5, WIDTH, 5, QtGui.QColor("#213047"))
        painter.fillRect(0, HEIGHT - 5, round(WIDTH * self.frames / self.total_frames), 5, QtGui.QColor("#55bcff"))
        painter.end()
        if self.proc:
            self.proc.stdin.write(bytes(image.constBits()))
        self.frames += 1
        self.scene_frames += 1
        return image

    def hold(self, seconds, recapture=False):
        if recapture:
            self.capture()
        count = max(1, round(seconds * FPS))
        if self.preview_only:
            self.frames += count
            self.scene_frames += count
            return
        for _ in range(count):
            self.frame()

    def move(self, target, seconds=.65):
        start = QtCore.QPointF(self.mouse)
        if self.preview_only:
            self.mouse = target
            self.hold(seconds)
            return
        for i in range(max(1, round(seconds * FPS))):
            t = (i + 1) / max(1, round(seconds * FPS))
            t = t * t * (3 - 2 * t)
            self.mouse = start * (1 - t) + target * t
            self.frame()

    def click(self, widget, point=None):
        point = point or widget.rect().center()
        self.move(self.position(widget, point))
        QtTest.QTest.mouseClick(widget, QtCore.Qt.MouseButton.LeftButton, pos=point)
        QtTest.QTest.qWait(120)
        self.capture()
        if self.preview_only:
            self.hold(.35)
        else:
            for i in range(round(.35 * FPS)):
                self.click_ring = 1 - i / round(.35 * FPS)
                self.frame()
        self.click_ring = 0

    def type_text(self, widget, value):
        self.click(widget)
        widget.selectAll()
        QtTest.QTest.keyClick(widget, QtCore.Qt.Key.Key_Backspace)
        for letter in value:
            QtTest.QTest.keyClicks(widget, letter)
            QtTest.QTest.qWait(35)
            self.hold(.10, recapture=True)
        QtTest.QTest.qWait(300)
        self.capture()

    def finish_scene(self):
        remaining = self.scene[3] - self.scene_frames / FPS
        if remaining > 0:
            self.hold(remaining)
        evidence = self.output / (self.scene[0] + ".png")
        image = self.frame() if self.preview_only else self.still()
        if self.preview_only:
            # A preview frame must not add a frame to the planned timeline.
            self.frames -= 1
            self.scene_frames -= 1
        if not image.save(str(evidence)):
            raise OSError(f"Cannot save {evidence}")
        self.cards.append(evidence)

    def still(self):
        proc = self.proc
        self.proc = None
        try:
            image = self.frame()
            self.frames -= 1
            self.scene_frames -= 1
            return image
        finally:
            self.proc = proc

    def finish(self):
        if self.proc:
            self.proc.stdin.close()
            if self.proc.wait(timeout=60):
                raise RuntimeError("Video encoding failed; inspect encoder.log")
            self.log_stream.close()
        sheet = QtGui.QImage(1440, 810, QtGui.QImage.Format.Format_RGB888)
        sheet.fill(QtGui.QColor("#07101e"))
        painter = QtGui.QPainter(sheet)
        for i, path in enumerate(self.cards):
            painter.drawImage(QtCore.QRectF(i % 3 * 480, i // 3 * 270, 480, 270), QtGui.QImage(str(path)))
        painter.end()
        sheet.save(str(self.output / "storyboard.png"))
        def stamp(seconds):
            milliseconds = round(seconds * 1000)
            return f"{milliseconds//3600000:02d}:{milliseconds//60000%60:02d}:{milliseconds//1000%60:02d},{milliseconds%1000:03d}"
        srt = "\n\n".join(f"{i}\n{stamp(a)} --> {stamp(b)}\n{title}\n{caption}"
                              for i, (a, b, title, caption) in enumerate(self.subtitle_rows, 1))
        (self.output / "captions.zh-TW.srt").write_text(srt + "\n", encoding="utf-8")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, default=ROOT / "artifacts/demo-video")
    parser.add_argument("--ffmpeg", default=shutil.which("ffmpeg"))
    parser.add_argument("--preview-only", action="store_true", help="Execute the workflow and save keyframes without encoding MP4")
    args = parser.parse_args()
    output = args.output_dir.expanduser().resolve()
    if not args.preview_only and not args.ffmpeg:
        parser.error("Install ffmpeg or supply --ffmpeg ABSOLUTE_PATH")
    for path in (ROOT / "main.py", ROOT / "data/attack/latest.json", ROOT / "data/atlas",
                 ROOT / "data/car", ROOT / "locales/zh_TW.json", ROOT / "assets/fusion-studio-icon-pixel-v2.png"):
        log(f"Input path: {path.resolve()}")
    log(f"Input encoder: {Path(args.ffmpeg).resolve() if args.ffmpeg else 'None (preview only)'}")
    log(f"Output directory: {output}")
    for filename in ["settings.ini", "demo-research.json", "demo-research.csv", "storyboard.png",
                     "captions.zh-TW.srt", "report.json", "encoder.log", "fusion-studio-demo-zh-TW.mp4"] + [s[0]+".png" for s in SCENES]:
        log(f"Output file: {output / filename}")
    output.mkdir(parents=True, exist_ok=True)
    protected_paths = [ROOT / "data/ui-settings.ini", ROOT / "data/workspace-session.json", ROOT / "data/attack/active.json"]
    protected = {p: p.read_bytes() if p.exists() else None for p in protected_paths}
    log("[Demo 1/4 prepare] Load actual application with isolated preferences and no recovery session")
    settings = QtCore.QSettings(str(output / "settings.ini"), QtCore.QSettings.Format.IniFormat)
    settings.setValue("interface/language", "zh_TW")
    settings.sync()
    app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
    configure_application(app)
    app.setFont(QtGui.QFont("Microsoft JhengHei", 10))
    window = MainWindow(ROOT / "data/attack", ROOT / "data/attack/latest.json", settings_path=output / "settings.ini", session_path=None)
    recorder = None
    try:
        window.resize(*APP_SIZE)
        window.show()
        wait_for(lambda: window.loaded_ok and not window.loader.isRunning(), "Load local ATT&CK, ATLAS and CAR catalogs")
        assert window.atlas_catalog and window.car_catalog, "ATLAS/CAR sources must load successfully"
        window.output_panel.hide()
        window.horizontal.setSizes([350, 1290])
        window.change_selection_preference("with_family", False)
        window.change_selection_preference("across_tactics", True)
        window.switch_category("Workplace")
        window.show_document_page()
        recorder = Recorder(window, output, args.ffmpeg, args.preview_only)
        for scene in SCENES:
            recorder.begin(scene)
            key = scene[0]
            if key == "workspace":
                recorder.hold(1)
                recorder.move(QtCore.QPointF(190, 50))
                QtTest.QTest.keyClick(window, QtCore.Qt.Key.Key_N, QtCore.Qt.KeyboardModifier.ControlModifier)
                wait_for(lambda: window.loaded_ok and len(window.documents) == 2, "Create second document")
                window.current_document.name = "Demo Research"
                window.update_document_labels()
                window.switch_category("Workplace")
                window.show_document_page()
                recorder.hold(1, recapture=True)
                recorder.move(recorder.position(window.document_tabs))
            elif key == "search":
                window.switch_category("TTP")
                recorder.capture()
                for identity in ("T1059.001", "T1053.005"):
                    recorder.type_text(window.ttp_search, identity)
                    obj_key = next(k for k, obj in window.catalog.records.items() if external_id(obj) == identity)
                    source = window.items_by_id[obj_key][0]
                    index = window.proxy.mapFromSource(source.index())
                    parent = index.parent()
                    while parent.isValid():
                        window.tree.expand(parent)
                        parent = parent.parent()
                    window.tree.scrollTo(index)
                    QtWidgets.QApplication.processEvents()
                    rectangle = window.tree.visualRect(index)
                    recorder.capture()
                    recorder.click(window.tree.viewport(), rectangle.center())
                    QtTest.QTest.keyClick(window.tree, QtCore.Qt.Key.Key_Space)
                    QtTest.QTest.qWait(120)
                    assert obj_key in window.current_document.selected, f"Select {identity} through actual tree keyboard action"
                    recorder.hold(1.15, recapture=True)
                assert len(window.current_document.selected) == 2
            elif key == "details":
                powershell = next(k for k, obj in window.catalog.records.items() if external_id(obj) == "T1059.001")
                window.ttp_search.setText("T1059.001")
                QtTest.QTest.qWait(300)
                window.show_record(powershell, "Windows", "execution")
                recorder.hold(2.8, recapture=True)
                bar = window.details.verticalScrollBar()
                recorder.move(recorder.position(window.details, QtCore.QPoint(window.details.width()-20, 300)))
                cursor = window.details.document().find(tr("Procedure Examples"))
                if not cursor.isNull():
                    window.details.setTextCursor(cursor)
                    window.details.ensureCursorVisible()
                    target = bar.value()
                    bar.setValue(0)
                else:
                    target = min(bar.maximum(), 1100)
                steps = 1 if args.preview_only else 60
                for i in range(steps):
                    bar.setValue(round(target * (i+1)/steps))
                    recorder.hold(2.5/steps, recapture=True)
            elif key == "matrix":
                window.open_matrix()
                window.matrix_view.set_controls_expanded(True)
                recorder.capture()
                recorder.type_text(window.matrix_view.search, "PowerShell")
                recorder.hold(2, recapture=True)
                recorder.click(window.matrix_view.controls_toggle)
            elif key == "atlas":
                window.open_atlas_matrix()
                recorder.capture()
                recorder.type_text(window.atlas_matrix.search, "Prompt")
                atlas_key = next(k for k, obj in window.current_atlas_catalog.records.items()
                                 if "prompt injection" in obj.get("name", "").lower())
                recorder.hold(1.5, recapture=True)
                item = None
                for tree in window.atlas_matrix.columns:
                    iterator = QtWidgets.QTreeWidgetItemIterator(tree)
                    while iterator.value():
                        if iterator.value().data(0, ATLAS_KEY) == atlas_key:
                            item = iterator.value()
                            break
                        iterator += 1
                    if item is not None:
                        break
                assert item is not None, "Prompt Injection must be visible in the filtered ATLAS matrix"
                tree.scrollToItem(item)
                recorder.capture()
                recorder.click(tree.viewport(), tree.visualItemRect(item).center())
                QtTest.QTest.keyClick(tree, QtCore.Qt.Key.Key_Space)
                QtTest.QTest.qWait(100)
                assert atlas_key in window.current_document.atlas_document.selected
                assert len(window.current_document.selected) == 2
                recorder.hold(1, recapture=True)
            elif key == "car":
                window.open_car_browser()
                recorder.capture()
                car_key = next((k for k, obj in window.car_catalog.analytics.items()
                                if "powershell" in obj.get("title", "").lower()), "CAR-2013-04-002")
                window.car_browser.open_analytic(car_key)
                recorder.hold(2, recapture=True)
                recorder.click(window.car_browser.add)
                recorder.hold(1.5, recapture=True)
                assert any(entry["included"] and entry["id"] == car_key
                           for entry in window.current_document.car_workspace["entries"].values())
            elif key == "export":
                window.switch_category("Workplace")
                window.show_document_page()
                window.tabs.setCurrentIndex(window.selection_tab_index)
                recorder.hold(1.5, recapture=True)
                file_action = window.menuBar().actions()[0]
                menu = file_action.menu()
                menu.popup(window.menuBar().mapToGlobal(window.menuBar().actionGeometry(file_action).bottomLeft()))
                menu.setActiveAction(window.save_action)
                QtTest.QTest.qWait(100)
                recorder.capture()
                recorder.move(QtCore.QPointF(window.mapFromGlobal(menu.mapToGlobal(menu.actionGeometry(window.save_action).center()))))
                recorder.hold(1)
                menu.hide()
                # Execute the native save/export handlers with explicit isolated destinations.
                target = output / "demo-research.json"
                assert window.save_studio_document(target=target, frameworks=(True, True, True)) == target
                csv_path = output / "demo-research.csv"
                window.export_current_document(csv_path, "csv", visible_only=False, frameworks=(True, False, False))
                assert target.is_file() and csv_path.is_file()
                recorder.hold(1, recapture=True)
                recorder.move(recorder.position(window.document_tabs))
            recorder.finish_scene()
        log("[Demo 3/4 encode] Finalize MP4, subtitles and storyboard")
        recorder.finish()
        log("[Demo 4/4 verify] Check real exports, media and protected user state")
        for path, before in protected.items():
            assert (path.read_bytes() if path.exists() else None) == before, f"User state changed: {path}"
        report = {"passed": True, "application": APP_NAME, "width": WIDTH, "height": HEIGHT,
                  "fps": FPS, "frames": recorder.frames, "duration_seconds": recorder.frames / FPS,
                  "language": "zh-TW", "audio": False, "real_ui": True,
                  "preview_only": args.preview_only, "protected_user_files_unchanged": True,
                  "scenes": [{"id":s[0],"title":s[1],"seconds":s[3]} for s in SCENES],
                  "video": str(output / "fusion-studio-demo-zh-TW.mp4") if not args.preview_only else None,
                  "exports": [str(output / "demo-research.json"), str(output / "demo-research.csv")]}
        if not args.preview_only:
            video = output / "fusion-studio-demo-zh-TW.mp4"
            assert video.stat().st_size > 100_000
            result = subprocess.run([args.ffmpeg,"-v","error","-i",str(video),"-f","null","-"],
                                    capture_output=True, timeout=120)
            assert result.returncode == 0, result.stderr.decode(errors="replace")
            report["video_decode_passed"] = True
            report["video_sha256"] = hashlib.sha256(video.read_bytes()).hexdigest()
        (output / "report.json").write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
        log(f"[Demo complete] {recorder.frames / FPS:.2f} seconds; report: {output / 'report.json'}")
    finally:
        if recorder and recorder.proc and recorder.proc.poll() is None:
            recorder.proc.stdin.close()
            recorder.proc.terminate()
            recorder.proc.wait(timeout=15)
        if recorder and recorder.log_stream and not recorder.log_stream.closed:
            recorder.log_stream.close()
        with patch.object(window, "finish_studio_exit", return_value=True):
            window.close()
        app.processEvents()


if __name__ == "__main__":
    main()
