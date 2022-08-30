# !/usr/bin/python3

# Analyzing tool for dumped back traces of reion allocations
# Dedong Xie 20220815
# Phase 1: implement translation DONE 0815 Reduce reading overhead 0816
# Phase 2: implement call site find DONE 0817
# phase 3: implement parser of options DONE 0817

import subprocess
import sys
import argparse

skip_list = ["allocate", "TypedAllocator", "heap_allocator"]
catch_list = ["TR_LoopVersioner::emitExpr", 
"RematTools::walkTreesCalculatingRematSafety", 
"J9::Compilation::verifyCompressedRefsAnchors", 
"TR_UseDefInfo::dereferenceDef", 
"TR_GlobalRegisterAllocator::findLoopsAndCorrespondingAutos",
"TR_GlobalRegisterAllocator::markAutosUsedIn"]

def skip_line(line):
    for seg in skip_list:
        if line.find(seg) != -1:
            return True
    return False

def catch_line(line):
    for seg in catch_list:
        if line.find(seg) != -1:
            return True
    return False

def get_callsite(backtrace_list, allocation_site_only):
    trimmed = backtrace_list
    for i in range(1, len(backtrace_list)):
        if (backtrace_list[i][1].find("/omr/") != -1 or backtrace_list[i][1].find("/openj9/") != -1) \
            and (catch_line(backtrace_list[i][0]) or not skip_line(backtrace_list[i][0])):
            trimmed = [backtrace_list[i]] if allocation_site_only else backtrace_list[:i+1]
            if i < len(backtrace_list) - 2:
                trimmed.append(["", backtrace_list[i+1][1]])
            return trimmed
    return trimmed

# From list of offsets, build dict to translate from offset to lines
def build_translation_table(executable_file_path, offset_list, offset_translation_dict):
    args = ["addr2line", "-e", executable_file_path, "-f", "-C"]
    args += offset_list
    output = subprocess.run(args, stdout=subprocess.PIPE, universal_newlines=True).stdout
    output = output.splitlines()
    if len(output) != 2 * len(offset_list):
        sys.stderr.write("Translation error\n")
        return {}
    for i in range(len(offset_list)):
        line = output[2*i+1]
        if "/openj9/" in line:
            line = line[line.find("/openj9/"):]
        if "/omr/" in line:
            line = line[line.find("/omr/"):]
        offset_translation_dict[offset_list[i]] = [output[2*i], line]
    return offset_translation_dict

# Read from formatted lines produce list of all offsets of interest
def read_offsets(file):
    offset_set = set()
    line = file.readline()
    while line:
        if line[0].isalpha():
            # Start of header for a region
            line = file.readline()
            constructor_offsets = (line.split())[1:-1]
            offset_set |= set(constructor_offsets)
        else:
            # Allocations in a region
            allocation_stack_traces = (line.split())[1:-1]
            offset_set |= set(allocation_stack_traces)
        line = file.readline()
    return list(offset_set)

# Parse input file and write translated callsites to output file
def write_translated_callsites(input_file, offset_translation_dict, output_file, translate_only, allocation_site_only):
    allocation_list = []
    constructor_stack_trace = []
    region_type, method_compiled = "", ""
    line = input_file.readline()
    while line:
        if line[0].isalpha():
            if allocation_list != []:
                # print header
                output_file.write(region_type + ": " + method_compiled)
                for function, line_of_call in constructor_stack_trace:
                    output_file.write(line_of_call[:-1] + "; " + function + '\n')
                # print allocations
                allocation_list.sort(reverse=True, key=lambda x: x[0])
                for allocation_size, allocation_stack_trace_list in allocation_list:
                    output_file.write("Allocated " + str(allocation_size) + " bytes\n")
                    for function, line_of_call in allocation_stack_trace_list:
                        output_file.write(line_of_call[:-1] + "; " + function + '\n')
                output_file.write("=== End of a region ===\n")
                allocation_list = []
                constructor_stack_trace = []
                region_type, method_compiled = "", ""
            # Start of header for a region
            method_compiled = line
            line = input_file.readline()
            if line[0] == '0':
                region_type = 'S'
            else:
                region_type = 'H'
            constructor_stack_trace_offsets = (line.split())[1:-1]
            for offset in constructor_stack_trace_offsets:
                constructor_stack_trace.append(offset_translation_dict[offset])
        else:
            # Allocations in a region
            allocation = (line.split())[:-1]
            allocation_size = int(allocation[0])
            allocation_stack_traces = allocation[1:]
            allocation_stack_trace_list = []
            for offset in allocation_stack_traces:
                # Here, offset_translation_dict's value is a pair of function name and line
                # We assume offset is a key in the dict
                allocation_stack_trace_list.append(offset_translation_dict[offset])
            # Find callsite from translated call back traces
            if not translate_only: allocation_stack_trace_list = get_callsite(allocation_stack_trace_list, allocation_site_only)
            allocation_list.append([allocation_size, allocation_stack_trace_list])
        line = input_file.readline()
    if allocation_list != []:
        # print header
        output_file.write(region_type + ": " + method_compiled)
        for function, line in constructor_stack_trace:
            output_file.write(line[:-1] + "; " + function + '\n')
        # print allocations
        allocation_list.sort(reverse=True, key=lambda x: x[0])
        for allocation_size, allocation_stack_trace_list in allocation_list:
            output_file.write("Allocated " + str(allocation_size) + " bytes\n")
            for function, line in allocation_stack_trace_list:
                output_file.write(line[:-1] + "; " + function + '\n')
        output_file.write("=== End of a region ===\n")

def main():
    parser = argparse.ArgumentParser()
    # Required arguments:
    parser.add_argument("input_file", type=str, help="name of the input file")
    parser.add_argument("executable_file_path", type=str, help="path to target executable file in the form /DIR/file.so")
    # Optional arguments
    parser.add_argument("-b", "--batch-size", type=int, default=10000, help="integer for batch size of input to addr2line")
    parser.add_argument("-c", "--callsite-only", action="store_true", help="set to only keep the line of callsite in all back traces")
    parser.add_argument("-o", "--output-file", type=str, help="name of the output file, default to <input_file>_translated_callsites.txt")
    parser.add_argument("-t", "--translation-only", action="store_true", help="set to only translates offsets do no call site find")
    parser.add_argument("-v", "--verbose", action="store_true", help="set to run in verbose mode")

    args = parser.parse_args()

    if args.verbose: sys.stderr.write("reading from " + args.input_file + "\n")
    with open(args.input_file, "r") as input:
        offset_list = read_offsets(input)

    if args.verbose:
        sys.stderr.write("Total offsets: " + str(len(offset_list)) + "\n")

    offset_translation_dict = {}
    i = 0
    step = args.batch_size
    for i in range(0, len(offset_list), step):
        if args.verbose: sys.stderr.write("translating " + str(i) + " to " + str(i+step) + " of all offsets\n")
        offset_translation_dict = build_translation_table(args.executable_file_path, offset_list[i:i+step], offset_translation_dict)
    
    output_file = args.output_file if args.output_file else args.input_file[:args.input_file.find('.')]+"_translated_callsites.txt"
    if args.verbose: sys.stderr.write("writing to output file " + output_file + "\n")
    with open(args.input_file, "r") as input:
        with open(output_file, "w") as output:
            write_translated_callsites(input, offset_translation_dict, output, args.translation_only, args.callsite_only)
    if args.verbose: sys.stderr.write("finished writing to file " + output_file + "\nprogram finished\n")

if __name__ == "__main__":
    main()