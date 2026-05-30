import sys
print("Loading opencc...")
try:
    from opencc import OpenCC
    cc = OpenCC('t2s')
    print("Converting...")
    res = cc.convert('靜夜思')
    print("Result:", res)
except Exception as e:
    print("Error:", e)
