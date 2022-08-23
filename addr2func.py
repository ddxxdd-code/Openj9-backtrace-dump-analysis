# This is a python file for converting offsets from utput of backtrace to 
# human-readable function names and lines
# Created by Dedong Xie on 2022-05-24
import os
import io
import sys

# This is a script that will take the first argument as file name
# Then will parse the content in the output file line by line
# Lines that are not / started are printed unchanged
# lines started with / will be parsed to get dynamic lib and offset separately

# A dict to store callsite-function pairs
# The key is the callsite, including file + line
# The value is a list containing the translated line of code 
# and function prototype
funcDict = {}

# A list of prefix to be removed in call line part from add3line output
remove_prefix_list = [
    "/mnt/nvme/dedong2022/openj9_jdk/jdk_home/openj9-openjdk-jdk17-backtrace",
    "/usr/include/c++/7"
    ]

# A function that takes a line of backtrace as input
# outputs the translated "line of code ; function prototype" to stdout
# returns None
def translate(line: str, f:io.IOBase) -> None:
    start_bracket = line.find('(')
    end_bracket = line.find(')')
    target = line[:start_bracket]+line[start_bracket+1:end_bracket]
    if target in funcDict:
        # print(funcDict[target][0] + "; " + funcDict[target][1])
        f.write(funcDict[target][0] + "; " + funcDict[target][1] + " <- " + funcDict[target][2])
        f.write('\n')
    else:
        # offset = line[start_bracket+1:end_bracket]
        # offset_int = int(offset[offset.find('+'):], 16)
        # stream = os.popen("addr2line -e " + line[:start_bracket] + " -f -C " + offset[:offset.find('+')] + "+" + hex(offset_int-3))
        offset = line[start_bracket+1:end_bracket]
        stream = os.popen("addr2line -e " + line[:start_bracket] + " -f -C " + offset)
        file_line = line[:start_bracket]
        file_line = file_line[len("/mnt/nvme/dedong2022/openj9_jdk/jdk_home/openj9-openjdk-jdk17-backtrace/build/linux-x86_64-server-release/images/jdk/lib/default"):]
        #file_line = file_line[len("/home/x/Desktop/dedong_2022_summer/jdk_home/openj9-openjdk-jdk17-backtrace/build/linux-x86_64-server-release/images/jdk/lib/default"):]
        output = stream.readlines()
        code = output[0]
        line_called = output[1]
        file_offset = file_line + '{' + offset + '}'
        # print(line_called[:-1] + "; " + code[:-1])
        for prefix in remove_prefix_list:
            if line_called.startswith(prefix):
                line_called = line_called[len(prefix):]
        # funcDict[target] = [line_called[:-1], code[:-1]]
        funcDict[target] = [line_called[:-1], code[:-1], file_offset]
        # f.write(line_called[:-1] + "; " + code[:-1])
        f.write(line_called[:-1] + "; " + code[:-1] + " <- " + file_offset)
        # print(line_called[:-1] + "; " + code[:-1] + " <- " + file_offset)
        f.write('\n')

if __name__ == "__main__":
    # This is the first part of getting and opening the input file
    if len(sys.argv) != 3:
        print("WRONG number of arguments. Call by \"python addr2func input_file out_prefix\"")
        sys.exit(1)
    filename = sys.argv[1]
    sys.stderr.write("reading from " + filename + "\n")
    sys.stderr.flush()
    input = open(filename, "r")
    # allocList is a list in which each element is a tuple
    # Each typle consists of heapAllocSize and 
    # a list of all backtraces of the callsite
    methodList = []
    allocList = []
    heapAllocSize = 0
    methodNumber = 0
    callBackTrace = []
    for line in input:
        # print(line)
        if line[0] == 'M':
            # Start of a method
            left_bracket = line.find('[')
            right_bracket = line.find(']')
            methodNumber = int(line[left_bracket+1:right_bracket])
        elif line[0:4] == "=== ":
            # End of a method
            if heapAllocSize != 0:
                allocList.append((heapAllocSize, callBackTrace))
            methodList.append((methodNumber, allocList))
            heapAllocSize = 0
            allocList = []
            callBackTrace = []
        elif line[0] == '/':
            # a back trace
            callBackTrace.append(line)
        elif line[0] == 'H':
            # Start of a back trace
            # Put previous back trace to allocList
            if heapAllocSize != 0:
                allocList.append((heapAllocSize, callBackTrace))
            callBackTrace = []
            left_bracket = line.find('[')
            right_bracket = line.find(']')
            heapAllocSize = int(line[left_bracket+1:right_bracket])
    # Sort reversly to get the largest entries
    file_out_prefix = sys.argv[2]
    for i in ["-1", "3", "5"]:
        if i != "-1":
            out_filename = file_out_prefix + "_" + i + ".txt"
            file_out = open(out_filename, "w")
            for method in methodList:
                if len(method[1]) == 0:
                    continue
                file_out.write("Method " + str(method[0]) + ": \n")
                allocList = method[1]
                allocList.sort(key=lambda x: x[0], reverse=True)
                for alloc in allocList[:int(i)]:
                    file_out.write("Heap allocated [" + str(alloc[0]) + "] bytes\n")
                    for line in alloc[1]:
                        translate(line, file_out)
                    file_out.write("End of alloc call\n")
        else:
            out_filename = file_out_prefix + ".txt"
            file_out = open(out_filename, "w")
            for method in methodList:
                if len(method[1]) == 0:
                    continue
                file_out.write("Method " + str(method[0]) + ": \n")
                allocList = method[1]
                allocList.sort(key=lambda x: x[0], reverse=True)
                for alloc in allocList:
                    file_out.write("Heap allocated [" + str(alloc[0]) + "] bytes\n")
                    for line in alloc[1]:
                        translate(line, file_out)
                    file_out.write("End of alloc call\n")
