#!/usr/bin/python
# -*-coding:utf-8 -*

DOCUMENTATION = '''
---
version_added: "1.2"
module: proxmox
short_description: proxmox
description:
- This module create, delete, migrate and recover containers on proxmox
options:
     state:
       description:
         choices=present|absent|migrate|recover
  #### create ####
    Create a new container from a ostemplate 
      idct:
        description:
          ID of the container to install.
      path:
        description:
          Path of the container's image.
          /To create a container from a backup, look restore's part/
      password:
        description:
          root's password of the containeur
      hostname:
        description:
          hostname of the container
      interface:
        description:
          set interfaces in your container 
         ° °°°°format°°°°°
         ° >>>>  name,vlan,MAC address
         °   put a blank or type "default" in VLAN and MAC Address if u don't need 
         °   /!!! follow the format carefully otherwise it will doesn't work!!! see examples below.
         °°°°°°°°°°°°°°°°°
      onboot:
        description:
          power the container when the proxmox server start

      cpu:
        description:
          allow N cpu to the container (1-N)
   
      cpuunits:
        description:
          this number put the priority of the containers compared to others containers for the cpu (0 - 500000)
     
     memory:
      description:
         allow N ram to the container

     swap:
      description:
         allow N swap to the container
      
      force:
        description:
          force the installation even if there is already a container (erase the old one)

  #### delete ####
    Delete a existant container
      idct:
        description:
          ID of the container to delete.

  #### migrate ####
    Move a container from a proxmox server to a another
      idct:
        description:
          ID of the container to migrate.(it's will work only with the container in the local computer, not the cluster, else you need to make a new migrate with every proxmox's address you want)
      target:
         description:
           set the target of the migration
  #### recover ####
   Create a new container from a backup file (look proxmox_dump to make backup file) 
      idct:
        description:
          ID of the new container
      path:
        description:
          path to the backup file

notes:
requirements: []
author: Guillaume Dubroeucq
'''
 
EXAMPLES = '''
- name: Install containers
  proxmox: state=present idct=102 password=toto hostname=monserveur interface=eth0,1,00:C2:FF:21:B2:3C,eth1,,

- state=absent 
  idct=130

- state=migrate
  idct=225
  target=serveur2

- state=recover
  idct=450
  path=/var/lib/vz/dump/vzdump-openvz-100-2015_06_03-15_01_03.tar.lzo
'''

import subprocess
import re 
import json
import os

def interf(network):

    n=0       
    lanold=""  # sauvegarde l'ancienne netif
    drapeau=0  # + de 2 interfaces
    taille=len(network)
    while n <= taille-1:
        if network[n] != "" and network[n] != None:
            if taille > n+1 and network[n+1] != "" and network[n+1] != "default" and re.search("^[0-9]+$",network[n+1]) != None:
                if taille > n+2 and network[n+2] != "" and network[n+2] != "default":
                    reponse=re.search("([0-9a-fA-F]{2}\:){5}[0-9a-fA-F]{2}",network[n+2]) 
                    if reponse != None: 
                        lan="ifname=%s,bridge=vmbr0v%s,mac=%s" % (network[n],network[n+1],network[n+2])
                        n=n+3
                    else:
                        lan="ifname=%s,bridge=vmbr0v%s" % (network[n],network[n+1])
                        n=n+3
                else:
                    lan="ifname=%s,bridge=vmbr0v%s" % (network[n],network[n+1])
                    n=n+3
            else:
                if taille > n+2 and network[n+2] != "" and network[n+2] != "default":
                    reponse=re.search("([0-9a-fA-F]{2}\:){5}[0-9a-fA-F]{2}",network[n+2])     
                    if reponse != None:
                        lan="ifname=%s,bridge=vmbr0,mac=%s" % (network[n],network[n+2])
                        n=n+3
                    else:
                        lan="ifname=%s,bridge=vmbr0" % (network[n])
                        n=n+3
                else:
                    lan="ifname=%s,bridge=vmbr0" % (network[n])
                    n=n+3
        if taille > 3 and drapeau == 1:
            lan="%s;%s" % (lanold,lan)
        lanold=lan
        drapeau=1
    if taille == 0:
        lan="ifname=eth0,bridge=vmbr0"
    return(lan)
