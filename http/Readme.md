When there was only urllib and no [requests](http://requests.org) I decided to build my own http-client.

I used it inside [flashget](https://github.com/balrok/Flashget) for basic webcrawling and downloading large files.

While this library worked quite stable in the end (handled serverside timeouts or strange mixed-case http-headers)
the codebase is very bad.. I didn't know enough of tcp and http before I started and some parts could've been better
designed. Also in the end it required quite much maintenance.

Example usage:

```python
    a = http('http://google.de')
    a.request['header'].append('User-Agent: Mozilla/5.0 (X11; U; Linux i686; en-US; rv:1.9) Gecko/2008062417 (Gentoo) Iceweasel/3.0.1')
    a.request['header'].append('Accept: text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8')
    a.request['header'].append('Accept-Language: en-us,en;q=0.5')
    a.request['header'].append('Accept-Charset: utf-8,ISO-8859-1;q=0.7,*;q=0.7')
    a.open()
    print a.get()
    a.head.get('bla')
    a.head.get('bl1')
    a.head.get('bl2')
    a.head.get('bl3')
```
