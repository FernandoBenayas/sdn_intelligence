import random
import sys
import random_scalefree
import random_errors
import ConfigParser
import time
import logging
import json

from os import makedirs, path, system
from datetime import datetime, timedelta

from mininet.topo import Topo
from mininet.net import Mininet
from mininet.node import RemoteController
from mininet.node import Node
from mininet.link import TCLink
from mininet.cli import CLI
from mininet.clean import cleanup
from mininet.node import OVSSwitch
from mininet.log import setLogLevel

# Randomize bw of access link
def random_access(self, link_type="equal"):
	type_id = 0

	if link_type == "equal":
		type_id = random.randint(0, 4)
	elif link_type == "badwifi":
		type_id_float = random.gauss(0, 0.75)
		type_id = int(type_id_float)
	elif link_type == "wifi":
		type_id_float = random.gauss(1, 0.75)
		type_id = int(type_id_float)
	elif link_type == "xdsl":
		type_id_float = random.gauss(2, 0.75)
		type_id = int(type_id_float)
	elif link_type == "fiber50":
		type_id_float = random.gauss(3, 0.75)
		type_id = int(type_id_float)
	elif link_type == "fiber300":
		type_id_float = random.gauss(4, 0.75)
		type_id = int(type_id_float)

	if type_id < 0:
		type_id = 0
	elif type_id > 4:
		type_id = 4

	bw_table = [3, 10, 20, 50, 300]
	return bw_table[type_id]

# Join networks
def join_networks(main_network, extra_networks, namespace, link_type):
	main = main_network
	main_switches = main.switches()

	for i in range(len(extra_networks)):
		topo = extra_networks["topo{}".format(i)]
		topo_links = topo.links()
		topo_switches = topo.switches()
		topo_hosts = topo.hosts()
		

		for n in range(len(topo_switches)):
			main.addSwitch(topo_switches[n])
		for n in range(len(topo_hosts)):
			main.addHost(topo_hosts[n])
		for n in range(len(topo_links)):
			if "h" not in topo_links[n][0] and "h" not in topo_links[n][1]:
				main.addLink(topo_links[n][0], topo_links[n][1], bw = 1000,
				lat = '3ms')
			else:
				main.addLink(topo_links[n][0], topo_links[n][1], bw = random_access(link_type), lat = '3ms')

		sw_connect = [random.choice(main_switches), random.choice(main_switches),
		random.choice(main_switches)]
		sw_connect_2 = [random.choice(topo_switches), random.choice(topo_switches),
		random.choice(topo_switches)]

		n_sw_conn = random.randint(1,4)

		for n in range(n_sw_conn):
			main.addSwitch('s{}'.format(namespace+n+1))
			for m in range(len(sw_connect)):
				main.addLink(sw_connect[m], 's{}'.format(namespace+n+1), bw = 1000, lat = '3ms')
			for m in range(len(sw_connect_2)):
				main.addLink(sw_connect_2[m], 's{}'.format(namespace+n+1), bw = 1000, lat = '3ms')
		namespace += n_sw_conn

	return [main, namespace]

def trim(topo):
	switches = topo.switches()
	links = topo.links()
	counter = 0
	other_switch = ''

	for s in range(len(switches)):
		for l in range(len(links)):
			if switches[s] == links[l][0]:
				if links[l][1] == other_switch:
					continue
				else:
					counter += 1
					other_switch = links[l][1]	
			if switches[s] == links[l][1]:
				if links[l][0] == other_switch:
					continue
				else:
					counter += 1
					other_switch = links[l][0]

		if counter == 1:
			switches_b = topo.switches()
			switches_b.remove(other_switch)
			switches_b.remove(switches[s])

			topo.addLink(switches[s], random.choice(switches_b), bw = 1000, lat = "3ms")
		counter = 0
		other_switch = ''

