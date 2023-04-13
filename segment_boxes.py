import numpy as np
import cv2


def segment_and_draw_boxes_by_aruco(draw, arucos, K, D,
        aruco_margin=0.0095, box_size=0.03):
    assert arucos.n_poses == 1
    n = arucos.n
    polygons_list = list()
    for i in range(n):
        rvec = arucos.rvecs[i, 0]
        R, _ = cv2.Rodrigues(rvec)
        x = R[:, 0]
        y = R[:, 1]
        z = R[:, 2]
        center = arucos.tvecs[i, 0]

        box_corners = list()
        aruco_size = arucos.aruco_sizes[i]
        first_corner = center + \
            -x * (aruco_size / 2 + aruco_margin) + \
            y * (aruco_size / 2 + aruco_margin)
        for dx, dy, dz in [(0, 0, 0), (1, 0, 0), (1, -1, 0), (0, -1, 0),
                (0, 0, -1), (1, 0, -1), (1, -1, -1), (0, -1, -1)]:
            box_corner = np.array(
                first_corner +
                x * dx * box_size +
                y * dy * box_size +
                z * dz * box_size)
            box_corners.append(box_corner)
        box_corners = np.array(box_corners)
        # box_corners.shape = (8, 3)

        top_face = box_corners[[0, 1, 2, 3], :]
        front_face = box_corners[[3, 2, 6, 7], :]
        right_face = box_corners[[2, 1, 5, 6], :]
        left_face = box_corners[[0, 3, 7, 4], :]
        bottom_face = box_corners[[7, 6, 5, 4], :]
        back_face = box_corners[[1, 0, 4, 5], :]
        box_faces = np.stack(
            (top_face, front_face, right_face, left_face, bottom_face, back_face),
            axis=0)
        # box_faces.shape = (6, 4, 3)

        segmented = np.zeros(draw.shape[:2], dtype=np.uint8)
        points, _ = \
            cv2.projectPoints(box_faces.reshape(-1, 3), np.zeros(3), np.zeros(3), K, D)
        points = points.reshape(6, 4, 2).astype(np.int)
        for pts in points:
            cv2.fillPoly(segmented, [pts], 255)

        polygons, _ = \
            cv2.findContours(segmented, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        assert len(polygons) == 1
        polygon = polygons[0].reshape(-1, 2)
        polygons_list.append(polygon)

    cv2.polylines(draw, polygons_list, True, (255, 255, 255), thickness=1)
    overlay = draw.copy()
    for polygon in polygons_list:
        cv2.fillPoly(overlay, [polygon], (255, 255, 255))
    cv2.addWeighted(draw, 0.7, overlay, 0.3, 0, dst=draw)


def segment_boxes_by_color(image: np.ndarray):
    assert len(image.shape) == 3
    hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV_FULL)
    # shift hue so that red color is continuous
    hsv = hsv + np.array([150, 0, 0], dtype=np.uint8).reshape(1, 1, 3)

    low = np.array([150 - 14, 100, 110], dtype=np.uint8)
    up = np.array([150 + 14, 255, 255], dtype=np.uint8)
    mask = cv2.inRange(hsv, low, up)
    polygons_red, _ = \
        cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)

    low = np.array([55 - 14, 100, 110], dtype=np.uint8)
    up = np.array([55 + 14, 255, 255], dtype=np.uint8)
    mask = cv2.inRange(hsv, low, up)
    polygons_blue, _ = \
        cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)

    mask[...] = 0
    num_red = 0
    num_blue = 0
    for polygon in polygons_red:
        if len(polygon) < 100:
            continue
        cv2.fillPoly(mask, [polygon], 255)
        num_red += 1
    for polygon in polygons_blue:
        if len(polygon) < 100:
            continue
        cv2.fillPoly(mask, [polygon], 255)
        num_blue += 1

    return mask, (num_red, num_blue)
