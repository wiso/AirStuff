import urllib2

def get_html(url):
    return urllib2.urlopen(url).read()
