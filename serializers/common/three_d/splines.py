import math
from typing import List


class BarrierPath:
    def __init__(self, points: List[List[float]]) -> None:
        super().__init__()
        self.points = points
        self.is_closed = points[0] == points[-1]
        self.z_up = False

    @property
    def middle_points(self):
        return [[(self.points[i][j] + self.points[i + 1][j]) / 2 for j in range(3)] for i in
                range(len(self.points) - 1)]

    @property
    def lengths(self):
        return [math.sqrt((self.points[i][0] - self.points[i + 1][0]) ** 2
                          + (self.points[i][1 if self.z_up else 2] - self.points[i + 1][
            1 if self.z_up else 2]) ** 2)
                for i in range(len(self.points) - 1)]

    @property
    def orientations(self):
        return [math.atan2(self.points[i + 1][0] - self.points[i][0],
                           self.points[i + 1][1 if self.z_up else 2] - self.points[i][1 if self.z_up else 2])
                for i in range(len(self.points) - 1)]

    def fix_angle(self, angle):
        while angle > math.pi:
            angle -= 2 * math.pi
        while angle <= -math.pi:
            angle += 2 * math.pi
        return angle

    def optimize(self):
        orientations = self.orientations
        lengths = self.lengths
        delta_angles = [abs(math.sin(orientations[i] - orientations[i + 1]) * (lengths[i] + lengths[i + 1]))
                        for i in range(len(orientations) - 1)]
        if self.is_closed:
            # make the most valuable angle as break
            break_delta_angle = abs(self.fix_angle(orientations[-1] - orientations[0]))
            max_delta_angle = max(delta_angles)
            if max_delta_angle > break_delta_angle:
                index = delta_angles.index(max_delta_angle)
                self.points = self.points[index + 1:] + self.points[:index + 2]
                orientations = self.orientations
                lengths = self.lengths
                delta_angles = [abs(math.sin(orientations[i] - orientations[i + 1]) * (lengths[i] + lengths[i + 1]))
                                for i in range(len(orientations) - 1)]
        while True:
            min_delta_angle = min(delta_angles)
            if min_delta_angle > 0.3:  # 30cm threshold
                break
            index = delta_angles.index(min_delta_angle)
            self.points = self.points[:index + 1] + self.points[index + 2:]
            orientations = self.orientations
            lengths = self.lengths
            delta_angles = [abs(math.sin(orientations[i] - orientations[i + 1]) * (lengths[i] + lengths[i + 1]))
                            for i in range(len(orientations) - 1)]
