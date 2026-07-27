"""Small CustomTkinter UI adapter for RVC-Realtime-GUI.

It intentionally implements only the controls used by ``realtime_gui.py``.
The adapter keeps the inference code independent from the GUI toolkit while
providing modern CustomTkinter widgets and thread-safe UI updates.
"""

from __future__ import annotations

import queue
import locale
import os
import threading
import time
import tkinter as tk
from tkinter import filedialog, messagebox

import customtkinter as ctk
from PIL import Image as PILImage
from PIL import ImageTk

_language = (
    os.environ.get("RVC_UI_LANGUAGE")
    or locale.getlocale()[0]
    or ""
).lower()
IS_JAPANESE_UI = _language.startswith("ja")
UI_FONT_FAMILY = "Yu Gothic UI" if IS_JAPANESE_UI else "Segoe UI"


WINDOW_CLOSED = "__WINDOW_CLOSED__"
TIMEOUT_EVENT = "__TIMEOUT__"
TIMEOUT_KEY = TIMEOUT_EVENT
BUTTON_STYLES = {
    "large": (32, 16),
    "medium": (24, 13),
    "small": (18, 11),
}

# Consistent spacing for every element in a layout row.
LAYOUT_PAD_X = 4
LAYOUT_PAD_Y = 2


def theme(_name):
    ctk.set_appearance_mode("System")
    ctk.set_default_color_theme("blue")


def set_appearance_mode(mode):
    """Set the explicit UI appearance mode (system, light, or dark)."""
    value = {"system": "System", "light": "Light", "dark": "Dark"}.get(
        str(mode).lower(), "System"
    )
    ctk.set_appearance_mode(value)


def get_appearance_mode():
    return str(ctk.get_appearance_mode()).lower()


def popup(message):
    messagebox.showinfo("RVC", message)


def popup_error(message):
    messagebox.showerror("RVC", message)


def choose_folder(initialdir=None):
    return filedialog.askdirectory(title="Select recording folder", initialdir=initialdir or None)


def choose_audio_file(initialdir=None):
    return filedialog.askopenfilename(
        title="Select audio file",
        initialdir=initialdir or None,
        filetypes=[
            ("Audio files", "*.wav *.mp3 *.flac *.m4a *.aac *.ogg *.opus *.wma *.aiff *.ape"),
            ("All files", "*.*"),
        ],
    )


def choose_save_text_file(initialdir=None):
    return filedialog.asksaveasfilename(
        title="Save log",
        initialdir=initialdir or None,
        defaultextension=".txt",
        filetypes=[("Text files", "*.txt"), ("All files", "*.*")],
    )


class StartupScreen:
    def __init__(self, text, title="RVC-Realtime-GUI", product_text=None):
        self.cancelled = False
        self.root = ctk.CTk()
        self.root.title(title)
        position = os.environ.get("RVC_SPLASH_POSITION", "")
        geometry = "290x150"
        if position:
            try:
                x, y = (int(value) for value in position.split(",", 1))
                geometry += f"+{x}+{y}"
            except ValueError:
                pass
        self.root.geometry(geometry)
        self.root.resizable(False, False)
        self.root.protocol("WM_DELETE_WINDOW", self.cancel)
        if product_text:
            self.product_label = ctk.CTkLabel(
                self.root,
                text=product_text,
                justify="center",
                font=ctk.CTkFont(family=UI_FONT_FAMILY, size=13),
                wraplength=260,
            )
            self.product_label.pack(fill="x", padx=15, pady=(14, 0))
            status_padding = (12, 4)
        else:
            self.product_label = None
            status_padding = (15, 5)
        self.label = ctk.CTkLabel(
            self.root,
            text=text,
            justify="center",
            font=ctk.CTkFont(family=UI_FONT_FAMILY, size=16, weight="bold"),
            wraplength=260,
        )
        self.label.pack(fill="x", padx=15, pady=status_padding)
        self.button = ctk.CTkButton(
            self.root,
            text="起動を中止" if IS_JAPANESE_UI else "Cancel startup",
            width=105,
            height=24,
            font=ctk.CTkFont(family=UI_FONT_FAMILY, size=12, weight="bold"),
            command=self.cancel,
        )
        self.button.pack(pady=(0, 12))
        self.refresh()

    def set_text(self, text):
        if not self.cancelled:
            self.label.configure(text=text)
            self.refresh()

    def cancel(self):
        self.cancelled = True
        self.root.destroy()

    def refresh(self):
        if self.cancelled:
            return
        try:
            self.root.update_idletasks()
            self.root.update()
        except tk.TclError:
            self.cancelled = True

    def close(self):
        if not self.cancelled:
            try:
                self.root.destroy()
            except tk.TclError:
                pass

    def take_root(self):
        """Hand the already-visible startup window to the main application."""
        if self.cancelled:
            return None
        for child in self.root.winfo_children():
            child.destroy()
        return self.root


