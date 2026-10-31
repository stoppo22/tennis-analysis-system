import cv2
import numpy as np

from .visualization_utils import (
    PANEL_COLOR,
    PLAYER_1_COLOR,
    PLAYER_2_COLOR,
    draw_translucent_panel,
)


TEXT_COLOR = (242, 245, 248)
MUTED_TEXT_COLOR = (166, 177, 190)


def _format_speed(speed):
    if np.isnan(speed):
        return "N/A"
    return f"{speed:.1f} km/h"


def _format_dashboard_speed(speed, available=True):
    if not available or np.isnan(speed):
        return "N/A"
    return f"{speed:.1f}"


def _put_centered_text(frame, text, center_x, y, scale, color, thickness=1):
    (width, _), _ = cv2.getTextSize(
        text,
        cv2.FONT_HERSHEY_SIMPLEX,
        scale,
        thickness,
    )
    cv2.putText(
        frame,
        text,
        (int(center_x - width / 2), y),
        cv2.FONT_HERSHEY_SIMPLEX,
        scale,
        color,
        thickness,
        cv2.LINE_AA,
    )


def _draw_metric_row(
    frame,
    label,
    values,
    y,
    start_x,
    column_centers,
    scale,
):
    cv2.putText(
        frame,
        label,
        (start_x + round(18 * scale), y),
        cv2.FONT_HERSHEY_SIMPLEX,
        max(0.3, 0.43 * scale),
        MUTED_TEXT_COLOR,
        1,
        cv2.LINE_AA,
    )
    for value, center_x, color in zip(
        values,
        column_centers,
        (PLAYER_1_COLOR, PLAYER_2_COLOR),
    ):
        _put_centered_text(
            frame,
            value,
            center_x,
            y,
            max(0.34, 0.48 * scale),
            color,
            1,
        )


def _get_stats_panel_bounds(frame):
    scale = max(
        0.55,
        min(frame.shape[1] / 1920, frame.shape[0] / 1080),
    )
    width = round(350 * scale)
    height = round(290 * scale)
    margin = round(50 * scale)
    start_x = frame.shape[1] - width - margin
    start_y = min(
        round(620 * scale),
        frame.shape[0] - height - round(40 * scale),
    )
    return (start_x, start_y, start_x + width, start_y + height, scale)


def draw_player_stats(output_video_frames, player_stats):
    for index, row in player_stats.iterrows():
        frame = output_video_frames[index]
        start_x, start_y, end_x, end_y, scale = (
            _get_stats_panel_bounds(frame)
        )

        draw_translucent_panel(
            frame,
            (start_x, start_y),
            (end_x, end_y),
            color=PANEL_COLOR,
            radius=max(9, round(16 * scale)),
        )

        cv2.circle(
            frame,
            (
                start_x + round(22 * scale),
                start_y + round(25 * scale),
            ),
            max(3, round(4 * scale)),
            (145, 255, 120),
            -1,
            cv2.LINE_AA,
        )
        cv2.putText(
            frame,
            "MATCH ANALYTICS",
            (
                start_x + round(34 * scale),
                start_y + round(31 * scale),
            ),
            cv2.FONT_HERSHEY_SIMPLEX,
            max(0.38, 0.55 * scale),
            TEXT_COLOR,
            1,
            cv2.LINE_AA,
        )

        column_centers = (
            start_x + round(235 * scale),
            start_x + round(315 * scale),
        )
        _put_centered_text(
            frame,
            "P1",
            column_centers[0],
            start_y + round(67 * scale),
            max(0.36, 0.5 * scale),
            PLAYER_1_COLOR,
            2,
        )
        _put_centered_text(
            frame,
            "P2",
            column_centers[1],
            start_y + round(67 * scale),
            max(0.36, 0.5 * scale),
            PLAYER_2_COLOR,
            2,
        )
        cv2.line(
            frame,
            (
                start_x + round(18 * scale),
                start_y + round(79 * scale),
            ),
            (
                end_x - round(18 * scale),
                start_y + round(79 * scale),
            ),
            (82, 70, 58),
            1,
            cv2.LINE_AA,
        )

        player_1_shots = int(row["player_1_number_of_shots"])
        player_2_shots = int(row["player_2_number_of_shots"])
        rows = (
            ("Shots", (str(player_1_shots), str(player_2_shots))),
            (
                "Last shot (km/h)",
                (
                    _format_dashboard_speed(
                        row["player_1_last_shot_speed"],
                        not np.isnan(row["player_1_average_shot_speed"]),
                    ),
                    _format_dashboard_speed(
                        row["player_2_last_shot_speed"],
                        not np.isnan(row["player_2_average_shot_speed"]),
                    ),
                ),
            ),
            (
                "Avg shot (km/h)",
                (
                    _format_dashboard_speed(row["player_1_average_shot_speed"]),
                    _format_dashboard_speed(row["player_2_average_shot_speed"]),
                ),
            ),
            (
                "Last move (km/h)",
                (
                    _format_dashboard_speed(
                        row["player_1_last_player_speed"],
                        not np.isnan(row["player_1_average_player_speed"]),
                    ),
                    _format_dashboard_speed(
                        row["player_2_last_player_speed"],
                        not np.isnan(row["player_2_average_player_speed"]),
                    ),
                ),
            ),
            (
                "Avg move (km/h)",
                (
                    _format_dashboard_speed(row["player_1_average_player_speed"]),
                    _format_dashboard_speed(row["player_2_average_player_speed"]),
                ),
            ),
        )
        for row_index, (label, values) in enumerate(rows):
            _draw_metric_row(
                frame,
                label,
                values,
                start_y + round((112 + row_index * 38) * scale),
                start_x,
                column_centers,
                scale,
            )

    return output_video_frames
