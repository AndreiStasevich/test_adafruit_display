#!/usr/bin/env python3
import argparse, signal, time
import numpy as np
from PIL import Image
from rgbmatrix import RGBMatrix, RGBMatrixOptions

def main():
    p = argparse.ArgumentParser()
    p.add_argument("--rows", type=int, default=16)
    p.add_argument("--cols", type=int, default=32)
    p.add_argument("--chain", type=int, default=1)
    p.add_argument("--parallel", type=int, default=1)
    p.add_argument("--hardware-mapping", default="adafruit-hat",
                   help="adafruit-hat, adafruit-hat-pwm, or regular")
    p.add_argument("--gpio-slowdown", type=int, default=4)
    p.add_argument("--brightness", type=int, default=80)
    p.add_argument("--seed", type=float, default=0.25, help="initial live density 0..1")
    p.add_argument("--fps", type=int, default=30)
    args = p.parse_args()

    # Configure matrix
    options = RGBMatrixOptions()
    options.rows = args.rows
    options.cols = args.cols
    options.chain_length = args.chain
    options.parallel = args.parallel
    options.hardware_mapping = args.hardware_mapping
    options.gpio_slowdown = args.gpio_slowdown
    options.brightness = args.brightness
    matrix = RGBMatrix(options=options)

    W = matrix.width
    H = matrix.height

    # Seed grid
    rng = np.random.default_rng()
    grid = rng.random((H, W)) < args.seed
    prev = grid.copy()

    # Graceful exit on Ctrl+C
    running = True
    def _stop(sig, frame):
        nonlocal running
        running = False
    signal.signal(signal.SIGINT, _stop)

    frame_delay = 1.0 / max(1, args.fps)

    while running:
        # Count neighbors via rolled sums
        neighbors = sum(np.roll(np.roll(grid, dy, 0), dx, 1)
                        for dy in (-1, 0, 1)
                        for dx in (-1, 0, 1)
                        if not (dx == 0 and dy == 0))
        # Life rules
        new_grid = (neighbors == 3) | (grid & (neighbors == 2))

        # Reseed if we die out or reach a steady loop
        if not new_grid.any() or np.array_equal(new_grid, prev):
            new_grid = rng.random((H, W)) < args.seed

        prev = grid
        grid = new_grid

        # Draw using PIL and push to matrix
        frame = np.zeros((H, W, 3), dtype=np.uint8)
        frame[grid] = [255, 255, 255]  # white live cells
        img = Image.fromarray(frame, "RGB")
        matrix.SetImage(img)

        time.sleep(frame_delay)

    matrix.Clear()

if __name__ == "__main__":
    main()
