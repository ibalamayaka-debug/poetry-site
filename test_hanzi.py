import sys
print("Loading HanziConv...")
from hanziconv import HanziConv
print("Converting...")
res = HanziConv.toTraditional('静夜思')
print("Result:", res)
