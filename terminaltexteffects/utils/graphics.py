import typing
import random
from dataclasses import dataclass

from terminaltexteffects.utils import ansitools, colorterm, hexterm, motion

if typing.TYPE_CHECKING:
    from terminaltexteffects import base_character


@dataclass
class Gradient:
    """A Gradient is a list of RGB hex color strings transitioning from one color to another. The gradient color
    list is calculated using linear interpolation based on the provided start and end colors and the number of steps.

    Args:
        start_color (str|int): RGB hex color string or XTerm-256 color code
        end_color (str|int): RGB hex color string or XTerm-256 color code
        steps (int): Number of intermediate colors to calculate

    Attributes:
        colors (list[str]): List (length=steps + 2) of RGB hex color strings

    """

    start_color: str | int
    end_color: str | int
    steps: int

    def __post_init__(self) -> None:
        self.colors: list[str] = self._generate()
        self.index: int = 0

    def _generate(self) -> list[str]:
        """Calculate a gradient of colors between two colors using linear interpolation.

        Returns:
            list[str]: List (length=steps + 2) of RGB hex color strings
        """
        # Convert start_color to hex if it's an XTerm-256 color code
        if isinstance(self.start_color, int):
            self.start_color = hexterm.xterm_to_hex(self.start_color)
        # Convert end_color to hex if it's an XTerm-256 color code
        if isinstance(self.end_color, int):
            self.end_color = hexterm.xterm_to_hex(self.end_color)
        # Convert start_color to a list of RGB values
        start_color_ints = colorterm._hex_to_int(self.start_color)
        # Convert end_color to a list of RGB values
        end_color_ints = colorterm._hex_to_int(self.end_color)
        # Initialize an empty list to store the gradient colors
        gradient_colors: list[str] = []
        # Add the start color to the gradient colors list
        gradient_colors.append(self.start_color)
        # Calculate the color deltas for each RGB value
        red_delta = (end_color_ints[0] - start_color_ints[0]) // self.steps
        green_delta = (end_color_ints[1] - start_color_ints[1]) // self.steps
        blue_delta = (end_color_ints[2] - start_color_ints[2]) // self.steps
        # Calculate the intermediate colors and add them to the gradient colors list
        for i in range(self.steps):
            red = start_color_ints[0] + (red_delta * i)
            green = start_color_ints[1] + (green_delta * i)
            blue = start_color_ints[2] + (blue_delta * i)

            # Ensure that the RGB values are within the valid range of 0-255
            red = max(0, min(red, 255))
            green = max(0, min(green, 255))
            blue = max(0, min(blue, 255))

            # Convert the RGB values to a hex color string and add it to the gradient colors list
            gradient_colors.append(f"{red:02x}{green:02x}{blue:02x}")
        # Add the end color to the gradient colors list
        gradient_colors.append(self.end_color)
        # Return the list of gradient colors
        return gradient_colors

    def __iter__(self) -> "Gradient":
        self.index = 0
        return self

    def __next__(self) -> str:
        if self.index < len(self.colors):
            color = self.colors[self.index]
            self.index += 1
            return color
        else:
            raise StopIteration

    def __add__(self, other: "Gradient") -> "Gradient":
        if not isinstance(other, Gradient):
            return NotImplemented
        new_gradient = Gradient("ffffff", "ffffff", 1)
        new_gradient.colors = self.colors + other.colors
        new_gradient.steps = self.steps + other.steps
        new_gradient.start_color = self.start_color
        new_gradient.end_color = other.end_color
        return new_gradient


@dataclass
class CharacterVisual:
    """A class for storing symbol, color, and terminal graphical modes for the character.

    Supported graphical modes:
    bold, dim, italic, underline, blink, inverse, hidden, strike

    Args:
        symbol (str): the symbol to show
        bold (bool): bold mode
        dim (bool): dim mode
        italic (bool): italic mode
        underline (bool): underline mode
        blink (bool): blink mode
        reverse (bool): reverse mode
        hidden (bool): hidden mode
        strike (bool): strike mode
        color (int | str): color code
    """

    symbol: str
    bold: bool = False
    dim: bool = False
    italic: bool = False
    underline: bool = False
    blink: bool = False
    reverse: bool = False
    hidden: bool = False
    strike: bool = False
    color: int | str | None = None

    def __post_init__(self):
        self.format_symbol()

    def disable_modes(self) -> None:
        """Disables all graphical modes."""
        self.bold = False
        self.dim = False
        self.italic = False
        self.underline = False
        self.blink = False
        self.reverse = False
        self.hidden = False
        self.strike = False

    def format_symbol(self) -> None:
        """Formats the symbol for printing."""
        formatting_string = ""
        if self.bold:
            formatting_string += ansitools.APPLY_BOLD()
        if self.italic:
            formatting_string += ansitools.APPLY_ITALIC()
        if self.underline:
            formatting_string += ansitools.APPLY_UNDERLINE()
        if self.blink:
            formatting_string += ansitools.APPLY_BLINK()
        if self.reverse:
            formatting_string += ansitools.APPLY_REVERSE()
        if self.hidden:
            formatting_string += ansitools.APPLY_HIDDEN()
        if self.strike:
            formatting_string += ansitools.APPLY_STRIKETHROUGH()
        if self.color is not None:
            formatting_string += colorterm.fg(self.color)

        self.symbol = f"{formatting_string}{self.symbol}{ansitools.RESET_ALL() if formatting_string else ''}"


