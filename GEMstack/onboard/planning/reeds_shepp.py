"""
Source: https://github.com/nathanlct/reeds-shepp-curves/blob/master/reeds_shepp.py

Implementation of the optimal path formulas given in the following paper:

OPTIMAL PATHS FOR A CAR THAT GOES BOTH FORWARDS AND BACKWARDS
J. A. REEDS AND L. A. SHEPP

notes: there are some typos in the formulas given in the paper;
some formulas have been adapted (cf http://msl.cs.uiuc.edu/~lavalle/cs326a/rs.c)

Each of the 12 functions (each representing 4 of the 48 possible words)
have 3 arguments x, y and phi, the goal position and angle (in degrees) of the
object given it starts at position (0, 0) and angle 0, and returns the
corresponding path (if it exists) as a list of PathElements (or an empty list).

(actually there are less than 48 possible words but this code is not optimized)
"""

import math
from enum import Enum
from dataclasses import dataclass, replace

def M(theta):
    """
    Return the angle phi = theta mod (2 pi) such that -pi <= theta < pi.
    """
    theta = theta % (2*math.pi)
    if theta < -math.pi: return theta + 2*math.pi
    if theta >= math.pi: return theta - 2*math.pi
    return theta

def R(x, y):
    """
    Return the polar coordinates (r, theta) of the point (x, y).
    """
    r = math.sqrt(x*x + y*y)
    theta = math.atan2(y, x)
    return r, theta

def change_of_basis(p1, p2):
    """
    Given p1 = (x1, y1, theta1) and p2 = (x2, y2, theta2) represented in a
    coordinate system with origin (0, 0) and rotation 0 (in degrees), return
    the position and rotation of p2 in the coordinate system which origin
    (x1, y1) and rotation theta1.
    """
    theta1 = p1[2]
    dx = p2[0] - p1[0]
    dy = p2[1] - p1[1]
    new_x = dx * math.cos(theta1) + dy * math.sin(theta1)
    new_y = -dx * math.sin(theta1) + dy * math.cos(theta1)
    new_theta = p2[2] - p1[2]
    return new_x, new_y, new_theta

def rad2deg(rad):
    return 180 * rad / math.pi

def deg2rad(deg):
    return math.pi * deg / 180

def sign(x):
    return 1 if x >= 0 else -1


class Steering(Enum):
    LEFT = -1
    RIGHT = 1
    STRAIGHT = 0


class Gear(Enum):
    FORWARD = 1
    BACKWARD = -1


@dataclass(eq=True)
class PathElement:
    param: float
    steering: Steering
    gear: Gear

    @classmethod
    def create(cls, param: float, steering: Steering, gear: Gear):
        if param >= 0:
            return cls(param, steering, gear)
        else:
            return cls(-param, steering, gear).reverse_gear()

    def __repr__(self):
        s = "{ Steering: " + self.steering.name + "\tGear: " + self.gear.name \
            + "\tdistance: " + str(round(self.param, 2)) + " }"
        return s

    def reverse_steering(self):
        steering = Steering(-self.steering.value)
        return replace(self, steering=steering)

    def reverse_gear(self):
        gear = Gear(-self.gear.value)
        return replace(self, gear=gear)
    
    def eval(self, t):
        t *= sign(self.gear.value)
        if self.steering == Steering.STRAIGHT:
            return (t, 0., 0.)
        if self.steering == Steering.LEFT:
            return (math.sin(t), 1 - math.cos(t), t)
        if self.steering == Steering.RIGHT:
            return (math.sin(t), math.cos(t) - 1, -t)


def path_length(path):
    """
    this one's obvious
    """
    return sum([e.param for e in path])


def get_optimal_path(start, end):
    """
    Return the shortest path from start to end among those that exist
    """
    paths = get_all_paths(start, end)
    return min(paths, key=path_length)


