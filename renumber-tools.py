import adsk.core
import adsk.fusion
import adsk.cam
import traceback
import os
import sys

# Add lib directory to path
_dir = os.path.dirname(os.path.realpath(__file__))
if _dir not in sys.path:
    sys.path.insert(0, _dir)

from commands import renumberTools, editToolList

_handlers = []
_commands = []


def run(context):
    ui = None
    try:
        app = adsk.core.Application.get()
        ui = app.userInterface

        # Register commands
        renumberTools.register(_handlers)
        editToolList.register(_handlers)

    except Exception:
        if ui:
            ui.messageBox('Failed to start Renumber Tools add-in:\n{}'.format(traceback.format_exc()))


def stop(context):
    ui = None
    try:
        app = adsk.core.Application.get()
        ui = app.userInterface

        # Clean up all commands and UI elements
        renumberTools.unregister()
        editToolList.unregister()

        # Remove palette if open
        palette = ui.palettes.itemById('renumberToolsPalette')
        if palette:
            palette.deleteMe()

    except Exception:
        if ui:
            ui.messageBox('Failed to stop Renumber Tools add-in:\n{}'.format(traceback.format_exc()))