# changer le bridge en fonction du serveur

def compare(num,chemin,mdp,hostname,cpu,cpuunits,space,ram,swap,boot,lan,module):
    pattern="pvectl config %s" % num
    proc=subprocess.Popen(pattern,
                          shell=True,
                          stdout=subprocess.PIPE,
                          )
    rep=proc.communicate()[0]
    infoct={}
    if re.search("ostemplate:",rep) == None:
        os.remove('/etc/pve/openvz/%s.conf'%num)
        return(2)
    for i in rep.split("\n")[0:14]:
        key=i.split(' ')[0][0:-1]
        value=i.split(' ')[1]
        infoct[key]=value

    chemin=chemin.split('/')[6] 
    if infoct['ostemplate'] != chemin:
        return(1) 
    if infoct['hostname'] != hostname:
        fullhostname="%s.perso" % hostname
        if infoct['hostname'] != fullhostname:
            return(1)  
    if infoct['cpus'] != str(cpu):
        return(1) 
    if infoct['cpuunits'] != str(cpuunits):
        return(1)
    if infoct['disk'] != str(space):
        return(1)
    if infoct['memory'] != str(ram):
        return(1)
    if infoct['swap'] != str(swap):
        return(1)
    if infoct['onboot'] != boot:
        return(1)
    #partie pas encore fonctionnelle
#    pattern="pvectl config %s | grep ifname | cut -d \"=\" -f 2" % (num)
#    proc = subprocess.Popen(pattern,
#                            shell=True,
#                            stdout=subprocess.PIPE,
#                            )
#    rep=proc.communicate()[0]
#    rep=rep.strip()
#    if rep != lan:
#        flag=1
    return(0)
def create_container(module,numero,network):
    chemin=module.params['path']
    mdp=module.params['password']
    host=module.params['hostname']
    cpu=module.params['cpu']
    cpuunits=module.params['cpuunits']
    space=module.params['disk']
    ram=module.params['memory']
    swap=module.params['swap']
    boot=module.params['onboot']
    force=module.params['force']
    lan=interf(network)  #manage interfaces 
    for num in numero:
     #faire un popen pour catch la reponse et s'adapter au cas
        pattern="pvectl create %s %s -password %s -hostname %s -netif %s -cpus %s -cpuunits %s -disk %s -memory %s -swap %s -onboot %s" % (num,chemin,mdp,host,lan,cpu,cpuunits,space,ram,swap,boot)
        proc = subprocess.Popen(pattern,
                                shell=True,
                                stdout=subprocess.PIPE,
                                stderr=subprocess.PIPE
                                )
        stdoutdata,stderrdata=proc.communicate()
        if re.search("Container private area was created",stdoutdata):
            ok=1
        elif re.search("CT %s already exists" % num, stderrdata) and force == "no":
        #if there is a container with the same ID, compare attribute
            diff=compare(num,chemin,mdp,host,cpu,cpuunits,space,ram,swap,boot,lan,module)
            if diff == 1:
                #case when the existant container is different
                subprocess.call(["pvectl","destroy",str(num)])
                rep=subprocess.call(["pvectl","create",str(num),str(chemin),"-password",str(mdp),"-hostname",str(host),"-netif",str(lan),"-cpus",str(cpu),"-cpuunits",str(cpuunits),"-disk",str(space),"-memory",str(ram),"-swap",str(swap),"-onboot",str(boot)])

            elif diff == 2:
                #case when proxmox create fake container
                rep=subprocess.call(["pvectl","create",str(num),str(chemin),"-password",str(mdp),"-hostname",str(host),"-netif",str(lan),"-cpus",str(cpu),"-cpuunits",str(cpuunits),"-disk",str(space),"-memory",str(ram),"-swap",str(swap),"-onboot",str(boot)])
                if rep == 255: 
                    erreur="Can't install CT %s --> Not enough space in the disk" % num
                    module.fail_json(msg=erreur)

        elif re.search("CT %s already exists" % num,stderrdata) and force == "yes":
            subprocess.call(["pvectl","destroy",str(num)])
            rep=subprocess.call(["pvectl","create",str(num),str(chemin),"-password",str(mdp),"-hostname",str(host),"-netif",str(lan),"-cpus",str(cpu),"-cpuunits",str(cpuunits),"-disk",str(space),"-memory",str(ram),"-swap",str(swap),"-onboot",str(boot)])
            if rep == 255:
                module.fail_json(msg="Can't install CT %s --> Not enough space in the disk" % num)
        elif re.search("Insufficient disk space",stdoutdata) and re.search("exit code 46",stderrdata):
            erreur="Can't install CT %s --> Not enough space in the disk" % num
            module.fail_json(msg=erreur)
        elif re.search("'/etc/pve/nodes/serveur1/openvz/%s.conf' failed: File exists"%num,stderrdata):
            erreur="CT %s already exist on another node, delete it first or change the ID on the .yml"%num
            module.fail_json(msg=erreur)
        else:
            erreur="Installation failed with %s, check attributes (wrong ID<0 or bad ostemplate, check path)" % (num)
            module.fail_json(msg=erreur)
    module.exit_json(changed = True, result="Created")