def get_all_paths(start, end):
    """
    Return a list of all the paths from start to end generated by the
    12 functions and their variants
    """
    path_fns = [path1, path2, path3, path4, path5, path6, \
                path7, path8, path9, path10, path11, path12]
    paths = []

    # get coordinates of end in the set of axis where start is (0,0,0)
    x, y, theta = change_of_basis(start, end)

    for get_path in path_fns:
        # get the four variants for each path type, cf article
        paths.append(get_path(x, y, theta))
        paths.append(timeflip(get_path(-x, y, -theta)))
        paths.append(reflect(get_path(x, -y, -theta)))
        paths.append(reflect(timeflip(get_path(-x, -y, theta))))

    # remove path elements that have parameter 0
    for i in range(len(paths)):
        paths[i] = list(filter(lambda e: e.param != 0, paths[i]))

    # remove empty paths
    paths = list(filter(None, paths))

    return paths

def eval_path(path, start, radius=1, resolution=0.1):
    """
    Given a path and a starting position, return the list of positions
    along the path
    """
    points = []
    for e in path:
        t = 0
        ps = []
        while t < e.param:
            dt = min(resolution, e.param-t)
            t += dt
            x, y, theta = e.eval(t)
            xp = (x * math.cos(start[2]) - y * math.sin(start[2])) * radius + start[0]
            yp = (x * math.sin(start[2]) + y * math.cos(start[2])) * radius + start[1]
            thetap = M(theta + start[2])
            ps.append([xp, yp, thetap, e.gear.value])
        start = ps[-1]
        points += ps
    return points


def timeflip(path):
    """
    timeflip transform described around the end of the article
    """
    new_path = [e.reverse_gear() for e in path]
    return new_path


def reflect(path):
    """
    reflect transform described around the end of the article
    """
    new_path = [e.reverse_steering() for e in path]
    return new_path


def path1(x, y, phi):
    """
    Formula 8.1: CSC (same turns)
    """
    path = []

    u, t = R(x - math.sin(phi), y - 1 + math.cos(phi))
    v = M(phi - t)

    path.append(PathElement.create(t, Steering.LEFT, Gear.FORWARD))
    path.append(PathElement.create(u, Steering.STRAIGHT, Gear.FORWARD))
    path.append(PathElement.create(v, Steering.LEFT, Gear.FORWARD))

    return path


def path2(x, y, phi):
    """
    Formula 8.2: CSC (opposite turns)
    """
    phi = M(phi)
    path = []

    rho, t1 = R(x + math.sin(phi), y - 1 - math.cos(phi))

    if rho * rho >= 4:
        u = math.sqrt(rho * rho - 4)
        t = M(t1 + math.atan2(2, u))
        v = M(t - phi)

        path.append(PathElement.create(t, Steering.LEFT, Gear.FORWARD))
        path.append(PathElement.create(u, Steering.STRAIGHT, Gear.FORWARD))
        path.append(PathElement.create(v, Steering.RIGHT, Gear.FORWARD))

    return path


def path3(x, y, phi):
    """
    Formula 8.3: C|C|C
    """
    path = []

    xi = x - math.sin(phi)
    eta = y - 1 + math.cos(phi)
    rho, theta = R(xi, eta)

    if rho <= 4:
        A = math.acos(rho / 4)
        t = M(theta + math.pi/2 + A)
        u = M(math.pi - 2*A)
        v = M(phi - t - u)

        path.append(PathElement.create(t, Steering.LEFT, Gear.FORWARD))
        path.append(PathElement.create(u, Steering.RIGHT, Gear.BACKWARD))
        path.append(PathElement.create(v, Steering.LEFT, Gear.FORWARD))

    return path


def path4(x, y, phi):
    """
    Formula 8.4 (1): C|CC
    """
    path = []

    xi = x - math.sin(phi)
    eta = y - 1 + math.cos(phi)
    rho, theta = R(xi, eta)

    if rho <= 4:
        A = math.acos(rho / 4)
        t = M(theta + math.pi/2 + A)
        u = M(math.pi - 2*A)
        v = M(t + u - phi)

        path.append(PathElement.create(t, Steering.LEFT, Gear.FORWARD))
        path.append(PathElement.create(u, Steering.RIGHT, Gear.BACKWARD))
        path.append(PathElement.create(v, Steering.LEFT, Gear.BACKWARD))

    return path


