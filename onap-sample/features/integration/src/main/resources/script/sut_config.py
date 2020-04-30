import requests
import re
import paramiko
from time import sleep
from time import ctime
from urllib import parse
import traceback

class SUT_config():
    def __init__(self, ip, username='root', password='password', timeout=30):
        self.ip = ip # IP address of OpenWrt, used for both SSH and Web login
        self.username = username # same for SSH and Web 
        self.password = password # same for SSH and Web 
        self.timeout = timeout # timeout for SSH connect
        self.t = ''
        self.chan = ''
        self.try_times = 3
        self.root_url = 'http://{}/'.format(ip)

    # using webUI to configure password for root user so that SSH will be availible to login
    def set_passwd_webui(self):
        # the url used for access WebUI and login 
        access_path = '/cgi-bin/luci/'
        access_url = parse.urljoin(self.root_url,access_path)

        print(' -------------------Send POST request to login WebUI-------------------')
        login_header = {
                        'content-type': 'application/x-www-form-urlencoded', 
                        'Upgrade-Insecure-Requests': '1',
                        'Referer':access_url,
                        'Accept-Encoding':'gzip, deflate'
                        }
        login_data = {'luci_username': self.username, 'luci_password': self.password}
        r = requests.post(access_url, data=login_data, headers=login_header, allow_redirects=False)
        cookie = r.headers['Set-Cookie'].split(';')[0].strip()

        print(' -------------------Send GET request to access WebUI after login-------------------')
        get_header = {
                      'Upgrade-Insecure-Requests': '1', 
                      'Accept-Encoding':'gzip, deflate',
                      'Referer':access_url,
                      'Cookie':cookie
                      }
        r1=requests.get(access_url, headers=get_header)
        assert r1.status_code == 200

        print(' -------------------Send GET request to admin url to obtain the token-------------------')
        admin_path = 'admin/system/admin'
        admin_url = parse.urljoin(access_url,admin_path)
        r2=requests.get(admin_url, headers=get_header)
        assert r2.status_code == 200
        x=re.search(r'name="token"\svalue="\w+',r2.text).group()
        token = x.split('"')[-1]

        print(' -------------------Send POST request to admin url to set the password-------------------')  
        post_header = {
                       'Upgrade-Insecure-Requests': '1', 
                       'Accept-Encoding':'gzip, deflate',
                       'Origin': self.root_url,
                       'Referer': admin_url,
                       'Cookie': cookie
                       }
        post_data = {
             "token": (None,token),
             "cbi.submit": (None,'1'),
             "password.cbid.system._pass.pw1": (None,''),
             "cbid.system._pass.pw1": (None,'password'),
             "password.cbid.system._pass.pw2": (None,''),
             "cbid.system._pass.pw2": (None,'password'),
             "cbid.dropbear.cfg014dd4.Interface": (None,''),
             "cbid.dropbear.cfg014dd4.Port": (None,'22'),
             "cbi.cbe.dropbear.cfg014dd4.PasswordAuth": (None,'1'),
             "cbid.dropbear.cfg014dd4.PasswordAuth": (None,'on'),
             "cbi.cbe.dropbear.cfg014dd4.RootPasswordAuth": (None,'1'),
             "cbid.dropbear.cfg014dd4.RootPasswordAuth": (None,'on'),
             "cbi.cbe.dropbear.cfg014dd4.GatewayPorts": (None,'1'),
             "cbid.dropbear._keys._data": (None,''),
             "cbi.apply": (None,'1')
             }
        r3 = requests.post(admin_url, files=post_data, headers=post_header) 
        assert r3.status_code == 200

    # connect to the SUT via SSH
    def connect(self):
        while True:
            try:
                self.t = paramiko.Transport(sock=(self.ip, 22))
                self.t.connect(username=self.username, password=self.password)
                self.chan = self.t.open_session()
                self.chan.settimeout(self.timeout)
                self.chan.get_pty()
                self.chan.invoke_shell()
                print(u'{} connected.'.format(self.ip))
                return
            except Exception as e1:
                if self.try_times != 0:
                    print(u'Connect {} failed，retry'.format(self.ip))
                    self.try_times -= 1
                else:
                    print(u'Retried 3 times all faied，end this')
                    exit(1)

    # close the SSH connection
    def close(self):
        if self.chan:
           self.chan.send('exit')
           self.chan.close()
        if self.t:
           self.t.close()
        print('SSH connection closed')

    # define this function to send command
    def send(self,cmd):
        print('---------------------executing {}------------------------'.format(cmd))
        cmd += '\r'
        p = re.compile(r'root@OpenWrt:~#')
        self.chan.send(cmd)
        sleep(0.5)
        ret = self.chan.recv(65535)
        ret = ret.decode('utf-8')
        print(ret)
        assert p.search(ret)
        return ret

    def get_if_name(self, ipaddr):
        ifname = ''
        if_name = ''
        ret1 = self.send('ifconfig')  # execute ifconfig
        pat1 = 'inet\saddr:{}'.format(ipaddr)  # use this to match and find the specified ip address in output
        ret1_lines = ret1.split('\n')
        if ret1_lines:
            for lineseq in range(len(ret1_lines)):
                #print(lll(lineseq))
                m1 = re.search(pat1, ret1_lines[lineseq]) # find the line in output which contains specified ip
                if m1:
                    #print(m.group())
                    ifname_line = ret1_lines[lineseq-1] # get the previous line to obtain the linux interface name : ifname
                    ifname = ifname_line.split(' ')[0]
        assert ifname

        ret2 = self.send('uci show network')        
        pat2 = "network\.\S+\.ifname='{}'".format(ifname) # use the ifname to find its corresponding interface name in OpenWrt , like: 'lan' 
        ret2_lines = ret2.split('\n')
        if ret2_lines:
            for line in ret2_lines:
                m2 = re.search(pat2, line)
                if m2:
                    if_name = m2.group().split('.')[1]
                    break
        assert if_name
        return if_name         
                    
    def create_zone(self, name, ifname):
        self.send('uci add firewall zone')
        self.send('uci set firewall.@zone[-1]=zone')
        self.send("uci set firewall.@zone[-1].name='{}'".format(name))
        self.send("uci set firewall.@zone[-1].input='ACCEPT'")
        self.send("uci set firewall.@zone[-1].output='ACCEPT'")
        self.send("uci set firewall.@zone[-1].forward='ACCEPT'")
        self.send("uci set firewall.@zone[-1].network='{}'".format(ifname))
        self.send("uci set firewall.@zone[-1].masq='1'")
        self.send("uci set firewall.@zone[-1].mtu_fix='1'")
        self.send("uci commit firewall")
        self.send("reload_config")
        result = self.send('uci get firewall.@zone[-1].name')
        assert name in result

    def create_rule(self, name, src, dst, proto, action, port=0):
        if proto == 'all':
            self.send('uci add firewall zone')
            self.send("uci set firewall.@rule[-1]=rule")
            self.send("uci set firewall.@rule[-1].name='{}'".format(name))            
            self.send("uci set firewall.@rule[-1].target='{}'".format(action))
            self.send("uci set firewall.@rule[-1].src='{}'".format(src))
            self.send("uci set firewall.@rule[10].dest='{}'".format(dst))
            self.send("uci set firewall.@rule[10].proto='all'")
            self.send("uci set firewall.@rule[9].family='ipv4'")
            self.send("uci commit firewall")
            self.send("reload_config")

        elif proto == 'tcp' or 'udp':
            self.send('uci add firewall rule')
            self.send("uci set firewall.@rule[-1]=rule")
            self.send("uci set firewall.@rule[-1].name='{}'".format(name))            
            self.send("uci set firewall.@rule[-1].target='{}'".format(action))
            self.send("uci set firewall.@rule[-1].src='{}'".format(src))
            self.send("uci set firewall.@rule[10].dest='{}'".format(dst))
            self.send("uci set firewall.@rule[10].proto='{}'".format(proto))
            self.send("uci set firewall.@rule[9].dest_port='{}'".format(port))
            self.send("uci set firewall.@rule[9].family='ipv4'")
            self.send("uci commit firewall")
            self.send("reload_config")
        else:
            pass
        result = self.send('uci get firewall.@rule[-1].name')
        assert name in result

if __name__ == '__main__':
    try:
        sut1 = SUT_config('192.168.235.84')
        #sut1.set_passwd_webui()
        sut1.connect()
        trust_if = sut1.get_if_name('192.168.123.9')
        sut1.create_zone('Trust',trust_if)
        ext_if = sut1.get_if_name('192.168.124.6')
        sut1.create_zone('External',ext_if) 
        sut1.create_rule('rule1', 'Trust', 'External', 'all', 'ACCEPT')
    except Exception as e:
        print(e)
        traceback.print_exc()
    finally:
        sut1.close()
