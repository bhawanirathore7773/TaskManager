# -*- coding: utf-8 -*-
"""TaskDesk: find out why the app cannot reach the server.

Run it with the Python that came with TaskDesk (double-click Check_Server.bat), or:
    python check_server.py [server address]
It only READS and prints. It changes nothing and sends no password.
"""
import json
import os
import socket
import ssl
import sys
import time
import urllib.error
import urllib.parse
import urllib.request


def find_config():
    cands = []
    for base in (os.environ.get('LOCALAPPDATA', ''), os.environ.get('ProgramFiles', ''), os.environ.get('ProgramFiles(x86)', '')):
        if base:
            cands.append(os.path.join(base, 'Programs', 'TaskDesk', 'app', 'taskdesk_config.json'))
            cands.append(os.path.join(base, 'TaskDesk', 'app', 'taskdesk_config.json'))
    here = os.path.dirname(os.path.abspath(__file__))
    cands += [os.path.join(here, 'taskdesk_config.json'), os.path.join(here, '..', 'client', 'app', 'taskdesk_config.json'), os.path.join(here, '..', 'app', 'taskdesk_config.json')]
    for p in cands:
        if os.path.isfile(p):
            return p
    return ''


def line(ok, text):
    print(('  OK     ' if ok else '  PROBLEM ') + text)


def main():
    print('=' * 64)
    print(' TaskDesk server check')
    print('=' * 64)
    addr = sys.argv[1].strip() if len(sys.argv) > 1 else ''
    if not addr:
        p = find_config()
        if not p:
            print('  PROBLEM  TaskDesk ki config file nahi mili. Address ko aise do:  check_server.py https://aapka-domain.com/taskdesk/api.php')
            return 1
        with open(p, 'rb') as f:
            addr = str(json.loads(f.read().decode('utf-8-sig')).get('cloud_url', '')).strip()
        print(' Config file :', p)
    print(' Server addr :', addr)
    print(' Python      :', sys.version.split()[0], '|', ssl.OPENSSL_VERSION)
    print(' Time on PC  :', time.strftime('%Y-%m-%d %H:%M:%S'), '(galat date/time se HTTPS fail hota hai)')
    px = urllib.request.getproxies()
    print(' Proxy       :', px if px else 'none')
    print()
    if 'YOUR-DOMAIN' in addr or not addr:
        line(False, 'Address abhi bhi "YOUR-DOMAIN" hai ya khali hai. Installer dobara banao, sahi address ke saath.')
        return 1
    u = urllib.parse.urlparse(addr)
    if u.scheme != 'https':
        line(False, 'Address https:// se shuru hona chahiye (abhi: %s)' % (u.scheme or 'kuch nahi'))
    if not u.path.endswith('api.php'):
        line(False, 'Address ke end me /api.php hona chahiye. Jaise https://domain.com/taskdesk/api.php (abhi: %s)' % u.path)
    host = u.hostname or ''
    port = u.port or (443 if u.scheme == 'https' else 80)
    print('1) Domain naam (DNS)')
    try:
        ips = sorted({a[4][0] for a in socket.getaddrinfo(host, port, type=socket.SOCK_STREAM)})
        line(True, '%s -> %s' % (host, ', '.join(ips)))
    except Exception as e:
        line(False, '%s ka address nahi mila (%s). Domain ka spelling check karo, ya is PC ka internet / DNS band hai.' % (host, e))
        return 1
    print('2) Connection (TCP %d)' % port)
    try:
        s = socket.create_connection((host, port), timeout=8)
        s.close()
        line(True, 'server se connect ho gaya')
    except Exception as e:
        line(False, 'connect nahi hua (%s). Office firewall / antivirus python.exe ko rok raha ho sakta hai, ya internet band hai.' % e)
        return 1
    if u.scheme == 'https':
        print('3) HTTPS certificate')
        try:
            ctx = ssl.create_default_context()
            with socket.create_connection((host, port), timeout=8) as raw:
                with ctx.wrap_socket(raw, server_hostname=host) as tls:
                    c = tls.getpeercert()
                    line(True, 'certificate theek hai, expiry: %s' % c.get('notAfter'))
        except ssl.SSLCertVerificationError as e:
            line(False, 'certificate verify nahi hua (%s). PC ki date/time galat ho sakti hai, ya office firewall HTTPS ko beech me rok raha hai.' % (e.verify_message or e))
            return 1
        except Exception as e:
            line(False, 'HTTPS handshake fail (%s)' % e)
            return 1
    print('4) TaskDesk server ka jawab (health)')
    url = addr + ('&' if '?' in addr else '?') + 'r=health'
    for label, ua in (('TaskDesk app jaisa', 'TaskDesk/1.1.0'), ('Python default', None)):
        req = urllib.request.Request(url, headers={'Accept': 'application/json', 'X-TD-Client': '1.1.0'})
        if ua:
            req.add_header('User-Agent', ua)
        try:
            with urllib.request.urlopen(req, timeout=15) as r:
                body, status = r.read(), r.status
        except urllib.error.HTTPError as e:
            body, status = e.read(), e.code
        except Exception as e:
            line(False, '[%s] jawab nahi mila: %s' % (label, e))
            continue
        text = body.decode('utf-8', 'replace').strip()
        try:
            d = json.loads(text)
        except Exception:
            d = None
        if status == 200 and isinstance(d, dict) and d.get('ok'):
            line(True, '[%s] server chal raha hai. Version %s, modules: %s' % (label, d.get('server'), ', '.join(d.get('modules', []))))
        else:
            hint = ''
            if status in (403, 406, 429, 503) and d is None:
                hint = ' -> hosting ka security (firewall / ModSecurity / Cloudflare) request rok raha hai.'
            elif status == 404:
                hint = ' -> api.php is jagah par nahi hai. Address ya upload ka folder check karo.'
            elif d is None:
                hint = ' -> jawab TaskDesk ka nahi hai (HTML ya khali). Address galat hai ya server files theek upload nahi hui.'
            elif isinstance(d, dict) and d.get('error') in ('not_installed', 'not_configured'):
                hint = ' -> server ka setup.php abhi chalana baaki hai.'
            line(False, '[%s] HTTP %s%s' % (label, status, hint))
            print('          jawab ka shuru:', text[:300].replace('\n', ' '))
    print()
    print('Ye poora output (screenshot ya copy) Claude ko bhej do.')
    return 0


if __name__ == '__main__':
    try:
        rc = main()
    except KeyboardInterrupt:
        rc = 1
    sys.exit(rc)
