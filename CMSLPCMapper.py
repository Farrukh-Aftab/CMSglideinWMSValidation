
import os
import time
import shutil
import urllib
import tempfile

import classad
import htcondor

g_expire_time = 0
g_cache = set()


def write_cache_file():
    final_fname = get_cache_filename()
    dirname, prefix = os.path.split(final_fname)
    fd, name = tempfile.mkstemp(dir=dirname, prefix=prefix)
    try:
        for dn in g_cache:
            os.write(fd, dn + "\n")
        os.close(fd)
        os.rename(name, final_fname)
    except Exception, e:
        htcondor.log(htcondor.LogLevel.Always, "Failed to write out cache file: %s" % str(e))
        try:
            os.unlink(name)
        except:
            pass


def cache_users_from_fd(fd):
    global g_cache
    new_cache = set()
    for line in fd.readlines():
        dn = line.strip()
        if not dn or dn.startswith("#"):
            continue
        new_cache.add(dn)
    g_cache = new_cache


def get_cache_filename():
    return htcondor.param.get('CMSLPC_USER_CACHE', os.path.join(htcondor.param['SPOOL'], 'cmslpc_cache.txt'))


def cache_users_from_file():
    cache_file = get_cache_filename()
    try:
        cache_users_from_fd(open(cache_file, "r"))
    except Exception, e:
        htcondor.log(htcondor.LogLevel.Always, "Failed to cache users from file %s: %s" % (cache_file, str(e)))


def cache_users():
    url = htcondor.param.get("CMSLPC_USER_URL")
    if not url:
        cache_users_from_file()
        return
    try:
        urlfd = urllib.urlopen(url)
        cache_users_from_fd(urlfd)
    except Exception, e:
        htcondor.log(htcondor.LogLevel.Always, "Failed to cache users from URL %s: %s" % (url, str(e)))
        cache_users_from_file()
        return
    write_cache_file()


def check_caches():
    global g_expire_time
    if time.time() > g_expire_time:
        cache_users()
        g_expire_time = time.time() + 15*3600

def lpcUserDN(user):
    check_caches()
    if isinstance(user, classad.ExprTree):
        try:
            user = user.eval()
        except:
            return False
    return user in g_cache


classad.register(lpcUserDN)


if __name__ == '__main__':
    htcondor.param['CMSLPC_USER_CACHE'] = 'test_lpccache.txt.temp'
    shutil.copy('test_lpccache.txt', 'test_lpccache.txt.temp')
    htcondor.enable_debug()
    print "true ==", lpcUserDN("/DC=ch/DC=cern/OU=Organic Units/OU=Users/CN=bbockelm/CN=659869/CN=Brian Paul Bockelman")
    print "true ==", classad.ExprTree('lpcUserDN("/DC=ch/DC=cern/OU=Organic Units/OU=Users/CN=bbockelm/CN=659869/CN=Brian Paul Bockelman")').eval()
    print "false ==", lpcUserDN("/DC=ch/DC=cern/OU=Organic Units/OU=Users/CN=bbockelm/CN=659869/CN=Brian Paul Bockelman/false")
    print "false ==", classad.ExprTree('lpcUserDN("/DC=ch/DC=cern/OU=Organic Units/OU=Users/CN=bbockelm/CN=659869/CN=Brian Paul Bockelman/false")').eval()
    ad = classad.ClassAd({'x509userproxysubject': '/DC=ch/DC=cern/OU=Organic Units/OU=Users/CN=bbockelm/CN=659869/CN=Brian Paul Bockelman', 'foo': classad.ExprTree('lpcUserDN(x509userproxysubject)')})
    print "true ==", ad.eval("foo")
    htcondor.param['CMSLPC_USER_URL'] = 'http://hcc-briantest.unl.edu/test_lpccache.txt'
    g_expire_time = 0
    print "true ==", classad.ExprTree('lpcUserDN("/DC=ch/DC=cern/OU=Organic Units/OU=Users/CN=bbockelm/CN=659869/CN=Brian Paul Bockelman/true")').eval()


