from reactors.utils import Reactor, agaveutils
import copy
import sys
import json
import os




def main():
    """Main function"""
    # create the reactor object
    r = Reactor()
    r.logger.info("Hello this is actor {}".format(r.uid))
    # pull in reactor context
    context = r.context
    #print(context)
    # get the message that was sent to the actor
    message = context.message_dict
    #site = message['site']
    print(message)


if __name__ == '__main__':
    main()
