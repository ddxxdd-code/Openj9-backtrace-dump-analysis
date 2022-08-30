# Plot the timeline of regions' usage of memory using matplotlib
# Created by Dedong Xie on 2022-08-24
import argparse
import matplotlib.pyplot as plt

def getSequence(regions, length):
    diff = [0] * length
    for size, start, end in regions:
        if end == -1:
            end = length - 1
        diff[start] += size
        diff[end] -= size
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
    parser.add_argument("-v", "--verbose", action="store_true", help="set to run in verbose mode")

    args = parser.parse_args()

    compilation_seq_num = args.input_file[:args.input_file.find('_')]

    heap_regions = []
    stack_regions = []
    with open(args.input_file, "r") as input:
        line = input.readline()
        while line:
            region_type, size, start, end = line.split()
            if region_type[0] == 'H':
                heap_regions.append([int(size)/1024**2, int(start), int(end)])
            elif region_type[0] == 'S':
                stack_regions.append([int(size)/1024**2, int(start), int(end)])
            line = input.readline()
    heap_regions_max_start_times = max(list(map(lambda x: x[1], heap_regions)))
    heap_regions_max_end_times = max(list(map(lambda x: x[2], heap_regions)))
    stack_regions_max_start_times = max(list(map(lambda x: x[1], stack_regions)))
    stack_regions_max_end_times = max(list(map(lambda x: x[2], stack_regions)))
    length = max(heap_regions_max_start_times, heap_regions_max_end_times, stack_regions_max_start_times, stack_regions_max_end_times) + 1
    heap_regions_time_series = getSequence(heap_regions, length)
    stack_regions_time_series = getSequence(stack_regions, length)
    x = range(0, length)
    plt.figure(figsize=(10,5))
    plt.stackplot(x, heap_regions_time_series, stack_regions_time_series, labels=["Heap", "Stack"])
    plt.legend(loc='upper left')
    plt.title(f"Execution logical time sequence of memory usage in compilation {compilation_seq_num}")
    plt.ylabel("Memory allocated (MB)")
    plt.xlabel("Logical time")
    plt.show()


if __name__ == "__main__":
    main()
