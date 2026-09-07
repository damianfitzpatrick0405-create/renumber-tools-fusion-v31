"""
renumberTools.py
Reads every tool in the document CAM library, matches descriptions
against the ACTIVE master list, writes tool numbers back.
"""
import adsk.core, adsk.fusion, adsk.cam, traceback, os, sys

_dir = os.path.dirname(os.path.realpath(__file__))
_lib_dir = os.path.join(os.path.dirname(_dir), 'lib')
if _lib_dir not in sys.path:
    sys.path.insert(0, _lib_dir)

import tool_list as tl

_CMD_ID   = 'renumberToolsToMasterList'
_CMD_NAME = 'Renumber Tools to Master List'
_CMD_DESC = 'Updates tool numbers in the document CAM library to match the active master tool list.'
_WORKSPACE = 'CAMEnvironment'
_PANEL     = 'CAMManagePanel'

_handlers = []
_button   = None


class _CreatedHandler(adsk.core.CommandCreatedEventHandler):
    def __init__(self): super().__init__()
    def notify(self, args):
        try:
            h = _ExecuteHandler()
            args.command.execute.add(h)
            _handlers.append(h)
        except Exception:
            adsk.core.Application.get().userInterface.messageBox(traceback.format_exc())


def perform_renumber():
    """
    Core renumber logic, shared by the toolbar command and the
    'Renumber Active Doc' button in the Tool List Manager palette.
    Returns a dict: {'ok': bool, 'message': str}
    """
    app = adsk.core.Application.get()

    # ── Get CAM product ───────────────────────────────────────────
    doc = app.activeDocument
    if not doc:
        return {'ok': False, 'message': 'No active document.'}

    cam = None
    for i in range(doc.products.count):
        p = doc.products.item(i)
        if p.objectType == adsk.cam.CAM.classType():
            cam = p
            break

    if not cam:
        return {'ok': False, 'message': 'No CAM workspace in the active document.\nOpen the Manufacturing workspace first.'}

    doc_lib = cam.documentToolLibrary
    if not doc_lib or doc_lib.count == 0:
        return {'ok': False, 'message': 'The document tool library is empty.\nAdd tools to your CAM setup first.'}

    # ── Load active master list ───────────────────────────────────
    active_name = tl.get_active_list_name()
    master      = tl.load()
    lookup      = tl.build_lookup(master)

    updated       = []
    already_ok    = []
    missing       = []

    for i in range(doc_lib.count):
        tool   = doc_lib.item(i)
        params = tool.parameters

        desc_p   = params.itemByName('tool_description')
        raw_desc = desc_p.value.value if desc_p else ''
        if not isinstance(raw_desc, str):
            raw_desc = str(raw_desc)

        tn_p = params.itemByName('tool_number')
        try:
            cur_num = int(tn_p.value.value) if tn_p else -1
        except (TypeError, ValueError):
            cur_num = -1

        key = tl.normalize(raw_desc)

        if key in lookup:
            new_num = lookup[key]
            if cur_num != new_num:
                tn_p.value.value = new_num
                doc_lib.update(tool, True)
                updated.append((new_num, raw_desc))
            else:
                already_ok.append(raw_desc)
        elif raw_desc:
            missing.append(raw_desc)

    # ── Sync unknowns back to JSON ────────────────────────────────
    if missing:
        tl.save(tl.sync_missing(master, missing))

    # ── Result message ────────────────────────────────────────────
    lines = ['Active list: {}'.format(active_name), '']
    if updated:
        lines.append('✅ Updated {} tool(s):'.format(len(updated)))
        for num, desc in updated:
            lines.append('   T{} — {}'.format(num, desc))
    if already_ok:
        lines.append('☑️  {} tool(s) already correct.'.format(len(already_ok)))
    if missing:
        lines.append('⚠️  {} tool(s) not in master list (added as T0):'.format(len(missing)))
        for desc in missing:
            lines.append('   • {}'.format(desc))
    if not updated and not missing:
        lines.append('All tools already match the master list.')

    return {'ok': True, 'message': '\n'.join(lines)}


class _ExecuteHandler(adsk.core.CommandEventHandler):
    def __init__(self): super().__init__()

    def notify(self, args):
        ui = None
        try:
            app = adsk.core.Application.get()
            ui  = app.userInterface
            result = perform_renumber()
            ui.messageBox(result['message'], 'Renumber Tools Result')

        except Exception:
            if ui:
                ui.messageBox('Renumber Tools failed:\n{}'.format(traceback.format_exc()))


def register(handler_list):
    global _button, _handlers
    _handlers = handler_list
    app = adsk.core.Application.get()
    ui  = app.userInterface

    existing = ui.commandDefinitions.itemById(_CMD_ID)
    if existing:
        existing.deleteMe()

    cmd_def = ui.commandDefinitions.addButtonDefinition(_CMD_ID, _CMD_NAME, _CMD_DESC)
    h = _CreatedHandler()
    cmd_def.commandCreated.add(h)
    handler_list.append(h)

    ws = ui.workspaces.itemById(_WORKSPACE)
    if ws:
        panel = ws.toolbarPanels.itemById(_PANEL)
        if not panel:
            panel = ws.toolbarPanels.add(_PANEL, 'Manage')
        _button = panel.controls.addCommand(cmd_def)
        _button.isPromotedByDefault = True
        _button.isPromoted = True


def unregister():
    global _button
    app = adsk.core.Application.get()
    ui  = app.userInterface
    if _button:
        _button.deleteMe()
        _button = None
    cmd = ui.commandDefinitions.itemById(_CMD_ID)
    if cmd:
        cmd.deleteMe()
