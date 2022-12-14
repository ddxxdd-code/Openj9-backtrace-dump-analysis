# !/usr/bin/python3

# Aggregate all allocations according to one compilation
# Automatically filter large compilations from performanc log
# Or manually specify certain compilations
# Dedong Xie 20220822
# Phase 1: implement walker and parser to retrive compilation + memory used in compilation
# Phase 2: implement aggregator of results

from collections import defaultdict
import sys
import argparse

# Parse performance verbose log line
# Return compilation_seq_num:str, compilation_system_memory:int, method_compiled:str, opt_level:str
def parse_performance_line(line):
    opt_level_start = line.find('(') + 1
    opt_level_end = line.find(')', opt_level_start)
    method_compiled_start = line.find(' ', opt_level_end) + 1
    method_compiled_end = line.find(' ', method_compiled_start)
    system_mem_start = line.find("system=", method_compiled_end) + len("system=")
    system_mem_end = line.find("]", system_mem_start)
    compilation_seq_num_start = line.find("CompSeqNum=", system_mem_end) + len("CompSeqNum=")
    compilation_seq_num_end = line.find("\n", compilation_seq_num_start)
    return line[compilation_seq_num_start:compilation_seq_num_end], int(line[system_mem_start:system_mem_end]), \
        line[method_compiled_start:method_compiled_end], line[opt_level_start:opt_level_end]
    
# Get list of compilation that uses more thsn threshold memory
def get_compilation_list(log_file, threshold, failed_only):
    compilations = []
    line = log_file.readline()
    while line:
        if (line[0] == '+' and not failed_only) or line[0] == '!':
            compilation_seq_num, compilation_system_memory, method_compiled, opt_level = parse_performance_line(line)
            if compilation_system_memory >= threshold:
                compilations.append([compilation_seq_num, method_compiled, opt_level, compilation_system_memory])
        line = log_file.readline()
    return compilations

# Get a dict of compilations_list : callsites_file
def get_associated_regions(callsites_file, compilations_list):
    associated_regions = defaultdict(list)
    # now to parse each region object
    line = callsites_file.readline()
    region_constructor_backtrace, allocation_list, allocation_backtrace = [], [], []
    in_region, in_region_header, in_allocation = False, False, False
    region_type, method_compiled, compilation_seq_num, region_start_time, region_end_time, \
    region_total_allocation_size, segment_provider_allocation_size, segment_provider_free_size, segment_provider_in_use_allocated, segment_provider_in_use_freed, \
    segment_provider_real_in_use_allocated, segment_provider_real_in_use_freed, segment_provider_start_usage, segment_provider_end_usage, allocation_size = \
    None, None, None, None, None, None, None, None, None, None, None, None, None, None, 0
    while line:
        if line[0] == 'H' or line[0] == 'S':
            # header of a region
            region_type, method_compiled, compilation_seq_num, region_start_time, region_end_time, \
            region_total_allocation_size, segment_provider_allocation_size, segment_provider_free_size, segment_provider_in_use_allocated, segment_provider_in_use_freed, \
                segment_provider_real_in_use_allocated, segment_provider_real_in_use_freed, segment_provider_start_usage, segment_provider_end_usage = line[:-1].split()
            if compilation_seq_num in compilations_list:
                in_region, in_region_header = True, True
        elif in_region and line[0] == '/':
            # Backtrace lines
            if in_region_header:
                region_constructor_backtrace.append(line)
            elif in_allocation:
                allocation_backtrace.append(line)
        elif in_region and line[0] == 'A':
            # Header line for an allocation
            if allocation_backtrace != [] and allocation_size != 0:
                allocation_list.append([allocation_size, allocation_backtrace])
                allocation_backtrace = []
            in_region_header, in_allocation = False, True
            allocation_size = int((line.split())[1])
        elif in_region and line[0] == "=":
            # End of a target region
            if allocation_backtrace != [] and allocation_size != 0:
                allocation_list.append([allocation_size, allocation_backtrace])
            associated_regions[compilation_seq_num].append(
                [region_total_allocation_size, region_type, region_start_time, region_end_time, \
                    segment_provider_allocation_size, segment_provider_free_size, segment_provider_in_use_allocated, segment_provider_in_use_freed, \
                        segment_provider_real_in_use_allocated, segment_provider_real_in_use_freed, segment_provider_start_usage, segment_provider_end_usage, \
                            region_constructor_backtrace, allocation_list])
            # reinitialize everything
            region_constructor_backtrace, allocation_list, allocation_backtrace = [], [], []
            in_region, in_region_header, in_allocation = False, False, False
            allocation_size = 0
        line = callsites_file.readline()
    return associated_regions