def _pixel_width(size, default):
    if not size or size[0] in (None, 0):
        return default
    return max(int(size[0]) * 8, 40)


class _Element:
    def __init__(self, key=None, expand_x=False, tooltip=None):
        self.key = key
        self.expand_x = expand_x
        self.tooltip = tooltip
        self.widget = None
        self.window = None

    def _attach(self, window):
        self.window = window
        if self.key is not None:
            window.elements[self.key] = self

    def _dispatch(self, callback):
        if (
            self.window is not None
            and threading.get_ident() != self.window.ui_thread_id
        ):
            self.window.ui_updates.put(callback)
        else:
            callback()

    def update(self, value=None, values=None, visible=None, **_kwargs):
        def apply_update():
            self._update(value=value, values=values)
            if visible is not None and self.widget is not None:
                target = getattr(self, "container", self.widget)
                if visible:
                    target.grid()
                    if hasattr(self, "_grid_parent"):
                        self._grid_parent.grid_rowconfigure(
                            self._grid_row, minsize=self._grid_minsize
                        )
                else:
                    target.grid_remove()
                    if hasattr(self, "_grid_parent"):
                        self._grid_parent.grid_rowconfigure(
                            self._grid_row, minsize=0
                        )

        self._dispatch(apply_update)

    Update = update

    def _update(self, value=None, values=None):
        del value, values

    def get(self):
        return None


class _Push(_Element):
    pass


def Push():
    return _Push(expand_x=True)


class Text(_Element):
    def __init__(
        self,
        text="",
        size=(None, None),
        justification=None,
        key=None,
        expand_x=False,
        tooltip=None,
        height=None,
        **_kwargs,
    ):
        super().__init__(key=key, expand_x=expand_x, tooltip=tooltip)
        self.text = str(text)
        self.size = size
        self.justification = justification
        self.height = height

    def _build(self, parent, window):
        self._attach(window)
        anchor = {
            "right": "e",
            "center": "center",
        }.get(self.justification, "w")
        options = {}
        if self.height is not None:
            options["height"] = self.height
        self.widget = ctk.CTkLabel(
            parent,
            text=self.text,
            width=_pixel_width(self.size, 0),
            anchor=anchor,
            font=ctk.CTkFont(family=UI_FONT_FAMILY, size=13),
            **options,
        )
        return self.widget

    def _update(self, value=None, values=None):
        del values
        if value is not None:
            self.text = str(value)
            self.widget.configure(text=self.text)

    def get(self):
        return self.text


class Button(_Element):
    def __init__(
        self,
        text,
        key=None,
        button_color=None,
        hover_color=None,
        width=None,
        height=26,
        size=(None, None),
        font_size=13,
        font_family=None,
        button_style=None,
        **_kwargs,
    ):
        super().__init__(key=key or text)
        self.text = text
        self.button_color = button_color
        self.hover_color = hover_color
        self.width = width if width is not None else (
            _pixel_width(size, 100) if size and size[0] else None
        )
        style = BUTTON_STYLES.get(button_style)
        self.height = (
            style[0] if style else
            max(int(size[1]) * 20, 20)
            if size and size[1]
            else (height if height is not None else 26)
        )
        self.font_size = style[1] if style else font_size
        self.font_family = font_family

    def _build(self, parent, window):
        self._attach(window)
        options = {}
        if self.button_color is not None:
            options["fg_color"] = self.button_color
        if self.hover_color is not None:
            options["hover_color"] = self.hover_color
        if self.width is not None:
            options["width"] = self.width
        self.widget = ctk.CTkButton(
            parent,
            text=self.text,
            height=self.height,
            corner_radius=6,
            font=ctk.CTkFont(
                family=self.font_family or UI_FONT_FAMILY,
                size=self.font_size,
                weight="bold",
            ),
            command=lambda: window.post_event(self.key),
            **options,
        )
        return self.widget

    def update(
        self,
        value=None,
        text=None,
        button_color=None,
        hover_color=None,
        visible=None,
        **_kwargs,
    ):
        def apply_update():
            label = text if text is not None else value
            options = {}
            if label is not None:
                self.text = str(label)
                options["text"] = self.text
            if button_color is not None:
                options["fg_color"] = button_color
            if hover_color is not None:
                options["hover_color"] = hover_color
            if options:
                self.widget.configure(**options)
            if visible is not None:
                if visible:
                    self.widget.grid()
                else:
                    self.widget.grid_remove()

        self._dispatch(apply_update)

    Update = update


