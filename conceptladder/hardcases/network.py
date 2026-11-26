import ipaddress

from . import alternatives, numeric


RFC_TCP = "https://www.rfc-editor.org/rfc/rfc9293.html"
RFC_IP = "https://www.rfc-editor.org/rfc/rfc791.html"
RFC_DNS = "https://www.rfc-editor.org/rfc/rfc1035.html"


def tcp_reassembly(r):
    base = r.randrange(12000, 87000)
    a, b, c, gap = (r.randrange(8, 24) for _ in range(4))
    def ack(segments, start):
        intervals = [(seq, seq + length + int(fin)) for seq, length, fin in segments]
        cur = start
        while True:
            next_cur = max([cur] + [end for begin, end in intervals if begin <= cur < end])
            if next_cur == cur:
                break
            cur = next_cur
        return cur % (2**32)
    cases = [
        (base, [(base, a, False)], "one in-order segment"),
        (base, [(base + a + gap, b, False), (base, a, False)], "an out-of-order segment followed by an earlier segment"),
        (base, [(base + a + gap, b, False), (base, a + 2, False), (base + a, gap, False), (base + a + gap + b, c, False)], "overlap, hole filling, and another queued segment"),
    ]
    wrap = 2**32 - r.randrange(15, 60)
    wa, wb, wc = r.randrange(8, 16), r.randrange(9, 18), r.randrange(4, 11)
    wrapped = [
        ((wrap + wa) % 2**32, wb, False),
        (wrap, wa, False),
        ((wrap + wa + wb) % 2**32, wc, True),
    ]
    def wrap_ack():
        unwrapped = [(wrap + ((seq - wrap) % (2**32)), length, fin) for seq, length, fin in wrapped]
        return ack(unwrapped, wrap)
    questions = []
    for i, (start, segments, title) in enumerate(cases):
        shown = "; ".join(f"seq={s}, payload={n}B, FIN={int(f)}" for s, n, f in segments)
        prompt = f"TCP reassembly ({title}). Receiver initially expects byte {start}. In arrival order: {shown}. All segments are in-window; ACK is cumulative. What ACK number is sent after the last segment?"
        answer = ack(segments, start)
        questions.append((prompt, *numeric(answer, delta=1 if i == 0 else 2)))
    prompt = f"TCP sequence numbers wrap mod 2^32. Receiver initially expects {wrap}. Segments arrive in this order: " + "; ".join(f"seq={s}, payload={n}B, FIN={int(f)}" for s, n, f in wrapped) + ". All segments are accepted in-window, and FIN consumes one sequence number. What is the final cumulative ACK (unsigned decimal)?"
    answer = wrap_ack()
    wrap_choices = [str((answer + offset) % 2**32) for offset in (-1, 1, -2, 2, -3, 3, -4, 4, -5, 5) if len(str((answer + offset) % 2**32)) == len(str(answer))]
    questions.append((prompt, *alternatives(answer, wrap_choices)))
    return ("net-hard", "tcp-reassembly", RFC_TCP, questions)


def tcp_window(r):
    cwnd = r.randrange(4200, 9500, 100)
    rwnd = r.randrange(3500, 9800, 100)
    flight = r.randrange(1500, min(cwnd, rwnd) - 500, 100)
    def left(c, w, f):
        return max(0, min(c, w) - f)
    questions = []
    prompt = f"TCP sender has cwnd={cwnd}B, peer-advertised usable rwnd={rwnd}B, and {flight}B outstanding. No SWS/Nagle/pacing constraint. Maximum additional NEW data bytes allowed now?"
    val = left(cwnd, rwnd, flight)
    questions.append((prompt, *numeric(val, delta=100)))
    acked = r.randrange(2, 9) * 100
    prompt = f"TCP sender has cwnd={cwnd}B, rwnd={rwnd}B, and {flight}B in flight. A cumulative ACK covers {acked} previously unacknowledged bytes, with no other changes. Maximum NEW data bytes sendable after processing it?"
    val = left(cwnd, rwnd, flight-acked)
    questions.append((prompt, *numeric(val, delta=100)))
    lower = min(cwnd, rwnd)
    smaller = max(500, lower-r.randrange(100, 1000, 100))
    flight3 = lower-r.randrange(100, 300, 100)
    prompt = f"TCP had cwnd={cwnd}B, rwnd={rwnd}B, and {flight3}B outstanding. Before new sends, receiver updates rwnd to {smaller}B without ACKing more bytes. Ignore probes and retransmits. How many NEW data bytes are currently permitted?"
    val = left(cwnd, smaller, flight3)
    questions.append((prompt, *numeric(val, delta=100 if val else 1)))
    flight4 = r.randrange(800, 2200, 100)
    first_ack, second_ack = r.randrange(100, 400, 100), r.randrange(100, 400, 100)
    new_cwnd = r.randrange(1800, 4900, 100)
    new_rwnd = r.randrange(1800, 4900, 100)
    prompt = f"TCP starts with {flight4}B in flight, cwnd={cwnd}B, rwnd={rwnd}B. Two cumulative ACK advances newly acknowledge {first_ack}B and then {second_ack}B (nonoverlapping). cwnd then becomes {new_cwnd}B and rwnd {new_rwnd}B. No data sent during these updates. Maximum NEW bytes sendable now?"
    val = left(new_cwnd, new_rwnd, flight4-first_ack-second_ack)
    questions.append((prompt, *numeric(val, delta=100)))
    return ("net-hard", "tcp-send-window", RFC_TCP, questions)


