import cv2
import numpy as np
import os

def extract_cells(image_path, output_dir="cells"):
    # Create output folder
    os.makedirs(output_dir, exist_ok=True)

    # Load image
    img = cv2.imread(image_path)
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

    # Binary image
    thresh = cv2.adaptiveThreshold(
        gray, 255,
        cv2.ADAPTIVE_THRESH_MEAN_C,
        cv2.THRESH_BINARY_INV, 15, 4
    )

    # Detect horizontal lines
    horizontal_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (50, 1))
    horizontal = cv2.morphologyEx(thresh, cv2.MORPH_OPEN, horizontal_kernel)

    # Detect vertical lines
    vertical_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (1, 50))
    vertical = cv2.morphologyEx(thresh, cv2.MORPH_OPEN, vertical_kernel)

    # Combine to get grid
    grid = cv2.add(horizontal, vertical)

    # Find contours (cells)
    contours, _ = cv2.findContours(grid, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)

    cells = []
    for cnt in contours:
        x, y, w, h = cv2.boundingRect(cnt)

        # Filter small noise (tune these!)
        if w > 40 and h > 20:
            cells.append((x, y, w, h))

    # Sort cells top-to-bottom, then left-to-right
    cells = sorted(cells, key=lambda b: (b[1], b[0]))

    # Save each cell
    for i, (x, y, w, h) in enumerate(cells):
        cell_img = img[y:y+h, x:x+w]
        cv2.imwrite(f"{output_dir}/cell_{i:03d}.png", cell_img)

    print(f"Saved {len(cells)} cells to '{output_dir}'")

# Example usage
extract_cells("data\game_002.jpg")