# vi: ts=4 expandtab
#
#    Copyright (C) 2013 CERN
#
#    Author: Cristovao Cordeiro <christovao.jose.domingues.cordeiro@cern.ch>
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License version 3, as
#    published by the Free Software Foundation.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>

# NOTE: Be very carefull with the user-data structure. A simple misplaced white-space can make cloud init skip the cloud config parameters.

import subprocess
import cloudinit.CloudConfig as cc
import urllib

# Cloud Config module for Ganglia
def handle(_name, cfg, cloud, log, _args):
    # Always check first if ganglia is referenced in the user-data	
    if 'ganglia' in cfg:
        print "Starting Ganglia setup..."
        # If it reaches this is because ganglia is referenced in user-data
        print "Ready to setup ganglia..."
        ganglia_cfg = cfg['ganglia']
        print "Installing and configuring Ganglia:"
        
        # Aux variables to know if we are dealing with headnode or node config
        headnode_bool = 0
        node_bool = 0        

        if 'nodes' in ganglia_cfg and 'headnode' in ganglia_cfg:
            print "ATTENTION: you can not configure a ganglia node and a ganlgia head node on the same machine!\nSkipping ganglia configuration..."
            return
        # For Ganglia setup there are just 2 main step: install packages and write gmond configuration
    
        # Install Ganglia and gmond
        cc.install_packages(("ganglia","ganglia-gmond",))
        # If ganglia-gmetad and ganglia-web are required they should be installed the same way as ganglia and ganglia-gmond
        if 'headnode' in ganglia_cfg:
            cc.install_packages(("ganglia-gmetad"," ganglia-web",))
            gmetad_conf_file = '/etc/ganglia/gmetad.conf'
            hconf = open(gmetad_conf_file, 'r')
            hlines = hconf.readlines()
            hconf.close()
            ganglia_param_cfg = ganglia_cfg['headnode']
            headnode_bool = 1
        else:
            ganglia_param_cfg = ganglia_cfg['nodes']
            node_bool = 1       

        gmond_conf_file = '/etc/ganglia/gmond.conf'
        flocal = open(gmond_conf_file, 'r')     # Open to read all the file and then close it
        lines = flocal.readlines()
        flocal.close()
        
        # Let start by changing the configuration on the collector server, in case headnode is referenced
        if headnode_bool:
            if 'source' in ganglia_param_cfg:
                data_source_name = ganglia_param_cfg['source']
            else:
                data_source_name = '"my servers"'    # Default value
            if 'polling' in ganglia_param_cfg:
                polling_interval = ganglia_param_cfg['polling']
            else:
                polling_interval = 15   # 15 sec is the default time
            if 'addresses' in ganglia_param_cfg:
                address = ganglia_param_cfg['addresses']
            else:
                address = 'localhost'   # Default
            for h in range(0,len(hlines)):
                if '#' not in hlines[h]:
                    if 'data_source' in hlines[h]:
                        hlines[h] = 'data_source '+data_source_name+' '+str(polling_interval)+' '+address+'\n'
                        break

            hconf_new = open(gmetad_conf_file, 'w')     # Open the same file, but let's overwrite it with the new variables
            hconf_new.writelines(hlines)
            hconf_new.close()
        
        flocal_new = open(gmond_conf_file, 'w')     # Open the gmond file, but let's overwrite it with the new variables
        if 'globals' in ganglia_param_cfg:
            globals_cfg = ganglia_param_cfg['globals']
            for param, value in globals_cfg.iteritems():
                if param == 'daemonize':
                    for i in range(0,len(lines)):
                        if 'daemonize' in lines[i]:
                            lines[i] = "  daemonize = "+str(value)+'\n'
                            break
                if param == 'setuid':
                    for i in range(0,len(lines)):
                        if 'setuid' in lines[i]:
                            lines[i] = "  setuid = "+str(value)+'\n'
                            break
                if param == 'user':
                    for i in range(0,len(lines)):
                        if 'user = ' in lines[i]:
                            lines[i] = "  user = "+str(value)+'\n'
                            break
                if param == 'debug-level':
                    for i in range(0,len(lines)):
                        if 'debug_level' in lines[i]:
                            lines[i] = "  debug_level = "+str(value)+'\n'
                            break
                if param == 'max-udp-msg-len':
                    for i in range(0,len(lines)):
                        if 'max_udp_msg_len' in lines[i]:
                            lines[i] = "  max_udp_msg_len = "+str(value)+'\n'
                            break
                if param == 'mute':
                    for i in range(0,len(lines)):
                        if 'mute' in lines[i]:
                            lines[i] = "  mute = "+str(value)+'\n'
                            break
                if param == 'deaf':
                    for i in range(0,len(lines)):
                        if 'deaf' in lines[i]:
                            lines[i] = "  deaf = "+str(value)+'\n'
                            break
                if param == 'allow-extra-data':
                    for i in range(0,len(lines)):
                        if 'allow_extra_data' in lines[i]:
                            lines[i] = "  allow_extra_data = "+str(value)+'\n'
                            break
                if param == 'host-dmax':
                    for i in range(0,len(lines)):
                        if 'host_dmax' in lines[i]:
                            lines[i] = "  host_dmax = "+str(value)+' /*secs */\n'
                            break
                if param == 'cleanup-threshold':
                    for i in range(0,len(lines)):
                        if 'cleanup_threshold' in lines[i]:
                            lines[i] = "  cleanup_threshold = "+str(value)+' /*secs */\n'
                            break
                if param == 'gexec':
                    for i in range(0,len(lines)):
                        if 'gexec = ' in lines[i]:
                            lines[i] = "  gexec = "+str(value)+'\n'
                            break
                if param == 'send-metadata-interval':
                    for i in range(0,len(lines)):
                        if 'send_metadata_interval' in lines[i]:
                            lines[i] = "  send_metadata_interval = "+str(value)+' /*secs */\n'
                            break
            # End of globals configuration

        if 'cluster' in ganglia_param_cfg:
            cluster_cfg = ganglia_param_cfg['cluster']
            for i in range(0,len(lines)):   # Optimization to find where cluster starts instead of reading file from top every time
                if 'cluster {' in lines[i]:
                    indice = i
                    break
            for param, value in cluster_cfg.iteritems():
                if param == 'name':
                    for l in range(indice,len(lines)):    
                        if 'name' in lines[l]:
                            lines[l] = "  name = "+str(value)+'\n'
                            break
                if param == 'owner':
                    for l in range(indice,len(lines)):    
                        if 'owner' in lines[l]:
                            lines[l] = "  owner = "+str(value)+'\n'
                            break
                if param == 'latlong':
                    for l in range(indice,len(lines)):    
                        if 'latlong' in lines[l]:
                            lines[l] = "  latlong = "+str(value)+'\n'
                            break
                if param == 'url':
                    for l in range(indice,len(lines)):
                        if 'url' in lines[l]:
                            lines[l] = "  url = "+str(value)+'\n'
                            break

            # End of cluster configuration

        lines = [word.replace('mcast_join','host') for word in lines]               # Change to 'host' instead of 'mcast_join'. If it isn't passed in cloud-config, it will be changed anyway.
        
        for i in range(0,len(lines)):
                if 'udp_recv_channel {' in lines[i]:
                    indice_aux = i
                    break
        for u in range(indice_aux, len(lines)):    # Erase the 'host' parameter in udp_recv_channel, because it causes parsing errors
                if 'host' in lines[u]:
                    lines[u] = ''
                    break

        if 'udpSendChannel' in ganglia_param_cfg:
            udp_send_cfg = ganglia_param_cfg['udpSendChannel']
            for i in range(0,len(lines)):   # Same process as cluster
                if 'udp_send_channel {' in lines[i]:
                    indice_udp = i
                    break
            for param, value in udp_send_cfg.iteritems():
                if param == 'host':
                    for a in range(indice_udp, len(lines)):   
                        if 'host = ' in lines[a]:
                            lines[a] = "  host = "+str(value)+'\n'
                            break
                if param == 'port':
                    for a in range(indice_udp, len(lines)):  
                        if 'port' in lines[a]:
                            lines[a] = "  port = "+str(value)+'\n'
                            break
                if param == 'ttl':
                    for a in range(indice_udp, len(lines)): 
                        if 'ttl' in lines[a]:
                            lines[a] = "  ttl = "+str(value)+'\n' 
                            break
            # End of udp_send_channel configuration  

        if 'udpRecvChannel' in ganglia_param_cfg:
            udp_recv_cfg = ganglia_param_cfg['udpRecvChannel']
            for i in range(0,len(lines)):
                if 'udp_recv_channel {' in lines[i]:
                    indice_udp_recv = i
                    break

            for param, value in udp_recv_cfg.iteritems():     
                if param == 'port':
                    for u in range(indice_udp_recv, len(lines)):  
                        if 'port' in lines[u]:
                            lines[u] = "  port = "+str(value)+'\n'
                            break
                if param == 'bind':
                    for u in range(indice_udp_recv, len(lines)):  
                        if 'bind' in lines[u]:
                            lines[u] = "  bind = "+str(value)+'\n'
                            break
            # End of udp_recv_channel configuration

        # Finally...
        if 'tcpAcceptChannel' in ganglia_param_cfg:
            tcp_cfg = ganglia_param_cfg['tcpAcceptChannel']
            for i in range(0,len(lines)):
                if 'tcp_accept_channel {' in lines[i]:
                    indice_tcp = i
                    break
            for param, value in tcp_cfg.iteritems():
                if param == 'port':
                    for t in range(indice_tcp, len(lines)):    # tcp_accept_channel is generally small. Five iterations just in case.
                        if 'port' in lines[t]:
                            lines[t] = "  port = "+str(value)+'\n'
                            break
            # End of tcp_accept_channel configuration

    
        # Start gmond
        flocal_new.writelines(lines)
        flocal_new.close()
        if headnode_bool:
            subprocess.check_call(['service','gmetad','restart'])
        
        subprocess.check_call(['/etc/init.d/gmond','restart'])
