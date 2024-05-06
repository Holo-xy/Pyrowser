import socket
import ssl
import platform
os_name = platform.system()
os_version = platform.release()
machine_type = platform.machine()

class URL:
    def __init__(self, url):
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

    def request(self,):
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
        request += "Connection: close\r\n"
        request += "User-Agent: " + f'Mozilla/5.0 ({os_name} {os_version}; {machine_type})\r\n'
        request += "\r\n"
        s.send(request.encode("utf8"))
        response = s.makefile("r", encoding="utf8", newline="\r\n")
        statusline = response.readline()
        version, status, explanation = statusline.split(" ", 2)
        response_headers = {}
        while True:
            line = response.readline()
            if line == "\r\n": break
            header, value = line.split(":", 1)
            response_headers[header.casefold()] = value.strip()
        assert "transfer-encoding" not in response_headers
        assert "content-encoding" not in response_headers
        content = response.read()
        s.close()
        return content

    def file_handler(self):
        path = self.path[1:]
        file = open(path,'r')
        return file.read()

def show(body):
    in_tag = False
    i = 0
    while i < len(body):
        c = body[i]
        if c == "<":
            in_tag = True
        elif c == ">":
            in_tag = False
        elif i+3 < len(body) and c == '&':
            if body[i:i + 4] == '&lt;':
                print('<',end="")
                i += 3
            elif body[i:i + 4] == '&gt;':
                print('>',end="")
                i += 3
        elif not in_tag:
            print(c,end="")
        i += 1

def load(url):
    body = url.request()
    show(body)


if __name__ == "__main__":
    import sys
    if len (sys.argv) < 2:
        sys.argv.append('file:///E:/Pyrowser/default.txt')
    load(URL(sys.argv[1]))