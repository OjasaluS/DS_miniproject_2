import random
import sys
import socket
import threading
import json

DEBUG = False
class Process(threading.Thread):
    # STATES
    # 0 - NOT FAULTY
    # 1 - FAULTY
    #
    # ORDERS
    # 0 - RETREAT
    # 1 - ATTACK

    def __init__(self, id):
        super().__init__()
        self.id = id
        self.primary = 0
        self.state = 0
        self.order = None
        self.decisions = []
        self.localAddr = '127.0.0.1'
        self.proc_amount = None
        self.primary_id = None
        self.majority = None
        # Thread for listening for receiving messages
        self.listener = threading.Thread(target=self.message_listener)

    def orders(self, order):
        self.order = order
        # PRIMARY WILL CARRY OUT ORDERS
        while True:
            if self.primary and self.order is not None:
                # SEND THE ORDERS TO THE SECONDARYS
                for t in threads:
                    if t != self:
                        # FAULTY, 50/50 ATTACK OR RETREAT
                        if self.state:
                            self.order = random.choice([1,0])
                        message = {'type': 'order', 'msg': self.order, 'primary-id': self.id}
                        self.send_message(message, t.id)
                self.order = None

            if self.primary and self.proc_amount is not None and len(self.decisions) == self.proc_amount - 1:
                if self.decisions.count(1) == self.decisions.count(0):
                    self.decisions = []
                    self.majority = -1
                    return -1
                elif self.decisions.count(1) > self.decisions.count(0):
                    if self.decisions.count(-1) >= self.decisions.count(1):
                        self.majority = -1
                        return -1
                    self.decisions = []
                    self.majority = 1
                    return 1
                else:
                    if self.decisions.count(-1) >= self.decisions.count(0):
                        self.majority = -1
                        return -1
                    self.decisions = []
                    self.majority = 0
                    return 0

    def run(self):
        self.listener.setDaemon(True)
        self.listener.start()
        while True:
            # SECONDARYS WILL WAIT FOR ORDERS
            if self.primary == 0 and self.order is not None:
                # NOT FAULTY
                if self.state == 0:
                    for t in threads:
                        if t != self and t.primary == 0:
                            message = {'type': 'decision', 'msg': self.order}
                            self.send_message(message, t.id)
                # FAULTY
                if self.state == 1:
                    for t in threads:
                        if t != self and t.primary == 0:
                            message = {'type': 'decision', 'msg': random.choice([0,1])}
                            self.send_message(message, t.id)
                self.order = None

            # AFTER SENDING THE MESSAGES
            # IF SECONDARY HAS ALL THE DECISIONS
            if self.primary == 0 and self.proc_amount is not None and len(self.decisions) == self.proc_amount-1:
                if self.decisions.count(1) == self.decisions.count(0):
                    message = {'type': 'decision', 'msg': -1}
                    self.send_message(message, self.primary_id)
                    self.majority = -1

                # MORE ATTACKS THAN RETREATS
                elif self.decisions.count(1) > self.decisions.count(0):
                    self.majority = 1
                    # FAULTY
                    if self.state:
                        message = {'type': 'decision', 'msg': random.choice([0,1])}
                    else:
                        # NOT FAULTY
                        message = {'type': 'decision', 'msg': 1}
                    self.send_message(message, self.primary_id)

                # MORE RETREATS THAN ATTACKS
                else:
                    self.majority = 0
                    # FAULTY
                    if self.state:
                        message = {'type': 'decision', 'msg': random.choice([0,1])}
                    else:
                        # NOT FAULTY
                        message = {'type': 'decision', 'msg': 0}
                    self.send_message(message, self.primary_id)

                # EMPTY THE LIST
                self.decisions = []

    # A separate thread is going to listen for messages
    def message_listener(self):
        listen = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        listen.bind((self.localAddr, 5550+self.id))

        while True:
            # When we get a message, handle it
            message = listen.recv(4096)
            self.message_handler(message)

    def send_message(self, message, address):
        sending = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sending.connect((self.localAddr, 5550+address))
        encode_data = json.dumps(message, indent=2).encode('utf-8')
        sending.send(encode_data)
        sending.close()

    def message_handler(self, message):
        # Decode from bytes
        message = eval(message.decode("utf-8"))
        # Got an order from the primary
        if message['type'] == 'order':
            # Set the order of the primary and add the decision to decisions
            self.order = int(message['msg'])
            self.decisions.append(int(message['msg']))
            self.primary_id = int(message['primary-id'])
        # Decision from other secondary
        if message['type'] == 'decision':
            self.decisions.append(int(message['msg']))