def route(r):
    ip = ipaddress.IPv4Address(f"10.{r.randrange(20,220)}.{r.randrange(20,220)}.{r.randrange(40,210)}")
    def subnet(p):
        return str(ipaddress.ip_network(f"{ip}/{p}", strict=False))
    def other(p):
        candidate = ipaddress.IPv4Address(int(ip) ^ (1 << (32-p)))
        return str(ipaddress.ip_network(f"{candidate}/{p}",strict=False))
    def make(level):
        entries = [("0.0.0.0/0", 10, "if00"), (subnet(8), 30, "if01")]
        if level >= 2:
            entries += [(subnet(16), 40, "if02"), (other(16), 1, "if03"), (subnet(24), 80, "if04")]
        if level >= 3:
            entries += [(subnet(24), 5, "if05"), (other(24), 1, "if06")]
        if level >= 4:
            entries += [(subnet(27), 300, "if07"), (subnet(26), 1, "if08"), (other(27), 1, "if09")]
        labels = list(range(10))
        r.shuffle(labels)
        entries = [(prefix, metric, f"if{labels[int(iface[2:])]:02d}") for prefix, metric, iface in entries]
        r.shuffle(entries)
        matched = [(ipaddress.ip_network(prefix).prefixlen, -metric, iface) for prefix,metric,iface in entries if ip in ipaddress.ip_network(prefix)]
        answer = max(matched) [2]
        prompt = f"IPv4 route lookup for destination {ip}. Choose longest matching prefix; if equally long, choose lowest metric (no ECMP). Routes (prefix, metric, interface): " + "; ".join(f"({a},{b},{c})" for a,b,c in entries) + ". Which interface is selected?"
        options = [f"if{x:02d}" for x in range(10) if f"if{x:02d}" != answer]
        r.shuffle(options)
        return (prompt,*alternatives(answer,options))
    return ("net-hard","ipv4-lpm","https://www.rfc-editor.org/rfc/rfc4632.html",[make(i) for i in range(1,5)])


