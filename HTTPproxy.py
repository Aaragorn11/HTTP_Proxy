# CS 4480 - Spring 2024
# Implemented by: Vincentio Dane - u1339382
# PA1

# Place your imports here
import signal
import socket
import sys
import threading
from optparse import OptionParser

# Signal handler for pressing ctrl-c
def ctrl_c_pressed(signal, frame):
    sys.exit(0)

class CacheAndBlocks:
    cache = dict()
    cacheEnabled = False
    blocklist = list()
    blocklistEnabled = False
    
    """
    Checks if a given hostname, port, and path are present in the cache.

    Parameters:
        this (object): The instance of the class.
        hostname (str): The hostname to be checked in the cache.
        port (str): The port to be checked in the cache.
        path (str): The path to be checked in the cache.

    Returns:
        bool: True if the hostname, port, and path are found in the cache. 
              False if the cache is not enabled or the hostname, port, and path are not found in the cache.
    """
    def check_cache(this, hostname: str, port: str, path: str):
        if not this.cacheEnabled:
            return False
        
        k = (hostname, port, path)
        if k in this.cache:
            return this.cache.get(k)
        return False
    
    """
    Stores the hostname, port, path, and resource into the cache.

    Parameters:
        this (object): The instance of the class.
        hostname (str): The hostname to be stored in the cache.
        port (str): The port to be stored in the cache.
        path (str): The path to be stored in the cache.
        data (bytes): The resource data to be stored in the cache.
    """
    def addto_cache(this, hostname: str, port: str, path: str, data: bytes) -> None:
        k = (hostname, port, path)
        this.cache[k] = data
    
    """
    Checks if a given hostname and port combination is present in the blocklist.

    Parameters:
        this (object): The instance of the class.
        hostname (str): The hostname to be checked in the blocklist.
        port (str, optional): The port to be checked in the blocklist. Defaults to an empty string.

    Returns:
        bool: True if the hostname and port combination is found in the blocklist. 
              False if the blocklist is not enabled or the hostname and port combination is not found in the blocklist.
    """
    def check_blocklist(this, hostname: str, port: str = '') -> bool:
        if not this.blocklistEnabled:
            return False
        
        for blocked in this.blocklist:
            if ":" in blocked:
                if f"{hostname}:{port}" in blocked:
                    return True
            else:
                if hostname in blocked:
                    return True
        return False

    """
    Stores a string into the blocklist.

    Parameters:
        this (object): The instance of the class.
        string (str): The string to be added to the blocklist.
    """
    def addto_blocklist(this, string: str) -> None:
        this.blocklist.append(string)
    
    """
    Checks if a given operation is valid based on its starting string.
    
    Parameters:
        path (str): The string format of the operation to be checked.
    
    Returns:
        bool: Returns True if the operation starts with either 'proxy' or '/proxy'. False otherwise.
    
    Note:
        All valid operations are expected to start with either 'proxy' or '/proxy'.
    """
    def check_isOperation(self, path: str) -> bool:
        if path.startswith(("proxy", "/proxy")):
            return True
        else:
            return False
        
    """
    Executes a user command if it's valid
    
    Parameters:
        this (object): The instance of the class where this method is defined.
        path (str): The operation to be processed. It is expected to be a string.
    
    Returns:
        bytes: a byte string indicating the HTTP response status. If the operation is invalid, 
               it returns 'HTTP/1.0 400 Bad Request\r\n\r\n'. 
               If the operation is processed successfully, it returns 'HTTP/1.0 200 OK\r\n\r\n'.
    
    Raises:
        Exception: If the operation is invalid, it raises an exception.
    
    Note:
        Depending on the arguments, it performs various operations such as enabling/disabling the cache, 
        flushing the cache, enabling/disabling the blocklist, adding to the blocklist, and removing from the blocklist.
    """
    def process_operation(this, path: str) -> bytes:
        if not this.check_isOperation(path):
            raise Exception("not a valid operation!")
        
        args = path.split("/")

        if not this.isValid_operation(args):
            return b"HTTP/1.0 400 Bad Request\r\n\r\n"
        
        if args[1] == "cache":
            if args[2] == "enable":
                this.cacheEnabled = True

            elif args[2] == "disable":
                this.cacheEnabled = False

            elif args[2] == "flush":
                this.cache.clear()

            return b"HTTP/1.0 200 OK\r\n\r\n"
        
        elif args[1] == "blocklist":
            if len(args) == 3:
                if args[2] == "enable":
                    this.blocklistEnabled = True

                elif args[2] == "disable":
                    this.blocklistEnabled = False

                elif args[2] == "flush":
                    this.blocklist.clear()

            elif len(args) == 4:
                if args[2] == "add":
                    this.addto_blocklist(args[3])

                elif args[2] == "remove":
                    this.blocklist.remove(args[3])

            return b"HTTP/1.0 200 OK\r\n\r\n"
    
    """
    Checks if the given arguments in an operation are valid.
    
    Parameters:
        this (object): The instance of the class where this method is defined.
        args (list): The arguments of the operation to be checked. It is expected to be a list of strings.
    
    Returns:
        bool: Returns True if the operation is valid. Otherwise, it returns False.
    """
    def isValid_operation(this, args: list) -> bool:
        if (args[1] == "cache"):
            return len(args) == 3 and \
            (args[2] == "enable" or args[2] == "disable" or args[2] == "flush")
        
        elif (args[1] == "blocklist"):
            if (len(args) == 3):
                return args[2] == "enable" or args[2] == "disable" or args[2] == "flush"
            
            elif (len(args) == 4):
                return args[2] == "add" or args[2] == "remove"
            
        else:
            return False

