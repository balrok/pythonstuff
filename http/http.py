# vim: set fileencoding=utf-8 :

import socket, time
ssl = False
try:
    import ssl
except ImportError:
    if not ssl:
        ssl = False
        pass

socket.setdefaulttimeout(15)

from random import choice

import logging
log = logging.getLogger(__name__)

config = False
try:
    import config
    config.keepalive
    config.dns_reset
except:
    if not config:
        class config:
            pass
    else:
        log.warning("Your config lacks keepalive or dns_reset")
    config.keepalive = True
    config.dns_reset = 60 * 60 * 8 # we cache dns->ip and after this time we will refresh our cacheentry

import StringIO, gzip

if 'MSG_WAITALL' in socket.__dict__:
    EASY_RECV = True
else:
    EASY_RECV = False

class http(object):
    conns = {} # this will store all keep-alive connections in form (host, state)
    dns_cache = {} # will translate host to ip ... 'dns_name.org': (ip, timestamp)
    encoding = '' # when the url might have umlauts the encoding will convert it

    def __init__(self, url):
        cleanUrl = url.replace("\r","").replace("\n","").replace("\t","")
        if cleanUrl == '':
            raise Exception("No url provided")
        self.origUrl = cleanUrl
        self.ssl, self.host, self.page, self.port = http.extract_ssl_host_page_port(cleanUrl)
        self.request = {}
        self.request['http_version'] = '1.1'
        self.request['method']       = 'GET'
        self.request['header']       = [] # can be set from outside
        self.post = ''
        self.request['header'].append('Accept-Encoding: gzip')
        self.redirection = ''
        self.cookies = [] # list should later be a dict it's just my lazyness :/
        self.socket = socket
        self.timeout = 45

    @classmethod
    def extract_ssl_host_page_port(cls, url, force = False):
        ''' returns tuple (host, page, port) force will avoid cache '''
        is_ssl = False
        if url.startswith('http://'):                       # we don't need this
            url = url[7:]
        if url.startswith('https://'):                       # we don't need this
            is_ssl = True
            url = url[8:]
        p  = url.find(':')                                  # port
        br = url.find('/')                                  # example.org:123/abc
        if br == -1:                                        # example.org:123?abc=1
            br = url.find('?')
            if br == -1:                                    # example.org:123
                br = len(url)
        if p != -1 and br > p:                              # br > p cause: example.org/bla=http://muh.org
            print url
            port = int(url[p+1:br])
            host = url[:p]
        else:
            port = 80
            if is_ssl:
                port = 443
            host = url[:br]
        page = url[br:]
        if page == '':
            page = '/'
        page = page
        return (is_ssl, host, page, port)

    @classmethod
    def get_ip(cls, host, force = False):
        if not force and host in cls.dns_cache:
            ipList, last_update = cls.dns_cache[host]
            if last_update < time.time() + config.dns_reset:
                return cls.get_ip(host, True)
        else:
            ip, aliasList, ipList = socket.gethostbyname_ex(host)
            #ipList.append(ip)
            cls.dns_cache[host] = (ipList, time.time())
        if len(ipList) > 1:
            return choice(ipList)
        return ipList[0]

    def connect(self, keepalive = False):
        if not keepalive:
            self.removeFromConns()
        if keepalive and self.request['http_version'] == '1.1' and config.keepalive:
            self.keepalive = True
        else:
            self.keepalive = False

        if self.keepalive and self.host in http.conns and http.conns[self.host][1] == 'CONN_OPEN':
            self.c = http.conns[self.host][0] # reuse connection
            http.conns[self.host] = (self.c, 'CONN_IN_USE')
            return

        self.c = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        if self.ssl and ssl:
            self.c = ssl.wrap_socket(self.c, ca_certs="cacert.pem", cert_reqs=ssl.CERT_REQUIRED)
        self.c.settimeout(self.timeout)
        try:
            self.ip = http.get_ip(self.host)
            self.c.connect((self.ip, self.port))
        except socket.timeout, (txt):
            log.error('error in connect to %s:%d timeout: %s' % (self.host, self.port, txt))
            return None
        except socket.error, e:
            # socket.gaierror: (-2, 'Name or service not known')
            log.error('error in connect to %s:%d error:%s' % (self.host, self.port, unicode(e)))
            return None
        http.conns[self.host] = (self.c, 'CONN_IN_USE')

    def open(self, post = '', keepAlive = True):
        if post:
            self.post = post

        header = []
        if self.post:
            self.request['method'] = 'POST'
        header.append('%s %s HTTP/%s' % (self.request['method'], self.page, self.request['http_version']))
        header.append('HOST: %s' % self.host)
        for i in self.request['header']:
            header.append(i)
        if self.post:
            if 'content_type' in self.request:
                header.append('Content-Type: %s' % self.request['content_type'])
            else:
                header.append('Content-Type: application/x-www-form-urlencoded')
            header.append('Content-Length: %d' % len(self.post))
            header.append('\r\n%s' % self.post)
        send = '\r\n'.join(header)
        if self.encoding:
            send = unicode(send).encode(self.encoding)
        if not self.post:
            send += '\r\n\r\n'

        self.connect(keepAlive)
        self.send = send
        if not self.c:
            return False
        try:
            self.c.sendall(send)
        except socket.error, e:
            if keepAlive:
                log.error("couldn't send to keepalive (%s) Retry", e)
                return self.open(post, False) # retry without allowing keepalive
        ret = self.get_head()
        if not ret and keepAlive:
            log.error("Retry without keepalive for '%s'" % self.origUrl)
            return self.open(post, False) # retry without allowing keepalive
        return ret

    def get_head(self):
        ''' just get the answering head - we need at least this, to receive the body (else we won't know if the body is chunked and so on)
        also returns all already gathered pieces of the body '''
        self.buf = None # reset it first (important)
        self.buf = self.recv_with_reconnect_call(self.c.recv, 4096)
        if self.buf is None:
            return False
        x = self.buf.find('\r\n\r\n')
        deadlockStop = 0
        lastData = ""
        buf = ''
        while x == -1:
            deadlockStop+=1
            if deadlockStop == 23:
                log.error("stopping getHead.. Deadlock")
                return False
            data = self.recv()
            if data == '':
                return False
            if data == lastData:
                log.error("stopping getHead.. receiving always the same")
                log.error((self.host, self.page))
                log.error(data)
                return False
            lastData = data
            buf += data
            x = buf.find('\r\n\r\n')
        self.buf += buf
        try:
            self.head = header(self.buf[:x+2]) # keep the \r\n at the end, so we can search easier
        except:
            self.removeFromConns()
            return False
        self.buf = self.buf[x+4:]
        if self.head.get('set-cookie'):
            self.cookies.extend(self.head.get('set-cookie'))
        if self.head.get('connection') and self.head.get('connection') == 'close':
            self.removeFromConns(False)
        if self.head.status == 301 or self.head.status == 302 or self.head.status == 303: # 302 == found, 303 == see other
            if self.redirection == self.head.get('Location'):
                log.error("redirection loop")
            self.redirection = self.head.get('Location')
            if not self.redirection.startswith('http://') and not self.redirection.startswith('https://'):
                self.redirection = 'http://'+self.host+self.redirection
            log.info("redirect "+self.origUrl+" -to-> "+self.redirection)
            self.ssl, self.host, self.page, self.port = http.extract_ssl_host_page_port(self.redirection)
            self.origUrl = self.redirection[:]
            self.request['method']       = 'GET'
            self.post = ''
            self.open()
        return True

    def recv(self, size = 4096, precision = False):
        if not self.c:
            return None
        ''' a blocking recv function - which should also work on windows and solaris
            this is the lowest level of recv, which i can call from this class '''
        data = ''
        if self.buf:
            data = self.buf[:size]
            self.buf = self.buf[size:]
            size -= len(data)
            if size == 0:
                return data
        call = self.recv_blocking
        data += self.recv_with_reconnect_call(call, size)
        if precision:
            self.buf = data[size:]
            return data[:size]
        return data

    def recv_blocking(self, size = 4096):
        data = ''
        if EASY_RECV:
            data += self.c.recv(size, socket.MSG_WAITALL)
        else:
            while size > 0:
                chunk = self.c.recv(size)
                if chunk == '':
                    break
                data += chunk
                size -= len(chunk)
        return data

    def recv_with_reconnect_call(self, call, arg):
        ''' a wrapper around the socketrecv to allow reconnect on closed sockets '''
        try:
            return call(arg)
        except socket.timeout, (txt):
            log.error('error in connect to %s:%d timeout: %s' % (self.host, self.port, txt))
        except socket.error, e:
            log.error("Problem in recv_with_reconnect_call "+str(e))
            self.connect(False) # reconnect
            try:
                return call(arg)
            except socket.error, e:
                log.error("Giving up "+str(e))

        self.removeFromConns()
        return ''

    def get_chunks(self):
        ''' getting chunks - through my recv implementation, i will first recv everything (in self.buf) and then just strip off the chunk-informations '''
        # TODO implement it better - currently it is quite slow
        body = self.buf
        if not body:
            return None
        # first we download the whole file
        while True:
            if body.endswith('\n0\r\n\r\n'):
                break
            try:
                buf = self.c.recv(4096)
            except socket.timeout, (txt):
                log.error('error in connect to %s:%d timeout: %s' % (self.host, self.port, txt))
                return None
            except socket.error, e:
                # socket.gaierror: (-2, 'Name or service not known')
                log.error('error in connect to %s:%d error:%s' % (self.host, self.port, e))
                return None
            body += buf
        body = body[:-5]

        # after that we create a new return string and eliminate all chunk-trash
        x = body.find('\r\n')
        body2 = ''
        while x > 0:
            length = int(body[:x], 16)
            body2 += body[(x + 2):(x + 2 + length)]
            body = body[x + 4 + length:]
            if not body:
                return body2
            x = body.find('\r\n')
        return None

    def finnish(self):
        ''' when a download gets ended, this function will mark the connection as free for future requests '''
        try:
            if self.host in http.conns:
                http.conns[self.host] = (self.c, 'CONN_OPEN')
        except AttributeError:
            pass

    def removeFromConns(self, close = True):
        if self.host in http.conns:
            if close:
                try:
                    http.conns[self.host][0].close()
                except:
                    pass
            del http.conns[self.host]

    def get(self):
        if self.head.get('Transfer-Encoding') == 'chunked':
            body = self.get_chunks()
        else:
            length = self.head.get('Content-Length')
            if not length:
                length = 9999999 # very big - to make sure we download everything
                log.warning('there was no content length in the header')
                log.warning(repr(self.head.plain))
            else:
                length = int(length)
            body = ''
            while length > 0:
                buf = self.recv(length)
                if buf == '':
                    break
                body+=buf
                length -= len(buf)

        if body is None:
            body = ''
        self.finnish() # close connection or free it for future requests

        if self.head.get('Content-Encoding') == 'gzip':
            gzipper = gzip.GzipFile(fileobj = StringIO.StringIO(body))
            try:
                body = gzipper.read()
            except:
                log.error("not gzip try using normal body")
        if body is None:
            body = ''
        return body

    def get_redirection(self):
        if self.redirection:
            return self.redirection
        return ''

    def __del__(self):
        # when we delete this object, we can free the connection for future use
        self.finnish()


