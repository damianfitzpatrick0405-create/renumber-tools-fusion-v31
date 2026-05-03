# Renumber Tools — Fusion 360 Add-in

This is for Machinists who are making a switch to a tool library with standardized tool numbers at your machines. This add-in in one click Syncs a legacy CAM programs tool numbers to your shop's master tool list. Or Manage multiple Master Lists for switching between machines that support different numbers of tools in their controls.

## What It Does

1. **Renumber Tools to Master List** — Reads every tool in the active document's CAM library, matches each tool's description against `shopToolList.json`, and writes the correct `toolNumber` back into the document library. Any tool descriptions not found in the master list are automatically added with `toolNumber: 0` so you can assign them later.

2. **Edit Master Tool List** — Opens an editor panel for managing `shopToolList.json` directly inside Fusion 360.

## Installation

1. Copy the entire `renumber-tools` folder to your Fusion 360 add-ins directory:
   - **Windows:** `%appdata%\Autodesk\Autodesk Fusion 360\API\AddIns\`
   - **Mac:** `~/Library/Application Support/Autodesk/Autodesk Fusion 360/API/AddIns/`

2. Open Fusion 360.

3. Go to **Utilities → ADD-INS → Add-Ins tab**.

4. Find **renumber-tools** in the list and click **Run**.

   To load automatically on startup, check **Run on Startup**.

## Usage

Both commands appear in the **Manufacturing workspace** toolbar under the **Manage** panel.

### Renumber Tools to Master List
1. Open a Fusion 360 document with a CAM setup.
2. Make sure tools have been added to the document's tool library.
3. Switch to the **Manufacturing** workspace.
4. Click **Renumber Tools to Master List**.
5. A summary dialog will show:
   - ✅ Tools that were updated with their new numbers
   - ☑️ Tools already at the correct number
   - ⚠️ Tools not found in the master list (added with T0)

### Edit Master Tool List
1. Click **Edit Master Tool List** in the Manufacturing toolbar.
2. The editor panel opens with your full tool list.
3. Add, edit, or remove tools.
4. Click **💾 Save** to write changes to disk.

## Master Tool List File

The master list is stored at:
```
renumber-tools/lib/shopToolList.json
```

Same format as the VS Code extension:
```json
[
  { "description": "1/2\" Flat Endmill", "toolNumber": 12 },
  { "description": "PROBE", "toolNumber": 3 }
]
```

- **Description matching is case-insensitive** and ignores extra whitespace.
- Tools with `toolNumber: 0` are flagged in orange in the editor — these need a number assigned.

## Sharing Across Machines

The `shopToolList.json` file is a plain JSON file. To share across your shop:
- Put the add-in folder on a network share and have each machine point to it, **or**
- Copy `shopToolList.json` to each machine when it changes.

## Notes

- Only the **tool number** is updated — no other tool parameters are changed.
- Changes to the document library take effect immediately in the CAM setup; post-process after running.
- The add-in does not auto-post — that remains a manual step so you can review before outputting NC.
