#!/usr/bin/env python3
"""
Stream Raspberry Pi Camera v2 to a 16x32 RGB LED matrix (HUB75).

Default settings assume:
- Raspberry Pi 4
- Adafruit RGB Matrix HAT/Bonnet
- One 16x32 panel (rows=16, cols=32)

Useful flags:
--rotate 90|180|270   rotate output if your panel is mounted sideways
--mirror              horizontal mirror (selfie view)
--fit crop|letterbox  how to fit camera aspect into 32x16
"""

import argparse, signal, time
import numpy as np
from PIL import Image, ImageOps
from picamera2 import Picamera2
from rgbmatrix import RGBMatrix, RGBMatrixOptions

def build_matrix(args):
    opts = RGBMatrixOptions()
    opts.rows = args.rows
    opts.cols = args.cols
    opts.chain_length = args.chain
    opts.parallel = args.parallel
    opts.hardware_mapping = args.hardware_mapping   # "adafruit-hat", "adafruit-hat-pwm", or "regular"
    opts.gpio_slowdown = args.gpio_slowdown
    opts.brightness = args.brightness
    return RGBMatrix(options=opts)

def fit_frame(img: Image.Image, w: int, h: int, mode: str) -> Image.Image:
    if mode == "crop":
        return ImageOps.fit(img, (w, h), method=Image.BILINEAR, bleed=0.0, centering=(0.5, 0.5))
    else:
        # letterbox: keep aspect, pad with black
        img2 = img.copy()
        img2.thumbnail((w, h), resample=Image.BILINEAR)
        canvas = Image.new("RGB", (w, h))
        x = (w - img2.width) // 2
        y = (h - img2.height) // 2
        canvas.paste(img2, (x, y))
        return canvas

def main():
    ap = argparse.ArgumentParser()
    # Panel defaults for 16x32
    ap.add_argument("--rows", type=int, default=16)
    ap.add_argument("--cols", type=int, default=32)
    ap.add_argument("--chain", type=int, default=1)
    ap.add_argument("--parallel", type=int, default=1)
    ap.add_argument("--hardware-mapping", default="adafruit-hat")
    ap.add_argument("--gpio-slowdown", type=int, default=4)
    ap.add_argument("--brightness", type=int, default=70)
    ap.add_argument("--fps-limit", type=int, default=30, help="Max FPS loop sleep limiter")
    ap.add_argument("--rotate", type=int, default=0, choices=[0,90,180,270], help="Rotate output")
    ap.add_argument("--mirror", action="store_true", help="Horizontal mirror (selfie)")
    ap.add_argument("--fit", choices=["crop","letterbox"], default="crop", help="Frame fit mode")
    args = ap.parse_args()

    matrix = build_matrix(args)
    W, H = matrix.width, matrix.height

    # Camera config: use 320x240 preview for speed, then downscale to 32x16
    picam2 = Picamera2()
    preview_cfg = picam2.create_preview_configuration(main={"size": (320, 240), "format":"RGB888"},
                                                      controls={"FrameRate":30})
    picam2.configure(preview_cfg)
    picam2.start()
    time.sleep(0.2)  # small warmup

    running = True
    def _stop(sig, frame):
        nonlocal running
        running = False
    signal.signal(signal.SIGINT, _stop)

    target_dt = 1.0 / max(1, args.fps_limit)

    try:
        while running:
            t0 = time.time()
            frame = picam2.capture_array()            # numpy array RGB, shape (H, W, 3)
            img = Image.fromarray(frame, "RGB")

            if args.mirror:
                img = ImageOps.mirror(img)
            if args.rotate:
                img = img.rotate(args.rotate, expand=True)

            img = fit_frame(img, W, H, args.fit)
            # Push to matrix
            matrix.SetImage(img)

            # crude FPS limiter
            dt = time.time() - t0
            if dt < target_dt:
                time.sleep(target_dt - dt)

    finally:
        matrix.Clear()
        picam2.stop()

if __name__ == "__main__":
    main()