class header(object):
    def __init__(self, head):
        self.plain = head
        self.plain_lower = head.lower()
        # HTTP/1.0 200 OK
        # HTTP/1.0 300 Moved Permanently
        if self.plain_lower[:4] != 'http':
            raise Exception("no http header")
        self.version = head[5:8]                            # 1.0
        if not head[9:12]:
            log.error(head)
        self.status  = int(head[9:12])                      # 200
        x = head.find('\r')
        self.status_str  = head[13:x]                       # OK / permanently moved..
        self.cache = {}
        while True:
            y = head.find(':', x + 3) # + 3 is just a guess about the minlength of keywords
            if y == -1:
                break
            keyword = head[x+2:y].lower()
            x = head.find('\r', y)
            value = head[y+2:x]
            if keyword == 'set-cookie':
                if keyword not in self.cache:
                    self.cache[keyword] = []
                self.cache[keyword].append(value)
            else:
                self.cache[keyword] = value

    def get(self, what):
        what = what.lower()
        try:
            return self.cache[what]
        except:
            return None
    def __str__(self):
        return self.plain


# Object adapter to create the same interface as requests library
# class HttpRequests(object):
#     def get(self, link):
#         self.h = http(link)
#         return self
#     def _content(self):
#         self.h.open()
#         return self.h.get()
#     content = property(fget=_content)
# requests = HttpRequests()

if __name__ == '__main__':
    a = http('http://google.de')
    a.request['header'].append('User-Agent: Mozilla/5.0 (X11; U; Linux i686; en-US; rv:1.9) Gecko/2008062417 (Gentoo) Iceweasel/3.0.1')
    a.request['header'].append('Accept: text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8')
    a.request['header'].append('Accept-Language: en-us,en;q=0.5')
    a.request['header'].append('Accept-Charset: utf-8,ISO-8859-1;q=0.7,*;q=0.7')
    a.open()
    a.get()
    #print a.head.plain()
    #print a.get()
    a = http('http://google.de')
    a.request['header'].append('User-Agent: Mozilla/5.0 (X11; U; Linux i686; en-US; rv:1.9) Gecko/2008062417 (Gentoo) Iceweasel/3.0.1')
    a.request['header'].append('Accept: text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8')
    a.request['header'].append('Accept-Language: en-us,en;q=0.5')
    a.request['header'].append('Accept-Charset: utf-8,ISO-8859-1;q=0.7,*;q=0.7')
    a.open()
    a.get()
    a.head.get('bla')
    a.head.get('bl1')
    a.head.get('bl2')
    a.head.get('bl3')
