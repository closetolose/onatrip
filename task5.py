n = int(input())
phones = []
for _ in range(n):
    s, a = map(int, input().split())
    phones.append((s, a))

events = []
for i, (s, a) in enumerate(phones):
    events.append((s, i, 0))   # 0 = standby
    events.append((a, i, 1))   # 1 = active

events.sort()

ranked = [False] * n
rank = [0] * n
front = 1
back = n
last_idx = -1
last_rank = 0

for value, idx, mode in events:
    if ranked[idx]:
        continue
    if mode == 0:
        rank[idx] = front
        front += 1
    else:
        rank[idx] = back
        back -= 1
    ranked[idx] = True
    last_idx = idx
    last_rank = rank[idx]

below = sum(1 for i in range(n) if rank[i] > last_rank)

print(last_idx + 1, below)