@dataclass
class Frame:
    """A Frame is a CharacterVisual with a duration.
    Args:
        character_visual (CharacterVisual): a CharacterVisual object
        duration (int): the number of animation steps to use the Frame
    """

    character_visual: CharacterVisual
    duration: int

    def __post_init__(self):
        self.frames_played = 0
        self.symbol = self.character_visual.symbol


class Scene:
    """A Scene is a list of Frames.

    Args:
        id (str): the id of the Scene
        sequences (list[Sequence]): a list of Sequence objects
        is_looping (bool): whether the Scene should loop
    """

    xterm_color_map: dict[str, int] = {}

    def __init__(
        self,
        scene_id: int,
        is_looping: bool = False,
        sync_waypoint: motion.Waypoint | None = None,
        no_color: bool = False,
        use_xterm_colors: bool = False,
    ):
        self.scene_id = scene_id
        self.is_looping = is_looping
        self.sync_waypoint: motion.Waypoint | None = sync_waypoint
        self.no_color = no_color
        self.use_xterm_colors = use_xterm_colors
        self.frames: list[Frame] = []
        self.played_frames: list[Frame] = []

    def add_frame(
        self,
        symbol: str,
        color: str | int,
        duration: int,
        *,
        BOLD=False,
        DIM=False,
        ITALIC=False,
        UNDERLINE=False,
        BLINK=False,
        REVERSE=False,
        HIDDEN=False,
        STRIKE=False,
    ) -> None:
        """Adds a Frame to the Scene.

        Args:
            graphicaleffect (GraphicalEffect): a GraphicalEffect object containing the symbol, graphical modes, and color of the character
            duration (int): the number of animation steps to display the frame
        """
        if not self.no_color:
            if self.use_xterm_colors and isinstance(color, str):
                if color in self.xterm_color_map:
                    color = self.xterm_color_map[color]
                else:
                    xterm_color = hexterm.hex_to_xterm(color)
                    self.xterm_color_map[color] = xterm_color
                    color = xterm_color
        if duration < 1:
            raise ValueError("duration must be greater than 0")
        char_vis = CharacterVisual(
            symbol,
            bold=BOLD,
            dim=DIM,
            italic=ITALIC,
            underline=UNDERLINE,
            blink=BLINK,
            reverse=REVERSE,
            hidden=HIDDEN,
            strike=STRIKE,
            color=color,
        )
        self.frames.append(Frame(char_vis, duration))

    def activate(self) -> str:
        """Activates the Scene.

        Returns:
            str: the next symbol in the Scene
        """
        if self.frames:
            return self.frames[0].symbol
        else:
            raise ValueError("Scene has no sequences.")

    def apply_gradient(self, start_color: str | int, end_color: str | int) -> None:
        """
        Applies a gradient effect across the sequences of the scene. The gradient is generated
        to have the same number of steps as the number of frames in the scene.

        Parameters
        ----------
        start_color : str | int
            The starting color of the gradient.
        end_color : str | int
            The ending color of the gradient.

        Returns
        -------
        None
        """
        if not self.frames:
            return
        else:
            gradient = Gradient(start_color, end_color, len(self.frames))
            for i, frame in enumerate(self.frames):
                frame.character_visual.color = gradient.colors[i]
                frame.character_visual.format_symbol()

    def get_next_symbol(self) -> str:
        """Returns the next symbol in the Scene.

        Returns:
            str: the next symbol in the Scene
        """

        current_sequence = self.frames[0]
        next_symbol = current_sequence.symbol
        current_sequence.frames_played += 1
        if current_sequence.frames_played == current_sequence.duration:
            current_sequence.frames_played = 0
            self.played_frames.append(self.frames.pop(0))
            if self.is_looping and not self.frames:
                self.frames.extend(self.played_frames)
                self.played_frames.clear()
        return next_symbol

    def reset_scene(self) -> None:
        """Resets the Scene."""
        for sequence in self.frames:
            sequence.frames_played = 0
            self.played_frames.append(sequence)
        self.frames.clear()
        self.frames.extend(self.played_frames)
        self.played_frames.clear()

    def __eq__(self, other: typing.Any):
        if not isinstance(other, Scene):
            return NotImplemented
        return self.scene_id == other.scene_id

    def __hash__(self):
        return hash(self.scene_id)


