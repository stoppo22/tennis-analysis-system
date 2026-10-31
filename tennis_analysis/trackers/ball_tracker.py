
from ultralytics import YOLO
import cv2
import  pickle

from tennis_analysis.utils.visualization_utils import BALL_COLOR, draw_corner_box

from tennis_analysis.utils.shot_detection_utils import (
    DEFAULT_SHOT_PERSISTENCE_SECONDS,
    DEFAULT_SMOOTHING_SECONDS,
    detect_shot_frames,
    interpolate_ball_positions,
)


class BallTracker:
    def __init__(self, model_path):
        self.model = YOLO(model_path)

    def interpolate_ball_positions(self, ball_positions):
        return interpolate_ball_positions(ball_positions)

    def get_ball_shot_frames(
        self,
        ball_positions,
        fps,
        persistence_seconds=DEFAULT_SHOT_PERSISTENCE_SECONDS,
        smoothing_seconds=DEFAULT_SMOOTHING_SECONDS,
    ):
        return detect_shot_frames(
            ball_positions,
            fps,
            persistence_seconds=persistence_seconds,
            smoothing_seconds=smoothing_seconds,
        )



    def detect_frames(self, frames, read_from_stub =False, stub_path = None):
        ball_detections = []

        if read_from_stub and stub_path is not None:
            with open(stub_path, 'rb') as f:
                ball_detections = pickle.load(f)
            return ball_detections

        for frame in frames:
            player_dict = self.detect_frame(frame)
            ball_detections.append(player_dict)

        if stub_path is not None:
            with open(stub_path, 'wb') as f:
                pickle.dump(ball_detections, f)   


        return ball_detections
        

    def detect_frame(self, frame):
        result = self.model.predict(frame, conf=0.15, verbose=False)[0]

        ball_dict = {}
        for box in result.boxes:
            ball_dict[1] = box.xyxy.tolist()[0]
        return ball_dict
    
    def draw_bboxes(self,video_frames, player_detections):
        output_video_frames = []
        for frame, ball_dict in zip(video_frames, player_detections):
            for bbox in ball_dict.values():
                draw_corner_box(
                    frame,
                    bbox,
                    BALL_COLOR,
                    corner_length=8,
                    thickness=2,
                )
                center = (
                    int((bbox[0] + bbox[2]) / 2),
                    int((bbox[1] + bbox[3]) / 2),
                )
                cv2.circle(frame, center, 3, BALL_COLOR, -1, cv2.LINE_AA)
            output_video_frames.append(frame)
        
        return output_video_frames
