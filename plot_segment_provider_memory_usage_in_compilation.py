import argparse
import matplotlib.pyplot as plt

def getSequence(regions, length):
    diff = [0] * length
    for start, end, alloc, free in regions:
        if end == -1:
            end = length - 1
        diff[start] += alloc
        diff[end] -= free
    val = 0
    result = []
    for i in diff:
        val += i
        result.append(val)
    return result

# Assume input file consists of lines of size, start, end
def main():
    parser = argparse.ArgumentParser()
    # Required arguments:
    parser.add_argument("input_file", type=str, help="file of timestamps of regions")
    # Optional arguments
    parser.add_argument("-d", "--data", type=int, default=1, help="plot the nth data 1: bytesAllocated 2: regionBytesInUse 3: regionRealBytesInUse")
    parser.add_argument("-v", "--verbose", action="store_true", help="set to run in verbose mode")

    args = parser.parse_args()

    compilation_seq_num = args.input_file[:args.input_file.find('_')]

    heap_regions = []
    stack_regions = []
    with open(args.input_file, "r") as input:
        line = input.readline()
        while line:
            if args.data == 1: region_type, _, start, end, alloc, free, _, _, _, _ = line.split()
            elif args.data == 2: region_type, _, start, end, _, _, alloc, free, _, _ = line.split()
            elif args.data == 3: region_type, _, start, end, _, _, _, _, alloc, free = line.split()
            if region_type[0] == 'H':
                heap_regions.append([int(start), int(end), int(alloc)/1024**2, int(free)/1024**2])
            elif region_type[0] == 'S':
                stack_regions.append([int(start), int(end), int(alloc)/1024**2, int(free)/1024**2])
            line = input.readline()
    heap_regions_max_start_times = max(list(map(lambda x: x[0], heap_regions)))
    heap_regions_max_end_times = max(list(map(lambda x: x[1], heap_regions)))
    stack_regions_max_start_times = max(list(map(lambda x: x[0], stack_regions)))
    stack_regions_max_end_times = max(list(map(lambda x: x[1], stack_regions)))
    length = max(heap_regions_max_start_times, heap_regions_max_end_times, stack_regions_max_start_times, stack_regions_max_end_times) + 1
    heap_regions_time_series = getSequence(heap_regions, length)
    stack_regions_time_series = getSequence(stack_regions, length)
    x = range(0, length)
    plt.figure(figsize=(10,5))
    plt.stackplot(x, heap_regions_time_series, stack_regions_time_series, labels=["Heap", "Stack"])
    plt.legend(loc='upper left')
    if args.data == 1: plt.title(f"Execution logical time sequence of allocated bytes in compilation {compilation_seq_num}")
    elif args.data == 2: plt.title(f"Execution logical time sequence of bytes in use in compilation {compilation_seq_num}")
    elif args.data == 3: plt.title(f"Execution logical time sequence of real bytes in use in compilation {compilation_seq_num}")
    plt.ylabel("Memory allocated (MB)")
    plt.xlabel("Logical time")
    plt.show()


if __name__ == "__main__":
    main()
