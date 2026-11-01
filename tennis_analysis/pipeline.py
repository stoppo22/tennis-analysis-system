import hashlib
from pathlib import Path

import cv2

from tennis_analysis.mini_court import MiniCourt
from tennis_analysis.utils import (
    build_player_stats_dataframe,
    calculate_player_stats_data,
    draw_player_stats,
    read_video,
    resolve_statistics_output_path,
    save_player_stats_csv,
    save_video,
)
from tennis_analysis.utils.detection_filters import suppress_static_detections
from tennis_analysis.utils.shot_detectors import (
    DEFAULT_SHOT_DETECTOR,
    detect_shots,
    validate_shot_detector,
)
from tennis_analysis.utils.visualization_utils import draw_translucent_panel

DETECTION_CACHE_VERSION = "1"

DEFAULT_PLAYER_MODEL_PATH = "yolo11l.pt"
DEFAULT_BALL_MODEL_PATH = "models/yolov11best.pt"
DEFAULT_COURT_MODEL_PATH = "models/keypoints_model.pth"
DEFAULT_CACHE_DIRECTORY = "tracker_stubs"

SHOT_BADGE_SECONDS = 0.35


def _calculate_file_sha256(file_path):
    hasher = hashlib.sha256()

    with file_path.open("rb") as file:
        for chunk in iter(lambda: file.read(1024 * 1024), b""):
            hasher.update(chunk)

    return hasher.hexdigest()


def _build_detection_cache_path(
    cache_directory,
    detector_name,
    video_path,
    model_path,
):
    cache_identity = "\0".join(
        [
            DETECTION_CACHE_VERSION,
            detector_name,
            _calculate_file_sha256(video_path),
            _calculate_file_sha256(model_path),
        ]
    )
    cache_digest = hashlib.sha256(cache_identity.encode("utf-8")).hexdigest()

    return cache_directory / f"{detector_name}_{cache_digest}.pkl"


def _require_files(required_files):
    """Raise ``FileNotFoundError`` listing every missing ``{description: path}``."""
    missing_files = [
        f"{description}: {path}"
        for description, path in required_files.items()
        if not Path(path).is_file()
    ]

    if missing_files:
        formatted_missing_files = "\n".join(
            f"- {missing_file}" for missing_file in missing_files
        )
        raise FileNotFoundError(f"Missing required files:\n{formatted_missing_files}")


def _filter_ball_detections(ball_detections, fps, frame_width, suppress_static):
    """Optionally drop detections that stay in one place (marks mistaken for the ball).

    Returns ``(detections, removed_count)``; with ``suppress_static`` false the
    detections are returned unchanged.
    """
    if not suppress_static:
        return ball_detections, 0
    return suppress_static_detections(ball_detections, fps, frame_width)


def _draw_frame_overlays(frames, fps, shot_frames):
    """Draw the frame/time panel and, near each shot, a "SHOT EVENT" badge."""
    shot_badge_duration_frames = max(1, round(fps * SHOT_BADGE_SECONDS))

    for i, frame in enumerate(frames):
        draw_translucent_panel(
            frame,
            (20, 18),
            (250, 62),
            opacity=0.82,
            radius=12,
        )
        cv2.putText(
            frame,
            f"FRAME {i + 1:04d}   {i / fps:05.2f}s",
            (36, 47),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.55,
            (242, 245, 248),
            1,
            cv2.LINE_AA,
        )

        recent_shot = any(
            0 <= i - shot_frame < shot_badge_duration_frames
            for shot_frame in shot_frames
        )
        if recent_shot:
            badge_start_x = frame.shape[1] // 2 - 95
            draw_translucent_panel(
                frame,
                (badge_start_x, 18),
                (badge_start_x + 190, 62),
                color=(78, 38, 52),
                opacity=0.9,
                radius=12,
            )
            cv2.circle(
                frame,
                (badge_start_x + 22, 40),
                5,
                (0, 235, 255),
                -1,
                cv2.LINE_AA,
            )
            cv2.putText(
                frame,
                "SHOT EVENT",
                (badge_start_x + 36, 47),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.55,
                (242, 245, 248),
                1,
                cv2.LINE_AA,
            )

    return frames


