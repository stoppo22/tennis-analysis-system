def getCenter(bbox):
    """
    Calculate the center of a bounding box.
    
    Args:
        bbox (list): A list containing the coordinates of the bounding box in the format [x1, y1, x2, y2].
    
    Returns:
        tuple: A tuple containing the center coordinates (cx, cy).
    """
    x1, y1, x2, y2 = bbox
    center_x = int((x1 + x2) / 2)
    center_y = int((y1 + y2) / 2)
    return (center_x, center_y)
def measure_distance(p1,p2):
    return ((p1[0] - p2[0])**2 + (p1[1] - p2[1])**2)**0.5

def get_foot_position(bbox):
    """
    Estimate the foot position of a player based on the bounding box.
    
    Args:
        bbox (list): A list containing the coordinates of the bounding box in the format [x1, y1, x2, y2].
    
    Returns:
        tuple: A tuple containing the estimated foot position coordinates (foot_x, foot_y).
    """
    x1, y1, x2, y2 = bbox
    foot_x = int((x1 + x2) / 2)
    foot_y = y2  # Assuming the bottom of the bounding box corresponds to the feet
    return (foot_x, foot_y)

def get_closest_keypoints_index(point, keypoints, keypoint_indices):
    closest_distance = float('inf')
    key_point_ind = keypoint_indices[0]
    for keypoints_indix in keypoint_indices:
        keypoint=  keypoints[keypoints_indix*2], keypoints[keypoints_indix*2+1]
        distance = abs(point[1]-keypoint[1])
        if distance < closest_distance:
            closest_distance = distance
            key_point_ind = keypoints_indix

    return key_point_ind

def get_height_of_bbox(bbox):
    return bbox[3]-bbox[1]

def measure_xy_distance(p1,p2):
    return abs(p1[0] - p2[0]), abs(p1[1] - p2[1])