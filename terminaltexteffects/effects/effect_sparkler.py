"""Effect that draws the characters spawning at varying rates from a single point."""

import time
import random
import argparse
import terminaltexteffects.utils.argtypes as argtypes
from terminaltexteffects.utils.terminal import Terminal
from terminaltexteffects.utils import graphics
from terminaltexteffects import base_effect, base_character
from enum import Enum, auto


def add_arguments(subparsers: argparse._SubParsersAction) -> None:
    """Adds arguments to the subparser.

    Args:
        subparser (argparse._SubParsersAction): subparser to add arguments to
    """
    effect_parser = subparsers.add_parser(
        "sparkler",
        help="Draws the characters spawning at varying rates from a single point.",
        description="sparkler | Draws the characters spawning at varying rates from a single point.",
        epilog="Example: terminaltexteffects sparkler -a 0.01 --sparkler-position center",
    )
    effect_parser.set_defaults(effect_class=SparklerEffect)
    effect_parser.add_argument(
        "-a",
        "--animation-rate",
        type=float,
        default=0.01,
        help="Time between animation steps. Defaults to 0.01 seconds.",
    )
    effect_parser.add_argument(
        "--sparkler-position",
        default="center",
        choices=["n", "ne", "e", "se", "s", "sw", "w", "nw", "center"],
        help="Position for the sparkler origin. Defaults to center.",
    )


class SparklerPosition(Enum):
    """Position for the sparkler origin."""

    N = auto()
    NE = auto()
    E = auto()
    SE = auto()
    S = auto()
    SW = auto()
    W = auto()
    NW = auto()
    CENTER = auto()


class SparklerEffect(base_effect.Effect):
    """Effect that draws the characters spawning at varying rates from a single point."""

    def __init__(
        self,
        terminal: Terminal,
        args: argparse.Namespace,
    ):
        """Effect that draws the characters spawning at varying rates from a single point.

        Args:
            terminal (Terminal): terminal to use for the effect
            args (argparse.Namespace): arguments from argparse
        """
        super().__init__(terminal, args.animation_rate)
        self.sparkler_position = {
            "n": SparklerPosition.N,
            "ne": SparklerPosition.NE,
            "e": SparklerPosition.E,
            "se": SparklerPosition.SE,
            "s": SparklerPosition.S,
            "sw": SparklerPosition.SW,
            "w": SparklerPosition.W,
            "nw": SparklerPosition.NW,
            "center": SparklerPosition.CENTER,
        }.get(args.sparkler_position, SparklerPosition.CENTER)

    def prepare_data(self) -> None:
        """Prepares the data for the effect by starting all of the characters from a point based on SparklerPosition."""
        sparkler_origin_map = {
            SparklerPosition.CENTER: (
                self.terminal.output_area.right // 2,
                self.terminal.output_area.top // 2,
            ),
            SparklerPosition.N: (self.terminal.output_area.right // 2, self.terminal.output_area.top),
            SparklerPosition.NW: (self.terminal.output_area.left, self.terminal.output_area.top),
            SparklerPosition.W: (self.terminal.output_area.left, self.terminal.output_area.top // 2),
            SparklerPosition.SW: (self.terminal.output_area.left, self.terminal.output_area.bottom),
            SparklerPosition.S: (self.terminal.output_area.right // 2, self.terminal.output_area.bottom),
            SparklerPosition.SE: (self.terminal.output_area.right - 1, self.terminal.output_area.bottom),
            SparklerPosition.E: (self.terminal.output_area.right - 1, self.terminal.output_area.top // 2),
            SparklerPosition.NE: (self.terminal.output_area.right - 1, self.terminal.output_area.top),
        }

        for character in self.terminal.characters:
            character.is_active = False
            character.current_coord.column, character.current_coord.row = sparkler_origin_map[self.sparkler_position]
            white = graphics.GraphicalEffect(color=231)
            yellow = graphics.GraphicalEffect(color=11)
            orange = graphics.GraphicalEffect(color=202)
            colors = [white, yellow, orange]
            random.shuffle(colors)
            final_animation_unit = graphics.AnimationUnit(character.input_symbol, 1, False, graphics.GraphicalEffect())
            character.animation_units.append(
                graphics.AnimationUnit(character.symbol, random.randint(20, 35), False, colors.pop())
            )
            character.animation_units.append(
                graphics.AnimationUnit(character.symbol, random.randint(20, 35), False, colors.pop())
            )
            character.animation_units.append(
                graphics.AnimationUnit(character.symbol, random.randint(20, 35), False, colors.pop())
            )
            character.animation_units.append(final_animation_unit)
            self.pending_chars.append(character)
        random.shuffle(self.pending_chars)

    def run(self) -> None:
        """Runs the effect."""
        self.prepare_data()
        while self.pending_chars or self.animating_chars:
            if self.pending_chars:
                for _ in range(random.randint(1, 5)):
                    if self.pending_chars:
                        next_character = self.pending_chars.pop()
                        next_character.is_active = True
                        self.animating_chars.append(next_character)

            self.animate_chars()
            self.terminal.print()
            self.animating_chars = [
                animating_char for animating_char in self.animating_chars if not animating_char.animation_completed()
            ]
            time.sleep(self.animation_rate)

    def animate_chars(self) -> None:
        for animating_char in self.animating_chars:
            animating_char.step_animation()
            animating_char.move()