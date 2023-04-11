#!/usr/bin/python
# -*- coding: utf8 -*-

import sys
import select
import socket
import datetime 
from threading import Timer

RECV_BUFFSIZE = 1024 

class Config:
    """
    Config object initialised with argument string that is the string representation
    of the config filepath for <obj> as initialised object name and <param> as the paramter in correct format
    each parameter's value can be accessed by <obj>.params["<param>"] and will give
    a list of string representation of the value/s
    
    """
    def __init__(self, path):
        """
        <path> : string representation of config location
        <params> : dict of key: parameter and value: value, all values are init as None
        <req_params> : set of strings of expected REQUIRED paramters in config file
        """
        self.path = path
        self.params = {
            'router-id':None,
            'input-ports':None,
            'outputs':None,
            'timers':None
        }
        self.__req_params = {'router-id', 'input-ports', 'outputs'}
        
    def __str__(self):
        return """Config path: {0}\nParamters: 
             router-id: {1}
             input-ports: {2}
             outputs: {3}
             timers: {4}""".format(self.path, self.params['router-id'],
                                                       self.params['input-ports'],
                                                       self.params['outputs'],
                                                       self.params['timers'],)
        
    def __isPortValid(self, port):
        """Checks if port is in range of 1024 <= port <= 64000
        returns True if in range and False otherwise"""
        return False if port < 1024 or port > 64000 else True
   
    def __isRouterIdValid(self, routerId):
        """Checks routerId is in range of 1 <= routerId <= 64000
        returns True if in range and False otherwise"""       
        return False if routerId < 1 or routerId > 64000 else True
        
    def unpack(self):
        """
        Function to unpack config parameters and stores them in their representative variables
        DOES NOT return anything. The values are stored as attributes of this class
        """
        config_file = open(self.path, "r")
        config = config_file.read().split('\n')
        config_file.close()
         
        for line in config:
            
            #checks if line is even worth further parsing ie. is a parameter line
            if line.split(' ', 1)[0] in self.params:
                
                try:
                    #parses the line, param is a string and value is a list of strings
                    param = line.split(' ', 1)[0]
                    value = line.split(' ', 1)[1].replace(' ', '').split(',')
                    
                    #error handles
                    if not value:
                        #no value
                        raise IndexError
                    
                    if param == "router-id":
                        if not self.__isRouterIdValid(int(value[0])):
                            #router-id is out of range
                            raise ValueError
                    
                    elif param == "input-ports":
                        for port in value:
                            if not self.__isPortValid(int(port)):
                                #input-ports is out of range
                                raise ValueError
                            
                    elif param == "outputs":
                        for output in value:
                            parsed = output.split("-")
                            if not self.__isRouterIdValid(int(parsed[2])):
                                #output router id is out of range
                                raise ValueError
                            if not self.__isPortValid(int(parsed[0])):
                                #output port is out of range
                                raise ValueError
                    
                    
                    #inserts the value in config file as the value for params dict for given key: param
                    self.params[param] = value
                    
                except(IndexError):
                    print("PARAMETER <{}> MISSING VALUES. PLEASE CHECK CONFIG".format(param))
                    sys.exit(1)
                except(ValueError):
                    print("PARAMETER <{}> INVALID VALUE. PLEASE CHECK CONFIG".format(param))
                    sys.exit(1)
                except:
                    #Uncatched error. Debug code if you see this prompted!!!
                    print("--FATAL INTERNAL ERROR--")
                    sys.exit(1)
                    
        #checks for missing required parameters by finding if any of the required fields are still None
        for param in self.params:
            if self.params[param] == None and param in self.__req_params:
                raise TypeError("PARAMETER <{}> MISSING. PLEASE CHECK CONFIG".format(param))    
        
class Router:
    """For this router to have its own information based on config file"""
    def __init__(self,  rtrId, inputs, outputs):
        
        self.rtr_id = rtrId # of type int
        self.inputs = [input_port for input_port in inputs] #list
        self.output = self.decompose_output(outputs) #list
        self.outputs = self.output[0] #list
        self.metrics = self.output[1] #list
        self.peer_rtr_id = self.output[2] #list
        
    
    def decompose_output(self, outputs):
        """split output format by '-' and sort by each item into list
        # output format [peer's_input_port - metric(link cost) - peer's router id (peer's_input_port is equal to current router's output_port)]"""
        #split output by '-'
        split_output = [outputs[i].split('-') for i in range(len(outputs))] 
        #return [ports, metrics, peer_rtr_ids]
        return [[int(split_output[0][i]), int(split_output[1][i]), int(split_output[2][i])] for i in range(len(split_output))]


