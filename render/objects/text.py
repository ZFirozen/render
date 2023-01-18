import string
from functools import lru_cache
from typing import Optional, Sequence
from typing_extensions import override, Self, Unpack

import pyphen
from PIL.ImageFont import FreeTypeFont, truetype

from render.base import (RenderObject, RenderImage, RenderText, Color,
                         BaseStyle, Alignment, Direction)
from render.utils import find_rightmost


class Text(RenderObject):

    MARKS = set("；：。，！？、.,!?”》;:")
    _dict = pyphen.Pyphen(lang="en_US")

    def __init__(
        self,
        text: str,
        font: str,
        size: int,
        max_width: Optional[int],
        alignment: Alignment,
        color: Optional[Color],
        spacing: int,
        hyphenation: bool,
        **kwargs: Unpack[BaseStyle],
    ) -> None:
        super(Text, self).__init__(**kwargs)

        self.font = font
        self.size = size
        self.alignment = alignment
        self.color = color
        self.spacing = spacing
        self.hyphenation = hyphenation
        self.pre_rendered = [
            RenderText.of(line, font, size, color).render()
            for line in self.cut(text, max_width)
        ]

    @staticmethod
    @lru_cache()
    def _calculate_width(font: FreeTypeFont, text: str):
        w, _ = font.getsize(text)
        return w

    @classmethod
    def _split_line(
        cls,
        font: FreeTypeFont,
        text: str,
        max_width: int,
        hyphenation: bool,
    ) -> Sequence[str]:
        if len(text) == 0:
            return []
        indices = list(range(len(text)))
        bound = find_rightmost(
            indices,
            max_width,
            key=lambda k: cls._calculate_width(font, text[:k]),
        )
        if cls._calculate_width(font, text[:bound]) > max_width:
            bound -= 1
        if bound <= 0:
            raise ValueError("Text is too long to fit in the given width")
        if bound == len(text):
            return [text]

        original_bound = bound
        # try to cut at a word boundary
        if text[bound] in string.ascii_letters:
            # search for the word boundary
            prev = next = bound
            while prev >= 0 and text[prev] in string.ascii_letters:
                prev -= 1
            while next < len(text) and text[next] in string.ascii_letters:
                next += 1
            prev += 1
            word = text[prev:next]
            if len(word) > 1:
                if not hyphenation:
                    # simply put the whole word in the next line
                    bound = prev
                else:
                    first, second = cls._split_word(
                        font, word,
                        max_width - cls._calculate_width(font, text[:prev]))
                    if not first:
                        # no possible cut, put the whole word in the next line
                        bound = prev
                    else:
                        return [
                            text[:prev] + first,
                            *cls._split_line(font, second + text[next:],
                                             max_width, hyphenation)
                        ]

        # try not to leave a mark at the beginning of the next line
        if text[bound] in cls.MARKS:
            if cls._calculate_width(font, text[:bound + 1]) <= max_width:
                bound += 1
            else:
                prev = bound - 1
                # word followed by the mark should go with it to the next line
                while prev >= 0 and text[prev] in string.ascii_letters:
                    prev -= 1
                prev += 1
                bound = prev
        # failed somewhere, give up
        if bound == 0:
            bound = original_bound
        return [
            text[:bound].rstrip(" "), *cls._split_line(
                font, text[bound:].lstrip(" "), max_width, hyphenation)
        ]

    @classmethod
    def _split_word(
        cls,
        font: FreeTypeFont,
        word: str,
        max_width: int,
    ):
        cuts = list(cls._dict.iterate(word))
        cuts.sort(key=lambda k: len(k[0]))
        cut_bound = find_rightmost(
            range(len(cuts)),
            max_width,
            key=lambda k: cls._calculate_width(font, cuts[k][0] + "-"))
        if cut_bound == 0 or not cuts:
            return "", word
        return cuts[cut_bound - 1][0] + "-", cuts[cut_bound - 1][1]

    def cut(self, text: str, max_width: Optional[int]) -> Sequence[str]:
        lines = text.splitlines()
        if max_width is None:
            return lines
        font = truetype(self.font, self.size)
        res = list[str]()
        for line in lines:
            splitted = self._split_line(font, line, max_width,
                                        self.hyphenation)
            res.extend(splitted)
        return res

    @classmethod
    def of(
        cls,
        text: str,
        font: str,
        size: int = 12,
        max_width: Optional[int] = None,
        alignment: Alignment = Alignment.START,
        color: Optional[Color] = None,
        spacing: int = 0,
        hyphenation: bool = True,
        **kwargs: Unpack[BaseStyle],
    ) -> Self:
        return cls(text, font, size, max_width, alignment, color, spacing,
                   hyphenation, **kwargs)

    @property
    @override
    def content_width(self) -> int:
        return max(rt.width for rt in self.pre_rendered)

    @property
    @override
    def content_height(self) -> int:
        sp = max(0, len(self.pre_rendered) - 1) * self.spacing
        return sum(rt.height for rt in self.pre_rendered) + sp

    @override
    def render_content(self) -> RenderImage:
        return RenderImage.concat(
            self.pre_rendered,
            direction=Direction.VERTICAL,
            alignment=self.alignment,
            color=self.background,
            spacing=self.spacing,
        )
