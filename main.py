from pipeline import analyze_video


def main():
    analyze_video(
        input_video_path="input_videos/input_video.mp4",
        output_video_path="output_videos/output_video.avi",
    )


if __name__ == "__main__":
    main()