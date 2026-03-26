from argparse import ArgumentParser, Namespace
from os.path import exists
from subprocess import DEVNULL, CalledProcessError, check_output, run
from pathlib import Path
from scanstitch import ScanStitch, snsMode
import signal

folder_path : str = ""
project : str = ""
mode : str = ""
veborse : bool = False
gui : bool = False
preview : bool = False
device_id : str = ""

def check_deps() -> None:
    try:
        _ = check_output(['which','hp-scan'], text=True)
    except CalledProcessError:
        raise SystemExit("missing deps, please install hplip")

def find_usb_scanner() -> str:
    global device_id
    out = check_output(['lsusb'], text=True)
    usb_id_str : str = ""
    for line in str(out).split('\n'):
        if "HP" not in line:
            continue
        tokens = line.split(' ')
        id : tuple[str,str] = (tokens[1], tokens[3])
        usb_id_str = "{}:{}".format(id[0], id[1])

    out = check_output(['hp-makeuri',usb_id_str], text=True, stderr=DEVNULL)
    for line in str(out).split('\n'):
        if "SANE URI:" not in line:
            continue
        out = line[line.find("hp"):]
        break
    device_id = out
    print("Found USB Scanner: {}".format(device_id))
    return str(out)

def init():
    global folder_path
    global mode
    global verbose
    global gui
    global preview
    global project

    parser : ArgumentParser = ArgumentParser()
    parser.add_argument('scan_dir')
    parser.add_argument('--gui', action='store_true')
    parser.add_argument('-p', '--preview', action='store_true')
    parser.add_argument('-v', '--verbose', action='store_true')
    parser.add_argument('--mode', choices=['PAGE','CHAPTER'], default='PAGE')
    parser.add_argument('-u','--uri', type=str, default='')
    parser.add_argument('-a', '--auto_usb', action='store_true', default=False)
    args : Namespace = parser.parse_args()
    if (args.verbose):
        print(args)

    mode = args.mode
    veborse = args.verbose
    gui = args.gui
    preview = args.preview
    device_id = args.uri
    project = args.scan_dir

    if (device_id == ''):
        if (args.auto_usb):
            find_usb_scanner()
        else:
            raise SystemExit('No hp device URI specified, auto detect off')

    folder_path = str(Path(args.scan_dir).resolve())
    print(folder_path)
    if (not exists(folder_path)):
        while (True):
            key = input("Output directory ({}) does not exist! Create now? [y]/n ? ".format(folder_path)) + 'y'
            if (key[0] == 'y' or key[0] == 'Y'):
                run(['mkdir', '-v' ,'{}'.format(folder_path)])
                break
            elif (key[0] == 'n' or key [0] == 'N'):
                print("No output path, exiting.")
                raise SystemExit
            else:
                print("Invalid input.")
    else:
        print("Found output directory ({})".format(folder_path))

    context_file = folder_path + '/context.sns'

    if not exists(context_file):
        print("Creating new context ({})".format(context_file))
        run(['touch', f'{context_file}'])
    #else:
    #    print("Reading context from file ({})".format(context_file))

def main():
    global mode

    prog : ScanStitch = ScanStitch(folder_path, project)
    prog.set_uri(device_id)
    prog.set_preview(preview)
    if (mode == 'CHAPTER'):
        prog.set_mode(snsMode.CHAPTER)

    prog.read_context()

    signal.signal(signal.SIGINT, prog.sig_exit)

    prog.begin()
if __name__ == "__main__":
    check_deps()
    init()
    main()