def create_traffic(net, datac, nm_ho, temp = False):
    for n in range(nm_ho):
        x = random.randint(0,6)
        h = net.get('h{}'.format(n+1))
        #DEBUGGING This is considering that we have 0 hosts in main network
        #DEBUGGING One could send messages to himself
        if datac > 0:
        	randip_datac = '10.0.0.' + str(random.randint(1, datac*3))
        else:
        	randip_datac = '0.0.0.0'

        randip_ho = '10.0.0.' + str(random.randint(datac + 1, nm_ho))

        if temp is True:
        	traffic = {
                    0: ' ',
                    1: './net/mail_receive.sh ' + randip_datac + ' temp' + ' &',
                    2: './net/mail_send.sh ' + randip_datac + ' temp' +  ' &',
                    3: './net/small_send.sh ' + randip_ho + ' temp' +  ' &',
                    4: './net/send.sh ' + randip_ho + ' temp' +  ' &',
                    5: './net/streaming_client.sh ' + randip_datac + ' temp' +  ' &',
                    6: './net/server_connect.sh ' + randip_datac + ' temp' +  ' &'
            }

        else:
         	traffic = {
                    0: ' ',
                    1: './net/mail_receive.sh ' + randip_datac + ' &',
                    2: './net/mail_send.sh ' + randip_datac + ' &',
                    3: './net/small_send.sh ' + randip_ho + ' &',
                    4: './net/send.sh ' + randip_ho + ' &',
                    5: './net/streaming_client.sh ' + randip_datac + ' &',
                    6: './net/server_connect.sh ' + randip_datac + ' &'
            }
        print "			Command type : " + str(x)
        h.cmd(str(traffic.get(x, ' ')))
        print "			 Done"

    print "		End of iteration"
    return