class RoutingTable:
    """ Temp skeleton of routing table entry """
    def __init__(self, Router, contents, new_entry, received_from):

        
        self.router = Router
        self.contents = contents
        self.new_entry = new_entry
        self.table = self.update_entry(new_entry, received_from)
 
    
    def update_entry(self, given_entry, receive_from):
        entry = self.contents + given_entry
        if self.router == None:
            return self.contents
        else :
            dest = []
            final_content = []
            link_cost = self.router.metrics[self.router.peer_rtr_id.index(receive_from)]
            for i in range(len(entry)):
                if (entry[i]['dest-rtr'] in self.router.peer_rtr_id) and (entry[i]['dest-rtr'] not in dest) :
                    dest.append(entry[i]['dest-rtr'])
                    final_content.append(entry[i])

                if (entry[i]['dest-rtr'] not in dest) and (entry[i]['dest-rtr'] != self.Router.rtr_id) :
                    dest.append(entry[i]['dest-rtr'])
                    entry[i]['input'] = self.router.inputs[self.router.peer_rtr_id.index(receive_from)]
                    entry[i]['output'] = self.router.outputs[self.router.peer_rtr_id.index(receive_from)]
                    entry[i]['metric'] += link_cost 
                    final_content.append(entry[i])

                if entry[i]['dest-rtr'] in dest:
                    #print(f"compare {entry[i]['metric']} and {final_content[dest.index(entry[i]['dest-rtr'])]['metric']}")
                    if (entry[i]['metric'] + link_cost) < final_content[dest.index(entry[i]['dest-rtr'])]['metric']:
                        final_content.remove(final_content[dest.index(entry[i]['dest-rtr'])])
                        dest.remove(dest[dest.index(entry[i]['dest-rtr'])])
                        entry[i]['input'] = self.router.inputs[self.router.peer_rtr_id.index(receive_from)]
                        entry[i]['output'] = self.router.outputs[self.router.peer_rtr_id.index(receive_from)]
                        entry[i]['metric'] += link_cost 
                        final_content.append(entry[i])
                        dest.append(entry[i]['dest-rtr'])
                    else :
                        pass
            self.contents = final_content
            #print("final contents ? ", self.contents)
            print(self.__str__())
            return final_content


