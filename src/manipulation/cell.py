import cv2
import numpy as np
import os

def extract_move_pairs(image_path, output_image="game_002_pairs.jpg", crop_dir="trocr_crops"):
    img = cv2.imread(image_path)
    if img is None:
        print(f"Fehler: Bild '{image_path}' konnte nicht geladen werden.")
        return

    img_visual = img.copy()
    img_h, img_w = img.shape[:2]

    # --- 1. Zellenerkennung (wie bisher) ---
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    thresh = cv2.adaptiveThreshold(gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, 
                                   cv2.THRESH_BINARY_INV, 11, 2)

    kernel_len = max(img_w, img_h) // 50
    ver_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (1, kernel_len))
    vertical_lines = cv2.morphologyEx(thresh, cv2.MORPH_OPEN, ver_kernel, iterations=2)
    
    hor_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (kernel_len, 1))
    horizontal_lines = cv2.morphologyEx(thresh, cv2.MORPH_OPEN, hor_kernel, iterations=2)
    
    grid_mask = cv2.addWeighted(vertical_lines, 0.5, horizontal_lines, 0.5, 0.0)
    _, grid_mask = cv2.threshold(grid_mask, 0, 255, cv2.THRESH_BINARY | cv2.THRESH_OTSU)
    grid_mask = cv2.dilate(grid_mask, cv2.getStructuringElement(cv2.MORPH_RECT, (3, 3)), iterations=1)

    contours, _ = cv2.findContours(grid_mask, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)

    boxes = []
    for cnt in contours:
        x, y, w, h = cv2.boundingRect(cnt)
        # NEU: Filtere Header heraus (y > 15% der Bildhöhe) und prüfe auf sinnvolle Größe
        if y > img_h * 0.15 and 30 < w < img_w // 2 and 15 < h < img_h // 10:
            boxes.append((x, y, w, h))

    # --- 2. In Reihen gruppieren ---
    boxes.sort(key=lambda b: b[1]) # Zuerst nach Y sortieren
    
    rows = []
    if boxes:
        current_row = [boxes[0]]
        row_y_threshold = 20 
        
        for b in boxes[1:]:
            if b[1] < current_row[-1][1] + row_y_threshold:
                current_row.append(b)
            else:
                rows.append(current_row)
                current_row = [b]
        rows.append(current_row)

    # --- 3. Paare (Weiß + Schwarz) anhand fester Zonen verschmelzen ---
    # Diese Zonen definieren (in % der Bildbreite), wo sich die 3 Zug-Blöcke befinden.
    zones = [
        (0.08, 0.35),  # Block 1 (Züge 1-20): ca. 8% bis 35% der Bildbreite
        (0.38, 0.65),  # Block 2 (Züge 21-40): ca. 38% bis 65% der Bildbreite
        (0.68, 0.95)   # Block 3 (Züge 41-60): ca. 68% bis 95% der Bildbreite
    ]

    pair_boxes = []
    
    for row in rows:
        for z_start_rel, z_end_rel in zones:
            z_start = img_w * z_start_rel
            z_end = img_w * z_end_rel
            
            # Finde alle erkannten Boxen in dieser Zeile, die in diese Zone fallen
            boxes_in_zone = [b for b in row if z_start <= (b[0] + b[2]/2) <= z_end]
            
            if boxes_in_zone:
                # Bounding Box spannen, die beide Zellen (Weiß und Schwarz) umschließt
                min_x = min([b[0] for b in boxes_in_zone])
                min_y = min([b[1] for b in boxes_in_zone])
                max_x = max([b[0] + b[2] for b in boxes_in_zone])
                max_y = max([b[1] + b[3] for b in boxes_in_zone])
                
                pair_boxes.append((min_x, min_y, max_x - min_x, max_y - min_y))

    # --- 4. Chronologische Sortierung für TrOCR ---
    # Sortiere zuerst nach dem vertikalen Block (linkes, mittleres, rechtes Drittel),
    # und danach nach der Zeile (Y-Koordinate), um die echte Zugfolge 1 bis 60 zu erhalten.
    pair_boxes.sort(key=lambda b: (b[0] // (img_w // 3), b[1]))

    # --- 5. Ausschneiden und Markieren ---
    if not os.path.exists(crop_dir):
        os.makedirs(crop_dir)

    for i, (x, y, w, h) in enumerate(pair_boxes):
        # Crop erstellen und speichern (Perfekt für TrOCR)
        crop = img[y:y+h, x:x+w]
        crop_path = os.path.join(crop_dir, f"zug_{i+1:02d}.jpg")
        cv2.imwrite(crop_path, crop)

        # Im Visualisierungsbild einzeichnen
        cv2.rectangle(img_visual, (x, y), (x + w, y + h), (0, 255, 0), 2)
        # Schreibe die echte Zugnummer in Rot darüber
        cv2.putText(img_visual, f"Zug {i+1}", (x + 5, y + 20), 
                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 255), 2)

    cv2.imwrite(output_image, img_visual)
    print(f"Fertig! Es wurden {len(pair_boxes)} Zug-Paare zusammengefasst.")
    print(f"Visualisierung gespeichert unter '{output_image}'.")
    print(f"Die fertigen Paare für TrOCR liegen im Ordner '{crop_dir}'.")

# Aufruf:
extract_move_pairs('data/game_002.jpg')