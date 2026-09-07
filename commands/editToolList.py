"""
editToolList.py
Opens the tool list editor palette.
"""
import adsk.core, adsk.fusion, adsk.cam, traceback, json, os, sys, time

_dir         = os.path.dirname(os.path.realpath(__file__))
_lib_dir     = os.path.join(os.path.dirname(_dir), 'lib')
_palette_dir = os.path.join(os.path.dirname(_dir), 'palette')
if _lib_dir not in sys.path:
    sys.path.insert(0, _lib_dir)

import tool_list as tl
from commands import renumberTools

_CMD_ID    = 'editMasterToolList'
_CMD_NAME  = 'Edit Master Tool List'
_CMD_DESC  = 'Manage master tool lists and import from Fusion libraries.'
_PAL_ID    = 'renumberToolsPalette'
_WORKSPACE = 'CAMEnvironment'
_PANEL     = 'CAMManagePanel'

_handlers = []
_button   = None


# ── Helpers ───────────────────────────────────────────────────────────────────

def _get_local_libraries():
    results = []
    try:
        cam_mgr   = adsk.cam.CAMManager.get()
        tool_libs = cam_mgr.libraryManager.toolLibraries
        root_url  = tool_libs.urlByLocation(adsk.cam.LibraryLocations.LocalLibraryLocation)

        def walk(url):
            try:
                for asset_url in tool_libs.childAssetURLs(url):
                    results.append({'name': asset_url.leafName, 'url': asset_url.toString()})
                for folder_url in tool_libs.childFolderURLs(url):
                    walk(folder_url)
            except Exception:
                pass

        walk(root_url)
    except Exception:
        pass
    return results


def _import_from_url(url_str, mode, data=None):
    if data is None:
        data = {}
    try:
        cam_mgr   = adsk.cam.CAMManager.get()
        tool_libs = cam_mgr.libraryManager.toolLibraries
        url       = adsk.core.URL.create(url_str)
        lib       = tool_libs.toolLibraryAtURL(url)
        if not lib:
            return {'ok': False, 'error': 'Could not open library.'}

        incoming = []
        for i in range(lib.count):
            tool   = lib.item(i)
            params = tool.parameters
            desc_p = params.itemByName('tool_description')
            tn_p   = params.itemByName('tool_number')
            desc   = desc_p.value.value if desc_p else ''
            if not isinstance(desc, str):
                desc = str(desc)
            num = 0
            if tn_p:
                try:
                    num = int(tn_p.value.value)
                except (TypeError, ValueError):
                    num = 0
            if desc.strip():
                incoming.append({'description': desc.strip(), 'toolNumber': num})

        if mode == 'replace':
            tl.save(incoming)
            return {'ok': True, 'mode': 'replace', 'count': len(incoming)}
        elif mode == 'newlist':
            new_name = data.get('newListName', 'Imported Library').strip()
            if not new_name.endswith('.json'):
                new_name += '.json'
            tl.create_list(new_name)
            tl.save(incoming, new_name)
            tl.set_active_list_name(new_name)
            return {'ok': True, 'mode': 'newlist', 'count': len(incoming), 'name': new_name}
        else:
            base = tl.load()
            merged, added, updated = tl.merge_into(base, incoming)
            tl.save(merged)
            return {'ok': True, 'mode': 'merge', 'added': added, 'updated': updated, 'total': len(merged)}

    except Exception:
        return {'ok': False, 'error': traceback.format_exc()}


def _build_state():
    """Build the full state payload to send to the palette."""
    all_lists   = tl.list_all()
    active_name = tl.get_active_list_name()
    if active_name not in all_lists and all_lists:
        active_name = all_lists[0]
        tl.set_active_list_name(active_name)
    return {
        'command':    'setState',
        'allLists':   all_lists,
        'activeList': active_name,
        'toolList':   tl.load(active_name),
        'localLibs':  _get_local_libraries(),
    }


def _send_state(palette):
    payload = json.dumps(_build_state())
    # Retry a few times in case the webview bridge isn't ready yet
    for _ in range(3):
        try:
            palette.sendInfoToHTML('setState', payload)
            break
        except Exception:
            time.sleep(0.15)


def _send_list_tools(palette, filename):
    """Send just the tools for a specific list (when user clicks sidebar item)."""
    payload = json.dumps({
        'command':  'setListTools',
        'filename': filename,
        'toolList': tl.load(filename),
    })
    for _ in range(3):
        try:
            palette.sendInfoToHTML('setListTools', payload)
            break
        except Exception:
            time.sleep(0.15)


# ── Command handlers ──────────────────────────────────────────────────────────

class _CreatedHandler(adsk.core.CommandCreatedEventHandler):
    def __init__(self): super().__init__()
    def notify(self, args):
        try:
            h = _ExecuteHandler()
            args.command.execute.add(h)
            _handlers.append(h)
        except Exception:
            adsk.core.Application.get().userInterface.messageBox(traceback.format_exc())


