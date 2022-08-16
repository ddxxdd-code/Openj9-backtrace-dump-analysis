# Analyzing tool for dumped back traces of reion allocations
# Dedong Xie 20220815
# Phase 1: implement translation
# Phase 2: implement call site find
# phase 3: implement parser of options

# Input form: 
# python3 backtrace_analyzer.py <input file> <path to libj9jit29.so> <output file>
import os
import io
import sys

prefixLength = len("/mnt/nvme/dedong2022/jdk/openj9-openjdk-jdk17")

# From list of offsets, build dict to translate from offset to lines
def build_translation_table(executableFilePath, offsetList, funcDict):
    stream = os.popen("addr2line -e " + executableFilePath + " -f -C " + " ".join(offsetList))
    output = stream.readlines()
    if len(output) != 2 * len(offsetList):
        print("Translation error")
        return {}
    for i in range(len(offsetList)):
        funcDict[offsetList[i]] = [output[2*i], output[2*i+1][prefixLength:]]
    return funcDict

# Read from formatted lines produce list of all regions and all offsets of interest
def read_regions(lines):
    regionList = []
    offsetSet = set()
    region = []
    allocationList = []
    index = 0
    while index < len(lines):
        if lines[index][0].isalpha():
            if allocationList != []:
                allocationList.sort(reverse=True, key=lambda x: x[0])
                region.append(allocationList)
                regionList.append(region)
                allocationList = []
            region = []
            # Start of header for a region
            region.append(lines[index])
            index += 1
            if lines[index][0] == '0':
                region.append("S")
            else:
                region.append("H")
            constructorOffsets = (lines[index].split())[1:-1]
            region.append(constructorOffsets)
            offsetSet |= set(constructorOffsets)
        else:
            # Allocations in a region
            allocation = (lines[index].split())[:-1]
            allocationSize = int(allocation[0])
            allocationBackTraces = allocation[1:]
            allocationList.append([allocationSize, allocationBackTraces])
            offsetSet |= set(allocationBackTraces)
        index += 1
    if allocationList != []:
        allocationList.sort(key=lambda x: x[0], reverse=True, )
        region.append(allocationList)
        regionList.append(region)
    return regionList, list(offsetSet)

# Write to output file of translated regions
def write_results(regionList, funcDict, file):
    for methodCompiled, regionType, constructorBackTrace, allocations in regionList:
        file.write(regionType + ": " + methodCompiled)
        for offset in constructorBackTrace:
            try:
                function, line = funcDict[offset]
                file.write(line[:-1] + "; " + function)
            except:
                file.write(offset + " no line found")
        for allocationSize, allocationBackTraceOffsets in allocations:
            file.write("Allocated " + str(allocationSize) + " bytes\n")
            for offset in allocationBackTraceOffsets:
                try:
                    function, line = funcDict[offset]
                    file.write(line[:-1] + "; " + function)
                except:
                    file.write(offset + " no line found\n")
        file.write("=== End of a region ===\n")

if __name__ == "__main__":
    fileName = sys.argv[1]
    sys.stderr.write("reading from " + fileName + "\n")
    input = open(fileName, "r")
    regionList, offsetList = read_regions(input.readlines())
    translationTable = {}
    i = 0
    step = 10
    for i in range(0, len(offsetList), step):
        translationTable = build_translation_table(sys.argv[2]+"libj9jit29.so", offsetList[i:i+step], translationTable)
    fileOut = sys.argv[3]
    output = open(fileOut, "w")
    write_results(regionList, translationTable, output)
    