def delete_container(module,numero):
    for num in numero:
        rep=subprocess.call(["pvectl","destroy",str(num)])
        if rep != 0 and rep != 2 and rep != 255:
            erreur="Failed to delete %s" % num
            module.fail_json(msg=erreur)
        if rep == 255:
            os.remove('/etc/pve/openvz/%s.conf'%num)
    module.exit_json(changed = True, result = "Deleted")

def migrate_container(module,numero):
    dest=module.params['target']
    live=module.params['online']
    for num in numero:
        if live == True: 
            rep=subprocess.call(["pvectl","migrate",str(num),str(dest),"-online"])
        else:
            rep=subprocess.call(["pvectl","migrate",str(num),str(dest)])
        if rep != 0 and rep != 2:
            erreur="Migration failed with %s, target is wrong" % (num)
            module.fail_json(msg=erreur)
    module.exit_json(changed = True, result = "Migrated")

def recover_container(module,numero):
    chemin=module.params['path']
    for num in numero:
        rep=subprocess.call(["pvectl","create",str(num),str(chemin),"-restore"])
        if rep !=0 and rep != 255:
            erreur="Restore failed with %s, the backup file doesn't exist" % (num)
            module.fail_json(msg=erreur)
    module.exit_json(changed = True, result = "Restore completed") 

def main():
    module = AnsibleModule(
        argument_spec = dict(
            state = dict(default=None, choices=['present','absent','recover','migrate']),
            idct = dict(type='list', required=True),
            path = dict(default=None),
            hostname = dict(default='localhost'),
            password = dict(default='root'),
            target = dict(default=None),
            netif = dict(default='eth0', type='list'),
            online = dict(default=True),
            cpu = dict(type='int', default='1'),
            cpuunits = dict(type='int', default='1000'),
            disk = dict(type='int', default='2'),
            memory = dict(type='int', default='512'),
            swap = dict(type='int', default='512'), 
            onboot = dict(default='0', choices=['1','0']),
            force = dict(default='no', choices=['yes','no']),
        ),
        supports_check_mode = True
    )
    network=module.params['netif']
    numero=module.params['idct']
    for juice in numero:
        for apple in juice:
            flag=0
            for ananas in range(0,9+1):
                if apple == str(ananas):
                    flag=1 
            if flag == 0:
                module.fail_json(msg="Problem in ID, check ID if they have only number")
    if module.params['state'] == 'present':
        create_container(module,numero,network)
    if module.params['state'] == 'absent':
        delete_container(module,numero)
    if module.params['state'] == 'recover':
        recover_container(module,numero)
    if module.params['state'] == 'migrate':
        migrate_container(module,numero)

# import module snippets
from ansible.module_utils.basic import *
if __name__ == '__main__':
    main()