class Proxy: 
    def __init__(this, address: str, port: str):
        this.port = port
        this.address = address
        this.operation = CacheAndBlocks()
    
    def start(this):
        # Sockets set-up to receive requests
        listen_skt = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        listen_skt.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        listen_skt.bind((this.address, this.port))
        listen_skt.listen()
        
        # Start listening for a connection
        while True:
            client_skt, client_addr = listen_skt.accept()
            client_thread = threading.Thread(target=this.accept_client, args=(client_skt,))
            client_thread.start()
        
    """
    Receives the client's request and processes it.
    
    Parameters:
        this (object): The instance of the class where this method is defined.
        client_skt (socket): The client socket from which the request is received.
    
    Note (method in a nutshell):
        The method first receives the request from the client socket. It then parses the request and performs various error checks.
        If the operation is valid, it processes the operation. If the operation is in the blocklisted, it sends a '403 Forbidden' response.
        If there are any header errors, it sends the appropriate error. If the operation is in the cache, it sends the cached response. 
        If the operation is not in the cache, it fetches the IP address of the hostname, sends a GET request to the server, receives the response,
        and sends the response to the client. If the response is '200 OK', it adds the response to the cache. If the response is '304 Not Modified',
        it then checks the cache and sends the cached response. Finally, it closes the request socket and the client socket.
    """
    def accept_client(this, client_skt):
        request = b''
        while not request.endswith(b"\r\n\r\n"):
            request_chunks = client_skt.recv(4096)
            if not request_chunks:
                break
            request += request_chunks
        request = request.decode()
        
        # parse the request
        url, method, version, headers = this.read_tags(request)

        if url is None or method is None or version is None:
            client_skt.sendall(f"HTTP/1.0 400 Bad Request\r\n\r\n".encode())
            client_skt.close()
            return

        # various error checks
        isValidHTTP = this.check_HTTP(url, method, version)
        if isValidHTTP:
            client_skt.sendall(isValidHTTP)
            client_skt.close()
            return
                            
        hostname, path, request_port, error = this.parse_URL(url)

        if hostname is None or path is None or request_port is None or error:
            client_skt.sendall(f"HTTP/1.0 400 Bad Request ({error})\r\n\r\n".encode())
            client_skt.close()
            return
        
        if this.operation.check_isOperation(path):
            client_skt.sendall(this.operation.process_operation(path))
            client_skt.close()
            return
        
        elif this.operation.check_blocklist(hostname, request_port):
            client_skt.sendall(b"HTTP/1.0 403 Forbidden\r\n\r\n")
            client_skt.close()
            return
        
        header_error = this.check_header(headers)
        if header_error:
            client_skt.send(header_error)
            client_skt.close()
            return
        
        # checks the cache
        in_cache = this.operation.check_cache(hostname, request_port, path)
        if in_cache:
            client_skt.sendall(in_cache)
            client_skt.close()
            return
        
        ip_addr = this.fetch_IP(hostname)
        if not ip_addr:
            client_skt.sendall(f"HTTP/1.0 400 Bad Request (Host not found)\r\n\r\n".encode())
            client_skt.close()
            return

        request_skt = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        request_skt.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        request_skt.connect((ip_addr, int(request_port)))
        
        # send the GET request to the server
        request = this.generate_request(path, hostname, headers)
        request_skt.send(request.encode())
        
        try:
            response = b''
            while not response.endswith(b"\r\n\r\n"):
                request_chunks = request_skt.recv(4096)
                if not request_chunks:
                    break
                response += request_chunks
        except Exception:
            client_skt.sendall(b"HTTP/1.0 400 Bad Request\r\n\r\n")
            client_skt.close()
            return

        if b'200 OK' in response:
            lastModified = ''
            for line in response.split(b'\r\n'):
                if b'Last-Modified:' in line:
                    lastModified = line.replace(b'Last-Modified: ', b'')
            with threading.Lock():
                this.operation.addto_cache(hostname, port, path, (lastModified, response))
        elif b'304 Not Modified' in response:
            res = this.operation.check_cache(hostname, port, path)
            if res:
                response = res[1]

        client_skt.sendall(response)
        request_skt.close()
        client_skt.close()
        
    """
    Builds a valid HTTP GET request for the server.
    
    Parameters:
        this (object): The instance of the class where this method is defined.
        path (str): The path of the resource to be requested.
        hostname (str): The hostname of the server.
        headers (str): The headers to be included in the request.
        last_modified (str, optional): The last modified date of the resource. Defaults to None.
    
    Returns:
        str: A string representing the HTTP GET request.
    """
    def generate_request(this, path: str, hostname: str, headers: str, last_modified: str = None) -> str:
        request = f"GET /{path} HTTP/1.0\r\nHost: {hostname}\r\n"
        if "Connection:" in headers:
            headers = headers.replace("keep-alive", "close")
        else:
            headers = "Connection: close\r\n" + headers
        if last_modified:
            headers += f"If-Modified-Since: {last_modified}\r\n"
        request += headers
        request += "\r\n"
        if not request.endswith("\r\n\r\n"):
            request += "\r\n"
        return request
    
    """
    Checks if an HTTP request is properly formatted.
    
    Parameters:
        this (object): The instance of the class where this method is defined.
        url (str): The URL in the HTTP request.
        head (str): The HTTP method in the request.
        HTTPversion (str): The HTTP version in the request.
    
    Returns:
        bytes or bool: Returns a byte string indicating the HTTP response status if the request is not properly formatted.
    """
    def check_HTTP(this, url: str, head: str, HTTPversion: str):
        if not url or not head or not HTTPversion:
            return b"HTTP/1.0 400 Bad Request\r\n\r\nBad request"
        elif head != "GET":
            return b"HTTP/1.0 501 Not Implemented\r\n\r\nMethod not supported"
        elif not url.startswith("http://"):
            return b"HTTP/1.0 400 Bad Request\r\n\r\nBad url"
        elif HTTPversion != "HTTP/1.0":
            return b"HTTP/1.0 400 Bad Request\r\n\r\nBad version"
        else:
            return False

    """
    Fetches the port, network location, and path from a given URL.
    
    Parameters:
        this (object): The instance of the class where this method is defined.
        url (str): The URL to be parsed.
    
    Returns:
        tuple: A tuple containing the hostname, path, port, and a boolean value indicating if there was an error.
    """
    def parse_URL(this, url: str):
        url = url.replace("http://", "", 1)
        if "/" in url:
            hostname, path = url.split("/", 1)
        else:
            return (None, None, None, None)
        port = 80
        if ":" in hostname:
            hostname, port = hostname.split(":")
        return (hostname, path, int(port), False)
    
    """
    Parses a hostname into an IP address.
    
    Parameters:
        this (object): The instance of the class where this method is defined.
        hostname (str): The hostname to be parsed into an IP address.
    
    Returns:
        str or bool: Returns the IP address if the hostname can be parsed into an IP address. If an exception occurs during parsing, it returns False.
    """
    def fetch_IP(this, hostname: str):
        try:
            return socket.gethostbyname(hostname)
        except Exception:
            return False
            
    """
    Checks if an HTTP header is properly formatted.
    
    Parameters:
        this (object): The instance of the class where this method is defined.
        headers (str): The HTTP headers to be checked.
    
    Returns:
        bytes or bool: Returns a byte string indicating the HTTP response status if the header is not properly formatted.
    """
    def check_header(this, headers: str):
        for header_chunks in headers.split("\r\n"):
            if header_chunks.strip():
                if not ":" in header_chunks:
                    return b"HTTP/1.0 400 Bad Request\r\n\r\n"
                elif not header_chunks.split(":")[0].strip():
                    return b"HTTP/1.0 400 Bad Request\r\n\r\n"
                elif not header_chunks.split(":")[1].strip():
                    return b"HTTP/1.0 400 Bad Request\r\n\r\n"
                elif not header_chunks[header_chunks.find(":") - 1].strip():
                    return b"HTTP/1.0 400 Bad Request\r\n\r\n"
                elif not header_chunks[header_chunks.find(":") + 1] == " ":
                    return b"HTTP/1.0 400 Bad Request\r\n\r\n"
        return False
    
    """
    Reads the tags in the client's HTTP request.
    
    Parameters:
        this (object): The instance of the class where this method is defined.
        request (str): The HTTP request to be parsed.
    
    Returns:
        tuple: A tuple containing the URL, method, HTTP version, and headers in the request. If the request does not contain exactly three tags, it returns (None, None, None, None).
    """
    def read_tags(this, request: str):
        lines = request.split("\r\n")
        get_line = lines[0]
        tags = get_line.split(" ")
        if len(tags) != 3:
            return None, None, None, None
        method, url, version = tags
        headers = None
        headers = "\r\n".join(lines[1:])
        return url.strip(), method.strip(), version.strip(), headers.strip()

# Start of program execution
# Parse out the command line server address and port number to listen to
parser = OptionParser()
parser.add_option('-p', type='int', dest='serverPort')
parser.add_option('-a', type='string', dest='serverAddress')
(options, args) = parser.parse_args()
port = options.serverPort
address = options.serverAddress

# Set up signal handling (ctrl-c)
signal.signal(signal.SIGINT, ctrl_c_pressed)

if address is None:
    address = 'localhost'
if port is None:
    port = 2100

proxy = Proxy(address, port)
proxy.start()