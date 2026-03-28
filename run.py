import argparse
import os
import pathlib
import sys
from enum import Enum


class Action(Enum):
    convert = 'convert'
    custom_command = 'custom_command'
    show_settings = 'show_settings'
    uncompress = 'uncompress'

    def __str__(self):
        return self.value


if __name__ == "__main__":
    # On macOS, files opened via Finder are delivered through Apple Events (odoc),
    # not as command-line arguments. We intercept the event here before the GUI starts.
    _macos_open_file = None
    if sys.platform == 'darwin':
        try:
            from AppKit import NSApplication, NSObject

            class _AppDelegate(NSObject):
                def application_openFile_(self, app, filename):
                    global _macos_open_file
                    _macos_open_file = filename
                    return True

            _app = NSApplication.sharedApplication()
            _delegate = _AppDelegate.alloc().init()
            _app.setDelegate_(_delegate)
            # Process pending events (including the odoc Apple Event) without blocking
            import time
            _deadline = time.time() + 0.5
            while time.time() < _deadline:
                _event = _app.nextEventMatchingMask_untilDate_inMode_dequeue_(
                    0xFFFFFFFF, None, 'kCFRunLoopDefaultMode', True
                )
                if _event:
                    _app.sendEvent_(_event)
                if _macos_open_file:
                    break
        except Exception:
            pass

    # check if first argument is a valid action. If not, it is a file
    action = None
    if len(sys.argv) > 1:
        try:
            action = Action(sys.argv[1])
            sys.argv.pop(1)
        except ValueError:
            pass
    parser = argparse.ArgumentParser()
    parser.add_argument('file', type=pathlib.Path, nargs='?', default=None, help='Input path')
    parser.add_argument('--custom-command', type=str, required=False, help='Name of custom function to run (action "custom_command" only)')
    parser.add_argument('--custom-command-args', nargs='*', required=False, default=[], help='Arguments for custom command (action "custom_command" only)')
    parser.add_argument('--out', type=pathlib.Path, required=False, help='Output path for converted files (action "convert" only)', default='out/')
    args = parser.parse_args()
    if action is None:
        if args.file is not None and os.path.isdir(args.file):
            raise Exception('Cannot open GUI for directory, use path to file')
        from actions.gui_editor import run_gui_editor
        file_to_open = str(args.file) if args.file is not None else _macos_open_file
        run_gui_editor(file_to_open)
    elif action == Action.convert:
        if args.file is None:
            raise Exception('file argument is required for convert action')
        if not args.out:
            raise Exception('--out argument has to be provided for convert action')
        from actions.convert_all import convert_all
        convert_all(args.file, args.out)
    elif action == Action.show_settings:
        from config import get_config_file_location
        print(f"Settings file location: {get_config_file_location()}")
    elif action == Action.uncompress:
        if args.file is None:
            raise Exception('file argument is required for uncompress action')
        if os.path.isdir(args.file):
            raise Exception('Cannot uncompress directory, use path to file')
        from actions.uncompress import uncompress_file
        uncompress_file(str(args.file))
    elif action == Action.custom_command:
        if args.file is None:
            raise Exception('file argument is required for custom_command action')
        if os.path.isdir(args.file):
            raise Exception('Cannot run custom command on directory, use path to file')
        if not args.custom_command:
            raise Exception('--custom-command argument has to be provided for custom command action')
        if not args.out:
            raise Exception('--out argument has to be provided for custom command action')
        from library import require_file
        (name, block, resource) = require_file(str(args.file))
        action_func = getattr(block, f'action_{args.custom_command}')
        action_func(resource, *args.custom_command_args)
        out_path = str(args.out)
        if os.path.isdir(args.out) or out_path[-4:] != str(args.file)[-4:]:
            os.makedirs(out_path, exist_ok=True)
            out_path += '/' + str(args.file).split('/')[-1]
        f = open(out_path, 'wb')
        try:
            f.write(block.pack(resource))
            print('Finished!')
            print(f'Support me :) >>>  https://www.buymeacoffee.com/andygura <<<')
        finally:
            f.close()
