import argparse
from enum import Enum, auto

from terminaltexteffects.utils import argtypes, motion
from terminaltexteffects.base_character import EffectCharacter
from terminaltexteffects.utils.terminal import Terminal


def add_arguments(subparsers: argparse._SubParsersAction) -> None:
    """Adds arguments to the subparser.

    Args:
        subparser (argparse._SubParsersAction): subparser to add arguments to
    """
    effect_parser = subparsers.add_parser(
        "rowslide",
        formatter_class=argtypes.CustomFormatter,
        help="Slides each row into place.",
        description="rowslide | Slides each row into place.",
        epilog=f"""{argtypes.EASING_EPILOG}
        
Example: terminaltexteffects rowslide -a 0.003 --slide-direction left""",
    )
    effect_parser.set_defaults(effect_class=RowSlide)
    effect_parser.add_argument(
        "-a",
        "--animation-rate",
        type=argtypes.nonnegative_float,
        default=0.01,
        help="Minimum time, in seconds, between animation steps. This value does not normally need to be modified. Use this to increase the playback speed of all aspects of the effect. This will have no impact beyond a certain lower threshold due to the processing speed of your device.",
    )
    effect_parser.add_argument(
        "--row-gap",
        default=5,
        type=argtypes.nonnegative_int,
        help="Number of characters to wait before adding a new row. Min 1.",
    )
    effect_parser.add_argument(
        "--slide-direction",
        default="left",
        choices=["left", "right"],
        help="Direction the text will slide.",
    )
    effect_parser.add_argument(
        "--movement-speed",
        type=argtypes.positive_float,
        default=0.8,
        metavar="(float > 0)",
        help="Movement speed of the characters. Note: Speed effects the number of steps in the easing function. Adjust speed and animation rate separately to fine tune the effect.",
    )
    effect_parser.add_argument(
        "--easing",
        default="IN_OUT_QUAD",
        type=argtypes.ease,
        help="Easing function to use for row movement.",
    )


class SlideDirection(Enum):
    LEFT = auto()
    RIGHT = auto()


class RowSlide:
    """Effect that slides each row into place."""

    def __init__(self, terminal: Terminal, args: argparse.Namespace):
        """Effect that slides each row into place.

        Args:
            terminal (Terminal): terminal to use for the effect
            args (argparse.Namespace): arguments from argparse
        """
        self.terminal = terminal
        self.args = args
        self.pending_chars: list[EffectCharacter] = []
        self.active_chars: list[EffectCharacter] = []
        self.row_gap: int = args.row_gap
        if args.slide_direction == "left":
            self.slide_direction = SlideDirection.LEFT
        else:
            self.slide_direction = SlideDirection.RIGHT

    def prepare_data(self) -> None:
        """Prepares the data for the effect by grouping the characters by row and setting the starting
        coordinate."""

        self.rows = self.terminal.get_characters_sorted(sort_order=self.terminal.CharacterSort.ROW_TOP_TO_BOTTOM)
        for row in self.rows:
            for character in row:
                if self.slide_direction == SlideDirection.LEFT:
                    character.motion.set_coordinate(
                        motion.Coord(self.terminal.output_area.right, character.input_coord.row)
                    )
                else:
                    character.motion.set_coordinate(motion.Coord(0, character.input_coord.row))
                input_coord_path = character.motion.new_path(speed=self.args.movement_speed, ease=self.args.easing)
                input_coord_path.new_waypoint(character.input_coord)
                character.motion.activate_path(input_coord_path)

    def get_next_row(self) -> list[EffectCharacter]:
        """Gets the next row of characters to animate.

        Returns:
            list[effect_char.EffectCharacter]: The next row of characters to animate.
        """
        next_row = self.rows.pop(0)
        return next_row

    def run(self) -> None:
        """Runs the effect."""
        self.prepare_data()
        active_rows: list[list[EffectCharacter]] = []
        active_rows.append(self.get_next_row())
        row_delay_countdown = self.row_gap
        while active_rows or self.active_chars:
            if (row_delay_countdown == 0 and self.rows) or (not active_rows and self.rows):
                active_rows.append(self.get_next_row())
                row_delay_countdown = self.row_gap
            else:
                if self.rows:
                    row_delay_countdown -= 1
            for row in active_rows:
                if row:
                    if self.slide_direction == SlideDirection.LEFT:
                        next_character = row.pop(0)
                        next_character.is_visible = True
                        self.active_chars.append(next_character)
                    else:
                        next_character = row.pop(-1)
                        next_character.is_visible = True
                        self.active_chars.append(next_character)
            self.animate_chars()
            self.terminal.print()
            self.active_chars = [character for character in self.active_chars if character.is_active]
            active_rows = [row for row in active_rows if row]

    def animate_chars(self) -> None:
        """Animates the characters by calling the move method."""
        for character in self.active_chars:
            character.motion.move()
