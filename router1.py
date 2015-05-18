# Copyright 2012 James McCauley
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at:
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""
This component is for use with the OpenFlow tutorial.

It acts as a simple hub, but can be modified to act like an L2
learning switch.

It's roughly similar to the one Brandon Heller did for NOX.
"""

from pox.core import core
import pox.openflow.libopenflow_01 as of
import pox.lib.packet as pkt
import pox.lib.addresses as adr

log = core.getLogger()



class Tutorial (object):
  """
  A Tutorial object is created for each switch that connects.
  A Connection object for that switch is passed to the __init__ function.
  """
  def __init__ (self, connection):
    # Keep track of the connection to the switch so that we can
    # send it messages!
    self.connection = connection

    # This binds our PacketIn event listener
    connection.addListeners(self)

    # Use this table to keep track of which ethernet address is on
    # which switch port (keys are MACs, values are ports).
    self.mac_to_port = {}
    self.ip_to_port = {"10.0.1.1":1,"10.0.2.1":2,"10.0.3.1":3}
    self.routing_table = {'10.0.1.0/24': ['10.0.1.100', 's1-eth1', '10.0.1.1', 1, '00:00:00:00:00:01'], '10.0.2.0/24': ['10.0.2.100', 's1-eth2', '10.0.2.1', 2, '00:00:00:00:00:02'], '10.0.3.0/24': ['10.0.3.100', 's1-eth3', '10.0.3.1', 3, '00:00:00:00:00:03']}

  def FlowMode(self, packet_in, out_port):
    log.debug("Flow Mode install  Successfully")
    msg = of.ofp_flow_mod()
    msg.match.in_port = packet_in.in_port
    msg.idle_timeout = 240
    msg.buffer_id = packet_in.buffer_id
    msg.actions.append(of.ofp_action_output(port = out_port))     
  
  def act_like_router (self, packet, packet_in):
    #handle arp
    if packet.type == pkt.ethernet.ARP_TYPE:
        if packet.payload.opcode == pkt.arp.REQUEST:
	    log.debug("ARP request received")
	    arp_reply = pkt.arp()
	    arp_reply.hwsrc = adr.EthAddr("40:10:40:10:40:10") #fake MAC
	    arp_reply.hwdst = packet.payload.hwsrc
	    arp_reply.opcode = pkt.arp.REPLY
	    arp_reply.protosrc = packet.payload.protodst
	    arp_reply.protodst = packet.payload.protosrc
	    ether = pkt.ethernet()
	    ether.type = pkt.ethernet.ARP_TYPE
	    ether.dst = packet.src
	    ether.src = packet.dst
	    ether.payload = arp_reply

	    msg = of.ofp_packet_out()
    	    msg.data = ether.pack()

    	    # Add an action to send to the specified port
    	    action = of.ofp_action_output(port = packet_in.in_port)
    	    msg.actions.append(action)
	    #msg.in_port = event.port

	    # Send message to switch
    	    self.connection.send(msg)
	    log.debug("ARP reply sent")
	elif packet.payload.opcode == pkt.arp.REPLY:
	    log.debug ("It's a reply!" )
	    self.mac_to_port[packet.src] = packet_in.in_port
	else:
	    log.debug( "Some other ARP opcode" )

    elif packet.type == pkt.ethernet.IP_TYPE:
	ip_packet = packet.payload
	if ip_packet.protocol == pkt.ipv4.ICMP_PROTOCOL:
	    icmp_packet = ip_packet.payload
	    if icmp_packet.type == pkt.TYPE_ECHO_REQUEST:
		log.debug("ICMP request received")
		src_ip = ip_packet.srcip
		dst_ip = ip_packet.dstip
		k = 0
		for key in self.routing_table.keys():
		    if dst_ip.inNetwork(key):
			k = key
			break
		if k!=0:
                    log.debug("ICMP reply sent")
		    log.debug("network containing host: "+k)
		    ech = pkt.echo()
		    ech.seq = icmp_packet.payload.seq + 1
		    ech.id = icmp_packet.payload.id

		    icmp_reply = pkt.icmp()
		    icmp_reply.type = pkt.TYPE_ECHO_REPLY
		    icmp_reply.payload = ech
		    
		    ip_p = pkt.ipv4()
		    ip_p.srcip = dst_ip
		    ip_p.dstip = src_ip
		    ip_p.protocol = pkt.ipv4.ICMP_PROTOCOL
		    ip_p.payload = icmp_reply

		    eth_p = pkt.ethernet()
		    eth_p.type = pkt.ethernet.IP_TYPE
		    eth_p.dst = packet.src
		    eth_p.src = packet.dst
		    eth_p.payload = ip_p

		    msg = of.ofp_packet_out()
		    msg.data = eth_p.pack()

		    # Add an action to send to the specified port
    	    	    action = of.ofp_action_output(port = packet_in.in_port)
		    #fl2.actions.append(action)
    	    	    msg.actions.append(action)
	    	    #msg.in_port = event.port

    	    	    # Send message to switch
	    	    self.connection.send(msg)
		else:
                    log.debug("ICMP destination unreachable")
		    unr = pkt.unreach()
		    unr.payload = ip_packet

		    icmp_reply = pkt.icmp()
		    icmp_reply.type = pkt.TYPE_DEST_UNREACH
		    icmp_reply.payload = unr
		    
		    ip_p = pkt.ipv4()
		    ip_p.srcip = dst_ip
		    ip_p.dstip = src_ip
		    ip_p.protocol = pkt.ipv4.ICMP_PROTOCOL
		    ip_p.payload = icmp_reply

		    eth_p = pkt.ethernet()
		    eth_p.type = pkt.ethernet.IP_TYPE
		    eth_p.dst = packet.src
		    eth_p.src = packet.dst
		    eth_p.payload = ip_p

		    msg = of.ofp_packet_out()
		    msg.data = eth_p.pack()

		    # Add an action to send to the specified port
    	    	    action = of.ofp_action_output(port = packet_in.in_port)
		    #fl2.actions.append(action)
    	    	    msg.actions.append(action)
	    	    #msg.in_port = event.port

    	    	    # Send message to switch
	    	    self.connection.send(msg)
	else:
	    src_ip = ip_packet.srcip
	    dst_ip = ip_packet.dstip
	
	    k = 0
	    for key in self.routing_table.keys():
		if dst_ip.inNetwork(key):
		    k = key
		    break
	    if k != 0:
		port1 = self.routing_table[k][3]
		dsteth = adr.EthAddr(self.routing_table[k][4])

		msg = of.ofp_packet_out()

		action = of.ofp_action_output(port = port1)

		packet.src = packet.dst
		packet.dst = dsteth
		msg.data = packet.pack()
		msg.actions.append(action)
		self.connection.send(msg)
	self.FlowMode( packet_in, packet_in.in_port)			


  def _handle_PacketIn (self, event):
    """
    Handles packet in messages from the switch.
    """
    packet = event.parsed # This is the parsed packet data.
    if not packet.parsed:
      log.warning("Ignoring incomplete packet")
      return

    packet_in = event.ofp # The actual ofp_packet_in message.



    # Comment out the following line and uncomment the one after
    # when starting the exercise.
    #self.act_like_hub(packet, packet_in)
    #self.act_like_switch(packet, packet_in)
    self.act_like_router(packet, packet_in)



def launch ():
  """
  Starts the component
  """
  def start_switch (event):
    log.debug("Controlling %s" % (event.connection,))
    Tutorial(event.connection)
  core.openflow.addListenerByName("ConnectionUp", start_switch)
