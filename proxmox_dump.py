#!/usr/bin/python
# -*-coding:utf-8 -*

DOCUMENTATION = '''
---
version_added: "1.0"
module: proxmox_dump
short_description: proxmox_dump
description:
  - This module make backup and restore containers
options:
       state:
         description:
           choices=backup|restore
  ####Backup####
    Make a backup from an existant containers
       idct:
         description:
          ID of the containers.
       path:
         description:
          Backup's directory (default path: /var/lib/vz/dump/)
       compress:
         description:
          set the level of compression (default: lzo) 
            choices: lzo|gzip|0|1
       mode:
         description:
          Backup mode (default: snapshot)
            choices: snapshot|stop|suspend 
       force:
         description:
          force backup even if there is already a backup of the day 
           /!/ it erases the save of the day by the new one
  ####Restore####
    Restore a container or create a new container from a backup
       idct:
         description:
          Restore the container identified by idct, or create a new one if the idct is not used
       path:
         description:
          restore's file (/! need complete path, not only file's name)
          --> default's backup directory is /var/lib/vz/dump/*file*
        force:
         description:
          if yes, it will erase container if there is already a container with same ID (default=no)
       
notes:
requirements: []
author: Guillaume Dubroeucq
'''
EXAMPLES = '''

name: Backup containers
proxmox_dump: state=backup idct=100,186,112 compress=lzo

name: restore containers
promox_dump: state=restore idct=115 path=/var/lib/vz/dump/vzdump-openvz-100-2015_06_03-15_01_03.tar.lzo

'''


import subprocess
from time import gmtime, strftime
import fnmatch

def backup(module,numachine):
    mod=module.params['mode']
    archive=module.params['compress']
    directory=module.params['path']
    brutal=module.params['force']
    flag=0
    rep=0
    #### check if a backup of the day is already here
    for num in numachine:
        pattern=strftime("%Y_%m_%d*",gmtime())
        pattern="vzdump-openvz-%s-%s" % (num,pattern)
        for root,dirs,files in os.walk(directory):
            for filename in fnmatch.filter(files,pattern):
                flag=1
        #### if there is no backup or too old (>1 day), then make a backup
        if flag == 0:
            rep=subprocess.call(["vzdump",str(num),"-mode",str(mod),"-compress",str(archive),"-dumpdir",str(directory)])
        else:
            flag=0
            if brutal == 'yes':
               #### force backup
                rep=subprocess.call(["vzdump",str(num),"-mode",str(mod),"-compress",str(archive),"-dumpdir",str(directory)])
        if rep != 0:
            erreur="Error with %s, check if the ID is valid" % (num)
            module.fail_json(msg=erreur)
        #### Good ending 
        module.exit_json(changed = True , result="Backup complete")

def restore(module,numachine):
    save=module.params['path']
    force=module.params['force']
    for num in numachine:
        if force == 'no':
            rep=subprocess.call(["vzrestore",str(save),str(num)])
        else:
            rep=subprocess.call(["vzrestore",str(save),str(num),"-force"])
        if rep != 0:
            erreur="Restore failed with %s, check the file/path" % (num)
            module.fail_json(msg=erreur)
    if rep == 0:
        module.exit_json(changed = True, result="Restore complete")
    

def main():
    module = AnsibleModule(
        argument_spec = dict(
            state = dict(required=True, choices=['backup','restore']),
            idct = dict(type='list', required=True),
            compress = dict(default='lzo'),
            path = dict(default='/var/lib/vz/dump/'),
            mode = dict(default='snapshot', choices=['snapshot','stop','suspend']),
            force = dict(default='no', choices=['yes','no']),
        ),
        supports_check_mode = True
    )
    numachine=module.params['idct']
    if module.params['state'] == 'backup':
        backup(module,numachine)
    if module.params['state'] == 'restore':
        restore(module,numachine)


# import module snippets
from ansible.module_utils.basic import *
if __name__ == '__main__':
    main()
