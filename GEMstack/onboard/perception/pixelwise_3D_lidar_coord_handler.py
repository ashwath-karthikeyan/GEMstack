import sys
import os
import cv2
import argparse
import random
import struct
import ctypes
import numpy as np
from typing import Dict, Tuple, List
import sensor_msgs.point_cloud2 as pc2


class PixelWise3DLidarCoordHandler:
    """ Get pixelwise 3D lidar coordinate relative to the vehicle """

    def __init__(self,
                 kernel_size=5,
                 extrinsic_fn="../../knowledge/calibration/gem_e4_lidar2oak.txt",
                 intrinsic_fn="../../knowledge/calibration/gem_e4_intrinsic.txt",
                 lidar2vehicle_fn="../../knowledge/calibration/gem_e4_lidar2vehicle.txt",
                 xrange=(0, 20),
                 yrange=(-10, 10),
                 zrange=(-3, 1)) -> None:
        
        self.extrinsic = np.loadtxt(extrinsic_fn)
        self.intrinsic = np.loadtxt(intrinsic_fn)
        self.T_lidar2_Gem = np.loadtxt(lidar2vehicle_fn)
        self.intrinsic = np.concatenate(
            [self.intrinsic, np.zeros((3, 1))], axis=1)
        
        self.kernel_size = kernel_size

        # For saving computation resource, only process lidar points within predefined range.
        # These range values are using lidar frame.
        self.xrange = xrange
        self.yrange = yrange
        self.zrange = zrange

    def interpolate(self, coord_3d_map):
        def interpolate_single_channel(image, kernel):
            """ helper function """
            kernel = cv2.flip(kernel, flipCode=-1)
            result = cv2.filter2D(
                image, -1, kernel, borderType=cv2.BORDER_CONSTANT)

            # Derive num_elements matrix
            has_value = image > 0
            has_value = has_value.astype(np.uint8)
            num_elements_mat = cv2.filter2D(
                has_value, -1, kernel, borderType=cv2.BORDER_CONSTANT)

            # divide by num of elements correspond to that particular pixel
            num_elements_mat[num_elements_mat == 0] = 1  # avoid divide by zero
            final_result = result / num_elements_mat  # divide element-wise
            return final_result

        # do interpolation
        channels = []
        num_channels = coord_3d_map.shape[-1]
        for i in range(num_channels):
            channel = coord_3d_map[:, :, i]
            kernel = np.ones(
                (self.kernel_size, self.kernel_size), dtype=np.float32)
            result = interpolate_single_channel(channel, kernel)
            channels.append(result)

        interpolate_3D_map = cv2.merge(channels)
        return interpolate_3D_map

    def filter_lidar_by_range(self, point_cloud, xrange: Tuple[float, float], yrange: Tuple[float, float], zrange: Tuple[float, float]):
        xmin, xmax = xrange
        ymin, ymax = yrange
        zmin, zmax = zrange
        idxs = np.where((point_cloud[:, 0] > xmin) & (point_cloud[:, 0] < xmax) &
                        (point_cloud[:, 1] > ymin) & (point_cloud[:, 1] < ymax) &
                        (point_cloud[:, 2] > zmin) & (point_cloud[:, 2] < zmax))
        return point_cloud[idxs]

    def lidar_to_image(self, point_cloud_lidar: np.ndarray, extrinsic: np.ndarray, intrinsic: np.ndarray):

        homo_point_cloud_lidar = np.hstack(
            (point_cloud_lidar, np.ones((point_cloud_lidar.shape[0], 1))))  # (N, 4)
        pointcloud_pixel = (intrinsic @ extrinsic @
                            (homo_point_cloud_lidar).T)  # (3, N)
        pointcloud_pixel = pointcloud_pixel.T  # (N, 3)

        # normalize
        pointcloud_pixel[:, 0] /= pointcloud_pixel[:, 2]  # normalize
        pointcloud_pixel[:, 1] /= pointcloud_pixel[:, 2]  # normalize
        point_cloud_image = pointcloud_pixel[:, :2]  # (N, 2)
        return point_cloud_image

    def lidar_to_vehicle(self, point_cloud_lidar: np.ndarray, T_lidar2_Gem: np.ndarray):
        ones = np.ones((point_cloud_lidar.shape[0], 1))
        pcd_homogeneous = np.hstack((point_cloud_lidar, ones))  # (N, 4)
        pointcloud_trans = np.dot(T_lidar2_Gem, pcd_homogeneous.T)  # (4, N)
        pointcloud_trans = pointcloud_trans.T  # (N, 4)
        point_cloud_image_world = pointcloud_trans[:, :3]  # (N, 3)
        return point_cloud_image_world

    def get3DCoord(self, image, point_cloud):
        filtered_point_cloud = self.filter_lidar_by_range(
            point_cloud, self.xrange, self.yrange, self.zrange)

        point_cloud_3D = self.lidar_to_vehicle(
            filtered_point_cloud, self.T_lidar2_Gem)

        point_cloud_image = self.lidar_to_image(filtered_point_cloud,
                                                self.extrinsic,
                                                self.intrinsic)

        # Keep only the lidar points whose projected coordinates lie within the boundary of images
        height, width = image.shape[:2]
        idxs = np.where((point_cloud_image[:, 0] > 0) & (point_cloud_image[:, 0] < width) &
                        (point_cloud_image[:, 1] > 0) & (point_cloud_image[:, 1] < height))[0]

        # initialize coord_3d_map
        coord_3d_map = np.zeros(shape=(height, width, 3),
                                dtype=point_cloud_3D.dtype)
        for idx in idxs:
            u, v = int(point_cloud_image[idx][0]), int(
                point_cloud_image[idx][1])
            coord_3d_map[v][u][:] = point_cloud_3D[idx]

        # interpolate
        interpolate_3D_map = self.interpolate(coord_3d_map)

        return interpolate_3D_map
    
    def ros_PointCloud2_to_numpy(self, pc2_msg, want_rgb=False):
        if pc2 is None:
            raise ImportError("ROS is not installed")
        # gen = pc2.read_points(pc2_msg, skip_nans=True)
        gen = pc2.read_points(pc2_msg, skip_nans=True, field_names=['x', 'y', 'z'])

        if want_rgb:
            xyzpack = np.array(list(gen), dtype=np.float32)
            if xyzpack.shape[1] != 4:
                raise ValueError(
                    "PointCloud2 does not have points with color data.")
            xyzrgb = np.empty((xyzpack.shape[0], 6))
            xyzrgb[:, :3] = xyzpack[:, :3]
            for i, x in enumerate(xyzpack):
                rgb = x[3]
                # cast float32 to int so that bitwise operations are possible
                s = struct.pack('>f', rgb)
                i = struct.unpack('>l', s)[0]
                # you can get back the float value by the inverse operations
                pack = ctypes.c_uint32(i).value
                r = (pack & 0x00FF0000) >> 16
                g = (pack & 0x0000FF00) >> 8
                b = (pack & 0x000000FF)
                # r,g,b values in the 0-255 range
                xyzrgb[i, 3:] = (r, g, b)
            return xyzrgb
        else:
            return np.array(list(gen), dtype=np.float32)[:, :3]