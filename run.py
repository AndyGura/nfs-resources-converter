import argparse
import os
import pathlib
from enum import Enum


class Action(Enum):
    convert = 'convert'
    gui = 'gui'
    custom_command = 'custom_command'
    show_settings = 'show_settings'

    def __str__(self):
        return self.value


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('action', type=Action, choices=list(Action), default=Action.gui, help='An action to perform')
    parser.add_argument('--custom-command', type=str, required=False, help='Name of custom function to run (action "custom_command" only)')
    parser.add_argument('--custom-command-args', nargs='*', required=False, default=[], help='Arguments for custom command (action "custom_command" only)')
    parser.add_argument('file', type=pathlib.Path, nargs='?', default=None, help='Input path')
    parser.add_argument('--out', type=pathlib.Path, required=False, help='Output path for converted files (action "convert" only)', default='out/')
    args = parser.parse_args()
    if args.action == Action.gui:
        if args.file is not None and os.path.isdir(args.file):
            raise Exception('Cannot open GUI for directory, use path to file')
        from actions.gui_editor import run_gui_editor
        run_gui_editor(str(args.file) if args.file is not None else None)
    elif args.action == Action.convert:
        if args.file is None:
            raise Exception('file argument is required for convert action')
        if not args.out:
            raise Exception('--out argument has to be provided for convert action')
        from actions.convert_all import convert_all
        convert_all(args.file, args.out)
    elif args.action == Action.show_settings:
        from config import get_config_file_location
        print(f"Settings file location: {get_config_file_location()}")
    elif args.action == Action.custom_command:
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
