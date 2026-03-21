p='data/raw/Graceful_Degradation.raw.txt'
s=open(p, encoding='utf-8').read()
idx=576
context=s[idx-20:idx+20]
print('context:', context)
for i,ch in enumerate(context):
    print(i, repr(ch), ord(ch))
print('problem char repr:', repr(s[idx]))
print('ord:', ord(s[idx]))