import argparse

import terminaltexteffects.utils.argtypes as argtypes
from terminaltexteffects.base_character import EffectCharacter
from terminaltexteffects.utils.terminal import Terminal
from terminaltexteffects.utils import graphics, argtypes


def add_arguments(subparsers: argparse._SubParsersAction) -> None:
    """Adds arguments to the subparser.

    Args:
        subparser (argparse._SubParsersAction): subparser to add arguments to
    """
    effect_parser = subparsers.add_parser(
        "wipe",
        formatter_class=argtypes.CustomFormatter,
        help="Wipes the text across the terminal to reveal characters.",
        description="Wipes the text across the terminal to reveal characters.",
        epilog=f"""Example: terminaltexteffects wipe -a 0.01 --wipe-direction column_left_to_right --gradient ffffff ff0000 00ff00 --wipe-delay 0""",
    )
    effect_parser.set_defaults(effect_class=WipeEffect)
    effect_parser.add_argument(
        "-a",
        "--animation-rate",
        type=argtypes.nonnegative_float,
        default=0.01,
        help="Minimum time, in seconds, between animation steps. This value does not normally need to be modified. Use this to increase the playback speed of all aspects of the effect. This will have no impact beyond a certain lower threshold due to the processing speed of your device.",
    )
    effect_parser.add_argument(
        "--wipe-direction",
        default="column_left_to_right",
        choices=[
            "column_left_to_right",
            "column_right_to_left",
            "row_top_to_bottom",
            "row_bottom_to_top",
            "diagonal_top_left_to_bottom_right",
            "diagonal_bottom_left_to_top_right",
            "diagonal_top_right_to_bottom_left",
            "diagonal_bottom_right_to_top_left",
        ],
        help="Direction the text will wipe.",
    )
    effect_parser.add_argument(
        "--gradient",
        type=argtypes.color,
        nargs="*",
        default=[],
        metavar="(XTerm [0-255] OR RGB Hex [000000-ffffff])",
        help="Space separated, unquoted, list of colors for the wipe gradient.",
    )
    effect_parser.add_argument(
        "--gradient-steps",
        type=argtypes.positive_int,
        default=10,
        metavar="(int > 0)",
        help="Number of gradient steps to use. More steps will create a smoother and longer gradient animation.",
    )
    effect_parser.add_argument(
        "--wipe-delay",
        type=argtypes.nonnegative_int,
        default=0,
        metavar="(int >= 0)",
        help="Number of animation cycles to wait before adding the next character group. Increase, to slow down the effect.",
    )


class WipeEffect:
    """Effect that performs a wipe across the terminal to reveal characters."""

    def __init__(self, terminal: Terminal, args: argparse.Namespace):
        self.terminal = terminal
        self.args = args
        self.pending_groups: list[list[EffectCharacter]] = []
        self.animating_chars: list[EffectCharacter] = []
        self.direction = self.args.wipe_direction
        if len(self.args.gradient) > 1:
            self.wipe_gradient = graphics.Gradient(self.args.gradient, self.args.gradient_steps)

    def prepare_data(self) -> None:
        """Prepares the data for the effect by ___."""
        sort_map = {
            "column_left_to_right": self.terminal.CharacterSort.COLUMN_LEFT_TO_RIGHT,
            "column_right_to_left": self.terminal.CharacterSort.COLUMN_RIGHT_TO_LEFT,
            "row_top_to_bottom": self.terminal.CharacterSort.ROW_TOP_TO_BOTTOM,
            "row_bottom_to_top": self.terminal.CharacterSort.ROW_BOTTOM_TO_TOP,
            "diagonal_top_left_to_bottom_right": self.terminal.CharacterSort.DIAGONAL_TOP_LEFT_TO_BOTTOM_RIGHT,
            "diagonal_bottom_left_to_top_right": self.terminal.CharacterSort.DIAGONAL_BOTTOM_LEFT_TO_TOP_RIGHT,
            "diagonal_top_right_to_bottom_left": self.terminal.CharacterSort.DIAGONAL_TOP_RIGHT_TO_BOTTOM_LEFT,
            "diagonal_bottom_right_to_top_left": self.terminal.CharacterSort.DIAGONAL_BOTTOM_RIGHT_TO_TOP_LEFT,
        }
        for group in self.terminal.get_characters(sort_map[self.direction]):
            if self.args.gradient:
                for character in group:
                    wipe_scn = character.animation.new_scene("gradient")
                    if len(self.args.gradient) > 1:
                        for color in self.wipe_gradient:
                            wipe_scn.add_frame(character.input_symbol, 7, color=color)
                    else:
                        wipe_scn.add_frame(character.input_symbol, 1, color=self.args.gradient[0])
                    character.animation.activate_scene(wipe_scn)
            self.pending_groups.append(group)

    def run(self) -> None:
        """Runs the effect."""
        self.prepare_data()
        wipe_delay = self.args.wipe_delay
        while self.pending_groups or self.animating_chars:
            if not wipe_delay:
                if self.pending_groups:
                    next_group = self.pending_groups.pop(0)
                    for character in next_group:
                        character.is_active = True
                        self.animating_chars.append(character)
                wipe_delay = self.args.wipe_delay
            else:
                wipe_delay -= 1
            self.terminal.print()
            self.animate_chars()

            # remove completed chars from animating chars
            self.animating_chars = [
                animating_char
                for animating_char in self.animating_chars
                if not animating_char.animation.active_scene_is_complete()
                or not animating_char.motion.movement_is_complete()
            ]

    def animate_chars(self) -> None:
        """Animates the characters by calling the move method and step animation. Move characters prior to stepping animation
        to ensure waypoint synced animations have the latest waypoint progress information."""
        for animating_char in self.animating_chars:
            animating_char.motion.move()
            animating_char.animation.step_animation()