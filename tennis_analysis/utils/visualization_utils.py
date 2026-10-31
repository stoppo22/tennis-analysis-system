import cv2


PLAYER_1_COLOR = (118, 80, 255)
PLAYER_2_COLOR = (255, 210, 65)
BALL_COLOR = (0, 245, 255)
KEYPOINT_COLOR = (145, 255, 120)
PANEL_COLOR = (38, 24, 14)
PANEL_BORDER_COLOR = (78, 58, 38)


def draw_rounded_rectangle(image, top_left, bottom_right, color, radius=16):
    """Draw a filled rounded rectangle on an OpenCV image."""
    x1, y1 = top_left
    x2, y2 = bottom_right
    radius = max(0, min(radius, (x2 - x1) // 2, (y2 - y1) // 2))

    cv2.rectangle(image, (x1 + radius, y1), (x2 - radius, y2), color, -1)
    cv2.rectangle(image, (x1, y1 + radius), (x2, y2 - radius), color, -1)

    for center in (
        (x1 + radius, y1 + radius),
        (x2 - radius, y1 + radius),
        (x1 + radius, y2 - radius),
        (x2 - radius, y2 - radius),
    ):
        cv2.circle(image, center, radius, color, -1, cv2.LINE_AA)


def draw_translucent_panel(
    frame,
    top_left,
    bottom_right,
    color=PANEL_COLOR,
    opacity=0.9,
    radius=16,
    border_color=PANEL_BORDER_COLOR,
):
    """Blend a rounded, translucent panel onto a video frame."""
    overlay = frame.copy()
    draw_rounded_rectangle(
        overlay,
        top_left,
        bottom_right,
        border_color,
        radius,
    )
    x1, y1 = top_left
    x2, y2 = bottom_right
    draw_rounded_rectangle(
        overlay,
        (x1 + 1, y1 + 1),
        (x2 - 1, y2 - 1),
        color,
        max(0, radius - 1),
    )
    cv2.addWeighted(overlay, opacity, frame, 1 - opacity, 0, frame)


def get_player_color(player_id):
    return {
        1: PLAYER_1_COLOR,
        2: PLAYER_2_COLOR,
    }.get(player_id, KEYPOINT_COLOR)


def draw_corner_box(frame, bbox, color, corner_length=20, thickness=3):
    """Draw only the corners of a bounding box to reduce visual clutter."""
    x1, y1, x2, y2 = (int(value) for value in bbox)
    corners = (
        ((x1, y1 + corner_length), (x1, y1), (x1 + corner_length, y1)),
        ((x2 - corner_length, y1), (x2, y1), (x2, y1 + corner_length)),
        ((x1, y2 - corner_length), (x1, y2), (x1 + corner_length, y2)),
        ((x2 - corner_length, y2), (x2, y2), (x2, y2 - corner_length)),
    )
    for start, corner, end in corners:
        cv2.line(frame, start, corner, color, thickness, cv2.LINE_AA)
        cv2.line(frame, corner, end, color, thickness, cv2.LINE_AA)


def draw_label(frame, text, origin, color):
    """Draw a compact filled label above a detection."""
    x, y = (int(value) for value in origin)
    font = cv2.FONT_HERSHEY_SIMPLEX
    scale = 0.5
    thickness = 1
    (text_width, text_height), baseline = cv2.getTextSize(
        text,
        font,
        scale,
        thickness,
    )
    label_y = max(text_height + baseline + 8, y)
    draw_rounded_rectangle(
        frame,
        (x, label_y - text_height - baseline - 8),
        (x + text_width + 14, label_y + 2),
        color,
        radius=6,
    )
    cv2.putText(
        frame,
        text,
        (x + 7, label_y - baseline - 2),
        font,
        scale,
        (20, 25, 32),
        thickness,
        cv2.LINE_AA,
    )