class _ExecuteHandler(adsk.core.CommandEventHandler):
    def __init__(self): super().__init__()
    def notify(self, args):
        ui = None
        try:
            app = adsk.core.Application.get()
            ui  = app.userInterface
            palette = ui.palettes.itemById(_PAL_ID)

            if palette:
                palette.isVisible = True
                _send_state(palette)
                return

            html_path = 'file:///' + os.path.join(_palette_dir, 'toolListEditor.html').replace('\\', '/') + '?v=' + str(int(time.time()))
            palette = ui.palettes.add(_PAL_ID, 'Tool List Manager', html_path,
                                      True, True, True, 960, 700)

            h = _HTMLHandler()
            palette.incomingFromHTML.add(h)
            _handlers.append(h)
            # Defensively try navigatedTo — not available in all API versions
            try:
                h2 = _NavigatedHandler()
                palette.navigatedTo.add(h2)
                _handlers.append(h2)
            except Exception:
                pass

        except Exception:
            if ui:
                ui.messageBox('Edit Tool List failed:\n{}'.format(traceback.format_exc()))


class _NavigatedHandler(adsk.core.NavigationEventHandler):
    def __init__(self): super().__init__()
    def notify(self, args):
        try:
            palette = adsk.core.Application.get().userInterface.palettes.itemById(_PAL_ID)
            if palette:
                _send_state(palette)
        except Exception:
            pass


class _HTMLHandler(adsk.core.HTMLEventHandler):
    def __init__(self): super().__init__()

    def notify(self, args):
        ui = None
        try:
            app    = adsk.core.Application.get()
            ui     = app.userInterface
            action = args.action
            data   = json.loads(args.data) if args.data else {}
            palette = ui.palettes.itemById(_PAL_ID)

            # Page loaded — send initial state
            if action == 'ready':
                if palette:
                    _send_state(palette)

            # User clicked a list in the sidebar — load its tools
            elif action == 'loadListTools':
                if palette:
                    _send_list_tools(palette, data['filename'])

            # Save the currently-editing list
            elif action == 'saveToolList':
                filename = data.get('filename', tl.get_active_list_name())
                tl.save(data.get('toolList', []), filename)
                if palette:
                    _send_state(palette)

            # Set which list is active for renumbering
            elif action == 'setActiveList':
                filename = data['filename']
                tl.set_active_list_name(filename)
                if palette:
                    _send_state(palette)  # applyState in JS now auto-switches editor

            # Create new empty list
            elif action == 'createList':
                name = data.get('name', '').strip()
                if not name.endswith('.json'):
                    name += '.json'
                if tl.create_list(name):
                    tl.set_active_list_name(name)
                    if palette:
                        _send_state(palette)
                else:
                    ui.messageBox('A list named "{}" already exists.'.format(name))

            # Delete a list
            elif action == 'deleteList':
                filename  = data['filename']
                all_lists = tl.list_all()
                if len(all_lists) <= 1:
                    ui.messageBox('Cannot delete the only list.')
                    return
                tl.delete_list(filename)
                remaining = tl.list_all()
                if tl.get_active_list_name() == filename and remaining:
                    tl.set_active_list_name(remaining[0])
                if palette:
                    _send_state(palette)

            # Rename a list
            elif action == 'renameList':
                old = data['oldFilename']
                new = data['newName'].strip()
                if not new.endswith('.json'):
                    new += '.json'
                if not tl.rename_list(old, new):
                    ui.messageBox('Could not rename — "{}" may already exist.'.format(new))
                if palette:
                    _send_state(palette)

            # Renumber the active document's CAM tool library against the
            # active master list (same action as the toolbar command)
            elif action == 'renumberTools':
                result = renumberTools.perform_renumber()
                ui.messageBox(result['message'],
                              'Renumber Tools Result' if result['ok'] else 'Renumber Tools')
                if palette:
                    _send_state(palette)

            # Import from a Fusion local library
            elif action == 'importLibrary':
                result = _import_from_url(data['url'], data.get('mode', 'merge'), data)
                if result['ok']:
                    if result['mode'] == 'replace':
                        msg = '✅ Replaced list with {} tools.'.format(result['count'])
                    elif result['mode'] == 'newlist':
                        msg = '✅ Created "{}" with {} tools.'.format(
                            result['name'].replace('.json',''), result['count'])
                    else:
                        msg = '✅ Merged: {} added, {} updated.'.format(result['added'], result['updated'])
                    ui.messageBox(msg, 'Import Complete')
                else:
                    ui.messageBox('Import failed:\n' + result.get('error', 'Unknown error'))
                if palette:
                    _send_state(palette)

        except Exception:
            if ui:
                ui.messageBox('Palette error:\n{}'.format(traceback.format_exc()))


# ── Register / unregister ─────────────────────────────────────────────────────

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
