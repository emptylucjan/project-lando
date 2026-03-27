"""
Remove gray background from Zalando packshot images → transparent PNG.
Usage: python remove_bg.py input.jpg [output.png]
"""

import sys
import os
from PIL import Image
import numpy as np


def remove_background(input_path: str, output_path: str = None, tolerance: int = 30):
    """
    Remove light gray/white background from packshot image.
    Detects bg color from corners, makes matching pixels transparent.
    
    Args:
        input_path: Path to input JPG/PNG image
        output_path: Path for output PNG (default: same name + .png)
        tolerance: Color distance threshold (higher = more aggressive removal)
    """
    if output_path is None:
        base = os.path.splitext(input_path)[0]
        output_path = base + ".png"

    img = Image.open(input_path).convert("RGBA")
    data = np.array(img)

    # Detect background color from corners (10x10 px samples)
    h, w = data.shape[:2]
    corners = [
        data[0:10, 0:10, :3],       # top-left
        data[0:10, w-10:w, :3],     # top-right  
        data[h-10:h, 0:10, :3],     # bottom-left
        data[h-10:h, w-10:w, :3],   # bottom-right
    ]
    bg_color = np.median(np.concatenate([c.reshape(-1, 3) for c in corners], axis=0), axis=0)
    print(f"Wykryty kolor tła: RGB({bg_color[0]:.0f}, {bg_color[1]:.0f}, {bg_color[2]:.0f})")

    # Calculate color distance from background for every pixel
    diff = np.sqrt(np.sum((data[:, :, :3].astype(float) - bg_color) ** 2, axis=2))

    # Make background pixels transparent
    alpha = np.where(diff < tolerance, 0, 255).astype(np.uint8)
    
    # Smooth edges — semi-transparent transition zone
    edge_zone = (diff >= tolerance) & (diff < tolerance + 15)
    alpha[edge_zone] = ((diff[edge_zone] - tolerance) / 15 * 255).clip(0, 255).astype(np.uint8)

    data[:, :, 3] = alpha
    
    result = Image.fromarray(data)
    result.save(output_path, "PNG")
    
    size_kb = os.path.getsize(output_path) / 1024
    print(f"Zapisano: {output_path} ({size_kb:.1f} KB)")
    return output_path


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Użycie: python remove_bg.py input.jpg [output.png]")
        sys.exit(1)
    
    input_file = sys.argv[1]
    output_file = sys.argv[2] if len(sys.argv) > 2 else None
    
    if not os.path.exists(input_file):
        print(f"Plik nie istnieje: {input_file}")
        sys.exit(1)
    
    remove_background(input_file, output_file)