def ipv4_frag(r):
    payload = r.randrange(1700, 3900, 8)
    mtu = r.choice([576, 620, 700, 980, 1260])
    full = ((mtu-20)//8)*8
    chunks = []
    pos=0
    while pos < payload:
        n=min(full,payload-pos)
        chunks.append((pos//8,n,int(pos+n < payload)))
        pos+=n
    questions=[]
    q1=f"IPv4 datagram has 20-byte header, payload={payload}B, outgoing MTU={mtu}B, DF=0. Every non-final fragment payload length must be divisible by 8. How many fragments result?"
    questions.append((q1,*numeric(len(chunks))))
    q2=f"Same IPv4 constraints: 20-byte header, MTU={mtu}B, original payload={payload}B, DF=0, initial fragment offset 0. What is the IPv4 fragment-offset FIELD (in 8-byte units) of the second emitted fragment?"
    questions.append((q2,*numeric(chunks[1][0],delta=1)))
    q3=f"IPv4 header=20B, payload={payload}B, egress MTU={mtu}B, DF=0, 8-byte alignment of non-final chunks. How many payload bytes are in the LAST emitted fragment?"
    questions.append((q3,*numeric(chunks[-1][1],delta=8)))
    oldoffset = r.randrange(10,90)
    fragment_len = full * 2
    smaller_mtu = r.choice([340, 420, 500])
    smaller_payload = ((smaller_mtu-20)//8)*8
    emitted = []
    at=0
    while at < fragment_len:
        length=min(smaller_payload,fragment_len-at)
        emitted.append(oldoffset+at//8)
        at+=length
    q4=f"A router receives an IPv4 fragment with fragment-offset field={oldoffset}, payload={fragment_len}B and MF=1, then refragments it for MTU={smaller_mtu}B (IPv4 header 20B, no options, DF=0). What is the offset FIELD of the LAST outgoing subfragment? Offsets are in 8-byte units."
    questions.append((q4,*numeric(emitted[-1],delta=1)))
    return ("net-hard","ipv4-fragment-offset",RFC_IP,questions)


def cidr(r):
    a, b = r.randrange(10,220),r.randrange(10,220)
    x = ipaddress.IPv4Address(f"172.{a}.{b}.{r.randrange(2,253)}")
    prefix=r.choice([19,20,21,22,23,24,25,26,27,28])
    net=ipaddress.ip_network(f"{x}/{prefix}",strict=False)
    questions=[]
    q1=f"For IPv4 address {x}/{prefix}, what is the LAST OCTET of the subnet network address?"
    questions.append((q1,*numeric(int(net.network_address)&255)))
    q2=f"For IPv4 address {x}/{prefix}, what is the LAST OCTET of the subnet broadcast address?"
    questions.append((q2,*numeric(int(net.broadcast_address)&255)))
    q3=f"An IPv4 subnet {net} has conventional network and broadcast addresses excluded. How many usable host addresses does it have?"
    questions.append((q3,*numeric(net.num_addresses-2,delta=2)))
    r1=ipaddress.IPv4Address(f"10.{a}.{b}.{r.randrange(2,120)}")
    r2=ipaddress.IPv4Address(int(r1) ^ (1 << r.randrange(5,18)) ^ (1 << r.randrange(0,5)))
    distance=int(r1)^int(r2)
    p=32-distance.bit_length()
    q4=f"Find the MOST SPECIFIC single IPv4 CIDR prefix that contains BOTH {r1} and {r2}. Return only the prefix length (number after /)."
    questions.append((q4,*numeric(p)))
    return ("net-hard","ipv4-cidr-boundaries","https://www.rfc-editor.org/rfc/rfc4632.html",questions)


def dns_ttl(r):
    base=r.randrange(1000,5000)
    tc=r.randrange(35,85)
    ta=r.randrange(50,120)
    check_time = base + ta - r.randrange(6,20)
    q1=f"A DNS resolver cached an A record at time t={base} with TTL={ta}s. At time t={check_time}, how many seconds of TTL remain, assuming it has not been refreshed?"
    remain=(base+ta)-check_time
    questions=[(q1,*numeric(remain))]
    check=base+r.randrange(30,100)
    q2=f"At time t={base}, a resolver caches a CNAME with TTL {tc}s and its target A record with TTL {ta}s. No refresh occurs. At t={check}, how many of these TWO cached records have expired? (Expiry time itself counts as expired.)"
    count=int(check>=base+tc)+int(check>=base+ta)
    questions.append((q2,*numeric(count)))
    refresh=base+min(tc,ta)+r.randrange(4,12)
    inspect=refresh+r.randrange(20,100)
    c_exp=base+tc
    a_exp=refresh+ta
    q3=f"Resolver caches CNAME (TTL={tc}s) and target A (TTL={ta}s) at t={base}. It refreshes ONLY the A record at t={refresh} with a new TTL={ta}s; CNAME is NOT refreshed. At t={inspect}, how many of these two cached records have expired?"
    count=int(inspect>=c_exp)+int(inspect>=a_exp)
    questions.append((q3,*numeric(count)))
    ts=[r.randrange(30,115) for _ in range(4)]
    refresh_at=base+r.randrange(45,85)
    now=base+r.randrange(96,180)
    expires=[base+ts[0],base+ts[1],refresh_at+ts[2],base+ts[3]]
    q4=f"A DNS resolver has three consecutive CNAME records and one final A record, all cached at t={base}, with TTLs {ts[0]},{ts[1]},{ts[2]},{ts[3]} seconds (in that order). At t={refresh_at} ONLY the third CNAME is replaced with a fresh record of TTL {ts[2]} seconds. At t={now}, how many of the FOUR records have expired? Do not assume expiration of one automatically refreshes another."
    answer=sum(now>=exp for exp in expires)
    questions.append((q4,*numeric(answer)))
    return ("net-hard","dns-ttl-chain",RFC_DNS,questions)


BUILDERS = [tcp_reassembly, tcp_window, route, ipv4_frag, cidr, dns_ttl]