def path5(x, y, phi):
    """
    Formula 8.4 (2): CC|C
    """
    path = []

    xi = x - math.sin(phi)
    eta = y - 1 + math.cos(phi)
    rho, theta = R(xi, eta)

    if rho <= 4:
        u = math.acos(1 - rho*rho/8)
        A = math.asin(2 * math.sin(u) / rho)
        t = M(theta + math.pi/2 - A)
        v = M(t - u - phi)

        path.append(PathElement.create(t, Steering.LEFT, Gear.FORWARD))
        path.append(PathElement.create(u, Steering.RIGHT, Gear.FORWARD))
        path.append(PathElement.create(v, Steering.LEFT, Gear.BACKWARD))

    return path


def path6(x, y, phi):
    """
    Formula 8.7: CCu|CuC
    """
    path = []

    xi = x + math.sin(phi)
    eta = y - 1 - math.cos(phi)
    rho, theta = R(xi, eta)

    if rho <= 4:
        if rho <= 2:
            A = math.acos((rho + 2) / 4)
            t = M(theta + math.pi/2 + A)
            u = M(A)
            v = M(phi - t + 2*u)
        else:
            A = math.acos((rho - 2) / 4)
            t = M(theta + math.pi/2 - A)
            u = M(math.pi - A)
            v = M(phi - t + 2*u)

        path.append(PathElement.create(t, Steering.LEFT, Gear.FORWARD))
        path.append(PathElement.create(u, Steering.RIGHT, Gear.FORWARD))
        path.append(PathElement.create(u, Steering.LEFT, Gear.BACKWARD))
        path.append(PathElement.create(v, Steering.RIGHT, Gear.BACKWARD))

    return path


def path7(x, y, phi):
    """
    Formula 8.8: C|CuCu|C
    """
    path = []

    xi = x + math.sin(phi)
    eta = y - 1 - math.cos(phi)
    rho, theta = R(xi, eta)
    u1 = (20 - rho*rho) / 16

    if rho <= 6 and 0 <= u1 <= 1:
        u = math.acos(u1)
        A = math.asin(2 * math.sin(u) / rho)
        t = M(theta + math.pi/2 + A)
        v = M(t - phi)

        path.append(PathElement.create(t, Steering.LEFT, Gear.FORWARD))
        path.append(PathElement.create(u, Steering.RIGHT, Gear.BACKWARD))
        path.append(PathElement.create(u, Steering.LEFT, Gear.BACKWARD))
        path.append(PathElement.create(v, Steering.RIGHT, Gear.FORWARD))

    return path


def path8(x, y, phi):
    """
    Formula 8.9 (1): C|C[pi/2]SC
    """
    path = []

    xi = x - math.sin(phi)
    eta = y - 1 + math.cos(phi)
    rho, theta = R(xi, eta)

    if rho >= 2:
        u = math.sqrt(rho*rho - 4) - 2
        A = math.atan2(2, u+2)
        t = M(theta + math.pi/2 + A)
        v = M(t - phi + math.pi/2)

        path.append(PathElement.create(t, Steering.LEFT, Gear.FORWARD))
        path.append(PathElement.create(math.pi/2, Steering.RIGHT, Gear.BACKWARD))
        path.append(PathElement.create(u, Steering.STRAIGHT, Gear.BACKWARD))
        path.append(PathElement.create(v, Steering.LEFT, Gear.BACKWARD))

    return path


def path9(x, y, phi):
    """
    Formula 8.9 (2): CSC[pi/2]|C
    """
    path = []

    xi = x - math.sin(phi)
    eta = y - 1 + math.cos(phi)
    rho, theta = R(xi, eta)

    if rho >= 2:
        u = math.sqrt(rho*rho - 4) - 2
        A = math.atan2(u+2, 2)
        t = M(theta + math.pi/2 - A)
        v = M(t - phi - math.pi/2)

        path.append(PathElement.create(t, Steering.LEFT, Gear.FORWARD))
        path.append(PathElement.create(u, Steering.STRAIGHT, Gear.FORWARD))
        path.append(PathElement.create(math.pi/2, Steering.RIGHT, Gear.FORWARD))
        path.append(PathElement.create(v, Steering.LEFT, Gear.BACKWARD))

    return path


