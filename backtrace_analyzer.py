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

def main():
    parser = argparse.ArgumentParser()
    # Required arguments:
    parser.add_argument("input_file", type=str, help="name of the input file")
    parser.add_argument("executable_file_path", type=str, help="path to target executable file in the form /DIR/file.so")
    # Optional arguments
    parser.add_argument("-o", "--output-file", type=str, help="name of the output file, default to <inputFile>_translated_callsites.txt")
    parser.add_argument("-t", "--translation-only", action="store_true", help="set to only translates offsets do no call site find")
    parser.add_argument("-c", "--callsite-only", action="store_true", help="set to only keep the line of callsite in all back traces")
    parser.add_argument("-b", "--batch-size", type=int, help="integer for batch size of input to addr2line")
    parser.add_argument("-kp", "--keep-prefix", action="store_true", help="set to keep prefix in translated lines")
    parser.add_argument("-p", "--prefix", type=str, help="common prefix to be removed from translated lines")
    parser.add_argument("-v", "--verbose", action="store_true", help="set to run in verbose mode")

    args = parser.parse_args()

    if args.verbose: sys.stderr.write("reading from " + args.input_file + "\n")
    with open(args.input_file, "r") as input:
        regionList, offsetList = read_regions(input)

    if args.verbose:
        sys.stderr.write("Total regions: " + str(len(regionList)) + "\n")
        sys.stderr.write("Total offsets: " + str(len(offsetList)) + "\n")

    pathPrefix = args.prefix if args.prefix else '/'.join(args.executable_file_path.split('/')[:-4]) + "/vm/runtime/compiler/../../../../.."
    prefixLength = len(pathPrefix)
    if args.verbose and not args.keep_prefix: sys.stderr.write("prefix to be removed from translated lines: " + pathPrefix + "\n")

    if args.batch_size:
        translationTable = {}
        i = 0
        step = args.batch_size
        for i in range(0, len(offsetList), step):
            if args.verbose: sys.stderr.write("translating " + str(i) + " to " + str(i+step) + " of all offsets\n")
            translationTable = build_translation_table(args.executable_file_path, offsetList[i:i+step], translationTable, 0 if args.keep_prefix else prefixLength)
    else:
        if args.verbose: sys.stderr.write("translating all offsets\n")
        translationTable = build_translation_table(args.executable_file_path, offsetList, {}, 0 if args.keep_prefix else prefixLength)
    
    if args.verbose: sys.stderr.write("translating callsites\n")
    regionList = get_translated_callsites(regionList, translationTable, args.translation_only, args.callsite_only)
    
    fileOut = args.output_file if args.output_file else args.inputFile[:args.inputFile.find('.')]+"_translated_callsites.txt"
    if args.verbose: sys.stderr.write("writing to output file " + fileOut + "\n")
    with open(fileOut, "w") as output:
        write_results(regionList, output)
    if args.verbose: sys.stderr.write("finished writing to file " + fileOut + "\nprogram finished\n")

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

def get_callsite(backTraceList, callsiteOnly):
    trimmed = backTraceList
    for i in range(1, len(backTraceList)):
        if (backTraceList[i][1].find("/omr/") != -1 or backTraceList[i][1].find("/openj9/") != -1) \
            and (catch_line(backTraceList[i][1]) or not skip_line(backTraceList[i][1])):
            trimmed = [backTraceList[i]] if callsiteOnly else backTraceList[:i+1]
            if i < len(backTraceList) - 2:
                trimmed.append([backTraceList[i+1][0], ""])
            return trimmed
    return trimmed

# From list of offsets, build dict to translate from offset to lines
def build_translation_table(executableFilePath, offsetList, funcDict, prefixLength):
    args = ["addr2line", "-e", executableFilePath, "-f", "-C"]
    args += offsetList
    output = subprocess.run(args, atdout=subprocess.PIPE, universal_newlines=True).stdout
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
def get_translated_callsites(regionList, funcDict, translateOnly, callsiteOnly):
    translatedRegionList = []
    for methodCompiled, regionType, constructorBackTrace, allocations in regionList:
        regionBackTraceList = []
        for offset in constructorBackTrace:
            regionBackTraceList.append(funcDict[offset])
        allocationList = []
        for allocationSize, allocationBackTraceOffsets in allocations:
            allocationBackTraceList = []
            for offset in allocationBackTraceOffsets:
                # Here, funcDict's value is a pair of function name and line
                # We assume offset is a key in the dict
                allocationBackTraceList.append(funcDict[offset])
                # Find callsite from translated call back traces
                if not translateOnly: allocationBackTraceList = get_callsite(allocationBackTraceList, callsiteOnly)
            allocationList.append([allocationSize, allocationBackTraceList])
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
    main()