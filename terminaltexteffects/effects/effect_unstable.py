"""Spawns characters jumbled, explodes them to the edge of the output area, then reassembles them.

Classes:
    Unstable: Spawns characters jumbled, explodes them to the edge of the output area, then reassembles them.
    UnstableConfig: Configuration for the Unstable effect.
    UnstableIterator: Effect iterator for the Unstable effect. Does not normally need to be called directly.
"""

import random
import typing
from dataclasses import dataclass

import terminaltexteffects.utils.argvalidators as argvalidators
from terminaltexteffects.engine.base_character import EffectCharacter
from terminaltexteffects.engine.base_effect import BaseEffect, BaseEffectIterator
from terminaltexteffects.utils import easing, graphics
from terminaltexteffects.utils.argsdataclass import ArgField, ArgsDataClass, argclass
from terminaltexteffects.utils.geometry import Coord


def get_effect_and_args() -> tuple[type[typing.Any], type[ArgsDataClass]]:
    return Unstable, UnstableConfig


@argclass(
    name="unstable",
    help="Spawn characters jumbled, explode them to the edge of the output area, then reassemble them in the correct layout.",
    description="unstable | Spawn characters jumbled, explode them to the edge of the output area, then reassemble them in the correct layout.",
    epilog=f"""{argvalidators.EASING_EPILOG}
    
    Example: terminaltexteffects unstable --unstable-color ff9200 --final-gradient-stops 8A008A 00D1FF FFFFFF --final-gradient-steps 12 --explosion-ease OUT_EXPO --explosion-speed 0.75 --reassembly-ease OUT_EXPO --reassembly-speed 0.75""",
)
@dataclass
class UnstableConfig(ArgsDataClass):
    """Configuration for the Unstable effect.

    Attributes:
        unstable_color (graphics.Color): Color transitioned to as the characters become unstable.
        final_gradient_stops (tuple[graphics.Color, ...]): Tuple of colors for the final color gradient. If only one color is provided, the characters will be displayed in that color.
        final_gradient_steps (tuple[int, ...]): Tuple of the number of gradient steps to use. More steps will create a smoother and longer gradient animation. Valid values are n > 0.
        final_gradient_direction (graphics.Gradient.Direction): Direction of the final gradient.
        explosion_ease (easing.EasingFunction): Easing function to use for character movement during the explosion.
        explosion_speed (float): Speed of characters during explosion. Valid values are n > 0.
        reassembly_ease (easing.EasingFunction): Easing function to use for character reassembly.
        reassembly_speed (float): Speed of characters during reassembly. Valid values are n > 0.
    """

    unstable_color: graphics.Color = ArgField(
        cmd_name=["--unstable-color"],
        type_parser=argvalidators.ColorArg.type_parser,
        default="ff9200",
        metavar=argvalidators.ColorArg.METAVAR,
        help="Color transitioned to as the characters become unstable.",
    )  # type: ignore[assignment]
    "graphics.Color : Color transitioned to as the characters become unstable."

    final_gradient_stops: tuple[graphics.Color, ...] = ArgField(
        cmd_name=["--final-gradient-stops"],
        type_parser=argvalidators.ColorArg.type_parser,
        nargs="+",
        default=("8A008A", "00D1FF", "FFFFFF"),
        metavar=argvalidators.ColorArg.METAVAR,
        help="Space separated, unquoted, list of colors for the character gradient (applied from bottom to top). If only one color is provided, the characters will be displayed in that color.",
    )  # type: ignore[assignment]
    "tuple[graphics.Color, ...] : Tuple of colors for the final color gradient. If only one color is provided, the characters will be displayed in that color."

    final_gradient_steps: tuple[int, ...] = ArgField(
        cmd_name=["--final-gradient-steps"],
        type_parser=argvalidators.PositiveInt.type_parser,
        nargs="+",
        default=(12,),
        metavar=argvalidators.PositiveInt.METAVAR,
        help="Space separated, unquoted, list of the number of gradient steps to use. More steps will create a smoother and longer gradient animation.",
    )  # type: ignore[assignment]
    "tuple[int, ...] : Tuple of the number of gradient steps to use. More steps will create a smoother and longer gradient animation."

    final_gradient_direction: graphics.Gradient.Direction = ArgField(
        cmd_name="--final-gradient-direction",
        type_parser=argvalidators.GradientDirection.type_parser,
        default=graphics.Gradient.Direction.VERTICAL,
        metavar=argvalidators.GradientDirection.METAVAR,
        help="Direction of the final gradient.",
    )  # type: ignore[assignment]
    "graphics.Gradient.Direction : Direction of the final gradient."

    explosion_ease: easing.EasingFunction = ArgField(
        cmd_name=["--explosion-ease"],
        type_parser=argvalidators.Ease.type_parser,
        default=easing.out_expo,
        help="Easing function to use for character movement during the explosion.",
    )  # type: ignore[assignment]
    "easing.EasingFunction : Easing function to use for character movement during the explosion."

    explosion_speed: float = ArgField(
        cmd_name=["--explosion-speed"],
        type_parser=argvalidators.PositiveFloat.type_parser,
        default=0.75,
        metavar=argvalidators.PositiveFloat.METAVAR,
        help="Speed of characters during explosion. ",
    )  # type: ignore[assignment]
    "float : Speed of characters during explosion. "

    reassembly_ease: easing.EasingFunction = ArgField(
        cmd_name=["--reassembly-ease"],
        type_parser=argvalidators.Ease.type_parser,
        default=easing.out_expo,
        help="Easing function to use for character reassembly.",
    )  # type: ignore[assignment]
    "easing.EasingFunction : Easing function to use for character reassembly."

    reassembly_speed: float = ArgField(
        cmd_name=["--reassembly-speed"],
        type_parser=argvalidators.PositiveFloat.type_parser,
        default=0.75,
        metavar=argvalidators.PositiveFloat.METAVAR,
        help="Speed of characters during reassembly. ",
    )  # type: ignore[assignment]
    "float : Speed of characters during reassembly."

    @classmethod
    def get_effect_class(cls):
        return Unstable