class Demon:
    def __init__(self, Router):
        """Initialize Demon with input ports for creating UDP sockets 
        <socket_list> : list of binded sockets indexed in its corresponding input port
        """
        #there are some self.xx variables that can be removed and replaced to Router.xx
        #Planning to cleaner variables when clean up codes in Demon
        self.router = Router
        self.cur_table = self.generate_table_entry([self.router.peer_rtr_id, self.router.inputs, self.router.outputs, self.router.metrics], self.router.rtr_id)  #need to be dictionarys in list
        self.socket_list = self.create_socket()
        self.response_pkt = None
        self.packet_exchange()

    def create_socket(self):
        """Creating UDP sockets and to bind one with each of input_port"""
        input_port_addr = [('', int(input_port)) for input_port in self.router.inputs]
        socket_list = []
        for i in range(len(input_port_addr)):
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            sock.bind(input_port_addr[i])
            socket_list.append(sock)
        return socket_list

    def display_table(self, contents):
        display = f"\nRouting table of router {self.router.rtr_id}--------------------------------------+\n"
        for i in range(len(contents)):
            display += "|destRtrId: {0}  |  port: {1} (next-hop : {2})  |  Metric : {3}  |\n".format(contents[i]['dest'],
                                                                                         contents[i]['input'],
                                                                                         contents[i]['output'],
                                                                                         contents[i]['metric']
                                                                                         )
        display += '+--------------------------------------------------------------+\n'
        return display
        
    def generate_table_entry(self, entry, receive_from):
       content = []
       dest, inputs, outputs, metrics = entry[0], entry[1], entry[2], entry[3]
       for i in range(len(entry[0])):
           content.append({'self.router-id' : receive_from, 
                             'dest' : dest[i], 
                             'input' : inputs[i], 
                             'output' : outputs[i], 
                             'metric' : metrics[i]})
       if receive_from == self.router.rtr_id:
           print(self.display_table(content))
       return content

    def rip_response_packet(self, rip_entry):
        """
        #   RIP PACKET FORMAT
        #+--------------------------------------------------------------+
        #|  command(1 byte) + version (1 byte) +   must_be_zero(2bytes) |
        #|--------------------------------------------------------------|
        #|       rip entry(20 bytes) * the number of rip entry          |
        #+--------------------------------------------------------------+
        #The number of rip entry can be up to 25(including) 
        #rip entry will be received as an bytearray from compose_rip_entry() 
        #and is added to the end of rip packet.
        """
        #components of common header
        command, version, must_be_zero_as_rtr_id = 2, 2, self.router.rtr_id
   
        #create bytearray for response_packet
        resp_pkt = bytearray()

        #adding common header into response_packet(bytearray)
        resp_pkt += command.to_bytes(1, 'big')
        resp_pkt += version.to_bytes(1, 'big')
        resp_pkt += must_be_zero_as_rtr_id.to_bytes(2,'big')
        #adding rip entry into response_packet(bytearray)
        resp_pkt += rip_entry
        return resp_pkt

    def compose_rip_entry(self, dest_id, metrics):
        """
        #   RIP ENTRY FORMAT
        #+--------------------------------------------------------------+
        #|  address family identifier(2 bytes) + must be zero (2 bytes) |
        #|                   IPv4 address (4 bytes)                     |
        #|                   must be zero (4 bytes)                     |
        #|                   must be zero (4 bytes)                     |
        #|                       metric(4 bytes)                        |
        #+--------------------------------------------------------------+
        #The number of rip entry can be up to 25(including)
        """
        rip_entry = bytearray()
        afi = 0 #afi = address family identifier
        must_be_zero = 0
        
        for i in range(len(dest_id)): #the item in range() will be replaced by lists of list entry contents
            #first 32 bits of rip entry
            rip_entry += afi.to_bytes(2, 'big')
            rip_entry += must_be_zero.to_bytes(2, 'big')
            # second to fifth of rip entry
            rip_entry += dest_id[i].to_bytes(4, 'big')
            rip_entry += must_be_zero.to_bytes(4, 'big')
            rip_entry += must_be_zero.to_bytes(4, 'big')
            rip_entry += metrics[i].to_bytes(4, 'big')
        return rip_entry
   
    def send_packet(self):
        #Triggered update and randomization of regular update need to be implemented
        #This timer below is regular update happening at the same time (For checking purpose). ->need to be modified
        Timer(7, self.send_packet).start()
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sending_socket:
                for i in range(len(self.router.output)):
                    sending_socket.connect(('127.0.0.1', self.router.outputs[i]))
                    customized_packet = self.split_horizon(self.router.outputs[i]) #customized_packet for each output
                    sending_socket.sendto(customized_packet, ('127.0.0.1', self.router.outputs[i])) 
                print(f"sending response packet ...... ")#:{self.response_pkt.hex()}")

    def split_horizon(self, port):
        routingTable = self.cur_table #need to be dictionarys in list
        output = []
        dest = []
        metric = []
        for i in range(len(routingTable)):
            if routingTable[i]['output'] != port:
                output.append(routingTable[i]['output'])
                dest.append(routingTable[i]['dest'])
                metric.append(routingTable[i]['metric'])

        customized_packet = self.rip_response_packet(self.compose_rip_entry(dest, metric))
        return customized_packet
    
    def is_packet_valid(self, packet):
        """"For packet validity check"""
        # Not implemented yet
        return packet

    

    def unpack_received_packet(self, received_pkt, receive_from):
        #received_from the the peer router id
        inputs = []
        outputs = [] 
        metrics = [] # link cost
        dest_ids = [] # destination self.router
        
        for i in range((len(received_pkt)-4)// 20):
            inputs.append(self.router.inputs[self.router.peer_rtr_id.index(receive_from)])
            outputs.append(self.router.outputs[self.router.peer_rtr_id.index(receive_from)])
            metrics.append(int.from_bytes(received_pkt[(20+20*i):(24+20*i)], "big"))
            dest_ids.append(int.from_bytes(received_pkt[(8+20*i):(12+20*i)], "big"))

        contents = [dest_ids, inputs, outputs, metrics]
        return self.generate_table_entry(contents, receive_from)


    def receive_packet(self):
        while True:
            read_socket_lis, _, _ = select.select(self.socket_list, [], [])
            for read_socket in read_socket_lis:
                for i in range(len(self.router.inputs)):
                    if read_socket == self.socket_list[i]:
                        print(f'\nReceived packet from router id : {self.router.peer_rtr_id[i]}')
                        resp_pkt, port = self.socket_list[i].recvfrom(RECV_BUFFSIZE)
                        #print("  Received response_pkt : ") #, resp_pkt.hex())
                        if self.is_packet_valid(resp_pkt):
                            self.response_pkt = resp_pkt
                            #for checking what entries I received
                            for j in range((len(self.response_pkt)-4)// 20):
                                print("----Received entries [destRtr : {0}, next-hop : {1}, metric : {2}]\n".format( int.from_bytes(self.response_pkt[(8+20*j):(12+20*j)], "big"),
                                self.router.outputs[i], int.from_bytes(self.response_pkt[(20+20*j):(24+20*i)], "big")))
                                receive_from = int.from_bytes(self.response_pkt[2:4], "big")
                                self.unpack_received_packet(self.response_pkt, receive_from) 
                            

    def packet_exchange(self):
        try:
            while True:
                
                self.send_packet()
                self.receive_packet()
                
                raise KeyboardInterrupt

        except KeyboardInterrupt:
            print('Keyboard Interrupted!')
        sys.exit(1)

                


                        
       

def main():
    config = Config(sys.argv[1])
    config.unpack()
    print(config)
    
    router = Router(int(config.params['router-id'][0]), config.params['input-ports'], config.params['outputs'])
    rip_routing = Demon(router)



if __name__ == "__main__":
    main()