# Creates an error in the network according to a number given
def create_error(err, nm_ho, datac, net, sim_id, logger, controller, err_int = 10):
	#DEBUGGING I'm supposing zero hosts in the main network
	host = random.randint(datac*3+1, nm_ho)
	
	if datac > 0:
		server = random.randint(1, datac*3)
		ip_datac = '10.0.0.' + str(server)
	else:
		ip_datac = '0.0.0.0'

	if err == 1:
		print 'Error %d in host %s' % (err, host)
		for n in range(0, 6):
			time.sleep(0.5)
			print '		 Iteration %d' % (n+1)
			h = net.get('h{}'.format(host))
			h.cmd('./net/streaming_client.sh ' + ip_datac + ' temp' +  ' &')

		random_errors.send_report(err, {'Host': 'h{}'.format(host), 'Timestamp': str(datetime.now())}, sim_id, logger)

		if err_int < 60:
			time.sleep(60)
		else:
			time.sleep(err_int)
		print "Fixed traffic-consuming host error"

		random_errors.send_report(str(err)+'f', {'Host': 'h{}'.format(host), 'Timestamp': str(datetime.now())}, sim_id, logger)

	elif err == 2:
		print 'Error %d ' % err
		for n in range(0, 10):
			print '		 Iteration %d' % (n+1)
			create_traffic(net, datac, nm_ho, temp=True)

		random_errors.send_report(err, {'Timestamp': str(datetime.now())}, sim_id, logger)

		if err_int < 60:
			time.sleep(60)
		else:
			time.sleep(err_int)
		print "Fixed general traffic error"

		random_errors.send_report(str(err) +'f', {'Timestamp': str(datetime.now())}, sim_id, logger)

	elif err == 3:
		print 'Error %d' % err
		links_list = net.links
		# Beginning in 1 instead of 0, because 0 is loopback
		link_down = links_list[random.randint(1, len(links_list)-1)]
		print 'link down: %s - %s' % (link_down.intf1, link_down.intf2)
		while not random_errors.check_pass():
			time.sleep(0.25)
		random_errors.send_report(err, {'Interface 1': str(link_down.intf1), 'Interface 2': str(link_down.intf2), 'Timestamp': str(datetime.now())}, sim_id, logger)
		net.configLinkStatus(str(link_down.intf1.node), str(link_down.intf2.node), "down")

		time.sleep(err_int)
		print "Fixing link down"
		while not random_errors.check_pass():
			time.sleep(0.25)
		net.configLinkStatus(str(link_down.intf1.node), str(link_down.intf2.node), "up")
		print 'Fixed'
		random_errors.send_report(str(err)+'f', {'Interface 1': str(link_down.intf1), 'Interface 2': str(link_down.intf2), 'Timestamp': str(datetime.now())}, sim_id, logger)

	elif err == 4:
		print 'Error %d' % err

		switches_list = net.switches
		switch_down = net.switches[random.randint(0, len(switches_list)-1)]
		print 'switch down: %s' % switch_down.name
		while not random_errors.check_pass():
			time.sleep(0.25)

		name = str(switch_down.name.replace('s', ''))
		random_errors.send_report(err, {'Switch': str(int(switch_down.dpid, 16)), 'Timestamp': str(datetime.now())}, sim_id, logger)
		old_xml = random_errors.delete_flow(switch_down.dpid)
		old_lldp = random_errors.delete_lldp_flow(switch_down.dpid)

		time.sleep(err_int)
		print 'Fixing switch down error...'
		
		while not random_errors.check_pass():
			time.sleep(0.25)
		
		random_errors.fix_node_table(switch_down.dpid, old_lldp)
		random_errors.fix_node_flow(switch_down.dpid, old_xml)
		print 'Fixed'
		random_errors.send_report(str(err)+'f', {'Switch': str(int(switch_down.dpid, 16)), 'Timestamp': str(datetime.now())}, sim_id, logger)

	elif err == 5:
		if datac <= 0:
			print 'No datacenters in the network!'
			print '  Error 5 shuts down a host in a datacenter'
		else:
			print 'Error %d' % err
			host_down = net.get("h"+ str(random.randint(1, datac*3)))
			print 'host down: pid: %s name: %s' % (host_down.pid, host_down.name)

			deleted_links = []

			links_list = net.links
			while not random_errors.check_pass():
				time.sleep(0.25)
			for link in links_list:
				if (host_down.name + '-' in str(link.intf1)) or (host_down.name + '-' in str(link.intf2)):
					deleted_links.append(link)
					print link
					net.configLinkStatus(str(link.intf1.node), str(link.intf2.node), 'down')

			random_errors.send_report(err, {'Host': host_down.name, 'Timestamp': str(datetime.now())}, sim_id, logger)

			time.sleep(err_int)
			print 'Fixing host down error...'
			while not random_errors.check_pass():
				time.sleep(0.25)
			for deleted in deleted_links:
				net.configLinkStatus(str(deleted.intf1.node), str(deleted.intf2.node), 'up')
			print 'Fixed'
			random_errors.send_report(str(err)+'f', {'Host': host_down.name, 'Timestamp': str(datetime.now())}, sim_id, logger)

	elif err == 6:
		print 'Error %d' % err
		switches_list = net.switches
		switch_flow = switches_list[random.randint(0, len(switches_list)-1)]
		print 'switch whose flow has been modified: %s' % switch_flow.dpid
		while not random_errors.check_pass():
			time.sleep(0.25)		
		random_errors.send_report(err, {'Switch': str(int(switch_flow.dpid, 16)), 'Timestamp': str(datetime.now())}, sim_id, logger)
		dictionary = random_errors.change_flow(switch_flow.dpid)

		time.sleep(err_int)
		print 'Fixing modified flows error...'

		while not random_errors.check_pass():
			time.sleep(0.25)
		random_errors.fix_node_flow(switch_flow.dpid, dictionary)
		print 'Fixed'
		random_errors.send_report(str(err) + 'f', {'Switch': str(int(switch_flow.dpid, 16)), 'Timestamp': str(datetime.now())}, sim_id, logger)

	elif err == 7:
		print 'Error %d' % err
		switches_list = net.switches
		switch_down = switches_list[random.randint(0, len(switches_list)-1)]
		print 'Switch whose in-ports have been messed: %s' % switch_down.dpid
		while not random_errors.check_pass():
			time.sleep(0.25)
		random_errors.send_report(err, {'Switch': str(int(switch_down.dpid, 16)), 'Timestamp': str(datetime.now())}, sim_id, logger)
		old_inports = random_errors.change_inport(switch_down.dpid)
		time.sleep(err_int)
		print 'Fixing in-ports error...'
		while not random_errors.check_pass():
			time.sleep(0.25)
		random_errors.fix_node_flow(switch_down.dpid, old_inports)
		print 'Fixed'
		random_errors.send_report(str(err)+'f', {'Switch': str(int(switch_down.dpid, 16)), 'Timestamp': str(datetime.now())}, sim_id, logger)

	elif err == 8:
		print 'Error %d' % err
		switches_list = net.switches
		seconds = random.randint(1, 5)
		switch_down = switches_list[random.randint(0, len(switches_list)-1)]
		print 'Switch %s: idle-timeout has been added with %d seconds' % (switch_down.name, seconds)
		dictionary = {}

		while not random_errors.check_pass():
			time.sleep(0.25)	
		random_errors.send_report(err, {'Time': str(seconds), 'Timestamp': str(datetime.now())}, sim_id, logger)
		old_xml = random_errors.change_idletimeout(switch_down.dpid, seconds)
		dictionary[switch_down.dpid] = old_xml

		time.sleep(err_int)
		print 'Fixing idle-timeout error...'

		for key, value in dictionary.iteritems():
			while not random_errors.check_pass():
				time.sleep(0.25)	
			random_errors.fix_node_flow(key, value)
		print 'Fixed'
		random_errors.send_report(str(err)+'f', {'Time': str(0), 'Timestamp': str(datetime.now())}, sim_id, logger)

	elif err == 9:
		print 'Error %d' % err
		switches_list = net.switches
		seconds = random.randint(30, 60)
		switch_down = switches_list[random.randint(0, len(switches_list)-1)]
		print 'Switch %s: hard-timeout has been added with %d seconds' % (switch_down.name, seconds)
		dictionary = {}
		
		while not random_errors.check_pass():
			time.sleep(0.25)	
		random_errors.send_report(err, {'Time': str(seconds), 'Timestamp': str(datetime.now())}, sim_id, logger)
		old_xml = random_errors.change_hardtimeout(switch_down.dpid, seconds)
		dictionary[switch_down.dpid] = old_xml

				
		time.sleep(err_int)
		print 'Fixing hard-timeout error...'

		for key, value in dictionary.iteritems():
			while not random_errors.check_pass():
				time.sleep(0.25)	
			random_errors.fix_node_flow(key, value)
		print 'Fixed'
		random_errors.send_report(str(err)+'f', {'Time': str(0), 'Timestamp': str(datetime.now())}, sim_id, logger)

	elif err == 10:
		print 'Error %d' % err
		switches_list = net.switches
		switch_down = switches_list[random.randint(0, len(switches_list)-1)]
		print 'Switch whose flows priorities have changed: %s' % switch_down.dpid
		while not random_errors.check_pass():
			time.sleep(0.25)
		random_errors.send_report(err, {'Switch': str(int(switch_down.dpid, 16)), 'Timestamp': str(datetime.now())}, sim_id, logger)
		old_xml = random_errors.change_priority(switch_down.dpid)

		time.sleep(err_int)
		print 'Fixing priorities error...'
		while not random_errors.check_pass():
			time.sleep(0.25)	
		random_errors.fix_node_flow(switch_down.dpid, old_xml)
		print 'Fixed'
		random_errors.send_report(str(err)+'f', {'Switch': str(int(switch_down.dpid, 16)), 'Timestamp': str(datetime.now())}, sim_id, logger)

	elif err == 11:
		print 'Error %d' % err
		switches_list = net.switches
		switch_down = switches_list[random.randint(0, len(switches_list)-1)]
		print 'Switch that will drop its lldp packages: %s' % switch_down.dpid
		while not random_errors.check_pass():
			time.sleep(0.25)	
		old_xml = random_errors.delete_lldp_flow(switch_down.dpid)
		random_errors.send_report(err, {'Switch': str(int(switch_down.dpid, 16)), 'Timestamp': str(datetime.now())}, sim_id, logger)
		time.sleep(err_int)
		print 'Fixing lldp error...'
		while not random_errors.check_pass():
			time.sleep(0.25)	
		random_errors.fix_node_table(switch_down.dpid, old_xml)
		print 'Fixed'
		random_errors.send_report(str(err)+'f', {'Switch': str(int(switch_down.dpid, 16)), 'Timestamp': str(datetime.now())}, sim_id, logger)
		
	return

