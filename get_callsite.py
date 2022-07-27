# Dedong Xie
# 2022-06-20
# get_callsite
# aggregate to get all callsite used
# read from output of translated raw
# print different callsite in each method.

import sys
from typing import List

# def insert(root, val):
#     if len(val) == 0:
#         return root
#     if val[0] in root:
#         root[val[0]] = insert(root[val[0]], val[1:])
#     else:
#         root[val[0]] = insert({}, val[1:])
#     return root
# # def insert(root, val):
# #     if len(val) == 0:
# #         if root != {}:
# #             root["*"] = {}
# #             return root
# #         return {}
# #     if val[0] in root:
# #         root[val[0]] = insert(root[val[0]], val[1:])
# #     else:
# #         root[val[0]] = insert({}, val[1:])
# #     return root

# trie = {}
# common_branch_nodes = set([])
# def trie_find_common_branch(root, route):
#     if root == None:
#         return
#     if len(root) > 1:
#         for node in route:
#             common_branch_nodes.add(node)
#     for i in root:
#         trie_find_common_branch(root[i], route + [i])

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

skip_list = ["allocate", "TypedAllocator", "heap_allocator"]
catch_list = ["TR_LoopVersioner::emitExpr", 
"RematTools::walkTreesCalculatingRematSafety", 
"J9::Compilation::verifyCompressedRefsAnchors", 
"TR_UseDefInfo::dereferenceDef", 
"TR_GlobalRegisterAllocator::findLoopsAndCorrespondingAutos",
"TR_GlobalRegisterAllocator::markAutosUsedIn"]
def skip_line(line: str) -> bool:
    for seg in skip_list:
        if line.find(seg) != -1:
            return True
    return False

def catch_line(line: str) -> bool:
    for seg in catch_list:
        if line.find(seg) != -1:
            return True
    return False

filename = sys.argv[1]
# input = open(filename, "r")
# call_stack = []

# for line in input:
#     if line[0] == 'E':
#         trie = insert(trie, call_stack)
#         call_stack = []
#     elif line[0] == '/':
#         call_stack.append(line)

# common_branch_nodes = set([])
# trie_find_common_branch(trie, [])

# for common_node in common_branch_nodes:
#     print(common_node, end='')
def get_callsite(lst:List) -> List:
    trimmed = lst
    for i in range(1, len(lst)):
        # if lst[i].find("OMR::Compilation::compile()") != -1 or lst[i].find("OMR::Optimizer::performOptimization") != -1:
        #     trimmed = lst[:i]
        #     if i < len(lst) - 1:
        #         cut = lst[i+1].find(";")
        #         trimmed.append(lst[i+1][:cut]+'\n')
        #     return trimmed
        if (lst[i].find("/omr/") != -1 or lst[i].find("/openj9/") != -1) and (catch_line(lst[i]) or not skip_line(lst[i])):
            trimmed = lst[:i+1]
            if i < len(lst) - 2:
                cut = lst[i+1].find(";")
                trimmed.append(lst[i+1][:cut]+'\n')
            return trimmed
    return trimmed
# lst[i].find("/dedong_2022_summer/") != -1 and 

input = open(filename, "r")
method_list = []
callsite_list = []
call_stack = []
heap_alloc_size = 0
method_header = None
for line in input:
    if line[0] == 'E':
        callsite = get_callsite(call_stack)
        if not in_list(callsite_list, callsite, heap_alloc_size):
            callsite_list.append([heap_alloc_size, callsite])
        call_stack = []
    elif line[0] == '/':
        call_stack.append(line)
    elif line[0] == 'H':
        left_bracket = line.find('[')
        right_bracket = line.find(']')
        heap_alloc_size = int(line[left_bracket+1:right_bracket])
    elif line[0] == 'M':
        if callsite_list != []:
            callsite_list.sort(key=lambda x: x[0], reverse=True)
            method_total = sum(call[0] for call in callsite_list)
            method_list.append([method_header, callsite_list, method_total])
            callsite_list = []
        method_header = line
if callsite_list != []:
    callsite_list.sort(key=lambda x: x[0], reverse=True)
    method_total = sum(call[0] for call in callsite_list)
    method_list.append([method_header, callsite_list, method_total])

method_list.sort(key=lambda entry: entry[2], reverse=True)
for header, calls, total_alloc in method_list:
    print(header, end='')
    print(f"total allocation: [{total_alloc}]")
    counter = 0
    for call in calls:
        print(f"Call {counter} allocated [{call[0]}] bytes")
        for line in call[1]:
            print(line, end='')
        print("=== End ===")
        counter += 1