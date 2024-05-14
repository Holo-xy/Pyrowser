import socket
import ssl
import platform
import gzip
import io
import tkinter
os_name = platform.system()
os_version = platform.release()
machine_type = platform.machine()
WIDTH, HEIGHT = 800, 600
HSTEP, VSTEP = 13, 18
SCROLL_STEP = 100
#TODO handle returning content when it's not enocded
class URL:
    max_redirects = 3

    def __init__(self, url):
        self.view_source = ''
        if url.startswith("view-source"):
            self.view_source, url = url.split(":", 1)
        self.scheme, url = url.split("://", 1)
        assert self.scheme in ["http", "https", "file"]
        if self.scheme == "http":
            self.port = 80
        elif self.scheme == "https":
            self.port = 443
        if "/" not in url:
            url = url + "/"
        self.host, url = url.split("/", 1)
        self.path = "/" + url

        if ":" in self.host:
            self.host, port = self.host.split(":", 1)
            self.port = int(port)

    def request(self):
        if self.scheme == "file":
            return self.file_handler()
        s = socket.socket(
            family=socket.AF_INET,
            type=socket.SOCK_STREAM,
            proto=socket.IPPROTO_TCP,
        )

        if self.scheme == "https":
            ctx = ssl.create_default_context()
            s = ctx.wrap_socket(s, server_hostname=self.host)

        s.connect((self.host, self.port))
        request = "GET {} HTTP/1.0\r\n".format(self.path)
        request += "Host: {}\r\n".format(self.host)
        request += "User-Agent: " + f'Mozilla/5.0 ({os_name} {os_version}; {machine_type})\r\n'
        request += "\r\n"
        s.send(request.encode("utf8"))

        response = b""
        while True:
            data = s.recv(4096)
            if not data:
                break
            response += data
        s.close()
        response = io.BytesIO(response)

        statusline = response.readline().decode("utf8")
        version, status, explanation = statusline.split(" ", 2)
        response_headers = {}
        while True:
            line = response.readline().decode("utf8")
            if line == "\r\n": break
            header, value = line.split(":", 1)
            response_headers[header.casefold()] = value.strip()

        content = response.read()

        # Chunked and compressed data handling
        if response_headers.get("transfer-encoding") and response_headers["transfer-encoding"] == "chunked":
            content = process_chunked(content)
        if response_headers.get("content-encoding") and response_headers["content-encoding"] == "gzip":
            content = gzip.decompress(content)

        # Handle Redirects
        if status.startswith('3'):
            if URL.max_redirects == 0:
                return ''
            URL.max_redirects -= 1
            path = response_headers['location']
            if path.startswith("/"):
                url = self.scheme + "://" + self.host + path
                content = URL(url).request()
            else:
                content = URL(path).request()
            URL.max_redirects = 3

        if self.view_source:
            view_source(content)
            return ''
        return content.decode("utf8")

    def file_handler(self):
        path = self.path[1:]
        file = open(path, 'r')
        return file.read()


def view_source(body):
    text = ""
    i = 0
    while i < len(body):
        c = body[i]
        if c == '&':
            if body[i:i + 4] == '&lt;':
                text += '<'
                i += 3
            elif body[i:i + 4] == '&gt;':
                text += '>'
                i += 3
        else:
            text += c
        i += 1
    return text


def lex(body):
    in_tag = False
    text = ""
    i = 0
    while i < len(body):
        c = body[i]
        if c == "<":
            in_tag = True
        elif c == ">":
            in_tag = False
        elif c == '&':
            if body[i:i + 4] == '&lt;':
                text += '<'
                i += 3
            elif body[i:i + 4] == '&gt;':
                text += '>'
                i += 3
        elif not in_tag:
            text += c
        i += 1
    return text


def process_chunked(chunked_data):
    data = b""
    while chunked_data:
        chunk_size, rest = chunked_data.split(b"\r\n", 1)
        chunk_size = int(chunk_size, 16)
        chunk, chunked_data = rest[:chunk_size], rest[chunk_size + 2:]
        data += chunk
    return data


def layout(text):
    display_list = []
    cursor_x, cursor_y = HSTEP, VSTEP
    for c in text:
        display_list.append((cursor_x, cursor_y, c))
        cursor_x += HSTEP
        if cursor_x >= WIDTH - HSTEP:
            cursor_x = HSTEP
            cursor_y += VSTEP

    return display_list


class Browser:
    def __init__(self):
        self.window = tkinter.Tk()
        self.window.geometry(f'{WIDTH}x{HEIGHT}')

        self.canvas = tkinter.Canvas(self.window, width=WIDTH, height=HEIGHT)
        self.canvas.pack(fill="both", expand=True)

        self.display_list = []
        self.scroll = 0
        self.text = ''

        self.window.bind("<Down>", self.scrolldown)
        self.window.bind("<Up>", self.scrollup)
        self.window.bind("<Configure>", self.resize)

        self.canvas.bind_all("<MouseWheel>", self._on_mousewheel)

    def draw(self):
        self.canvas.delete("all")
        for x, y, c in self.display_list:
            if y > self.scroll + HEIGHT: continue
            if y + VSTEP < self.scroll: continue
            self.canvas.create_text(x, y - self.scroll, text=c)

    def load(self, url):
        body = url.request()
        self.text = lex(body)
        self.display_list = layout(self.text)
        self.draw()

    def scrolldown(self, e):
        if self.display_list[-1][1] <= HEIGHT or self.display_list[-1][1] <= HEIGHT+self.scroll:
            return
        self.scroll += SCROLL_STEP
        self.draw()

    def scrollup(self,e):
        if self.scroll == 0:
            return
        self.scroll -= SCROLL_STEP
        self.draw()

    def _on_mousewheel(self, event):
        if int(event.delta) < 0:
            self.scrolldown(1)
        else:
            self.scrollup(1)

    def resize(self, event):
        global HEIGHT,WIDTH
        HEIGHT = event.height
        WIDTH = event.width
        self.canvas.config(width=WIDTH,height=HEIGHT)
        self.display_list = layout(self.text)
        self.draw()

if __name__ == "__main__":
    import sys
    if len(sys.argv) < 2:
        sys.argv.append('file:///E:/Pyrowser/default.txt')
    Browser().load(URL(sys.argv[1]))
    tkinter.mainloop()
