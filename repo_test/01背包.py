a,b = map(int,input().split())
wl=[0]
cl=[0]
f = [[0 for i in range(b+1)]for j in range(a+1)]

for i in range(a):
    w,c = map(int,input().split())
    wl.append(w)
    cl.append(c)
for i in range(1,a+1):
    for j in range(1,b+1):
        if j<wl[i]:
            f[i][j]=f[i-1][j]
        else:
            f[i][j]=max(f[i-1][j-wl[i]]+cl[i],f[i-1][j])
ans=0
for i in range(1,a+1):
    for j in range(1,b+1):
        ans = max(f[i][j],ans)

print(ans)