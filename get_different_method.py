# This is a python file for converting various method call stack
# leave only the different calls
# Created by Dedong Xie on 2022-05-30
import os
import sys
from typing import List

def in_list(lst:List, item:List, size:int) -> bool:
    for i in lst:
        diff = False
        if len(i[1]) == len(item):
            for j in range(len(i)):
                if i[1][j] != item[j]:
                    diff = True
                    break
            if diff == False:
                i[0] += size
                return True
    return False
if len(sys.argv) > 2:
	threshold = int(sys.argv[2])
elif len(sys.argv) == 2:
	threshold = 0
else:
	print("usage: get_different_method.py <filename> OR get_different_method.py <filename> <threshold>")
	exit(1)
filename = sys.argv[1]
input = open(filename, "r")
callsite_list = []
call_stack = []
heapAllocSize = 0
for line in input:
    if line[0] == '=':
        if not in_list(callsite_list, call_stack, heapAllocSize):
            callsite_list.append([heapAllocSize, call_stack])
        call_stack = []
    elif line[0] == '/':
        call_stack.append(line)
    elif line[0] == 'C':
        left_bracket = line.find('[')
        right_bracket = line.find(']')
        heapAllocSize = int(line[left_bracket+1:right_bracket])
counter = 0
callsite_list.sort(key=lambda x: x[0], reverse=True)
for call in callsite_list:
	if call[0] >= threshold:
		print(f"Call {counter} allocated [{call[0]}] bytes")
		for line in call[1]:
		    print(line, end='')
		print("=== End ===")
		counter += 1