# Start of methods for threads
def order(given_order):
    output = -1
    given_order = given_order.lower()
    available = ["retreat", "attack", "undefined"]
    faulty = 0
    if given_order in available:
        for t in threads:
            if t.state:
                faulty += 1

            if t.primary:
                # Run the algorithm
                output = t.orders(available.index(given_order))
    else:
        print("Wrong input")

    for t in threads:
        state = "NF" if t.state == 0 else "F"
        prim = "secondary" if t.primary == 0 else "primary"
        majority = ["retreat", "attack", "undefined"][t.majority]

        print(f'G{t.id}, {prim}, majority: {majority}, state={state}')

    if len(threads) <= 3*faulty:
        print(f'Execute order: cannot be determined – not enough generals in the system! {faulty} faulty node(s) in the system - {len(threads)-faulty} out of {len(threads)} quorum not consistent')
        return

    if output == -1:
        print(f'Execute order: cannot be determined - majority vote undefined!')

    else:
        if faulty == 0:
            strfaulty = f'Non-faulty nodes in the system - {len(threads)-1} out of {len(threads)} quorum suggests {available[output]}'
        else:
            strfaulty = f'{faulty} faulty node(s) in the system - {len(threads)-faulty-1} out of {len(threads)} quorum suggests {available[output]}'

        if output:
            strexecute = f'Execute order: attack! '
        elif not output:
            strexecute = f'Execute order: retreat! '

        print(strexecute + strfaulty)

def gstate():
    # g-state
    # utility method to list generals
    for t in threads:
        if t.state == 0:
            state = "NF"
        else:
            state = "F"
        if t.primary == 0:
            prim = "Secondary"
        else:
            prim = "Primary"
        print(f'G{t.id}, {prim}, State={state}')


def gstatechange(n, state):
    for t in threads:
        if t.id == n:
            if state.lower() == "faulty":
                t.state = 1
            elif state.lower() == "non-faulty":
                t.state = 0
            else:
                print("Wrong input")
    gstate()


# main program function
if __name__=='__main__':

    pid = 1
    threads = []

    if len(sys.argv) > 1:
        try:
            if int(sys.argv[1]) < 1:
                print("Input is smaller than 1")
                exit()
            for i in range(int(sys.argv[1])):
                t = Process(pid)
                threads.append(t)
                t.setDaemon(True)
                if pid == 1:
                    t.primary = 1
                else:
                    t.primary_id = 1
                pid += 1

            for t in threads:
                t.proc_amount = len(threads)
                t.start()


        except Exception as e:
            print(e)
            exit()
    else:
        print("No input provided")
        exit()

    print("Commands: actual-order attack/retreat, g-state, g-state n non-faulty/faulty, g-kill n, g-add n, exit ")

    # start the main loop
    running = True

    while running:
        inp = input().lower()
        cmd = inp.split(" ")

        command = cmd[0]

        if len(cmd) > 3:
            print("Too many arguments")

        # EXIT
        elif command == "exit":
            running = False

        # ACTUAL-ORDER
        elif command == "actual-order":
            try:
                order(cmd[1])
            except Exception as e:
                print(e)

        # G-STATE
        elif command == "g-state":
            if len(cmd) == 1:
                try:
                    gstate()
                except Exception as e:
                    print(e)
            else:
                try:
                    gstatechange(int(cmd[1]), cmd[2])
                except Exception as e:
                    print(e)

        # G-ADD
        elif command == "g-add":
            try:
                for i in range(int(cmd[1])):
                    t = Process(pid)
                    threads.append(t)
                    t.setDaemon(True)
                    pid += 1
                    t.start()
                for t in threads:
                    t.proc_amount = len(threads)
                gstate()
            except Exception as e:
                print(e)

        elif command == "g-kill":
            try:
                for t in threads:
                    if t.id == int(cmd[1]):
                        new = t.primary
                        threads.remove(t)
                        if new:
                            threads[0].primary = 1
                for t in threads:
                    t.proc_amount = len(threads)
                gstate()
            except Exception as e:
                print(e)

        else:
            print("Unsupported command:", inp)

    print("Program exited")