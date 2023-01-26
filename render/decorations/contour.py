from enum import Enum
from typing_extensions import Self, override

import cv2
import numpy as np

from render.base import BoxSizing, Color, ForegroundDecoration, RenderImage


class ContourType(Enum):
    EXTERNAL = cv2.RETR_EXTERNAL
    ALL = cv2.RETR_TREE


class Contour(ForegroundDecoration):
    """Draw a contour around the foreground of the image.
    
    Attributes:
        color: color of the contour
        thickness: thickness of the contour
        dilation: size of the dilation kernel
        contour_type: type of the contour, either EXTERNAL or ALL
        threshold: threshold of alpha channel for foreground
        box_sizing: which render stage to apply the decoration
    """

    def __init__(
        self,
        color: Color,
        thickness: int,
        dilation: int,
        contour_type: ContourType,
        threshold: int,
        box_sizing: BoxSizing,
    ) -> None:
        super(Contour, self).__init__(box_sizing)
        self.color = color
        self.thickness = thickness
        self.dilation = dilation
        self.threshold = threshold
        self.contour_type = contour_type

    @classmethod
    def of(
        cls,
        color: Color,
        thickness: int = 0,
        dilation: int = 0,
        contour_type: ContourType = ContourType.EXTERNAL,
        threshold: int = 0,
        box_sizing: BoxSizing = BoxSizing.CONTENT_BOX,
    ) -> Self:
        return cls(color, thickness, dilation, contour_type, threshold,
                   box_sizing)

    @override
    def apply(self, obj: RenderImage) -> RenderImage:
        threshed = obj.base_im[:, :, 3] > self.threshold  # type: ignore
        fore = threshed.astype(np.uint8) * 255
        if self.dilation > 0:
            fore = cv2.dilate(
                fore, np.ones((self.dilation, self.dilation), np.uint8))

        contours, _ = cv2.findContours(
            fore,
            self.contour_type.value,
            cv2.CHAIN_APPROX_NONE,
        )
        im_with_contour = cv2.drawContours(
            obj.base_im,
            contours,
            -1,
            self.color,
            self.thickness,
            cv2.LINE_AA,
        )
        obj.base_im = im_with_contour
        return obj
