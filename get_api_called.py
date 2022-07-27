# Dedong Xie
# 2022-06-08
# get_api_called
# aggregate to get all api used
# read from output of translated raw
# print different apis used.

import sys
from typing import List

def in_list(lst:List, item:List, size:int) -> bool:
    for i in lst:
        diff = False
        if len(i[1]) == len(item):
            for j in range(len(item)):
                if i[1][j] != item[j]:
                    diff = True
                    break
            if diff == False:
                i[0] += size
                return True
    return False

def get_api(lst:List) -> List:
    for i in range(1, len(lst)):
        if lst[i].find("/dedong_2022_summer/") != -1:
            return lst[:i+1]
    return []

filename = sys.argv[1]
input = open(filename, "r")
api_list = []
call_stack = []
heapAllocSize = 0
for line in input:
    if line[0] == 'E':
        api_called = get_api(call_stack)
        if not in_list(api_list, api_called, heapAllocSize):
            api_list.append([heapAllocSize, api_called])
        call_stack = []
    elif line[0] == '/':
        call_stack.append(line)
    elif line[0] == 'H':
        left_bracket = line.find('[')
        right_bracket = line.find(']')
        heapAllocSize = int(line[left_bracket+1:right_bracket])
counter = 0
api_list.sort(key=lambda x: x[0], reverse=True)
for call in api_list:
    print(f"Call {counter} allocated {call[0]} bytes")
    for line in call[1]:
        print(line, end='')
    print("=== End ===")
    counter += 1