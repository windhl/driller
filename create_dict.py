#!/usr/bin/env python

import sys
import angr
import string
import signal
import logging
import resource
import driller.config as config

l = logging.getLogger("driller.create_dict")

def hexescape(s):
    ''' 
    perform hex escaping on a raw string s
    '''

    out = [ ] 
    acceptable = string.letters + string.digits + " ."
    for c in s:
        if c not in acceptable:
            out.append("\\x%02x" % ord(c))
        else:
            out.append(c)

    return ''.join(out)

def create(binary, outfile):

        b = angr.Project(binary)
        cfg = b.analyses.CFG(keep_input_state=True, enable_advanced_backward_slicing=True)

        string_references = [ ] 
        for f in cfg.function_manager.functions.values():
            try:
                string_references.append(f.string_references())
            except ZeroDivisionError:
                pass

        string_references = sum(string_references, []) 

        strings = [] if len(string_references) == 0 else zip(*string_references)[1]

        valid_strings = filter(lambda s: len(s) <= 128 and len(s) > 0, strings)
        if len(valid_strings) > 0:
            with open(outfile, 'wb') as f:
                for i, string in enumerate(valid_strings):
                    # AFL has a limit of 128 bytes per dictionary entries
                    if len(string) <= 128:
                        s = hexescape(string)
                        f.write("driller_%d=\"%s\"\n" % (i, s)) 

            return True

        return False

def main(argv):

    if len(argv) < 3:
        l.error("incorrect number of arguments passed to create_dict")
        return 1

    binary  = argv[1]
    outfile = argv[2]

    # limit memory to avoid killing a worker node
    if config.MEM_LIMIT is not None:
        resource.setrlimit(resource.RLIMIT_AS, 
                           (config.MEM_LIMIT, config.MEM_LIMIT))

    # place a timeout so we always get some time to fuzz, even if we encounter
    # an infinite loop CFG bug
    if config.DICTIONARY_TIMEOUT is not None:
        signal.alarm(config.DICTIONARY_TIMEOUT)

    return int(not create(binary, outfile))

if __name__ == "__main__":
    sys.exit(main(sys.argv))