class Combo(_Element):
    def __init__(
        self,
        values,
        key=None,
        default_value="",
        enable_events=False,
        size=(None, None),
        readonly=False,
        tooltip=None,
        **_kwargs,
    ):
        super().__init__(key=key, tooltip=tooltip)
        self.values = list(values)
        self.value = default_value
        self.enable_events = enable_events
        self.size = size
        self.readonly = readonly

    def _build(self, parent, window):
        self._attach(window)
        self.variable = tk.StringVar(value=self.value)
        self.widget = ctk.CTkComboBox(
            parent,
            values=self.values or [""],
            variable=self.variable,
            width=_pixel_width(self.size, 180),
            state="readonly" if self.readonly else "normal",
            font=ctk.CTkFont(family=UI_FONT_FAMILY, size=13),
            dropdown_font=ctk.CTkFont(family=UI_FONT_FAMILY, size=13),
            command=(
                (lambda _value: window.post_event(self.key))
                if self.enable_events
                else None
            ),
        )
        return self.widget

    def _update(self, value=None, values=None):
        if values is not None:
            self.values = list(values)
            self.widget.configure(values=self.values or [""])
        if value is not None:
            self.value = value
            self.variable.set(value)

    def get(self):
        return self.variable.get()


class Checkbox(_Element):
    def __init__(
        self,
        text,
        key=None,
        default=False,
        enable_events=False,
        **_kwargs,
    ):
        super().__init__(key=key)
        self.text = text
        self.default = bool(default)
        self.enable_events = enable_events

    def _build(self, parent, window):
        self._attach(window)
        self.variable = tk.BooleanVar(value=self.default)
        self.widget = ctk.CTkCheckBox(
            parent,
            text=self.text,
            variable=self.variable,
            onvalue=True,
            offvalue=False,
            font=ctk.CTkFont(family=UI_FONT_FAMILY, size=13),
            command=(
                (lambda: window.post_event(self.key))
                if self.enable_events
                else None
            ),
        )
        return self.widget

    def _update(self, value=None, values=None):
        del values
        if value is not None:
            self.variable.set(bool(value))

    def get(self):
        return bool(self.variable.get())


class Radio(_Element):
    def __init__(
        self,
        text,
        group_id,
        key=None,
        default=False,
        enable_events=False,
        **_kwargs,
    ):
        super().__init__(key=key)
        self.text = text
        self.group_id = group_id
        self.default = default
        self.enable_events = enable_events

    def _build(self, parent, window):
        self._attach(window)
        variable = window.radio_variables.setdefault(
            self.group_id, tk.StringVar(value="")
        )
        if self.default:
            variable.set(self.key)
        self.variable = variable
        self.widget = ctk.CTkRadioButton(
            parent,
            text=self.text,
            width=60,
            height=24,
            font=ctk.CTkFont(family=UI_FONT_FAMILY, size=13),
            variable=self.variable,
            value=self.key,
            command=(
                (lambda: window.post_event(self.key))
                if self.enable_events
                else None
            ),
        )
        return self.widget

    def _update(self, value=None, values=None):
        del values
        if value:
            self.variable.set(self.key)
        elif self.variable.get() == self.key:
            self.variable.set("")

    def get(self):
        return self.variable.get() == self.key


