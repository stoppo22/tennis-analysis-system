from utils import (read_video,
                    save_video,
                    draw_player_stats,
                    calculate_player_stats_data,
                    build_player_stats_dataframe,
                    resolve_statistics_output_path,
                    save_player_stats_csv)

from trackers import PlayerTracker, BallTracker
from court_line_detector import CourtLineDetector
from mini_court import MiniCourt
import cv2
import hashlib
from pathlib import Path
from utils.shot_detection_utils import (
    DEFAULT_SHOT_PERSISTENCE_SECONDS,
    DEFAULT_SMOOTHING_SECONDS,
)
from utils.visualization_utils import draw_translucent_panel


DETECTION_CACHE_VERSION = "1"


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


def analyze_video(
    input_video_path,
    output_video_path,
    statistics_output_path=None,
):
    """Analyze a video and return paths plus basic processing metadata."""
    input_path = Path(input_video_path)
    output_path = Path(output_video_path)
    statistics_path = resolve_statistics_output_path(
        output_path,
        statistics_output_path,
    )

    player_model_path = Path("yolo11l.pt")
    ball_model_path = Path("models/yolov11best.pt")
    court_model_path = Path("models/keypoints_model.pth")

    required_files = {
        "input video": input_path,
        "player detection model": player_model_path,
        "ball detection model": ball_model_path,
        "court keypoint model": court_model_path,
    }

    missing_files = [
        f"{description}: {path}"
        for description, path in required_files.items()
        if not path.is_file()
    ]

    if missing_files:
        formatted_missing_files = "\n".join(
            f"- {missing_file}" for missing_file in missing_files
        )
        raise FileNotFoundError(
            f"Missing required files:\n{formatted_missing_files}"
        )

    output_path.parent.mkdir(parents=True, exist_ok=True)

    cache_directory = Path("tracker_stubs")
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
    ball_detections = ball_tracker.interpolate_ball_positions(
        ball_detections
    )

    # Detect court keypoints
    court_line_detector = CourtLineDetector(str(court_model_path))
    court_keypoints = court_line_detector.predict(video_frames[0])

    #Choose and filter players based on court keypoints
    player_detections = player_tracker.choose_and_filter_players(court_keypoints, player_detections)

    #Mini court
    mini_court = MiniCourt(video_frames[0])

    #Detect ball shots 
    ball_shot_frames = ball_tracker.get_ball_shot_frames(
        ball_detections,
        fps,
        persistence_seconds=DEFAULT_SHOT_PERSISTENCE_SECONDS,
        smoothing_seconds=DEFAULT_SMOOTHING_SECONDS,
    )

   #Convert positions to mini court positions
    player_mini_court_detections, ball_mini_court_detections = mini_court.convert_bounding_boxes_to_mini_court_coordinates(player_detections, ball_detections, court_keypoints)


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

    





    #Draw output
    
    ##Draw bounding boxes on video frames
    output_video_frames = player_tracker.draw_bboxes(video_frames, player_detections)
    output_video_frames = ball_tracker.draw_bboxes(output_video_frames, ball_detections)
    
    ##Draw keypoints 
    output_video_frames = court_line_detector.draw_keypoints_on_video(
        output_video_frames,
        court_keypoints,
        show_labels=False,
    )

    ##Draw mini court
    output_video_frames = mini_court.draw_mini_court(output_video_frames)
    output_video_frames = mini_court.draw_points_on_mini_court(output_video_frames, player_mini_court_detections)
    output_video_frames = mini_court.draw_points_on_mini_court(output_video_frames, ball_mini_court_detections, color=(0,255,255))


   ##Draw player stats on video frames
    output_video_frames = draw_player_stats(output_video_frames, player_stats_data_df)

    shot_badge_duration_frames = max(1, round(fps * 0.35))
    for i, frame in enumerate(output_video_frames):
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
            for shot_frame in ball_shot_frames
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

    # Save output video
    save_video(output_video_frames, output_video_path, fps)
    save_player_stats_csv(player_stats_data_df, statistics_path)

    return {
        "output_video_path": str(output_path),
        "statistics_csv_path": str(statistics_path),
        "fps": fps,
        "frame_count": len(video_frames),
        "duration_seconds": len(video_frames) / fps,
        "detected_shot_frames": [int(frame) for frame in ball_shot_frames],
    }
