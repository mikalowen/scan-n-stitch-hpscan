from enum import Enum, auto
from logging import root
from subprocess import DEVNULL, CalledProcessError, check_output, run
from sys import exit
import tkinter
from PIL import Image, ImageTk


class snsMode(Enum):
    PAGE = auto()
    CHAPTER = auto()

class snsFileExt(Enum):
    PNG = auto()
    PDF = auto()

file_ext_str : dict[snsFileExt,str] = {
    snsFileExt.PNG : ".png",
    snsFileExt.PDF : ".pdf"
}

class ScanStitch():

    def sig_exit(self, sig, frame):
        self.write_context()
        exit(0)

    def __init__(self, path_ : str, name_ : str) -> None:
        self._project_name : str = name_
        self._page_map : list[tuple[str, int]] = []
        self._page_num : int = 0
        self._page_num_in_chapter : int = 0
        self._base_path : str = path_ + '/'
        self._mode : snsMode = snsMode.PAGE
        self._chapters : list[str] = ['none']
        self._chapter_num : int = 0
        self._scan_dpi : int = 0
        self._file_ext : snsFileExt = snsFileExt.PNG
        self._uri : str = ""
        self._preview : bool = True
        self._parent_window = None
        self._preview_image = None
        self._image_label = None

        run(['mkdir', '-p', self._base_path + '00_none'])

    def setup_preview_window(self) -> None:
        self._parent_window = tkinter.Tk()
        self._parent_window.title("Preview")
        self._preview_image = tkinter.PhotoImage()
        self._image_label = tkinter.Label(self._parent_window, image=self._preview_image)
        self._image_label.pack()

        self._parent_window.protocol("WM_DELETE_WINDOW", self._delete_window)

    def _delete_window(self) -> None:
        self._parent_window.destroy()
        self._parent_window = None

    def set_mode(self, mode : snsMode) -> None:
        self._mode = mode

    def set_dpi(self, dpi : int) -> None:
        self._scan_dpi = dpi

    def set_pdf(self) -> None:
        self._file_ext = snsFileExt.PDF

    def set_png(self) -> None:
        self._file_ext = snsFileExt.PNG

    def set_uri(self, uri : str) -> None:
        self._uri = uri

    def set_preview(self, p : bool) -> None:
        self._preview = p

    def begin(self) -> None:
        while(True):
            command = input(" > ")
            command = command.split(' ')

            if command[0] == "" or command[0] == "scan":
                _ = self.scan(rescan=False)
                continue
            if command[0] == "rescan":
                self._page_num -= 1
                if not self.scan(rescan=True):
                    self._page_num += 1
                continue
            if command[0] == "write":
                self.write_context()
                continue
            if command[0] == "chapter":
                if len(command) != 2:
                    print("please provied chapter title without spaces")
                    continue
                if self._mode == snsMode.PAGE:
                    print("chapters are disabled in page mode.")
                    continue
                if not self.new_chapter(command[1]):
                    print("failed to create new chapter.")
                continue
            if command[0] == "exit":
                self.write_context()
                raise SystemExit

    def new_chapter(self, chapter : str) -> bool:
        if chapter in self._chapters:
            return False
        try:
            check_output(['mkdir', self._base_path + "{:02}_{}".format(self._chapter_num+1, chapter)])
            self._chapters.append(chapter)
            self._chapter_num += 1
            self._page_num_in_chapter = 0
            return True
        except CalledProcessError:
            return False

    def test(self) -> None:
        input("test scan?")
        print(self.get_next_filename())
        if not self.scan(False):
            print("scan failed.")
            return
        self._page_map.append(("test{}".format(self._page_num),0))
        self._page_num += 1

    def scan(self, rescan : bool) -> bool:
        try:
            scan_name : str = self._base_path + "{:02}_{}/".format(self._chapter_num, self._chapters[self._chapter_num]) + self.get_next_filename()
            print("scaning ...")
            check_output(['hp-scan', '-r', '300','-d', self._uri, '-o', scan_name])
            print("done: ", scan_name)

            if self._preview:
                if (self._parent_window == None):
                    self.setup_preview_window()
                image = Image.open(scan_name)
                rs_image = image.resize(size=(400,560))
                self._preview_image = ImageTk.PhotoImage(rs_image)
                self._image_label.config(image=self._preview_image)
                self._parent_window.update()

            if not rescan:
                self._page_map.append((self.get_next_filename(), self._chapter_num))
                self._page_num += 1
                self._page_num_in_chapter += 1
            return True
        except CalledProcessError:
            return False


    def get_next_filename(self) -> str:
        return f"{self._page_num:03}__{self._chapter_num:02}_{self._page_num_in_chapter:03}_{self._project_name}{file_ext_str[self._file_ext]}"

    def open_context(self) -> None:
        pass

    def read_context(self) -> bool:
        with open(self._base_path + 'context.sns', "r") as context_file:
            context_file.seek(0,2)
            if (context_file.tell() == 0):
                return False
            context_file.seek(0,0)

            mode_selected : bool = False
            cur_page : int = 0

            for line in context_file.readlines():
                line = line.strip()
                if line == "":
                    continue
                tokens = line.split(' ')

                if (tokens[0] == "mode"):
                    if (mode_selected):
                        raise SystemError("context error: mode defined twice")
                    mode_selected = True
                    if (tokens[1] == snsMode.PAGE.name):
                        self._mode = snsMode.PAGE
                    else:
                        self._mode = snsMode.CHAPTER
                    print("set mode: {}".format(self._mode))
                    continue

                if (tokens[0] == "chapters"):
                    tokens = tokens[1].split(',')
                    if (self._chapters != ['none']):
                        raise SystemError("context error: chapters defined twice")
                    self._chapters = tokens
                    self._chapter_num = len(self._chapters) - 1
                    print("loaded chapters: {}".format(self._chapters))
                    continue

                if (int(tokens[0]) != self._page_num):
                    raise SyntaxError("context error: missing page({},{})".format(cur_page,tokens[0]))

                self._page_num = int(tokens[0]) + 1
                self._page_map.append((tokens[2], int(tokens[1])))

            out = str(check_output(['ls', self._base_path + "{:02}_{}".format(self._chapter_num, self._chapters[-1])], text=True))
            out = out.strip()
            out = out.split('\n')
            self._page_num_in_chapter = int(len(out))

        return False

    def write_context(self) -> None:
        print("write context: {}".format(self._base_path + 'context.sns'))
        with open(self._base_path + 'context.sns', 'w') as context_file:
            # HEADER
            context_file.write("mode {}\n".format(self._mode.name))
            if self._mode == snsMode.CHAPTER:
                context_file.write("chapters ")
                for i,c in enumerate(self._chapters):
                    context_file.write("{}".format(c))
                    if i != self._chapter_num:
                        context_file.write(",")
                context_file.write("\n")
            # FILES
            for i,p in enumerate(self._page_map):
                context_file.write("{PAGE_NUM} {CHAP_NUM} {NAME}\n".format(PAGE_NUM=i, CHAP_NUM=p[1], NAME=p[0]))