def analyze_video(
    input_video_path,
    output_video_path,
    statistics_output_path=None,
    player_model_path=DEFAULT_PLAYER_MODEL_PATH,
    ball_model_path=DEFAULT_BALL_MODEL_PATH,
    court_model_path=DEFAULT_COURT_MODEL_PATH,
    cache_directory=DEFAULT_CACHE_DIRECTORY,
    shot_detector=DEFAULT_SHOT_DETECTOR,
    suppress_static=False,
):
    """Analyze a video and return paths plus basic processing metadata.

    ``shot_detector`` selects the shot-event method (see
    ``tennis_analysis.utils.shot_detectors``). With ``suppress_static`` the ball
    detections that stay in the same place for about a second are removed before the
    gaps are interpolated; they are marks on the court mistaken for the ball.
    """
    # Heavy dependencies are imported here so that importing this module, running
    # ``--help`` and the unit tests do not require PyTorch or Ultralytics.
    from tennis_analysis.court_line_detector import CourtLineDetector
    from tennis_analysis.trackers import BallTracker, PlayerTracker

    input_path = Path(input_video_path)
    output_path = Path(output_video_path)
    statistics_path = resolve_statistics_output_path(
        output_path,
        statistics_output_path,
    )

    player_model_path = Path(player_model_path)
    ball_model_path = Path(ball_model_path)
    court_model_path = Path(court_model_path)

    _require_files(
        {
            "input video": input_path,
            "player detection model": player_model_path,
            "ball detection model": ball_model_path,
            "court keypoint model": court_model_path,
        }
    )
    validate_shot_detector(shot_detector)

    output_path.parent.mkdir(parents=True, exist_ok=True)

    cache_directory = Path(cache_directory)
    cache_directory.mkdir(parents=True, exist_ok=True)

    player_stub_path = _build_detection_cache_path(
        cache_directory=cache_directory,
        detector_name="player_detections",
        video_path=input_path,
        model_path=player_model_path,
    )
    ball_stub_path = _build_detection_cache_path(
        cache_directory=cache_directory,
        detector_name="ball_detections",
        video_path=input_path,
        model_path=ball_model_path,
    )

    video_frames, fps = read_video(input_video_path)

    # Detect players and ball
    player_tracker = PlayerTracker(model_path=str(player_model_path))
    ball_tracker = BallTracker(model_path=str(ball_model_path))

    player_detections = player_tracker.detect_frames(
        video_frames,
        read_from_stub=player_stub_path.exists(),
        stub_path=player_stub_path,
    )

    ball_detections = ball_tracker.detect_frames(
        video_frames,
        read_from_stub=ball_stub_path.exists(),
        stub_path=ball_stub_path,
    )
    ball_detections, static_removed = _filter_ball_detections(
        ball_detections, fps, video_frames[0].shape[1], suppress_static
    )
    ball_detections = ball_tracker.interpolate_ball_positions(ball_detections)

    # Detect court keypoints
    court_line_detector = CourtLineDetector(str(court_model_path))
    court_keypoints = court_line_detector.predict(video_frames[0])

    # Choose and filter players based on court keypoints
    player_detections = player_tracker.choose_and_filter_players(
        court_keypoints, player_detections
    )

    mini_court = MiniCourt(video_frames[0])

    ball_shot_frames = detect_shots(shot_detector, ball_detections, fps)

    # Convert positions to mini court positions
    (
        player_mini_court_detections,
        ball_mini_court_detections,
    ) = mini_court.convert_bounding_boxes_to_mini_court_coordinates(
        player_detections, ball_detections, court_keypoints
    )

    player_stats_data = calculate_player_stats_data(
        ball_shot_frames=ball_shot_frames,
        player_positions=player_mini_court_detections,
        ball_positions=ball_mini_court_detections,
        fps=fps,
        mini_court_width=mini_court.get_width_mini_court(),
    )

    player_stats_data_df = build_player_stats_dataframe(
        player_stats_data,
        frame_count=len(video_frames),
    )

    # Draw output: boxes, court keypoints, mini court, statistics, overlays
    output_video_frames = player_tracker.draw_bboxes(video_frames, player_detections)
    output_video_frames = ball_tracker.draw_bboxes(output_video_frames, ball_detections)
    output_video_frames = court_line_detector.draw_keypoints_on_video(
        output_video_frames,
        court_keypoints,
        show_labels=False,
    )
    output_video_frames = mini_court.draw_mini_court(output_video_frames)
    output_video_frames = mini_court.draw_points_on_mini_court(
        output_video_frames, player_mini_court_detections
    )
    output_video_frames = mini_court.draw_points_on_mini_court(
        output_video_frames, ball_mini_court_detections, color=(0, 255, 255)
    )
    output_video_frames = draw_player_stats(output_video_frames, player_stats_data_df)
    output_video_frames = _draw_frame_overlays(
        output_video_frames, fps, ball_shot_frames
    )

    save_video(output_video_frames, output_video_path, fps)
    save_player_stats_csv(player_stats_data_df, statistics_path)

    return {
        "output_video_path": str(output_path),
        "statistics_csv_path": str(statistics_path),
        "fps": fps,
        "frame_count": len(video_frames),
        "duration_seconds": len(video_frames) / fps,
        "detected_shot_frames": [int(frame) for frame in ball_shot_frames],
        "shot_detector": shot_detector,
        "static_detections_removed": static_removed,
    }