class Slider(_Element):
    def __init__(
        self,
        range=(None, None),
        default_value=None,
        resolution=None,
        orientation="h",
        enable_events=False,
        size=(None, None),
        show_value=True,
        value_pady=0,
        value_right_margin=0,
        value_width=24,
        key=None,
        tooltip=None,
        **_kwargs,
    ):
        super().__init__(key=key, tooltip=tooltip)
        self.minimum, self.maximum = range
        self.value = float(default_value)
        self.resolution = resolution
        self.orientation = orientation
        self.enable_events = enable_events
        self.size = size
        self.show_value = show_value
        self.value_pady = value_pady
        self.value_right_margin = value_right_margin
        self.value_width = value_width

    def _format_value(self, value):
        if self.resolution is not None and self.resolution >= 1:
            return str(int(round(value)))
        decimals = 2
        if self.resolution is not None:
            text = f"{self.resolution:.8f}".rstrip("0")
            decimals = len(text.split(".")[1]) if "." in text else 0
        return f"{value:.{decimals}f}"

    def _build(self, parent, window):
        self._attach(window)
        slider_width = _pixel_width(self.size, 160)
        try:
            background = parent._apply_appearance_mode(parent.cget("fg_color"))
        except (AttributeError, tk.TclError):
            background = parent.cget("bg")
        container = tk.Frame(
            parent,
            background=background,
            width=slider_width + (self.value_width if self.show_value else 0),
            height=26,
        )
        container.grid_propagate(False)
        container.grid_columnconfigure(0, weight=1)
        steps = None
        if self.resolution:
            steps = max(
                int(round((self.maximum - self.minimum) / self.resolution)),
                1,
            )
        self.variable = tk.DoubleVar(value=self.value)
        self.widget = ctk.CTkSlider(
            container,
            from_=self.minimum,
            to=self.maximum,
            number_of_steps=steps,
            variable=self.variable,
            width=slider_width,
            height=16,
            border_width=0,
            progress_color=("#3b8ed0", "#1f6aa5"),
            button_color=("#1f6aa5", "#3b8ed0"),
            button_hover_color=("#144870", "#5aa9e6"),
            command=lambda value: self._changed(value, window),
        )
        # CTkSlider's visual track sits a few pixels above the center of its
        # nominal control. Match the 26px media buttons beside it.
        self.widget.grid(row=0, column=0, sticky="ew", padx=(0, 6), pady=(4, 0))
        self.value_label = None
        if self.show_value:
            self.value_label = ctk.CTkLabel(
                container,
                text=self._format_value(self.value),
                width=self.value_width,
                height=20,
                anchor="e",
                font=ctk.CTkFont(family=UI_FONT_FAMILY, size=12),
            )
            self.value_label.grid(
                row=0,
                column=1,
                sticky="e",
                padx=(0, self.value_right_margin),
                pady=(self.value_pady, 0),
            )
        self.container = container
        return container

    def _changed(self, value, window):
        self.value = float(value)
        if self.value_label is not None:
            self.value_label.configure(text=self._format_value(self.value))
        if self.enable_events:
            window.post_event(self.key)

    def _update(self, value=None, values=None):
        del values
        if value is not None:
            self.value = float(value)
            self.variable.set(self.value)
            if self.value_label is not None:
                self.value_label.configure(text=self._format_value(self.value))

    def get(self):
        return float(self.variable.get())