def run(topo, ip, config, config2, pred_error, err_int = 10):

	cont = RemoteController('c1', ip=ip, port=6633)
	net = Mininet(topo=topo, link=TCLink, controller=cont)
	setLogLevel("debug")
	net.start()
	net.pingAll()

	# DEBUGGING: MainHosts is zero
	nm_ho_sf = 0
	datac = int(config.get('main','Datacenters'))

	#All datacenters will activate their servers
	scenario = config.get('main', 'StreamingScenario')
	for n in range(nm_ho_sf+1, nm_ho_sf+datac*3+1):
		h = net.get('h{}'.format(n))
		h.cmd('./net/server.sh &')
		h.cmd('./net/streaming_server.sh &')
		h.cmd('./net/mail_listen_receive.sh &')
		h.cmd('./net/mail_listen_send.sh &')
		h.cmd('iperf -s &')
	if 'Yes' in scenario:
		for n in range(nm_ho_sf, nm_ho_sf+datac):
			h = net.get('h{}'.format(n*3+1))
			h.cmd('./net/vlc_send.sh &')
			# XTERM any host to connect vlc to the datacenter
			CLI(net)
	elif 'No' not in scenario:
		print '		I could not understand the "StreamingScenario" field '

	#nm_ho is the number of hosts (incuding datacenters) in the network
	nm_ho = nm_ho_sf + datac*3
	ex_net = config.sections()
	if (len(ex_net)>1):
		n_networks = len(ex_net)-1
		for i in range(n_networks):
			nm_ho += int(config2.get(ex_net[i+1],'Hosts'))

	#All hosts will be listening for normal and small traffic
	for n in range(nm_ho):
		h = net.get('h{}'.format(n+1))
		h.cmd('./net/listen.sh &')
		h.cmd('./net/small_listen.sh &')

	print "Generating traffic..."
	#DEBUGGING: not smart enough
	create_traffic(net, datac, nm_ho)

	#Simulation ID
	orig_timestamp = datetime.now()
	sim_id = str(orig_timestamp.year) + str(orig_timestamp.month) + str(orig_timestamp.day) + str(orig_timestamp.hour)+ str(orig_timestamp.minute) + '_' + str(pred_error)
	print "Simulation ID = %s" % sim_id
	#Setting up log
	print "Setting up log..."
	logger = logging.getLogger()
	hdlr = logging.FileHandler('/root/log/' + sim_id + '.log')
	formatter = logging.Formatter('%(asctime)s %(levelname)s %(message)s')
	hdlr.setFormatter(formatter)
	logger.addHandler(hdlr)
	logger.setLevel(logging.INFO)
	logger.info(sim_id + " start " + str(json.dumps(random_errors.encode_errors())))
	
	switches_list = net.switches
	for switch in switches_list:
		random_errors.config_push(switch.dpid)
	
	print "Giving time for the collector to catch up..."
	time.sleep(25)

	print "Beginning test..."
	minutes = int(config.get('main', 'MinutesRunning'))
	now_timestamp = datetime.now()

	while (now_timestamp - orig_timestamp).total_seconds() < minutes*60:
		time.sleep(err_int)
		if pred_error != 0:
			if (pred_error == 2 or pred_error == 1):
				print '1 and 2 errors not supported for the time being'
				break
			create_error(pred_error, nm_ho, datac, net, sim_id, logger, cont, err_int)
		else:
			# Excluding traffic errors (1 and 2) for the time being
			create_error(random.randint(3,11), nm_ho, datac, net, sim_id, logger, cont, err_int)
		now_timestamp = datetime.now()

	logger.info(sim_id + " stop")
	print "Test ended. Shutting down network..."
	net.stop()

	return

