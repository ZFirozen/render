from __future__ import annotations

from abc import abstractmethod
from typing_extensions import Self, override

import cv2
import numpy as np

from render.base import BoxSizing, ForegroundDecoration, ImageMask, RenderImage


class Crop(ForegroundDecoration):
    """Crop foreground image by applying a mask to it."""

    @abstractmethod
    def get_mask(self, obj: RenderImage) -> ImageMask:
        """Create a crop mask.
        
        Mask should be a 2D array of shape (height, width) with 
        values in [0, 255].
        """
        raise NotImplementedError()

    @override
    def apply(self, obj: RenderImage) -> RenderImage:
        mask = self.get_mask(obj)
        obj = obj.mask(mask)
        return obj


class CircleCrop(Crop):
    """Crop foreground image to a circle."""

    def __init__(
        self,
        radius: int | None,
        box_sizing: BoxSizing,
    ) -> None:
        super(CircleCrop, self).__init__(box_sizing)
        self.radius = radius

    @classmethod
    def of(
        cls,
        radius: int | None = None,
        box_sizing: BoxSizing = BoxSizing.CONTENT_BOX,
    ) -> Self:
        return cls(radius, box_sizing)

    @override
    def get_mask(self, obj: RenderImage) -> ImageMask:
        if self.radius is None:
            radius = min(obj.height, obj.width) // 2
        else:
            radius = self.radius

        mask = np.zeros((obj.height, obj.width), dtype=np.uint8)
        mask = cv2.circle(
            mask,
            (obj.height // 2, obj.width // 2),
            radius,
            255,
            thickness=-1,
            lineType=cv2.LINE_AA,
        )
        return mask


class RectCrop(Crop):
    """Crop foreground image to a (rounded-)rectangle."""

    def __init__(
        self,
        width: int | None,
        height: int | None,
        border_radius: int,
        box_sizing: BoxSizing,
    ) -> None:
        super(RectCrop, self).__init__(box_sizing)
        self.width = width
        self.height = height
        self.border_radius = border_radius

    @classmethod
    def of(
        cls,
        width: int | None = None,
        height: int | None = None,
        border_radius: int = 0,
        box_sizing: BoxSizing = BoxSizing.CONTENT_BOX,
    ) -> Self:
        return cls(width, height, border_radius, box_sizing)

    @classmethod
    def of_square(
        cls,
        size: int | None = None,
        border_radius: int = 0,
        box_sizing: BoxSizing = BoxSizing.CONTENT_BOX,
    ) -> Self:
        return cls(size, size, border_radius, box_sizing)

    @override
    def get_mask(self, obj: RenderImage) -> ImageMask:
        height = self.height if self.height is not None else obj.height
        width = self.width if self.width is not None else obj.width
        start_x = (obj.width - width) // 2
        start_y = (obj.height - height) // 2
        mask = np.zeros((obj.height, obj.width), dtype=np.uint8)
        if self.border_radius == 0:
            return cv2.rectangle(
                mask,
                (start_x, start_y),
                (start_x + width, start_y + height),
                255,
                thickness=-1,
                lineType=cv2.LINE_AA,
            )

        if self.border_radius > min(width, height) // 2:
            border_radius = min(width, height) // 2
        else:
            border_radius = self.border_radius

        corners = [
            (start_x + border_radius, start_y + border_radius),
            (start_x + border_radius, start_y + height - border_radius),
            (start_x + width - border_radius, start_y + border_radius),
            (start_x + width - border_radius,
             start_y + height - border_radius),
        ]
        for corner in corners:
            mask = cv2.circle(
                mask,
                corner,
                border_radius,
                255,
                thickness=-1,
                lineType=cv2.LINE_AA,
            )
        mask = cv2.rectangle(
            mask,
            (start_x, start_y + border_radius),
            (start_x + width, start_y + height - border_radius),
            255,
            thickness=-1,
            lineType=cv2.LINE_AA,
        )
        mask = cv2.rectangle(
            mask,
            (start_x + border_radius, start_y),
            (start_x + width - border_radius, start_y + height),
            255,
            thickness=-1,
            lineType=cv2.LINE_AA,
        )
        return mask
