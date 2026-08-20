import cv2

def read_video(video_path):
    cap = cv2.VideoCapture(video_path)
    frames = []
    if not cap.isOpened():
        raise ValueError(f"Error opening video file: {video_path}")
    fps = cap.get(cv2.CAP_PROP_FPS)
    if fps <= 0:
        cap.release()
        raise ValueError(f"Invalid frame rate for video file: {video_path}")
    while(True):
        ret, frame = cap.read()
        if not ret:
            break
        frames.append(frame) 
    
    cap.release()

    if not frames:
        raise ValueError(f"No frames could be read from video file: {video_path}")

    return frames, fps


def save_video(output_video_frames, output_video_path, fps):
    if not output_video_frames:
        raise ValueError("Cannot save a video without frames")
    if fps <= 0:
        raise ValueError(f"Cannot save a video with invalid frame rate: {fps}")

    frame_height, frame_width = output_video_frames[0].shape[:2]
    fourcc = cv2.VideoWriter_fourcc(*"MJPG")
    out = cv2.VideoWriter(
        output_video_path,
        fourcc,
        fps,
        (frame_width, frame_height),
    )

    if not out.isOpened():
        out.release()
        raise ValueError(f"Error opening output video file: {output_video_path}")

    try:
        for frame_number, frame in enumerate(output_video_frames):
            if frame.shape[:2] != (frame_height, frame_width):
                raise ValueError(
                    "All output video frames must have the same dimensions; "
                    f"frame {frame_number} has shape {frame.shape[:2]}"
                )
            out.write(frame)
    finally:
        out.release()