def init(pred_error, seed = None):

	cleanup()

	config = ConfigParser.ConfigParser()
	config.read('./config')

	ip = config.get('main','Ip')
	link_type = config.get('main','Distribution')
	nm_sw_sf = int(config.get('main','MainSwitches'))
	nm_ho_sf = 0
	datac = int(config.get('main','Datacenters'))
	err_int = int(config.get('main', 'ErrorInterval'))

	if seed == None or 'None' in seed:
		seed = random.randint(1, 10000)
	print '			Seed = %s' % seed

	topo = random_scalefree.RandomScaleFree(seed, link_type, datac, nm_sw_sf, nm_ho_sf)
	if datac > 0:
		namespace = [nm_sw_sf+3*datac, nm_ho_sf+3*datac]
	else:
		namespace = [nm_sw_sf, nm_ho_sf]
	trim(topo)

	ex_net = config.sections()

	if (len(ex_net)>1):
		extra_topos = {}
		n_networks = len(ex_net)-1
		config2 = ConfigParser.ConfigParser()
		config2.read('./repo_subnets')
		topo_counter = 0

		for i in range(n_networks):
			nm_networks = int(config.get(ex_net[i+1], 'Number'))
			for n in range(nm_networks):
				nm_sw = int(config2.get(ex_net[i+1],'Switches'))
				nm_ho = int(config2.get(ex_net[i+1],'Hosts'))

				extra_topos["topo{}".format(topo_counter)] = random_scalefree.RandomScaleFree(seed, link_type, 0, nm_sw, nm_ho, namespace)
				namespace[0] += nm_sw
				namespace[1] += nm_ho
				topo_counter += 1

		print "Building network..."
		join = join_networks(topo, extra_topos, namespace[0], link_type)
		topo = join[0]
		namespace[0] = join[1]

	run(topo, ip, config, config2, pred_error, err_int)
	return