class UnstableIterator(BaseEffectIterator[UnstableConfig]):
    def __init__(self, effect: "Unstable") -> None:
        super().__init__(effect)
        self.pending_chars: list[EffectCharacter] = []
        self.jumbled_coords: dict[EffectCharacter, Coord] = dict()
        self.character_final_color_map: dict[EffectCharacter, graphics.Color] = {}
        self.build()

    def build(self) -> None:
        final_gradient = graphics.Gradient(*self.config.final_gradient_stops, steps=self.config.final_gradient_steps)
        final_gradient_mapping = final_gradient.build_coordinate_color_mapping(
            self.terminal.output_area.top, self.terminal.output_area.right, self.config.final_gradient_direction
        )
        for character in self.terminal.get_characters():
            self.character_final_color_map[character] = final_gradient_mapping[character.input_coord]
        character_coords = [character.input_coord for character in self.terminal.get_characters()]
        for character in self.terminal.get_characters():
            pos = random.randint(0, 3)
            match pos:
                case 0:
                    col = self.terminal.output_area.left
                    row = random.randint(1, self.terminal.output_area.top)
                case 1:
                    col = self.terminal.output_area.right
                    row = random.randint(1, self.terminal.output_area.top)
                case 2:
                    col = random.randint(1, self.terminal.output_area.right)
                    row = self.terminal.output_area.bottom
                case 3:
                    col = random.randint(1, self.terminal.output_area.right)
                    row = self.terminal.output_area.top
            jumbled_coord = character_coords.pop(random.randint(0, len(character_coords) - 1))
            self.jumbled_coords[character] = jumbled_coord
            character.motion.set_coordinate(jumbled_coord)
            explosion_path = character.motion.new_path(id="explosion", speed=1.25, ease=self.config.explosion_ease)
            explosion_path.new_waypoint(Coord(col, row))
            reassembly_path = character.motion.new_path(id="reassembly", speed=0.75, ease=self.config.reassembly_ease)
            reassembly_path.new_waypoint(character.input_coord)
            unstable_gradient = graphics.Gradient(
                self.character_final_color_map[character], self.config.unstable_color, steps=25
            )
            rumble_scn = character.animation.new_scene(id="rumble")
            rumble_scn.apply_gradient_to_symbols(
                unstable_gradient,
                character.input_symbol,
                10,
            )
            final_color = graphics.Gradient(
                self.config.unstable_color, self.character_final_color_map[character], steps=12
            )
            final_scn = character.animation.new_scene(id="final")
            final_scn.apply_gradient_to_symbols(final_color, character.input_symbol, 5)
            character.animation.activate_scene(rumble_scn)
            self.terminal.set_character_visibility(character, True)
        self._explosion_hold_time = 50
        self.phase = "rumble"
        self._max_rumble_steps = 250
        self._current_rumble_steps = 0
        self._rumble_mod_delay = 20

    def __next__(self) -> str:
        next_frame = None
        if self.phase == "rumble":
            if self._current_rumble_steps < self._max_rumble_steps:
                if self._current_rumble_steps > 30 and self._current_rumble_steps % self._rumble_mod_delay == 0:
                    row_offset = random.choice([-1, 0, 1])
                    column_offset = random.choice([-1, 0, 1])
                    for character in self.terminal.get_characters():
                        character.motion.set_coordinate(
                            Coord(
                                character.motion.current_coord.column + column_offset,
                                character.motion.current_coord.row + row_offset,
                            )
                        )
                        character.animation.step_animation()
                    next_frame = self.terminal.get_formatted_output_string()
                    for character in self.terminal.get_characters():
                        character.motion.set_coordinate(self.jumbled_coords[character])
                    self._rumble_mod_delay -= 1
                    self._rumble_mod_delay = max(self._rumble_mod_delay, 1)
                else:
                    for character in self.terminal.get_characters():
                        character.animation.step_animation()
                    next_frame = self.terminal.get_formatted_output_string()

                self._current_rumble_steps += 1
            else:
                self.phase = "explosion"
                for character in self.terminal.get_characters():
                    character.motion.activate_path(character.motion.query_path("explosion"))
                self.active_characters = [character for character in self.terminal.get_characters()]

        if self.phase == "explosion":
            if self.active_characters:
                for character in self.active_characters:
                    character.tick()
                self.active_characters = [
                    character
                    for character in self.active_characters
                    if not character.motion.current_coord == character.motion.query_path("explosion").waypoints[0].coord
                ]
                next_frame = self.terminal.get_formatted_output_string()

            elif self._explosion_hold_time:
                for character in self.active_characters:
                    character.tick()
                self._explosion_hold_time -= 1
                next_frame = self.terminal.get_formatted_output_string()
            else:
                self.phase = "reassembly"
                for character in self.terminal.get_characters():
                    character.animation.activate_scene(character.animation.query_scene("final"))
                    self.active_characters.append(character)
                    character.motion.activate_path(character.motion.query_path("reassembly"))

        if self.phase == "reassembly":
            if self.active_characters:
                for character in self.active_characters:
                    character.tick()
                self.active_characters = [
                    character
                    for character in self.active_characters
                    if not character.motion.current_coord
                    == character.motion.query_path("reassembly").waypoints[0].coord
                    or not character.animation.active_scene_is_complete()
                ]
                next_frame = self.terminal.get_formatted_output_string()

        if next_frame is not None:
            return next_frame
        else:
            raise StopIteration


class Unstable(BaseEffect[UnstableConfig]):
    """Spawns characters jumbled, explodes them to the edge of the output area, then reassembles them.

    Attributes:
        effect_config (UnstableConfig): Configuration for the effect.
        terminal_config (TerminalConfig): Configuration for the terminal.
    """

    _config_cls = UnstableConfig
    _iterator_cls = UnstableIterator

    def __init__(self, input_data: str) -> None:
        """Initialize the effect with the provided input data.

        Args:
            input_data (str): The input data to use for the effect."""
        super().__init__(input_data)