class LevelMeter(_Element):
    def __init__(self, key=None, size=(90, 8), tooltip=None, **_kwargs):
        super().__init__(key=key, tooltip=tooltip)
        self.size = size
        self.value = 0.0
        self.forced_color = None

    def _build(self, parent, window):
        self._attach(window)
        width = self.size[0] if self.size and self.size[0] else 90
        height = self.size[1] if self.size and self.size[1] else 8
        self.widget = ctk.CTkProgressBar(
            parent,
            width=width,
            height=height,
            corner_radius=max(height // 2, 1),
            progress_color="#2fa572",
        )
        self.widget.set(0)
        return self.widget

    def _update(self, value=None, values=None):
        del values
        if value is None:
            return
        self.value = max(0.0, min(float(value), 1.0))
        if self.value >= 0.95:
            color = "#e05252"
        elif self.value >= 0.80:
            color = "#d99b35"
        else:
            color = "#2fa572"
        if self.forced_color is not None:
            color = self.forced_color
        self.widget.configure(progress_color=color)
        self.widget.set(self.value)

    def set_color(self, color=None):
        self.forced_color = color
        if self.widget is not None:
            self.widget.configure(progress_color=color or "#2fa572")

    def get(self):
        return self.value


class Image(_Element):
    def __init__(
        self, path=None, key=None, size=(120, 120), expand_x=False, **_kwargs
    ):
        super().__init__(key=key, expand_x=expand_x)
        self.path = path
        self.size = size
        self.image = None

    def _load_image(self, path):
        width, height = self.size
        canvas = PILImage.new("RGBA", (width, height), (35, 35, 35, 255))
        if path and os.path.isfile(path):
            with PILImage.open(path) as source:
                source = source.convert("RGBA")
                if source.width and source.height:
                    scale = min(width / source.width, height / source.height)
                    target = (
                        max(1, round(source.width * scale)),
                        max(1, round(source.height * scale)),
                    )
                    source = source.resize(target, PILImage.Resampling.LANCZOS)
                x = (width - source.width) // 2
                y = (height - source.height) // 2
                canvas.alpha_composite(source, (x, y))
        self.image = ctk.CTkImage(
            light_image=canvas,
            dark_image=canvas,
            size=(width, height),
        )

    def _build(self, parent, window):
        self._attach(window)
        self._load_image(self.path)
        self.widget = ctk.CTkLabel(
            parent, text="", image=self.image, anchor="center"
        )
        return self.widget

    def _update(self, value=None, values=None):
        del values
        if value is not None:
            self.path = value
        self._load_image(self.path)
        self.widget.configure(image=self.image)

    def get(self):
        return self.path


class ModelGallery(_Element):
    """A compact model picker with a fixed eight-card row."""

    def __init__(self, cards=None, key=None, size=(690, 94), **_kwargs):
        super().__init__(key=key)
        self.cards = list(cards or [])
        self.size = size
        self.selected = ""
        self._images = []
        self._buttons = {}

    @staticmethod
    def _label(name):
        return name if len(name) <= 10 else f"{name[:9]}…"

    def _thumbnail(self, path):
        # ModelGallery is hosted in a plain Tk canvas.  Do not use CTkImage
        # here: its appearance tracker does not reliably propagate below a
        # raw Tk canvas.  The gallery is rebuilt at each theme switch.
        background = (55, 55, 55, 255) if get_appearance_mode() == "dark" else (227, 227, 227, 255)
        canvas = PILImage.new("RGBA", (60, 60), background)
        if path and os.path.isfile(path):
            try:
                with PILImage.open(path) as source:
                    source = source.convert("RGBA")
                    source.thumbnail((60, 60), PILImage.Resampling.LANCZOS)
                    x = (60 - source.width) // 2
                    y = (60 - source.height) // 2
                    canvas.alpha_composite(source, (x, y))
            except (OSError, ValueError):
                pass
        image = ImageTk.PhotoImage(canvas)
        self._images.append(image)
        return image

    def _render_cards(self):
        for child in self.content.winfo_children():
            child.destroy()
        self._images = []
        self._buttons = {}
        if not self.cards:
            tk.Label(
                self.widget,
                text="No models available",
                font=(UI_FONT_FAMILY, 12),
                background=self._native_background(),
            ).grid(row=0, column=0, padx=6, pady=6, sticky="w")
            return
        dark = get_appearance_mode() == "dark"
        text_color = "#f2f2f2" if dark else "#202020"
        gallery_background = self.content.cget("background")
        for index, (event_key, name, path) in enumerate(self.cards):
            row, column = divmod(index, 8)
            selected = name == self.selected
            card_color = "#2b79b7" if selected else ("#3a3a3a" if dark else "#e3e3e3")
            card = tk.Canvas(
                self.content,
                width=76,
                height=86,
                background=card_color,
                highlightthickness=0,
                borderwidth=0,
            )
            card.grid(row=row, column=column, padx=(0, 6), pady=2, sticky="n")
            # Draw the rounded body over the gallery background.  Keeping
            # the canvas background equal to its parent leaves true rounded
            # corners without reintroducing CTk appearance tracking here.
            card.configure(background=gallery_background)
            self._rounded_rectangle(card, 0, 0, 76, 86, 7, fill=card_color)
            # 60px thumbnail: place it at y=35 for a 5px top margin.
            card.create_image(38, 35, image=self._thumbnail(path), anchor="center")
            card.create_text(
                38,
                76,
                text=self._label(name),
                fill="#ffffff" if selected else text_color,
                font=(UI_FONT_FAMILY, 8),
                anchor="center",
            )
            card.bind(
                "<Button-1>",
                lambda _event, key=event_key: self.window.post_event(key),
            )
            card.bind("<MouseWheel>", self._on_mousewheel, add="+")
            self._buttons[name] = card
        scrollbar = getattr(self.widget, "_scrollbar", None)
        del scrollbar
        if len(self.cards) > 8:
            self.scrollbar.grid()
        else:
            self.scrollbar.grid_remove()
        self._sync_scroll_region()
        self.canvas.yview_moveto(0.0)

    @staticmethod
    def _native_background():
        return "#212121" if get_appearance_mode() == "dark" else "#f0f0f0"

    @staticmethod
    def _rounded_rectangle(canvas, x1, y1, x2, y2, radius, **options):
        points = [
            x1 + radius, y1,
            x2 - radius, y1,
            x2, y1,
            x2, y1 + radius,
            x2, y2 - radius,
            x2, y2,
            x2 - radius, y2,
            x1 + radius, y2,
            x1, y2,
            x1, y2 - radius,
            x1, y1 + radius,
            x1, y1,
        ]
        return canvas.create_polygon(points, smooth=True, splinesteps=16, **options)

    def _sync_scroll_region(self, _event=None):
        self.content.update_idletasks()
        row_count = max(1, (len(self.cards) + 7) // 8)
        self.canvas.configure(
            scrollregion=(0, 0, 656, row_count * 90 + 4)
        )

    def _on_mousewheel(self, event):
        if event.delta:
            self.canvas.yview_scroll(-int(event.delta / 120), "units")
        return "break"

    def _on_global_mousewheel(self, event):
        try:
            x = self.canvas.winfo_pointerx()
            y = self.canvas.winfo_pointery()
            left = self.canvas.winfo_rootx()
            top = self.canvas.winfo_rooty()
            if (
                left <= x < left + self.canvas.winfo_width()
                and top <= y < top + self.canvas.winfo_height()
            ):
                return self._on_mousewheel(event)
        except tk.TclError:
            return None
        return None

    def _build(self, parent, window):
        self._attach(window)
        try:
            background = parent._apply_appearance_mode(parent.cget("fg_color"))
        except (AttributeError, tk.TclError):
            background = parent.cget("bg")
        self.widget = tk.Frame(
            parent,
            background=background,
            width=self.size[0],
            height=self.size[1],
        )
        self.widget.grid_propagate(False)
        self.canvas = tk.Canvas(
            self.widget,
            width=663,
            height=self.size[1],
            background=background,
            highlightthickness=0,
            borderwidth=0,
        )
        self.scrollbar = tk.Scrollbar(
            self.widget,
            orient="vertical",
            width=12,
            command=self.canvas.yview,
        )
        self.canvas.configure(yscrollcommand=self.scrollbar.set)
        self.content = tk.Frame(self.canvas, background=background, width=656)
        self.canvas.create_window((0, 0), window=self.content, anchor="nw")
        self.canvas.grid(row=0, column=0, sticky="nsew")
        self.scrollbar.grid(row=0, column=1, sticky="ns")
        self.widget.grid_columnconfigure(0, weight=1)
        self.content.bind("<Configure>", self._sync_scroll_region)
        self.canvas.bind("<MouseWheel>", self._on_mousewheel)
        self.content.bind("<MouseWheel>", self._on_mousewheel, add="+")
        self.widget.bind_all("<MouseWheel>", self._on_global_mousewheel, add="+")
        self._render_cards()
        return self.widget

    def update(self, cards=None, selected=None, visible=None, **_kwargs):
        def apply_update():
            if cards is not None:
                self.cards = list(cards)
            if selected is not None:
                self.selected = selected
            if cards is not None or selected is not None:
                self._render_cards()
            if visible is not None:
                if visible:
                    self.widget.grid()
                else:
                    self.widget.grid_remove()

        self._dispatch(apply_update)

    Update = update

    def get(self):
        return self.selected


class Multiline(_Element):
    def __init__(
        self,
        default_text="",
        key=None,
        size=(None, None),
        disabled=False,
        autoscroll=False,
        font=None,
        expand_x=False,
        pixel_size=None,
        **_kwargs,
    ):
        super().__init__(key=key, expand_x=expand_x)
        self.text = default_text
        self.size = size
        self.disabled = disabled
        self.autoscroll = autoscroll
        self.font = font
        self.pixel_size = pixel_size

    def _build(self, parent, window):
        self._attach(window)
        if self.pixel_size:
            width, height = self.pixel_size
        else:
            width = _pixel_width(self.size, 700)
            height = 120 if not self.size or not self.size[1] else self.size[1] * 18
        self.widget = ctk.CTkTextbox(
            parent,
            width=width,
            height=height,
            font=self.font
            or ctk.CTkFont(family=UI_FONT_FAMILY, size=11),
            wrap="word",
        )
        self.widget.insert("1.0", self.text)
        if self.disabled:
            self.widget.configure(state="disabled")
        return self.widget

    def _update(self, value=None, values=None):
        del values
        if value is None:
            return
        self.text = str(value)
        self.widget.configure(state="normal")
        self.widget.delete("1.0", "end")
        self.widget.insert("1.0", self.text)
        if self.autoscroll:
            self.widget.see("end")
        if self.disabled:
            self.widget.configure(state="disabled")

    def get(self):
        return self.text


class Frame(_Element):
    def __init__(
        self,
        title="",
        layout=None,
        expand_x=False,
        size=None,
        header_button=None,
        header_buttons=None,
        key=None,
        **_kwargs,
    ):
        super().__init__(key=key, expand_x=expand_x)
        self.title = title
        self.layout = layout or []
        self.size = size
        self.header_button = header_button
        self.header_buttons = list(header_buttons or ([] if header_button is None else [header_button]))

    def _build(self, parent, window):
        self._attach(window)
        options = {"corner_radius": 7}
        if self.size:
            options.update(width=self.size[0], height=self.size[1])
        self.widget = ctk.CTkFrame(parent, **options)
        if self.size:
            self.widget.grid_propagate(False)
        self.widget.grid_columnconfigure(0, weight=1)
        content_start_row = 0
        if self.title:
            title = ctk.CTkLabel(
                self.widget,
                text=self.title,
                font=ctk.CTkFont(
                    family=UI_FONT_FAMILY, size=14, weight="bold"
                ),
                anchor="w",
            )
            title.grid(row=0, column=0, sticky="ew", padx=(8, 4), pady=(4, 0))
            content_start_row = 1
        for column, spec in enumerate(self.header_buttons, start=1):
            button_text, button_key, *button_options = spec
            button_width = button_options[0] if button_options else 112
            button_style = button_options[1] if len(button_options) > 1 else "small"
            button_height, button_font_size = BUTTON_STYLES[button_style]
            header_button = ctk.CTkButton(
                self.widget,
                text=button_text,
                width=button_width,
                height=button_height,
                corner_radius=5,
                font=ctk.CTkFont(
                    family=UI_FONT_FAMILY, size=button_font_size, weight="bold"
                ),
                command=lambda key=button_key: window.post_event(key),
            )
            header_button.grid(
                row=0,
                column=column,
                sticky="e",
                padx=(4, 8),
                pady=(4, 0),
            )
            window.header_buttons[button_key] = header_button
        window._render_layout(self.widget, self.layout, start_row=content_start_row)
        return self.widget

    def update(self, size=None, visible=None, **_kwargs):
        def apply_update():
            if size is not None:
                self.size = size
                self.widget.configure(width=size[0], height=size[1])
                self.widget.grid_propagate(False)
                if hasattr(self, "_grid_parent"):
                    self._grid_minsize = size[1]
                    self._grid_parent.grid_rowconfigure(
                        self._grid_row, minsize=size[1]
                    )
            if visible is not None:
                if visible:
                    self.widget.grid()
                else:
                    self.widget.grid_remove()

        self._dispatch(apply_update)

    Update = update


class Column(Frame):
    def __init__(self, layout=None, size=None, **_kwargs):
        super().__init__(layout=layout, size=size, **_kwargs)

    def _build(self, parent, window):
        self._attach(window)
        try:
            background = parent._apply_appearance_mode(parent.cget("fg_color"))
        except (AttributeError, tk.TclError):
            background = parent.cget("bg")
        self.widget = tk.Frame(parent, background=background)
        window._render_layout(self.widget, self.layout)
        return self.widget


class Window:
    def __init__(self, title, layout, finalize=False, root=None, **_kwargs):
        del finalize
        self.root = root or ctk.CTk()
        self.root.title(title)
        self.root.geometry("700x600")
        self.root.resizable(False, False)
        self.ui_thread_id = threading.get_ident()
        self.events = queue.Queue()
        self.ui_updates = queue.Queue()
        self.elements = {}
        self.header_buttons = {}
        self.radio_variables = {}
        self.closed = False
        self.status_window = None
        self.status_label = None
        self.root.protocol("WM_DELETE_WINDOW", self._request_close)
        self._render_layout(self.root, layout)
        self.root.update_idletasks()

    def _request_close(self):
        if not self.closed:
            self.closed = True
            self.post_event(WINDOW_CLOSED)

    def _render_layout(self, parent, layout, start_row=0):
        for row_offset, row in enumerate(layout):
            grid_row = start_row + row_offset
            try:
                background = parent._apply_appearance_mode(
                    parent.cget("fg_color")
                )
            except (AttributeError, tk.TclError):
                background = parent.cget("bg")
            row_container = tk.Frame(parent, background=background, height=1)
            row_container.grid(
                row=grid_row,
                column=0,
                columnspan=20,
                sticky="ew",
                padx=0,
                pady=0,
            )
            parent.grid_columnconfigure(0, weight=1)
            column = 0
            for element in row:
                if isinstance(element, _Push):
                    spacer = tk.Frame(
                        row_container,
                        background=background,
                        width=1,
                        height=1,
                    )
                    spacer.grid(row=0, column=column, sticky="ew")
                    row_container.grid_columnconfigure(column, weight=1)
                    column += 1
                    continue
                widget = element._build(row_container, self)
                sticky = (
                    "nsew"
                    if isinstance(element, Frame) and element.size
                    else "ew" if element.expand_x else "w"
                )
                widget.grid(
                    row=0,
                    column=column,
                    sticky=sticky,
                    padx=LAYOUT_PAD_X,
                    pady=LAYOUT_PAD_Y,
                )
                element._grid_parent = parent
                element._grid_row = grid_row
                element._grid_minsize = (
                    element.size[1]
                    if isinstance(element, Frame) and element.size
                    else 0
                )
                if element.expand_x:
                    row_container.grid_columnconfigure(column, weight=1)
                if isinstance(element, Frame) and element.size:
                    row_container.grid_columnconfigure(
                        column, minsize=element.size[0]
                    )
                    parent.grid_rowconfigure(grid_row, minsize=element.size[1])
                column += 1

    def set_size(self, width, height):
        self.root.geometry(f"{int(width)}x{int(height)}")

    def set_position(self, x, y):
        self.root.geometry(f"+{int(x)}+{int(y)}")

    @staticmethod
    def _native_background(widget):
        """Resolve the current CTk colour for a plain Tk child widget."""
        parent = widget.master
        while parent is not None:
            try:
                color = parent.cget("fg_color")
                if color != "transparent" and hasattr(parent, "_apply_appearance_mode"):
                    return parent._apply_appearance_mode(color)
            except (AttributeError, tk.TclError):
                pass
            parent = getattr(parent, "master", None)
        return "#f0f0f0" if get_appearance_mode() == "light" else "#212121"

    def refresh_appearance(self):
        """Refresh plain Tk containers, which CTk cannot recolour by itself."""
        def refresh(widget):
            for child in widget.winfo_children():
                # CTkFrame inherits from tkinter.Frame but does not accept
                # Tk's ``background`` option.  Only recolour plain Tk
                # containers created by this adapter.
                if type(child) in (tk.Frame, tk.Canvas):
                    try:
                        child.configure(background=self._native_background(child))
                    except tk.TclError:
                        pass
                refresh(child)

        self.root.update_idletasks()
        refresh(self.root)

    def update_header_button(self, key, text):
        button = self.header_buttons.get(key)
        if button is not None:
            button.configure(text=str(text))

    def get_position(self):
        self.root.update_idletasks()
        return self.root.winfo_x(), self.root.winfo_y()

    def show_status(self, text):
        if self.status_window is None or not self.status_window.winfo_exists():
            self.status_window = ctk.CTkToplevel(self.root)
            self.status_window.title("RVC-Realtime-GUI")
            self.status_window.geometry("260x90")
            self.status_window.resizable(False, False)
            self.status_window.transient(self.root)
            self.status_window.attributes("-topmost", True)
            self.status_label = ctk.CTkLabel(
                self.status_window,
                text=text,
                font=ctk.CTkFont(family=UI_FONT_FAMILY, size=14),
            )
            self.status_label.pack(expand=True, fill="both", padx=15, pady=15)
        else:
            self.status_label.configure(text=text)
        self.status_window.update_idletasks()
        self.status_window.update()

    def hide_status(self):
        if self.status_window is not None and self.status_window.winfo_exists():
            self.status_window.destroy()
        self.status_window = None
        self.status_label = None

    def refresh(self):
        self.root.update_idletasks()
        self.root.update()
    def post_event(self, event):
        self.events.put(event)

    def _drain_ui_updates(self):
        for _ in range(500):
            try:
                callback = self.ui_updates.get_nowait()
            except queue.Empty:
                break
            callback()

    def _values(self):
        return {key: element.get() for key, element in self.elements.items()}

    def read(self, timeout=None, timeout_key=TIMEOUT_EVENT, close=False):
        del close
        deadline = (
            None if timeout is None else time.perf_counter() + timeout / 1000.0
        )
        while True:
            self._drain_ui_updates()
            try:
                self.root.update_idletasks()
                self.root.update()
            except tk.TclError:
                return WINDOW_CLOSED, self._values()
            try:
                event = self.events.get_nowait()
                return event, self._values()
            except queue.Empty:
                pass
            if deadline is not None and time.perf_counter() >= deadline:
                return timeout_key, self._values()
            time.sleep(0.01)

    def __getitem__(self, key):
        return self.elements[key]

    def close(self):
        if not self.closed:
            self.closed = True
        try:
            self.root.destroy()
        except tk.TclError:
            pass
