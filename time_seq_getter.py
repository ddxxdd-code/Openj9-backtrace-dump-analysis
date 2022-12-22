# From alloctraces to create file of only region sizes
# Dedong Xie 2022-12-22
import sys
import argparse

def get_time_seq(input_file, output_file, verbose):
    if verbose: sys.stderr.write("reading from " + input_file + "\n")
    with open(input_file, "r") as input:
        with open(output_file, "w+") as output:
            line = input.readline()
            while line:
                if line[0:2] in ["H ", "S "]:
                    output.write(line)
                line = input.readline()

    if verbose: sys.stderr.write("finished writing to file " + output_file + "\nprogram finished\n")


def main():
    parser = argparse.ArgumentParser()
    # Required arguments:
    parser.add_argument("input_file", type=str, help="name of the input file")
    parser.add_argument("out_file", type=str, default="time_seq.txt", help="name of the output file, default to time_seq.txt")
    parser.add_argument("-v", "--verbose", action="store_true", help="set to run in verbose mode")

    args = parser.parse_args()

    get_time_seq(args.input_file, args.out_file, args.verbose)

    

if __name__ == "__main__":
    main()