class Animation:
    def __init__(self, character: "base_character.EffectCharacter"):
        """Animation handles the animations of a character. It contains a list of Scenes, and the active scene id. GraphicalEffects are
        added to the Scenes, and the Animation returns the next symbol in the active scene.

        Args:
            character (base_character.EffectCharacter): the EffectCharacter object to animate
        """
        self.next_scene_id = 0
        self.scenes: dict[str, Scene] = {}
        self.character = character
        self.active_scene: Scene | None = None
        self.use_xterm_colors: bool = False
        self.no_color: bool = False
        self.xterm_color_map: dict[str, int] = {}

    def new_scene(self, scene_name: str) -> Scene:
        """Creates a new Scene and adds it to the Animation.

        Args:
            scene_name (str): Unique name for the scene. Used to reference the scene outside the scope in which is was created.

        Returns:
            Scene: the new Scene
        """
        new_scene = Scene(self.next_scene_id)
        self.scenes[scene_name] = new_scene
        new_scene.no_color = self.no_color
        new_scene.use_xterm_colors = self.use_xterm_colors
        self.next_scene_id += 1
        return new_scene

    def active_scene_is_complete(self) -> bool:
        """Returns whether the active scene is complete. A scene is complete if all sequences have been played.
        Looping scenes are always complete.

        Returns:
            bool: True if complete, False otherwise
        """
        if not self.active_scene:
            return True
        elif not self.active_scene.frames or self.active_scene.is_looping:
            return True
        elif (
            self.active_scene.sync_waypoint and self.character.motion.active_waypoint is self.active_scene.sync_waypoint
        ):
            return True
        return False

    def random_color(self) -> str:
        """Returns a random hex color code.

        Returns:
            str: hex color code
        """
        return hex(random.randint(0, 0xFFFFFF))[2:].zfill(6)

    def step_animation(self) -> None:
        """Apply the next symbol in the scene to the character. If a scene order exists, the next scene
        will be activated when the current scene is complete."""
        if self.active_scene and self.active_scene.frames:
            # if the active scene is synced to the active waypoint, calculate the sequence index based on the
            # current waypoint progress
            if self.active_scene.sync_waypoint:
                if (
                    self.character.motion.active_waypoint
                    and self.character.motion.active_waypoint is self.active_scene.sync_waypoint
                ):
                    sequence_index = round(
                        len(self.active_scene.frames)
                        * (
                            max(self.character.motion.inter_waypoint_current_step, 1)
                            / max(self.character.motion.inter_waypoint_max_steps, 1)
                        )
                    )
                    try:
                        self.character.symbol = self.active_scene.frames[sequence_index].symbol
                    except IndexError:
                        self.character.symbol = self.active_scene.frames[-1].symbol
                else:  # when the active waypoint has been deactivated or changed, use the final symbol in the scene and finish the scene
                    self.character.symbol = self.active_scene.frames[-1].symbol
                    self.active_scene.played_frames.extend(self.active_scene.frames)
                    self.active_scene.frames.clear()
            else:
                self.character.symbol = self.active_scene.get_next_symbol()
            if self.active_scene_is_complete():
                completed_scene = self.active_scene
                if not self.active_scene.is_looping:
                    self.active_scene.reset_scene()
                    self.active_scene = None

                self.character.event_handler.handle_event(
                    self.character.event_handler.Event.SCENE_COMPLETE, completed_scene
                )

    def activate_scene(self, scene: Scene) -> None:
        """Sets the active scene.

        Args:
            scene_id (str): the ID of the Scene to set as active
        """
        self.active_scene = scene
        self.character.symbol = self.active_scene.activate()
        self.character.event_handler.handle_event(self.character.event_handler.Event.SCENE_ACTIVATED, scene)

    def deactivate_scene(self, scene: Scene) -> None:
        """Deactivates a scene.

        Args:
            scene_id (str): the ID of the Scene to deactivate
        """
        if self.active_scene is scene:
            self.active_scene = None