def path10(x, y, phi):
    """
    Formula 8.10 (1): C|C[pi/2]SC
    """
    path = []

    xi = x + math.sin(phi)
    eta = y - 1 - math.cos(phi)
    rho, theta = R(xi, eta)

    if rho >= 2:
        t = M(theta + math.pi/2)
        u = rho - 2
        v = M(phi - t - math.pi/2)

        path.append(PathElement.create(t, Steering.LEFT, Gear.FORWARD))
        path.append(PathElement.create(math.pi/2, Steering.RIGHT, Gear.BACKWARD))
        path.append(PathElement.create(u, Steering.STRAIGHT, Gear.BACKWARD))
        path.append(PathElement.create(v, Steering.RIGHT, Gear.BACKWARD))

    return path


def path11(x, y, phi):
    """
    Formula 8.10 (2): CSC[pi/2]|C
    """
    path = []

    xi = x + math.sin(phi)
    eta = y - 1 - math.cos(phi)
    rho, theta = R(xi, eta)

    if rho >= 2:
        t = M(theta)
        u = rho - 2
        v = M(phi - t - math.pi/2)

        path.append(PathElement.create(t, Steering.LEFT, Gear.FORWARD))
        path.append(PathElement.create(u, Steering.STRAIGHT, Gear.FORWARD))
        path.append(PathElement.create(math.pi/2, Steering.LEFT, Gear.FORWARD))
        path.append(PathElement.create(v, Steering.RIGHT, Gear.BACKWARD))

    return path


def path12(x, y, phi):
    """
    Formula 8.11: C|C[pi/2]SC[pi/2]|C
    """
    path = []

    xi = x + math.sin(phi)
    eta = y - 1 - math.cos(phi)
    rho, theta = R(xi, eta)

    if rho >= 4:
        u = math.sqrt(rho*rho - 4) - 4
        A = math.atan2(2, u+4)
        t = M(theta + math.pi/2 + A)
        v = M(t - phi)

        path.append(PathElement.create(t, Steering.LEFT, Gear.FORWARD))
        path.append(PathElement.create(math.pi/2, Steering.RIGHT, Gear.BACKWARD))
        path.append(PathElement.create(u, Steering.STRAIGHT, Gear.BACKWARD))
        path.append(PathElement.create(math.pi/2, Steering.LEFT, Gear.BACKWARD))
        path.append(PathElement.create(v, Steering.RIGHT, Gear.FORWARD))

    return path

import numpy as np
from ...utils import settings

precomputed = settings.get("planner.search_planner.precomputed", None)
HS, RESOLUTION, ANGLE_RESOLUTION, BOUNDS = None, None, None, None

def load_precomputed():
    try:
        h_dict = np.load(precomputed, allow_pickle=True).item()
        hs = h_dict['hs']
        resolution = h_dict['resolution']
        angle_resolution = h_dict['angle_resolution']
        bounds = h_dict['bounds']
    except:
        print("WARNING: Could not load precomputed heuristic")
        hs, resolution, angle_resolution, bounds = None, None, None, None
    return hs, resolution, angle_resolution, bounds

if precomputed is not None:
    HS, RESOLUTION, ANGLE_RESOLUTION, BOUNDS = load_precomputed()

def precompute(start, end):
    if HS is None:
        return path_length(get_optimal_path(start, end))
    x, y, phi = change_of_basis(start, end)
    x = round(x/RESOLUTION)
    y = round(y/RESOLUTION)
    phi = round(rad2deg(phi)/ANGLE_RESOLUTION) % HS.shape[2]
    x, y, phi = abs(x), abs(y), abs(phi)
    if x >= HS.shape[0] or y >= HS.shape[1]:
        return path_length(get_optimal_path(start, end))
    return HS[x, y, phi]


