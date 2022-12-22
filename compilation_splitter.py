# Split raw alloctraces to seperate files named by <compilation sequence number>_<memory_usage>.txt
# Dedong Xie 2022-12-22
import sys
import argparse

def split(input_file, output_directory, verbose):
    if output_directory[-1] != '/': output_directory += '/' # Makesure output directory is ended with /
    if verbose: sys.stderr.write("reading from " + input_file + "\n")
    output_file = 0
    with open(input_file, "r") as input:
        line = input.readline()
        while line:
            if line[0:11] == "Compilation":
                if output_file:
                    output_file.close()
                # This is a compilation header line
                # parse compilation number
                seq_num_start = line.find(' ')
                seq_num_end = line.find(',', seq_num_start)
                compilation_num = line[seq_num_start+1:seq_num_end]
                size_start = line.find(':', seq_num_end)
                total_memory_usage = line[size_start+2:-1]
                output_filename = output_directory + compilation_num + '_' + total_memory_usage + ".txt"
                output_file = open(output_filename, "w+")
                if verbose: sys.stderr.write("writing compilation " + compilation_num + " memory used: " + total_memory_usage + "B to file " + output_filename + "\n")
            else:
                output_file.write(line)
            line = input.readline()
    if output_file:
        output_file.close()

    if verbose: sys.stderr.write("finished writing to directory " + output_directory + "\nprogram finished\n")


def main():
    parser = argparse.ArgumentParser()
    # Required arguments:
    parser.add_argument("input_file", type=str, help="name of the input file")
    parser.add_argument("out_directory", type=str, default="./", help="name of the output directory, default to current directory")
    parser.add_argument("-v", "--verbose", action="store_true", help="set to run in verbose mode")

    args = parser.parse_args()

    split(args.input_file, args.out_directory, args.verbose)

    

if __name__ == "__main__":
    main()