# write output from list of regions to output
def write_output(output_file, compilation_regions):
    for total_allocated_bytes, region_type, region_start_time, region_end_time, segment_provider_allocation_size, segment_provider_free_size, \
        segment_provider_in_use_allocated, segment_provider_in_use_freed, segment_provider_real_in_use_allocated, segment_provider_real_in_use_freed, \
            segment_provider_start_usage, segment_provider_end_usage, region_constructor, allocations in compilation_regions:
        output_file.write(f"{region_type} {total_allocated_bytes} {region_start_time} {region_end_time} {segment_provider_allocation_size} {segment_provider_free_size} {segment_provider_in_use_allocated} {segment_provider_in_use_freed} {segment_provider_real_in_use_allocated} {segment_provider_real_in_use_freed} {segment_provider_start_usage} {segment_provider_end_usage}\n")


def main():
    parser = argparse.ArgumentParser()
    # Required arguments:
    parser.add_argument("region_callsites_file", type=str, help="file of translated call sites in regions")
    parser.add_argument("performance_log_file", type=str, help="file of the performance log dump")
    # Optional arguments
    parser.add_argument("-t", "--threshold", type=int, default=20000, help="threshold of memory usage for a compilation to be collected")
    # parser.add_argument("-c", "--compilation", type=str, nargs='+', help="only collect specified compilations of listed compilation sequence number")
    parser.add_argument("-o", "--output-file", type=str, default=".txt", help="name of the output file, default to <compilation sequence number>.txt")
    parser.add_argument("-f", "--failed-only", action="store_true", help="set to collect failed compilations only")
    parser.add_argument("-v", "--verbose", action="store_true", help="set to run in verbose mode")

    args = parser.parse_args()

    if args.verbose: 
        sys.stderr.write(f"Reading from {args.performance_log_file} for compilations use at least {args.threshold}KB of memory\n")
        if args.failed_only: sys.stderr.write("Collect failed compilations only\n")
    with open(args.performance_log_file, "r") as vlog:
        compilation_list = get_compilation_list(vlog, args.threshold, args.failed_only)
        compilation_seq_num_list = [compilation[0] for compilation in compilation_list]
    if args.verbose: sys.stderr.write(f"list of compilations captured: \n" + " ".join(compilation_seq_num_list) + f"\ntotal of {len(compilation_seq_num_list)}compilations\n")

    if args.verbose: 
        sys.stderr.write(f"Reading from {args.region_callsites_file}\n\t Aggregating " + " ".join(compilation_seq_num_list) + " compilations\n")
    with open(args.region_callsites_file, "r") as callsites:
        aggregated_regions_dict = get_associated_regions(callsites, compilation_seq_num_list)

    if args.verbose: sys.stderr.write(f"Sorting regions in decreasing order of total allocated bytes\n")
    for key in aggregated_regions_dict:
        aggregated_regions_dict[key].sort(reverse=True, key=lambda region: int(region[0]))

    if args.verbose: sys.stderr.write(f"Writing results to <compilation_seq_num>_{args.output_file}\n")
    for compilation in compilation_list:
        if aggregated_regions_dict[compilation[0]] != []:
            with open(compilation[0] + '_' + args.output_file, "w") as output:
                write_output(output, aggregated_regions_dict[compilation[0]])
    if args.verbose: sys.stderr.write(f"Program finished\n")

if __name__ == "__main__":
    main()