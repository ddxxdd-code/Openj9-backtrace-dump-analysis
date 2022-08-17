# Analyzing tool for dumped back traces of reion allocations
# Dedong Xie 20220815
# Phase 1: implement translation
# Phase 2: implement call site find
# phase 3: implement parser of options

# Input form: 
# python3 backtrace_analyzer.py <input file> <path to libj9jit29.so> <output file>
import os
import subprocess
import io
import sys

prefixLength = len("/mnt/nvme/dedong2022/jdk/openj9-openjdk-jdk17")

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

def get_callsite(backTraceList):
    trimmed = backTraceList
    for i in range(1, len(backTraceList)):
        if (backTraceList[i][1].find("/omr/") != -1 or backTraceList[i][1].find("/openj9/") != -1) and (catch_line(backTraceList[i][1]) or not skip_line(backTraceList[i][1])):
            trimmed = backTraceList[:i+1]
            if i < len(backTraceList) - 2:
                trimmed.append(backTraceList[i+1][1]+'\n')
            return trimmed
    return trimmed

# From list of offsets, build dict to translate from offset to lines
def build_translation_table(executableFilePath, offsetList, funcDict):
    args = ["addr2line", "-e", executableFilePath, "-f", "-C"]
    args += offsetList
    output = subprocess.run(args, capture_output=True, text=True).stdout
    output = output.split('\n')[:-1]
    if len(output) != 2 * len(offsetList):
        print("Translation error")
        return {}
    for i in range(len(offsetList)):
        funcDict[offsetList[i]] = [output[2*i], output[2*i+1][prefixLength:]]
    return funcDict

# Read from formatted lines produce list of all regions and all offsets of interest
def read_regions(file):
    regionList = []
    offsetSet = set()
    region = []
    allocationList = []
    line = file.readline()
    while line:
        if line[0].isalpha():
            if allocationList != []:
                allocationList.sort(reverse=True, key=lambda x: x[0])
                region.append(allocationList)
                regionList.append(region)
                allocationList = []
            region = []
            # Start of header for a region
            region.append(line)
            line = file.readline()
            if line[0] == '0':
                region.append("S")
            else:
                region.append("H")
            constructorOffsets = (line.split())[1:-1]
            region.append(constructorOffsets)
            offsetSet |= set(constructorOffsets)
        else:
            # Allocations in a region
            allocation = (line.split())[:-1]
            allocationSize = int(allocation[0])
            allocationBackTraces = allocation[1:]
            allocationList.append([allocationSize, allocationBackTraces])
            offsetSet |= set(allocationBackTraces)
        line = file.readline()
    if allocationList != []:
        allocationList.sort(key=lambda x: x[0], reverse=True, )
        region.append(allocationList)
        regionList.append(region)
    return regionList, list(offsetSet)

# Translate and get callsites
def get_translated_callsites(regionList, funcDict):
    translatedRegionList = []
    for methodCompiled, regionType, constructorBackTrace, allocations in regionList:
        regionBackTraceList = []
        for offset in constructorBackTrace:
            regionBackTraceList.append([funcDict[offset]])
        allocationList = []
        for allocationSize, allocationBackTraceOffsets in allocations:
            allocationBackTraceList = []
            for offset in allocationBackTraceOffsets:
                allocationBackTraceList.append([funcDict[offset]])
                # Here, funcDict's value is a pair of function name and line
                # We care about the line.
                allocationBackTraceList = get_callsite(allocationBackTraceList)
            allocationList.append(allocationSize, allocationBackTraceList)
        translatedRegionList.append([methodCompiled, regionType, regionBackTraceList, allocationList])
    return translatedRegionList

# Write to output file of translated regions
def write_results(regionList, file):
    for methodCompiled, regionType, constructorBackTrace, allocations in regionList:
        file.write(regionType + ": " + methodCompiled)
        for function, line in constructorBackTrace:
                file.write(line[:-1] + "; " + function + '\n')
        for allocationSize, allocationBackTraceOffsets in allocations:
            file.write("Allocated " + str(allocationSize) + " bytes\n")
            for function, line in allocationBackTraceOffsets:
                file.write(line[:-1] + "; " + function + '\n')
        file.write("=== End of a region ===\n")

if __name__ == "__main__":
    fileName = sys.argv[1]
    sys.stderr.write("reading from " + fileName + "\n")
    with open(fileName, "r") as input:
        regionList, offsetList = read_regions(input)
    translationTable = {}
    sys.stderr.write("Total regions: " + str(len(regionList)) + "\n")
    sys.stderr.write("Total offsets: " + str(len(offsetList)) + "\n")
    i = 0
    step = 10000
    for i in range(0, len(offsetList), step):
        translationTable = build_translation_table(sys.argv[2]+"libj9jit29.so", offsetList[i:i+step], translationTable)
    regionList = get_translated_callsites(regionList, translationTable)
    fileOut = sys.argv[3]
    with open(fileOut, "w") as output:
        write_results(regionList, output)
    