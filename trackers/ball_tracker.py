
from ultralytics import YOLO
import cv2
import  pickle

from utils.shot_detection_utils import (
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
        minimum_change_frames_per_hit=25,
    ):
        return detect_shot_frames(
            ball_positions,
            fps,
            minimum_change_frames_per_hit=minimum_change_frames_per_hit,
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
            #Draw the bounding boxes on the frame
            for track_id, bbox in ball_dict.items():
                x1, y1, x2, y2 = bbox
                cv2.putText(frame, f"Ball ID: {track_id}",(int(bbox[0]),int(bbox[1] -10 )),cv2.FONT_HERSHEY_SIMPLEX, 0.9, (0, 255, 255), 2)
                cv2.rectangle(frame, (int(x1), int(y1)), (int(x2), int(y2)), (0, 255, 255), 2)
            output_video_frames.append(frame)
        
        return output_video_frames
