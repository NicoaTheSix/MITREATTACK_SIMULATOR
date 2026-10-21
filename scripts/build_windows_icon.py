"""Package the existing pixel PNG as a multi-size ICO. See README.md."""
from pathlib import Path
import struct

from PySide6 import QtCore, QtGui


def main():
    root = Path(__file__).resolve().parents[1]
    source = root / "assets" / "fusion-studio-icon-pixel-v2.png"
    target = source.with_suffix(".ico")
    print(f"Input file: {source}", flush=True)
    print(f"Output file: {target}", flush=True)
    print("[Windows icon 1/3] Reading pixel artwork", flush=True)
    image = QtGui.QImage(str(source))
    if image.isNull():
        raise ValueError(f"Could not read {source}")
    frames = []
    sizes = (16, 32, 48, 64, 128, 256)
    for index, size in enumerate(sizes, 1):
        print(f"[Windows icon 2/3] Encoding {size}px ({index}/{len(sizes)})", flush=True)
        frame = image.scaled(size, size, QtCore.Qt.AspectRatioMode.KeepAspectRatio,
                             QtCore.Qt.TransformationMode.FastTransformation)
        buffer = QtCore.QBuffer()
        buffer.open(QtCore.QIODevice.OpenModeFlag.WriteOnly)
        if not frame.save(buffer, "PNG"):
            raise ValueError(f"Could not encode {size}px icon")
        frames.append((size, bytes(buffer.data())))
    offset = 6 + 16 * len(frames)
    directory, payload = [], []
    for size, data in frames:
        directory.append(struct.pack("<BBBBHHII", size % 256, size % 256, 0, 0, 1, 32, len(data), offset))
        payload.append(data)
        offset += len(data)
    target.write_bytes(struct.pack("<HHH", 0, 1, len(frames)) + b"".join(directory + payload))
    print(f"[Windows icon 3/3] Complete: {target}", flush=True)


if __name__ == "__main__":
    main()
